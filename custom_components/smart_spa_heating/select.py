"""Select platform for Smart Spa Heating."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_SCHEDULING_ALGORITHM,
    ALGORITHM_INTERVAL,
    ALGORITHM_PEAK_AVOIDANCE,
)
from .coordinator import SmartSpaHeatingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Smart Spa Heating select entities from config entry."""
    coordinator: SmartSpaHeatingCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        SchedulingAlgorithmSelect(coordinator, entry),
    ])


class SchedulingAlgorithmSelect(
    CoordinatorEntity[SmartSpaHeatingCoordinator], SelectEntity
):
    """Select entity for choosing the scheduling algorithm."""

    _attr_has_entity_name = True
    _attr_name = "Scheduling Algorithm"
    _attr_icon = "mdi:strategy"
    _attr_options = [ALGORITHM_INTERVAL, ALGORITHM_PEAK_AVOIDANCE]

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_scheduling_algorithm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Spa Heating",
            "manufacturer": "Custom",
            "model": "Smart Spa Heating Controller",
        }

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return self.coordinator.scheduling_algorithm

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        new_options = dict(self._entry.options)
        new_options[CONF_SCHEDULING_ALGORITHM] = option

        self.hass.config_entries.async_update_entry(
            self._entry,
            options=new_options,
        )
