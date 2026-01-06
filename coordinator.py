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
    CONF_HEATING_FREQUENCY,
    CONF_HEATING_DURATION,
    CONF_PRICE_THRESHOLD,
    CONF_HIGH_PRICE_THRESHOLD,
    CONF_HEATING_TEMPERATURE,
    CONF_IDLE_TEMPERATURE,
    CONF_MANUAL_OVERRIDE_DURATION,
    DEFAULT_HEATING_FREQUENCY,
    DEFAULT_HEATING_DURATION,
    DEFAULT_PRICE_THRESHOLD,
    DEFAULT_HIGH_PRICE_THRESHOLD,
    DEFAULT_HEATING_TEMPERATURE,
    DEFAULT_IDLE_TEMPERATURE,
    DEFAULT_MANUAL_OVERRIDE_DURATION,
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
        self._last_heating_time: datetime | None = None
        self._manual_override_end: datetime | None = None
        self._heating_active = False
        self._current_price: float | None = None
        self._skip_next = False
        self._expected_temperature: float | None = None  # Track what temp we set
        self._expected_temperature_until: datetime | None = None  # Valid until this time
        self._ignore_next_temp_change = False  # Flag to ignore our own changes

        # Listeners
        self._unsub_nordpool_listener: callable | None = None
        self._unsub_manual_override_end: callable | None = None
        self._unsub_climate_listener: callable | None = None
        self._unsub_hourly_update: callable | None = None
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

    @property
    def last_heating_time(self) -> datetime | None:
        """Return the last heating time."""
        return self._last_heating_time

    def _get_config_value(self, key: str, default: Any) -> Any:
        """Get configuration value from options or data."""
        if key in self.entry.options:
            return self.entry.options[key]
        return self.entry.data.get(key, default)

    @property
    def heating_frequency(self) -> float:
        """Return heating frequency in hours."""
        return self._get_config_value(CONF_HEATING_FREQUENCY, DEFAULT_HEATING_FREQUENCY)

    @property
    def heating_duration(self) -> float:
        """Return heating duration in minutes."""
        return self._get_config_value(CONF_HEATING_DURATION, DEFAULT_HEATING_DURATION)

    @property
    def price_threshold(self) -> float:
        """Return price threshold (always heat below this)."""
        return self._get_config_value(CONF_PRICE_THRESHOLD, DEFAULT_PRICE_THRESHOLD)

    @property
    def high_price_threshold(self) -> float:
        """Return high price threshold (never heat above this)."""
        return self._get_config_value(CONF_HIGH_PRICE_THRESHOLD, DEFAULT_HIGH_PRICE_THRESHOLD)

    @property
    def heating_temperature(self) -> float:
        """Return heating temperature."""
        return self._get_config_value(CONF_HEATING_TEMPERATURE, DEFAULT_HEATING_TEMPERATURE)

    @property
    def idle_temperature(self) -> float:
        """Return idle temperature."""
        return self._get_config_value(CONF_IDLE_TEMPERATURE, DEFAULT_IDLE_TEMPERATURE)

    @property
    def manual_override_duration(self) -> float:
        """Return manual override duration in hours."""
        return self._get_config_value(CONF_MANUAL_OVERRIDE_DURATION, DEFAULT_MANUAL_OVERRIDE_DURATION)

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
        self._unsub_hourly_update = async_track_time_interval(
            self.hass, self._hourly_update, timedelta(hours=1)
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

        # Check if we're currently in a heating slot
        now = dt_util.now()
        in_heating_slot = False
        for slot in self._schedule:
            if slot.start <= now < slot.end:
                in_heating_slot = True
                break

        if in_heating_slot:
            _LOGGER.info("Manual override cleared - currently in heating slot, starting heating")
            await self._start_heating()
        else:
            _LOGGER.info("Manual override cleared - not in heating slot, setting idle temperature")
            await self._end_heating()

    async def _hourly_update(self, now: datetime) -> None:
        """Perform hourly schedule update."""
        _LOGGER.debug("Hourly update triggered")
        await self.async_recalculate_schedule()

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

        # Calculate schedule
        self._schedule = self._scheduler.calculate_schedule(
            today_prices=today_prices,
            tomorrow_prices=tomorrow_prices,
            heating_frequency_hours=self.heating_frequency,
            heating_duration_minutes=self.heating_duration,
            price_threshold=self.price_threshold,
            high_price_threshold=self.high_price_threshold,
        )

        _LOGGER.debug("Calculated %d heating slots", len(self._schedule))

        # Schedule the heating events
        self._schedule_heating_events()

        self.async_set_updated_data(self.data)

    def _cancel_scheduled_heating(self) -> None:
        """Cancel any scheduled heating events."""
        if self._unsub_heating_start:
            self._unsub_heating_start()
            self._unsub_heating_start = None
        if self._unsub_heating_end:
            self._unsub_heating_end()
            self._unsub_heating_end = None

    def _schedule_heating_events(self) -> None:
        """Schedule heating start/end events."""
        self._cancel_scheduled_heating()

        if not self._schedule or not self._enabled:
            return

        now = dt_util.now()

        # Find current or next slot
        for slot in self._schedule:
            if self._skip_next and slot.start > now:
                self._skip_next = False
                continue

            if slot.end > now:
                # This slot is relevant
                if slot.start <= now:
                    # We're in the middle of a slot, start heating now
                    self.hass.async_create_task(self._start_heating())
                    # Schedule end
                    self._unsub_heating_end = async_track_point_in_time(
                        self.hass, self._end_heating_callback, slot.end
                    )
                else:
                    # Schedule start
                    self._unsub_heating_start = async_track_point_in_time(
                        self.hass, self._start_heating_callback, slot.start
                    )
                    # Schedule end
                    self._unsub_heating_end = async_track_point_in_time(
                        self.hass, self._end_heating_callback, slot.end
                    )
                break

    @callback
    def _start_heating_callback(self, now: datetime) -> None:
        """Callback for scheduled heating start."""
        self.hass.async_create_task(self._start_heating())

    @callback
    def _end_heating_callback(self, now: datetime) -> None:
        """Callback for scheduled heating end."""
        self.hass.async_create_task(self._end_heating())
        # Reschedule for next slot
        self._schedule_heating_events()

    async def _start_heating(self) -> None:
        """Start heating the spa."""
        if self.manual_override_active:
            _LOGGER.debug("Manual override active, not starting heating")
            return

        if not self._enabled:
            return

        _LOGGER.info("Starting spa heating, setting temperature to %.1f°C", self.heating_temperature)

        # Set expected temperature so we don't trigger manual override
        # Keep it valid for 30 seconds to handle any delayed state updates
        self._expected_temperature = self.heating_temperature
        self._expected_temperature_until = dt_util.now() + timedelta(seconds=30)

        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": self._climate_entity,
                "temperature": self.heating_temperature,
            },
            blocking=True,
        )

        self._heating_active = True
        self._last_heating_time = dt_util.now()
        self.async_set_updated_data(self.data)

    async def _end_heating(self) -> None:
        """End heating the spa."""
        if self.manual_override_active:
            _LOGGER.debug("Manual override active, not ending heating")
            return

        _LOGGER.info("Ending spa heating, setting temperature to %.1f°C", self.idle_temperature)

        # Set expected temperature so we don't trigger manual override
        # Keep it valid for 30 seconds to handle any delayed state updates
        self._expected_temperature = self.idle_temperature
        self._expected_temperature_until = dt_util.now() + timedelta(seconds=30)

        await self.hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": self._climate_entity,
                "temperature": self.idle_temperature,
            },
            blocking=True,
        )

        self._heating_active = False
        self.async_set_updated_data(self.data)

    async def async_force_heat_on(self) -> None:
        """Force heating on immediately."""
        _LOGGER.info("Force heating ON requested")

        # Clear any manual override
        self._manual_override_end = None

        # Start heating
        await self._start_heating()

        # Update last heating time (counts toward schedule)
        self._last_heating_time = dt_util.now()

        # Schedule end after configured duration
        self._cancel_scheduled_heating()
        end_time = dt_util.now() + timedelta(minutes=self.heating_duration)
        self._unsub_heating_end = async_track_point_in_time(
            self.hass, self._end_heating_callback, end_time
        )

        # Recalculate schedule
        await self.async_recalculate_schedule()

    async def async_force_heat_off(self) -> None:
        """Force heating off immediately."""
        _LOGGER.info("Force heating OFF requested")

        # Clear any manual override
        self._manual_override_end = None

        # End heating
        await self._end_heating()

        # Update last heating time (counts toward schedule)
        self._last_heating_time = dt_util.now()

        # Recalculate schedule
        await self.async_recalculate_schedule()

    def skip_next_heating(self) -> None:
        """Skip the next scheduled heating session."""
        _LOGGER.info("Skipping next heating session")
        self._skip_next = True
        self._schedule_heating_events()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        self._cancel_scheduled_heating()

        if self._unsub_nordpool_listener:
            self._unsub_nordpool_listener()
        if self._unsub_climate_listener:
            self._unsub_climate_listener()
        if self._unsub_hourly_update:
            self._unsub_hourly_update()
