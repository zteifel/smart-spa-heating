"""Data coordinator for Smart Spa Heating integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    async_track_point_in_time,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_NORDPOOL_ENTITY,
    CONF_CLIMATE_ENTITY,
    CONF_MANUAL_OVERRIDE_DURATION,
    CONF_PP_MAX_TEMPERATURE,
    CONF_PP_MIN_TEMPERATURE,
    CONF_LOOKAHEAD_HOURS,
    CONF_PRICE_WINDOW_HOURS,
    DEFAULT_MANUAL_OVERRIDE_DURATION,
    DEFAULT_PP_MAX_TEMPERATURE,
    DEFAULT_PP_MIN_TEMPERATURE,
    DEFAULT_LOOKAHEAD_HOURS,
    DEFAULT_PRICE_WINDOW_HOURS,
)
from .scheduler import SpaHeatingScheduler, HeatingSlot

_LOGGER = logging.getLogger(__name__)


class SmartSpaHeatingCoordinator(DataUpdateCoordinator):
    """Coordinator for Smart Spa Heating."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )
        self.entry = entry
        self.hass = hass

        # Get configuration
        self._nordpool_entity = entry.data[CONF_NORDPOOL_ENTITY]
        self._climate_entity = entry.data[CONF_CLIMATE_ENTITY]

        # State
        self._enabled = True
        self._schedule: list[HeatingSlot] = []
        self._manual_override_end: datetime | None = None
        self._heating_active = False
        self._current_price: float | None = None
        self._expected_temperature: float | None = None  # Track what temp we set
        self._expected_temperature_until: datetime | None = None  # Valid until this time
        self._ignore_next_temp_change = False  # Flag to ignore our own changes

        # Listeners
        self._unsub_nordpool_listener: callable | None = None
        self._unsub_manual_override_end: callable | None = None
        self._unsub_climate_listener: callable | None = None
        self._unsub_periodic_check: callable | None = None
        self._unsub_heating_start: callable | None = None
        self._unsub_heating_end: callable | None = None

        # Scheduler
        self._scheduler = SpaHeatingScheduler()

    @property
    def nordpool_entity(self) -> str:
        """Return the Nordpool entity ID."""
        return self._nordpool_entity

    @property
    def climate_entity(self) -> str:
        """Return the climate entity ID."""
        return self._climate_entity

    @property
    def enabled(self) -> bool:
        """Return whether smart heating is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether smart heating is enabled."""
        self._enabled = value
        if value:
            self.hass.async_create_task(self.async_recalculate_schedule())
        else:
            self._cancel_scheduled_heating()

    @property
    def schedule(self) -> list[HeatingSlot]:
        """Return the current heating schedule."""
        return self._schedule

    @property
    def next_heating(self) -> datetime | None:
        """Return the next scheduled heating start time."""
        now = dt_util.now()
        for slot in self._schedule:
            if slot.start > now:
                return slot.start
        return None

    @property
    def heating_active(self) -> bool:
        """Return whether heating is currently active."""
        return self._heating_active

    @property
    def current_price(self) -> float | None:
        """Return the current electricity price."""
        return self._current_price

    @property
    def manual_override_end(self) -> datetime | None:
        """Return when manual override ends."""
        return self._manual_override_end

    @property
    def manual_override_active(self) -> bool:
        """Return whether manual override is active."""
        if self._manual_override_end is None:
            return False
        return dt_util.now() < self._manual_override_end

    def _get_config_value(self, key: str, default: Any) -> Any:
        """Get configuration value from options or data."""
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    @property
    def manual_override_duration(self) -> float:
        """Return manual override duration in hours."""
        return self._get_config_value(CONF_MANUAL_OVERRIDE_DURATION, DEFAULT_MANUAL_OVERRIDE_DURATION)

    @property
    def pp_max_temperature(self) -> float:
        """Return price proportional max temperature."""
        return self._get_config_value(CONF_PP_MAX_TEMPERATURE, DEFAULT_PP_MAX_TEMPERATURE)

    @property
    def pp_min_temperature(self) -> float:
        """Return price proportional min temperature."""
        return self._get_config_value(CONF_PP_MIN_TEMPERATURE, DEFAULT_PP_MIN_TEMPERATURE)

    @property
    def lookahead_hours(self) -> int:
        """Return lookahead hours for price proportional algorithm."""
        return int(self._get_config_value(CONF_LOOKAHEAD_HOURS, DEFAULT_LOOKAHEAD_HOURS))

    @property
    def price_window_hours(self) -> int:
        """Return price window hours for rolling min/max calculation."""
        return int(self._get_config_value(CONF_PRICE_WINDOW_HOURS, DEFAULT_PRICE_WINDOW_HOURS))

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Nordpool sensor."""
        nordpool_state = self.hass.states.get(self._nordpool_entity)

        if nordpool_state is None:
            _LOGGER.warning("Nordpool entity %s not found", self._nordpool_entity)
            return {}

        # Get current price
        try:
            self._current_price = float(nordpool_state.state)
        except (ValueError, TypeError):
            self._current_price = None

        # Debug: Log all available attributes from Nordpool entity
        _LOGGER.debug(
            "Nordpool entity attributes: %s",
            list(nordpool_state.attributes.keys())
        )

        # Get today and tomorrow prices from attributes
        today_prices = nordpool_state.attributes.get("today", [])
        tomorrow_prices = nordpool_state.attributes.get("tomorrow", [])

        _LOGGER.debug("Today prices (%d values)", len(today_prices))
        _LOGGER.debug("Tomorrow prices (%d values)", len(tomorrow_prices))

        return {
            "current_price": self._current_price,
            "today": today_prices,
            "tomorrow": tomorrow_prices,
        }

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh and set up listeners."""
        await super().async_config_entry_first_refresh()

        # Set up state change listeners
        self._unsub_nordpool_listener = async_track_state_change_event(
            self.hass, [self._nordpool_entity], self._handle_nordpool_update
        )

        self._unsub_climate_listener = async_track_state_change_event(
            self.hass, [self._climate_entity], self._handle_climate_update
        )

        # Set up hourly recalculation
        self._unsub_periodic_check = async_track_time_interval(
            self.hass, self._periodic_check, timedelta(minutes=15)
        )

        # Initial schedule calculation
        await self.async_recalculate_schedule()

    @callback
    def _handle_nordpool_update(self, event: Event) -> None:
        """Handle Nordpool entity state change."""
        _LOGGER.debug("Nordpool entity updated, recalculating schedule")
        self.hass.async_create_task(self.async_request_refresh())
        self.hass.async_create_task(self.async_recalculate_schedule())

    @callback
    def _handle_climate_update(self, event: Event) -> None:
        """Handle climate entity state change - detect manual changes."""
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        if new_state is None or old_state is None:
            return

        # Ignore state changes from unavailable/unknown states
        if old_state.state in ("unavailable", "unknown"):
            _LOGGER.debug(
                "Ignoring climate state change from %s state",
                old_state.state
            )
            return

        # Check if temperature changed
        new_temp = new_state.attributes.get("temperature")
        old_temp = old_state.attributes.get("temperature")

        if new_temp == old_temp or new_temp is None:
            return

        # Check if this is a temperature we set ourselves
        if self._expected_temperature is not None and self._expected_temperature_until is not None:
            now = dt_util.now()
            if now <= self._expected_temperature_until:
                # Allow small tolerance for float comparison
                if abs(new_temp - self._expected_temperature) < 0.1:
                    _LOGGER.debug(
                        "Ignoring our own temperature change to %.1f°C",
                        new_temp
                    )
                    return
            else:
                # Expected temperature window expired, clear it
                self._expected_temperature = None
                self._expected_temperature_until = None

        # Check if we should ignore this change
        if self._ignore_next_temp_change:
            _LOGGER.debug("Ignoring temperature change (flag set)")
            self._ignore_next_temp_change = False
            return

        # Temperature changed externally - activate manual override
        _LOGGER.info(
            "Manual temperature change detected (%.1f -> %.1f), activating override for %d hours",
            old_temp or 0,
            new_temp,
            self.manual_override_duration,
        )
        self._activate_manual_override()

    def _activate_manual_override(self) -> None:
        """Activate manual override mode."""
        # Cancel any existing override end callback
        if self._unsub_manual_override_end:
            self._unsub_manual_override_end()
            self._unsub_manual_override_end = None

        self._manual_override_end = dt_util.now() + timedelta(
            hours=self.manual_override_duration
        )
        self._cancel_scheduled_heating()

        # Schedule callback for when override ends
        self._unsub_manual_override_end = async_track_point_in_time(
            self.hass, self._manual_override_end_callback, self._manual_override_end
        )
        _LOGGER.debug("Scheduled manual override end callback for %s", self._manual_override_end)

        self.async_set_updated_data(self.data)

    def _manual_override_end_callback(self, now: datetime) -> None:
        """Handle manual override end."""
        _LOGGER.info("Manual override ended, applying current schedule state")
        self._manual_override_end = None
        self._unsub_manual_override_end = None
        self.hass.async_create_task(self._apply_current_schedule_state())

    def clear_manual_override(self) -> None:
        """Clear manual override mode and apply current schedule state."""
        # Cancel the scheduled override end callback
        if self._unsub_manual_override_end:
            self._unsub_manual_override_end()
            self._unsub_manual_override_end = None

        self._manual_override_end = None
        self.hass.async_create_task(self._apply_current_schedule_state())
        self.async_set_updated_data(self.data)

    async def _apply_current_schedule_state(self) -> None:
        """Recalculate schedule and immediately apply the correct temperature."""
        await self.async_recalculate_schedule()

        now = dt_util.now()
        current_slot = None
        for slot in self._schedule:
            if slot.start <= now < slot.end:
                current_slot = slot
                break

        if current_slot is not None:
            _LOGGER.debug(
                "Periodic check: applying %.1f°C",
                current_slot.target_temperature,
            )
            await self._set_target_temperature(current_slot.target_temperature)
        else:
            _LOGGER.debug(
                "No current slot, setting min temperature %.1f°C",
                self.pp_min_temperature,
            )
            await self._set_target_temperature(self.pp_min_temperature)

    async def _periodic_check(self, now: datetime) -> None:
        """Perform periodic schedule check every 15 minutes."""
        _LOGGER.debug("Periodic check triggered")

        if self.manual_override_active:
            _LOGGER.debug("Manual override active, skipping periodic check")
            return

        if not self._enabled:
            _LOGGER.debug("Integration disabled, skipping periodic check")
            return

        await self._apply_current_schedule_state()

    async def async_recalculate_schedule(self) -> None:
        """Recalculate the heating schedule."""
        if not self._enabled:
            self._schedule = []
            self.async_set_updated_data(self.data)
            return

        # Get price data
        data = self.data or {}
        today_prices = data.get("today", [])
        tomorrow_prices = data.get("tomorrow", [])

        if not today_prices:
            _LOGGER.warning("No price data available, cannot calculate schedule")
            return

        self._schedule = self._scheduler.calculate_schedule_price_proportional(
            today_prices=today_prices,
            tomorrow_prices=tomorrow_prices,
            max_temperature=self.pp_max_temperature,
            min_temperature=self.pp_min_temperature,
            lookahead_hours=self.lookahead_hours,
            price_window_hours=self.price_window_hours,
        )

        _LOGGER.debug("Calculated %d heating slots", len(self._schedule))

        self._schedule_temperature_slots()

        self.async_set_updated_data(self.data)

    def _cancel_scheduled_heating(self) -> None:
        """Cancel any scheduled heating events."""
        if self._unsub_heating_start:
            self._unsub_heating_start()
            self._unsub_heating_start = None
        if self._unsub_heating_end:
            self._unsub_heating_end()
            self._unsub_heating_end = None

    def _schedule_temperature_slots(self) -> None:
        """Schedule temperature slot transitions."""
        self._cancel_scheduled_heating()

        if not self._schedule or not self._enabled:
            return

        now = dt_util.now()

        for slot in self._schedule:
            if slot.end > now:
                if slot.start <= now:
                    # We're in this slot - apply its temperature now
                    self.hass.async_create_task(
                        self._set_target_temperature(slot.target_temperature)
                    )
                    # Schedule callback at slot end to chain to next
                    self._unsub_heating_end = async_track_point_in_time(
                        self.hass, self._temperature_slot_callback, slot.end
                    )
                else:
                    # Future slot - schedule callback at its start
                    self._unsub_heating_start = async_track_point_in_time(
                        self.hass, self._temperature_slot_callback, slot.start
                    )
                break

    @callback
    def _temperature_slot_callback(self, now: datetime) -> None:
        """Callback for temperature slot transition."""
        self._schedule_temperature_slots()

    async def _set_target_temperature(self, temperature: float) -> None:
        """Set the spa target temperature."""
        if self.manual_override_active:
            _LOGGER.debug("Manual override active, not setting temperature")
            return

        if not self._enabled:
            return

        # Check current temperature to avoid unnecessary updates
        climate_state = self.hass.states.get(self._climate_entity)
        if climate_state:
            current_temp = climate_state.attributes.get("temperature")
            if current_temp is not None and abs(current_temp - temperature) < 0.1:
                _LOGGER.debug(
                    "Climate already at target temperature %.1f°C, skipping update",
                    temperature
                )
                self._heating_active = temperature > self.pp_min_temperature
                self.async_set_updated_data(self.data)
                return

        _LOGGER.info("Setting temperature to %.1f°C", temperature)

        # Set expected temperature so we don't trigger manual override
        self._expected_temperature = temperature
        self._expected_temperature_until = dt_util.now() + timedelta(seconds=30)

        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": self._climate_entity,
                "temperature": temperature,
            },
            blocking=True,
        )

        self._heating_active = temperature > self.pp_min_temperature
        self.async_set_updated_data(self.data)

    async def async_force_heat_on(self) -> None:
        """Force heating on immediately at max temperature."""
        _LOGGER.info("Force heating ON requested")

        # Clear any manual override
        self._manual_override_end = None

        await self._set_target_temperature(self.pp_max_temperature)

    async def async_force_heat_off(self) -> None:
        """Force heating off immediately at min temperature."""
        _LOGGER.info("Force heating OFF requested")

        # Clear any manual override
        self._manual_override_end = None

        await self._set_target_temperature(self.pp_min_temperature)

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        self._cancel_scheduled_heating()

        if self._unsub_nordpool_listener:
            self._unsub_nordpool_listener()
        if self._unsub_climate_listener:
            self._unsub_climate_listener()
        if self._unsub_periodic_check:
            self._unsub_periodic_check()
