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
    CONF_HEATING_FREQUENCY,
    CONF_HEATING_DURATION,
    CONF_PRICE_THRESHOLD,
    CONF_HIGH_PRICE_THRESHOLD,
    CONF_HEATING_TEMPERATURE,
    CONF_IDLE_TEMPERATURE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_NUM_PEAKS,
    MIN_HEATING_FREQUENCY,
    MAX_HEATING_FREQUENCY,
    MIN_HEATING_DURATION,
    MAX_HEATING_DURATION,
    MIN_PRICE_THRESHOLD,
    MAX_PRICE_THRESHOLD,
    MIN_HIGH_PRICE_THRESHOLD,
    MAX_HIGH_PRICE_THRESHOLD,
    MIN_HEATING_TEMPERATURE,
    MAX_HEATING_TEMPERATURE,
    MIN_IDLE_TEMPERATURE,
    MAX_IDLE_TEMPERATURE,
    MIN_MANUAL_OVERRIDE_DURATION,
    MAX_MANUAL_OVERRIDE_DURATION,
    MIN_NUM_PEAKS,
    MAX_NUM_PEAKS,
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
        HeatingFrequencyNumber(coordinator, entry),
        HeatingDurationNumber(coordinator, entry),
        PriceThresholdNumber(coordinator, entry),
        HighPriceThresholdNumber(coordinator, entry),
        HeatingTemperatureNumber(coordinator, entry),
        IdleTemperatureNumber(coordinator, entry),
        ManualOverrideDurationNumber(coordinator, entry),
        NumPeaksNumber(coordinator, entry),
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


class HeatingFrequencyNumber(SmartSpaNumberBase):
    """Number entity for heating frequency."""

    _attr_name = "Heating Frequency"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = MIN_HEATING_FREQUENCY
    _attr_native_max_value = MAX_HEATING_FREQUENCY
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "hours"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_HEATING_FREQUENCY)
        self._attr_unique_id = f"{entry.entry_id}_heating_frequency"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.heating_frequency


class HeatingDurationNumber(SmartSpaNumberBase):
    """Number entity for heating duration."""

    _attr_name = "Heating Duration"
    _attr_icon = "mdi:timer-sand"
    _attr_native_min_value = MIN_HEATING_DURATION
    _attr_native_max_value = MAX_HEATING_DURATION
    _attr_native_step = 15
    _attr_native_unit_of_measurement = "minutes"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_HEATING_DURATION)
        self._attr_unique_id = f"{entry.entry_id}_heating_duration"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.heating_duration


class PriceThresholdNumber(SmartSpaNumberBase):
    """Number entity for price threshold."""

    _attr_name = "Price Threshold"
    _attr_icon = "mdi:cash"
    _attr_native_min_value = MIN_PRICE_THRESHOLD
    _attr_native_max_value = MAX_PRICE_THRESHOLD
    _attr_native_step = 0.01

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_PRICE_THRESHOLD)
        self._attr_unique_id = f"{entry.entry_id}_price_threshold"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.price_threshold


class HighPriceThresholdNumber(SmartSpaNumberBase):
    """Number entity for high price threshold (never heat above)."""

    _attr_name = "High Price Threshold"
    _attr_icon = "mdi:cash-remove"
    _attr_native_min_value = MIN_HIGH_PRICE_THRESHOLD
    _attr_native_max_value = MAX_HIGH_PRICE_THRESHOLD
    _attr_native_step = 0.01

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_HIGH_PRICE_THRESHOLD)
        self._attr_unique_id = f"{entry.entry_id}_high_price_threshold"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.high_price_threshold


class HeatingTemperatureNumber(SmartSpaNumberBase):
    """Number entity for heating temperature."""

    _attr_name = "Heating Temperature"
    _attr_icon = "mdi:thermometer-high"
    _attr_native_min_value = MIN_HEATING_TEMPERATURE
    _attr_native_max_value = MAX_HEATING_TEMPERATURE
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "°C"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_HEATING_TEMPERATURE)
        self._attr_unique_id = f"{entry.entry_id}_heating_temperature"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.heating_temperature


class IdleTemperatureNumber(SmartSpaNumberBase):
    """Number entity for idle temperature."""

    _attr_name = "Idle Temperature"
    _attr_icon = "mdi:thermometer-low"
    _attr_native_min_value = MIN_IDLE_TEMPERATURE
    _attr_native_max_value = MAX_IDLE_TEMPERATURE
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = "°C"

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_IDLE_TEMPERATURE)
        self._attr_unique_id = f"{entry.entry_id}_idle_temperature"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.idle_temperature


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


class NumPeaksNumber(SmartSpaNumberBase):
    """Number entity for number of peaks to avoid."""

    _attr_name = "Number of Peaks"
    _attr_icon = "mdi:chart-bell-curve"
    _attr_native_min_value = MIN_NUM_PEAKS
    _attr_native_max_value = MAX_NUM_PEAKS
    _attr_native_step = 1

    def __init__(
        self,
        coordinator: SmartSpaHeatingCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry, CONF_NUM_PEAKS)
        self._attr_unique_id = f"{entry.entry_id}_num_peaks"

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.coordinator.num_peaks
