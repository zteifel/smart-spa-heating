"""Sensor platform for Smart Spa Heating."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SmartSpaHeatingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Spa Heating sensors from config entry."""
    coordinator: SmartSpaHeatingCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        NextHeatingSensor(coordinator, entry),
        HeatingScheduleSensor(coordinator, entry),
        CurrentPriceSensor(coordinator, entry),
        ManualOverrideRemainingSensor(coordinator, entry),
        PlannedTemperatureSensor(coordinator, entry),
    ])


class SmartSpaSensorBase(CoordinatorEntity[SmartSpaHeatingCoordinator], SensorEntity):
    """Base class for Smart Spa Heating sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Spa Heating",
            "manufacturer": "Custom",
            "model": "Smart Spa Heating Controller",
        }


class NextHeatingSensor(SmartSpaSensorBase):
    """Sensor showing next scheduled heating time."""

    _attr_name = "Next Heating"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_heating"

    @property
    def native_value(self) -> datetime | None:
        """Return the next heating time."""
        return self.coordinator.next_heating


class HeatingScheduleSensor(SmartSpaSensorBase):
    """Sensor showing the full heating schedule."""

    _attr_name = "Heating Schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_heating_schedule"

    @property
    def native_value(self) -> str:
        """Return the number of scheduled heating slots."""
        schedule = self.coordinator.schedule
        if not schedule:
            return "No heating scheduled"
        return f"{len(schedule)} slot(s) scheduled"

    @property
    def extra_state_attributes(self) -> dict:
        """Return the schedule as an attribute."""
        schedule = self.coordinator.schedule
        return {
            "schedule": [slot.to_dict() for slot in schedule],
            "slot_count": len(schedule),
        }


class CurrentPriceSensor(SmartSpaSensorBase):
    """Sensor showing current electricity price."""

    _attr_name = "Current Price"
    _attr_icon = "mdi:currency-usd"
    _attr_device_class = SensorDeviceClass.MONETARY

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_current_price"

    @property
    def native_value(self) -> float | None:
        """Return the current price."""
        return self.coordinator.current_price


class ManualOverrideRemainingSensor(SmartSpaSensorBase):
    """Sensor showing remaining time in manual override."""

    _attr_name = "Manual Override Remaining"
    _attr_icon = "mdi:hand-back-left"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_override_remaining"

    @property
    def native_value(self) -> str:
        """Return the remaining override time."""
        if not self.coordinator.manual_override_active:
            return "Inactive"

        end_time = self.coordinator.manual_override_end
        if end_time is None:
            return "Inactive"

        now = dt_util.now()
        remaining = end_time - now

        if remaining.total_seconds() <= 0:
            return "Inactive"

        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def extra_state_attributes(self) -> dict:
        """Return override details."""
        return {
            "active": self.coordinator.manual_override_active,
            "end_time": (
                self.coordinator.manual_override_end.isoformat()
                if self.coordinator.manual_override_end
                else None
            ),
        }


class PlannedTemperatureSensor(SmartSpaSensorBase):
    """Sensor showing planned temperatures over time for ApexCharts visualization."""

    _attr_name = "Planned Temperature"
    _attr_icon = "mdi:chart-timeline-variant"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_planned_temperature"

    @property
    def native_value(self) -> float:
        """Return the current planned temperature."""
        now = dt_util.now()
        for slot in self.coordinator.schedule:
            if slot.start <= now < slot.end and slot.target_temperature is not None:
                return slot.target_temperature
        return self.coordinator.pp_min_temperature

    @property
    def extra_state_attributes(self) -> dict:
        """Return planned temperature timeline for ApexCharts."""
        now = dt_util.now()
        schedule = self.coordinator.schedule
        min_temp = self.coordinator.pp_min_temperature
        max_temp = self.coordinator.pp_max_temperature

        timeline = []

        # Find current or first future slot for initial state
        current_temp = min_temp
        for slot in schedule:
            if slot.start <= now < slot.end and slot.target_temperature is not None:
                current_temp = slot.target_temperature
                break

        timeline.append({
            "time": now.isoformat(),
            "temperature": current_temp,
            "state": "proportional"
        })

        for slot in schedule:
            if slot.end <= now:
                continue
            if slot.target_temperature is None:
                continue

            start_time = max(slot.start, now)

            # Step transition at slot start
            timeline.append({
                "time": start_time.isoformat(),
                "temperature": slot.target_temperature,
                "state": "proportional"
            })

            # Hold until slot end
            timeline.append({
                "time": slot.end.isoformat(),
                "temperature": slot.target_temperature,
                "state": "proportional"
            })

        # End point at 24 hours
        end_time = now + timedelta(hours=24)
        timeline.append({
            "time": end_time.isoformat(),
            "temperature": min_temp,
            "state": "proportional"
        })

        timeline.sort(key=lambda x: x["time"])

        data_series = []
        for point in timeline:
            ts = datetime.fromisoformat(point["time"])
            timestamp_ms = int(ts.timestamp() * 1000)
            data_series.append([timestamp_ms, point["temperature"]])

        return {
            "timeline": timeline,
            "data": data_series,
            "max_temperature": max_temp,
            "min_temperature": min_temp,
            "heating_active": self.coordinator.heating_active,
        }
