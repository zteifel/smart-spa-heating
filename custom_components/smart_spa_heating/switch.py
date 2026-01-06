"""Switch platform for Smart Spa Heating."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up Smart Spa Heating switch from config entry."""
    coordinator: SmartSpaHeatingCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([SmartSpaHeatingSwitch(coordinator, entry)])


class SmartSpaHeatingSwitch(CoordinatorEntity[SmartSpaHeatingCoordinator], SwitchEntity):
    """Switch to enable/disable smart spa heating."""

    _attr_has_entity_name = True
    _attr_name = "Smart Heating"
    _attr_icon = "mdi:hot-tub"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_smart_heating"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Spa Heating",
            "manufacturer": "Custom",
            "model": "Smart Spa Heating Controller",
        }

    @property
    def is_on(self) -> bool:
        """Return true if smart heating is enabled."""
        return self.coordinator.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on smart heating."""
        self.coordinator.enabled = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off smart heating."""
        self.coordinator.enabled = False
        self.async_write_ha_state()
