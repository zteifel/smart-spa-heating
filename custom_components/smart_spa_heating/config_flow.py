"""Config flow for Smart Spa Heating integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_CLIMATE_ENTITY,
    CONF_HEATING_FREQUENCY,
    CONF_HEATING_DURATION,
    CONF_PRICE_THRESHOLD,
    CONF_HIGH_PRICE_THRESHOLD,
    CONF_HEATING_TEMPERATURE,
    CONF_IDLE_TEMPERATURE,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_NUM_PEAKS,
    CONF_SCHEDULING_ALGORITHM,
    DEFAULT_HEATING_FREQUENCY,
    DEFAULT_HEATING_DURATION,
    DEFAULT_PRICE_THRESHOLD,
    DEFAULT_HIGH_PRICE_THRESHOLD,
    DEFAULT_HEATING_TEMPERATURE,
    DEFAULT_IDLE_TEMPERATURE,
    DEFAULT_MANUAL_OVERRIDE_DURATION,
    DEFAULT_NUM_PEAKS,
    DEFAULT_SCHEDULING_ALGORITHM,
    ALGORITHM_INTERVAL,
    ALGORITHM_PEAK_AVOIDANCE,
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

_LOGGER = logging.getLogger(__name__)


def get_entity_schema() -> vol.Schema:
    """Return schema for entity selection step."""
    return vol.Schema(
        {
            vol.Required(CONF_NORDPOOL_ENTITY): EntitySelector(
                EntitySelectorConfig(domain="sensor")
            ),
            vol.Required(CONF_CLIMATE_ENTITY): EntitySelector(
                EntitySelectorConfig(domain="climate")
            ),
        }
    )


def get_settings_schema(
    heating_frequency: float = DEFAULT_HEATING_FREQUENCY,
    heating_duration: float = DEFAULT_HEATING_DURATION,
    price_threshold: float = DEFAULT_PRICE_THRESHOLD,
    high_price_threshold: float = DEFAULT_HIGH_PRICE_THRESHOLD,
    heating_temperature: float = DEFAULT_HEATING_TEMPERATURE,
    idle_temperature: float = DEFAULT_IDLE_TEMPERATURE,
    manual_override_duration: float = DEFAULT_MANUAL_OVERRIDE_DURATION,
    scheduling_algorithm: str = DEFAULT_SCHEDULING_ALGORITHM,
    num_peaks: int = DEFAULT_NUM_PEAKS,
) -> vol.Schema:
    """Return schema for settings step."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HEATING_FREQUENCY, default=heating_frequency
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_HEATING_FREQUENCY,
                    max=MAX_HEATING_FREQUENCY,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="hours",
                )
            ),
            vol.Required(
                CONF_HEATING_DURATION, default=heating_duration
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_HEATING_DURATION,
                    max=MAX_HEATING_DURATION,
                    step=15,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="minutes",
                )
            ),
            vol.Required(
                CONF_PRICE_THRESHOLD, default=price_threshold
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_PRICE_THRESHOLD,
                    max=MAX_PRICE_THRESHOLD,
                    step=0.01,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_HIGH_PRICE_THRESHOLD, default=high_price_threshold
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_HIGH_PRICE_THRESHOLD,
                    max=MAX_HIGH_PRICE_THRESHOLD,
                    step=0.01,
                    mode=NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_HEATING_TEMPERATURE, default=heating_temperature
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_HEATING_TEMPERATURE,
                    max=MAX_HEATING_TEMPERATURE,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
            vol.Required(
                CONF_IDLE_TEMPERATURE, default=idle_temperature
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_IDLE_TEMPERATURE,
                    max=MAX_IDLE_TEMPERATURE,
                    step=0.5,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
            vol.Required(
                CONF_MANUAL_OVERRIDE_DURATION, default=manual_override_duration
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_MANUAL_OVERRIDE_DURATION,
                    max=MAX_MANUAL_OVERRIDE_DURATION,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="hours",
                )
            ),
            vol.Required(
                CONF_SCHEDULING_ALGORITHM, default=scheduling_algorithm
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[ALGORITHM_INTERVAL, ALGORITHM_PEAK_AVOIDANCE],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(
                CONF_NUM_PEAKS, default=num_peaks
            ): NumberSelector(
                NumberSelectorConfig(
                    min=MIN_NUM_PEAKS,
                    max=MAX_NUM_PEAKS,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                )
            ),
        }
    )


class SmartSpaHeatingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Spa Heating."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - entity selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            nordpool_entity = user_input[CONF_NORDPOOL_ENTITY]
            climate_entity = user_input[CONF_CLIMATE_ENTITY]

            # Validate entities exist
            if not self.hass.states.get(nordpool_entity):
                errors[CONF_NORDPOOL_ENTITY] = "entity_not_found"
            elif not self.hass.states.get(climate_entity):
                errors[CONF_CLIMATE_ENTITY] = "entity_not_found"
            else:
                # Validate Nordpool entity has expected attributes
                nordpool_state = self.hass.states.get(nordpool_entity)
                if nordpool_state and not hasattr(nordpool_state, "attributes"):
                    errors[CONF_NORDPOOL_ENTITY] = "invalid_nordpool"
                elif nordpool_state and "today" not in nordpool_state.attributes:
                    errors[CONF_NORDPOOL_ENTITY] = "invalid_nordpool"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_settings()

        return self.async_show_form(
            step_id="user",
            data_schema=get_entity_schema(),
            errors=errors,
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the settings step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate temperature settings
            if user_input[CONF_IDLE_TEMPERATURE] >= user_input[CONF_HEATING_TEMPERATURE]:
                errors["base"] = "idle_temp_too_high"
            else:
                self._data.update(user_input)

                # Create unique ID from entities
                await self.async_set_unique_id(
                    f"{self._data[CONF_NORDPOOL_ENTITY]}_{self._data[CONF_CLIMATE_ENTITY]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Smart Spa Heating",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="settings",
            data_schema=get_settings_schema(),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return SmartSpaHeatingOptionsFlow(config_entry)


class SmartSpaHeatingOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Smart Spa Heating."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input[CONF_IDLE_TEMPERATURE] >= user_input[CONF_HEATING_TEMPERATURE]:
                errors["base"] = "idle_temp_too_high"
            else:
                return self.async_create_entry(title="", data=user_input)

        # Get current values from config entry
        current = {**self._config_entry.data, **self._config_entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=get_settings_schema(
                heating_frequency=current.get(CONF_HEATING_FREQUENCY, DEFAULT_HEATING_FREQUENCY),
                heating_duration=current.get(CONF_HEATING_DURATION, DEFAULT_HEATING_DURATION),
                price_threshold=current.get(CONF_PRICE_THRESHOLD, DEFAULT_PRICE_THRESHOLD),
                high_price_threshold=current.get(CONF_HIGH_PRICE_THRESHOLD, DEFAULT_HIGH_PRICE_THRESHOLD),
                heating_temperature=current.get(CONF_HEATING_TEMPERATURE, DEFAULT_HEATING_TEMPERATURE),
                idle_temperature=current.get(CONF_IDLE_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE),
                manual_override_duration=current.get(CONF_MANUAL_OVERRIDE_DURATION, DEFAULT_MANUAL_OVERRIDE_DURATION),
                scheduling_algorithm=current.get(CONF_SCHEDULING_ALGORITHM, DEFAULT_SCHEDULING_ALGORITHM),
                num_peaks=current.get(CONF_NUM_PEAKS, DEFAULT_NUM_PEAKS),
            ),
            errors=errors,
        )
