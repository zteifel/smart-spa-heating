"""Number platform for Smart Spa Heating."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_PP_MAX_TEMPERATURE,
    CONF_PP_MIN_TEMPERATURE,
    CONF_LOOKAHEAD_HOURS,
    CONF_PRICE_WINDOW_HOURS,
    MIN_MANUAL_OVERRIDE_DURATION,
    MAX_MANUAL_OVERRIDE_DURATION,
    MIN_PP_MAX_TEMPERATURE,
    MAX_PP_MAX_TEMPERATURE,
    MIN_PP_MIN_TEMPERATURE,
    MAX_PP_MIN_TEMPERATURE,
    MIN_LOOKAHEAD_HOURS,
    MAX_LOOKAHEAD_HOURS,
    MIN_PRICE_WINDOW_HOURS,
    MAX_PRICE_WINDOW_HOURS,
)
from .coordinator import SmartSpaHeatingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Spa Heating number entities from config entry."""
    coordinator: SmartSpaHeatingCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        ManualOverrideDurationNumber(coordinator, entry),
        PpMaxTemperatureNumber(coordinator, entry),
        PpMinTemperatureNumber(coordinator, entry),
        LookaheadHoursNumber(coordinator, entry),
        PriceWindowHoursNumber(coordinator, entry),
    ])


class SmartSpaNumberBase(CoordinatorEntity[SmartSpaHeatingCoordinator], NumberEntity):
    """Base class for Smart Spa Heating number entities."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
        config_key: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._config_key = config_key
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Spa Heating",
            "manufacturer": "Custom",
            "model": "Smart Spa Heating Controller",
        }

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        # Update options - the update listener in __init__.py handles recalculation
        new_options = dict(self._entry.options)
        new_options[self._config_key] = value

        self.hass.config_entries.async_update_entry(
            self._entry,
            options=new_options,
        )


class ManualOverrideDurationNumber(SmartSpaNumberBase):
    """Number entity for manual override duration."""

    _attr_name = "Manual Override Duration"
    _attr_icon = "mdi:hand-back-left-outline"
    _attr_native_min_value = MIN_MANUAL_OVERRIDE_DURATION
    _attr_native_max_value = MAX_MANUAL_OVERRIDE_DURATION
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "hours"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_MANUAL_OVERRIDE_DURATION)
        self._attr_unique_id = f"{entry.entry_id}_manual_override_duration"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.manual_override_duration


class PpMaxTemperatureNumber(SmartSpaNumberBase):
    """Number entity for price proportional max temperature."""

    _attr_name = "Max Temperature"
    _attr_icon = "mdi:thermometer-chevron-up"
    _attr_native_min_value = MIN_PP_MAX_TEMPERATURE
    _attr_native_max_value = MAX_PP_MAX_TEMPERATURE
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "°C"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_PP_MAX_TEMPERATURE)
        self._attr_unique_id = f"{entry.entry_id}_pp_max_temperature"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.pp_max_temperature


class PpMinTemperatureNumber(SmartSpaNumberBase):
    """Number entity for price proportional min temperature."""

    _attr_name = "Min Temperature"
    _attr_icon = "mdi:thermometer-chevron-down"
    _attr_native_min_value = MIN_PP_MIN_TEMPERATURE
    _attr_native_max_value = MAX_PP_MIN_TEMPERATURE
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "°C"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_PP_MIN_TEMPERATURE)
        self._attr_unique_id = f"{entry.entry_id}_pp_min_temperature"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.pp_min_temperature


class LookaheadHoursNumber(SmartSpaNumberBase):
    """Number entity for lookahead hours."""

    _attr_name = "Lookahead Hours"
    _attr_icon = "mdi:crystal-ball"
    _attr_native_min_value = MIN_LOOKAHEAD_HOURS
    _attr_native_max_value = MAX_LOOKAHEAD_HOURS
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "hours"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_LOOKAHEAD_HOURS)
        self._attr_unique_id = f"{entry.entry_id}_lookahead_hours"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.lookahead_hours


class PriceWindowHoursNumber(SmartSpaNumberBase):
    """Number entity for price window hours."""

    _attr_name = "Price Window Hours"
    _attr_icon = "mdi:chart-timeline-variant-shimmer"
    _attr_native_min_value = MIN_PRICE_WINDOW_HOURS
    _attr_native_max_value = MAX_PRICE_WINDOW_HOURS
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "hours"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_PRICE_WINDOW_HOURS)
        self._attr_unique_id = f"{entry.entry_id}_price_window_hours"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.price_window_hours
