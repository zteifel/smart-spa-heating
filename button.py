"""Button platform for Smart Spa Heating."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Smart Spa Heating buttons from config entry."""
    coordinator: SmartSpaHeatingCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        ForceHeatOnButton(coordinator, entry),
        ForceHeatOffButton(coordinator, entry),
        ClearManualOverrideButton(coordinator, entry),
    ])


class SmartSpaButtonBase(CoordinatorEntity[SmartSpaHeatingCoordinator], ButtonEntity):
    """Base class for Smart Spa Heating buttons."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Spa Heating",
            "manufacturer": "Custom",
            "model": "Smart Spa Heating Controller",
        }


class ForceHeatOnButton(SmartSpaButtonBase):
    """Button to force heating on."""

    _attr_name = "Force Heat On"
    _attr_icon = "mdi:radiator"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_force_heat_on"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_force_heat_on()


class ForceHeatOffButton(SmartSpaButtonBase):
    """Button to force heating off."""

    _attr_name = "Force Heat Off"
    _attr_icon = "mdi:radiator-off"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_force_heat_off"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_force_heat_off()


class ClearManualOverrideButton(SmartSpaButtonBase):
    """Button to clear manual override."""

    _attr_name = "Clear Manual Override"
    _attr_icon = "mdi:hand-back-left-off"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_clear_manual_override"

    async def async_press(self) -> None:
        """Handle the button press."""
        self.coordinator.clear_manual_override()
