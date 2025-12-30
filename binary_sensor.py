"""Binary sensor platform for Smart Spa Heating."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartSpaHeatingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Spa Heating binary sensors from config entry."""
    coordinator: SmartSpaHeatingCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        HeatingActiveBinarySensor(coordinator, entry),
        ManualOverrideActiveBinarySensor(coordinator, entry),
    ])


class SmartSpaBinarySensorBase(
    CoordinatorEntity[SmartSpaHeatingCoordinator], BinarySensorEntity
):
    """Base class for Smart Spa Heating binary sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Spa Heating",
            "manufacturer": "Custom",
            "model": "Smart Spa Heating Controller",
        }


class HeatingActiveBinarySensor(SmartSpaBinarySensorBase):
    """Binary sensor showing whether heating is currently active."""

    _attr_name = "Heating Active"
    _attr_icon = "mdi:fire"
    _attr_device_class = BinarySensorDeviceClass.HEAT

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_heating_active"

    @property
    def is_on(self) -> bool:
        """Return true if heating is active."""
        return self.coordinator.heating_active

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        return {
            "last_heating": (
                self.coordinator.last_heating_time.isoformat()
                if self.coordinator.last_heating_time
                else None
            ),
        }


class ManualOverrideActiveBinarySensor(SmartSpaBinarySensorBase):
    """Binary sensor showing whether manual override is active."""

    _attr_name = "Manual Override Active"
    _attr_icon = "mdi:hand-back-left"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_override_active"

    @property
    def is_on(self) -> bool:
        """Return true if manual override is active."""
        return self.coordinator.manual_override_active
