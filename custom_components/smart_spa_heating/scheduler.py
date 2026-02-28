"""Scheduling algorithm for Smart Spa Heating."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Interval detection
SLOTS_PER_HOUR_15MIN = 4  # 96 values per day
SLOTS_PER_HOUR_1H = 1     # 24 values per day


@dataclass
class HeatingSlot:
    """Represents a scheduled heating time slot."""

    start: datetime
    end: datetime
    reason: str  # "threshold", "scheduled"
    target_temperature: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "reason": self.reason,
        }
        if self.target_temperature is not None:
            result["target_temperature"] = self.target_temperature
        return result


@dataclass
class PriceSlot:
    """Represents a time slot with its price."""

    start: datetime
    duration: timedelta
    price: float

    @property
    def end(self) -> datetime:
        """Return the end time of this slot."""
        return self.start + self.duration


class SpaHeatingScheduler:
    """Calculate optimal heating schedule based on prices."""

    def calculate_schedule_price_proportional(
        self,
        today_prices: list[float],
        tomorrow_prices: list[float] | None,
        max_temperature: float,
        min_temperature: float,
        lookahead_hours: int,
        price_window_hours: int = 0,
    ) -> list[HeatingSlot]:
        """
        Calculate heating schedule using price proportional algorithm.

        Maps electricity prices to target temperatures continuously:
        cheapest price -> max_temperature, most expensive -> min_temperature.
        Includes a lookahead boost to pre-heat before expensive periods.

        price_window_hours controls the rolling window for min/max price:
        0 = use all available prices (global), >0 = rolling window of N hours.
        """
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        slots_per_hour = self._detect_slots_per_hour(today_prices, tomorrow_prices)
        slot_duration = timedelta(minutes=60 // slots_per_hour)

        _LOGGER.debug(
            "Price proportional: %d slots/hour (%d min intervals), "
            "temp range=%.1f-%.1f°C, lookahead=%dh, price_window=%dh",
            slots_per_hour, 60 // slots_per_hour,
            min_temperature, max_temperature, lookahead_hours,
            price_window_hours,
        )

        price_slots = self._build_price_slots(
            today_prices, tomorrow_prices, today_start, now, slot_duration, slots_per_hour
        )

        if not price_slots:
            _LOGGER.warning("No price data available for scheduling")
            return []

        use_rolling_window = price_window_hours > 0
        window_duration = timedelta(hours=price_window_hours)

        if not use_rolling_window:
            # Global min/max price
            all_prices = [ps.price for ps in price_slots]
            global_min_price = min(all_prices)
            global_max_price = max(all_prices)
            global_price_range = global_max_price - global_min_price

            _LOGGER.debug(
                "Global price range: %.3f to %.3f (range=%.3f)",
                global_min_price, global_max_price, global_price_range,
            )

            if global_price_range < 0.001:
                mid_temp = round((max_temperature + min_temperature) / 2 * 2) / 2
                _LOGGER.debug("Flat prices, using midpoint temperature %.1f°C", mid_temp)
                return [HeatingSlot(
                    start=price_slots[0].start,
                    end=price_slots[-1].end,
                    reason="scheduled",
                    target_temperature=mid_temp,
                )]

        temp_range = max_temperature - min_temperature
        lookahead_duration = timedelta(hours=lookahead_hours)

        # Calculate target temperature for each slot
        slot_temps: list[tuple[PriceSlot, float]] = []
        for i, ps in enumerate(price_slots):
            # Determine price range for this slot
            if use_rolling_window:
                # Rolling window: centered on current slot
                half_window = window_duration / 2
                window_start = ps.start - half_window
                window_end = ps.start + half_window
                window_slots = [
                    ws for ws in price_slots
                    if ws.start >= window_start and ws.start < window_end
                ]
                if not window_slots:
                    window_slots = [ps]
                window_prices = [ws.price for ws in window_slots]
                min_price = min(window_prices)
                max_price = max(window_prices)
                price_range = max_price - min_price
            else:
                min_price = global_min_price
                max_price = global_max_price
                price_range = global_price_range

            if price_range < 0.001:
                # Flat prices in this window - use midpoint
                base_temp = (max_temperature + min_temperature) / 2
            else:
                # Base temperature from price ratio
                price_ratio = (ps.price - min_price) / price_range  # 0=cheapest, 1=most expensive
                base_temp = max_temperature - price_ratio * temp_range

            # Lookahead boost: compute avg price of next lookahead_hours
            lookahead_end = ps.start + lookahead_duration
            upcoming_slots = [
                future_ps for future_ps in price_slots
                if future_ps.start > ps.start and future_ps.start < lookahead_end
            ]

            if upcoming_slots and price_range >= 0.001:
                upcoming_avg = sum(s.price for s in upcoming_slots) / len(upcoming_slots)
                lookahead_factor = max(0.0, min(1.0, (upcoming_avg - ps.price) / price_range))
                boost = lookahead_factor * (max_temperature - base_temp) * 0.5
                target_temp = min(base_temp + boost, max_temperature)
            else:
                target_temp = base_temp

            # Round to nearest 0.5°C
            target_temp = round(target_temp * 2) / 2

            slot_temps.append((ps, target_temp))

        # Merge consecutive slots with the same target_temperature
        slots: list[HeatingSlot] = []
        current_start = slot_temps[0][0].start
        current_end = slot_temps[0][0].end
        current_temp = slot_temps[0][1]

        for ps, temp in slot_temps[1:]:
            if temp == current_temp:
                current_end = ps.end
            else:
                slots.append(HeatingSlot(
                    start=current_start,
                    end=current_end,
                    reason="scheduled",
                    target_temperature=current_temp,
                ))
                current_start = ps.start
                current_end = ps.end
                current_temp = temp

        # Don't forget the last block
        slots.append(HeatingSlot(
            start=current_start,
            end=current_end,
            reason="scheduled",
            target_temperature=current_temp,
        ))

        _LOGGER.debug("Price proportional schedule: %d temperature slots", len(slots))
        for slot in slots:
            _LOGGER.debug(
                "  %s to %s -> %.1f°C",
                slot.start.strftime("%Y-%m-%d %H:%M"),
                slot.end.strftime("%Y-%m-%d %H:%M"),
                slot.target_temperature,
            )

        return slots

    def _detect_slots_per_hour(
        self,
        today_prices: list[float],
        tomorrow_prices: list[float] | None,
    ) -> int:
        """Detect the number of slots per hour from the data."""
        today_len = len(today_prices) if today_prices else 0
        tomorrow_len = len(tomorrow_prices) if tomorrow_prices else 0

        # Use whichever has data
        data_len = today_len or tomorrow_len

        if data_len == 0:
            return SLOTS_PER_HOUR_1H  # Default to hourly

        if data_len >= 96:
            return SLOTS_PER_HOUR_15MIN  # 15-minute intervals
        elif data_len >= 48:
            return 2  # 30-minute intervals
        else:
            return SLOTS_PER_HOUR_1H  # Hourly

    def _build_price_slots(
        self,
        today_prices: list[float],
        tomorrow_prices: list[float] | None,
        today_start: datetime,
        now: datetime,
        slot_duration: timedelta,
        slots_per_hour: int,
    ) -> list[PriceSlot]:
        """Build list of PriceSlot objects from price data."""
        price_slots: list[PriceSlot] = []

        # Limit to 24 hours worth of slots each
        max_slots_per_day = 24 * slots_per_hour
        today_prices_limited = today_prices[:max_slots_per_day] if today_prices else []
        tomorrow_prices_limited = (tomorrow_prices[:max_slots_per_day] if tomorrow_prices else []) or []

        _LOGGER.debug(
            "Price data: today=%d slots, tomorrow=%d slots",
            len(today_prices_limited),
            len(tomorrow_prices_limited),
        )

        # Add today's remaining slots
        for i, price in enumerate(today_prices_limited):
            if price is None:
                continue
            slot_start = today_start + (slot_duration * i)
            if slot_start + slot_duration > now:  # Only future slots
                try:
                    price_float = float(price)
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid price value at slot %d: %s", i, price)
                    continue

                price_slots.append(PriceSlot(
                    start=slot_start,
                    duration=slot_duration,
                    price=price_float,
                ))

        # Add tomorrow's slots
        if tomorrow_prices_limited:
            tomorrow_start = today_start + timedelta(days=1)
            for i, price in enumerate(tomorrow_prices_limited):
                if price is None:
                    continue
                slot_start = tomorrow_start + (slot_duration * i)
                try:
                    price_float = float(price)
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid tomorrow price at slot %d: %s", i, price)
                    continue

                price_slots.append(PriceSlot(
                    start=slot_start,
                    duration=slot_duration,
                    price=price_float,
                ))

        # Sort by time
        price_slots.sort(key=lambda x: x.start)

        return price_slots
