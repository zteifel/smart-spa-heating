"""Smart Spa Heating integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_NORDPOOL_ENTITY,
    CONF_CLIMATE_ENTITY,
    CONF_HEATING_FREQUENCY,
    CONF_HEATING_DURATION,
    CONF_PRICE_THRESHOLD,
    CONF_HEATING_TEMPERATURE,
    CONF_IDLE_TEMPERATURE,
    CONF_MANUAL_OVERRIDE_DURATION,
)
from .coordinator import SmartSpaHeatingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Spa Heating from a config entry."""
    _LOGGER.debug("Setting up Smart Spa Heating integration")

    coordinator = SmartSpaHeatingCoordinator(
        hass,
        entry,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Smart Spa Heating integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update - just recalculate schedule, no reload needed."""
    _LOGGER.debug("Options updated, recalculating schedule")
    coordinator: SmartSpaHeatingCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_recalculate_schedule()
