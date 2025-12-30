"""Scheduling algorithm for Smart Spa Heating."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from enum import Enum

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Interval detection
SLOTS_PER_HOUR_15MIN = 4  # 96 values per day
SLOTS_PER_HOUR_1H = 1     # 24 values per day


class SlotStatus(Enum):
    """Status of a time slot."""
    UNMARKED = "unmarked"
    HEATING = "heating"
    COOLING = "cooling"


@dataclass
class HeatingSlot:
    """Represents a scheduled heating time slot."""

    start: datetime
    end: datetime
    reason: str  # "threshold", "scheduled"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "reason": self.reason,
        }


@dataclass
class PriceSlot:
    """Represents a time slot with its price and status."""

    start: datetime
    duration: timedelta
    price: float
    status: SlotStatus = SlotStatus.UNMARKED

    @property
    def end(self) -> datetime:
        """Return the end time of this slot."""
        return self.start + self.duration


class SpaHeatingScheduler:
    """Calculate optimal heating schedule based on prices."""

    def calculate_schedule(
        self,
        today_prices: list[float],
        tomorrow_prices: list[float] | None,
        heating_frequency_hours: float,
        heating_duration_minutes: float,
        price_threshold: float,
        high_price_threshold: float,
    ) -> list[HeatingSlot]:
        """
        Calculate the optimal heating schedule.

        Algorithm:
        1. Mark all slots below price_threshold as HEATING (always heat when cheap)
        2. Mark all slots above high_price_threshold as COOLING (never heat when expensive)
        3. Find highest price point among unmarked slots, center a cooling interval
           of heating_frequency_hours around it
        4. Place heating periods of heating_duration_minutes on either side of the
           cooling interval
        5. Repeat until no unmarked interval exceeds heating_frequency_hours
        """
        now = dt_util.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Detect interval size from data
        slots_per_hour = self._detect_slots_per_hour(today_prices, tomorrow_prices)
        slot_duration = timedelta(minutes=60 // slots_per_hour)

        _LOGGER.debug(
            "Detected %d slots per hour (%d min intervals)",
            slots_per_hour, 60 // slots_per_hour
        )

        # Build list of price slots
        price_slots = self._build_price_slots(
            today_prices, tomorrow_prices, today_start, now, slot_duration, slots_per_hour
        )

        if not price_slots:
            _LOGGER.warning("No price data available for scheduling")
            return []

        _LOGGER.debug(
            "Scheduling with %d price slots, frequency=%dh, duration=%dm, "
            "low_threshold=%.3f, high_threshold=%.3f",
            len(price_slots),
            heating_frequency_hours,
            heating_duration_minutes,
            price_threshold,
            high_price_threshold,
        )

        # Step 1: Mark all slots below price_threshold as HEATING
        heating_count = 0
        for ps in price_slots:
            if ps.price < price_threshold:
                ps.status = SlotStatus.HEATING
                heating_count += 1

        _LOGGER.debug("Marked %d slots as HEATING (below threshold %.3f)", heating_count, price_threshold)

        # Step 2: Mark all slots above high_price_threshold as COOLING
        cooling_count = 0
        for ps in price_slots:
            if ps.status == SlotStatus.UNMARKED and ps.price > high_price_threshold:
                ps.status = SlotStatus.COOLING
                cooling_count += 1

        _LOGGER.debug("Marked %d slots as COOLING (above threshold %.3f)", cooling_count, high_price_threshold)

        # Step 3 & 4: Find peaks and create cooling intervals with heating on sides
        duration = timedelta(minutes=heating_duration_minutes)
        max_gap = timedelta(hours=heating_frequency_hours)

        iteration = 0
        max_iterations = 100  # Safety limit

        while iteration < max_iterations:
            iteration += 1

            # Find the longest unmarked interval
            longest_gap = self._find_longest_unmarked_gap(price_slots)

            if longest_gap is None or longest_gap["duration"] <= max_gap:
                _LOGGER.debug(
                    "No unmarked gap exceeds %.1fh, stopping iteration",
                    heating_frequency_hours
                )
                break

            _LOGGER.debug(
                "Iteration %d: Found unmarked gap of %.1fh from %s to %s",
                iteration,
                longest_gap["duration"].total_seconds() / 3600,
                longest_gap["start"].strftime("%d %H:%M"),
                longest_gap["end"].strftime("%d %H:%M"),
            )

            # Find highest priced unmarked slot in this gap
            gap_slots = [
                ps for ps in price_slots
                if ps.status == SlotStatus.UNMARKED
                and ps.start >= longest_gap["start"]
                and ps.start < longest_gap["end"]
            ]

            if not gap_slots:
                break

            peak_slot = max(gap_slots, key=lambda x: x.price)
            _LOGGER.debug(
                "Peak price in gap: %s at %.3f",
                peak_slot.start.strftime("%d %H:%M"), peak_slot.price
            )

            # Center a cooling interval of heating_frequency_hours around the peak
            half_interval = timedelta(hours=heating_frequency_hours / 2)
            cooling_start = peak_slot.start - half_interval
            cooling_end = peak_slot.start + half_interval

            # Mark slots in the cooling interval
            for ps in price_slots:
                if (ps.status == SlotStatus.UNMARKED and
                    ps.start >= cooling_start and ps.start < cooling_end):
                    ps.status = SlotStatus.COOLING

            # Determine data boundaries
            data_start = price_slots[0].start
            data_end = price_slots[-1].end

            # Calculate heating periods on both sides
            heating_before_end = cooling_start
            heating_before_start = heating_before_end - duration
            heating_after_start = cooling_end
            heating_after_end = heating_after_start + duration

            # Check if heating periods fall outside data range
            can_heat_before = heating_before_start >= data_start
            can_heat_after = heating_after_end <= data_end

            if can_heat_before and can_heat_after:
                # Normal case - place heating on both sides
                self._mark_heating_period(price_slots, heating_before_start, heating_before_end)
                self._mark_heating_period(price_slots, heating_after_start, heating_after_end)
            elif can_heat_before and not can_heat_after:
                # Can't heat after - extend heating before to compensate
                extended_before_start = heating_before_end - (duration * 2)
                _LOGGER.debug(
                    "Peak near end of data, extending heating before: %s to %s",
                    extended_before_start.strftime("%d %H:%M"),
                    heating_before_end.strftime("%d %H:%M")
                )
                self._mark_heating_period(price_slots, extended_before_start, heating_before_end)
            elif not can_heat_before and can_heat_after:
                # Can't heat before - extend heating after to compensate
                extended_after_end = heating_after_start + (duration * 2)
                _LOGGER.debug(
                    "Peak near start of data, extending heating after: %s to %s",
                    heating_after_start.strftime("%d %H:%M"),
                    extended_after_end.strftime("%d %H:%M")
                )
                self._mark_heating_period(price_slots, heating_after_start, extended_after_end)
            else:
                # Can't heat on either side - just mark what we can
                _LOGGER.warning(
                    "Peak at %s: cannot place heating on either side of cooling interval",
                    peak_slot.start.strftime("%d %H:%M")
                )
                self._mark_heating_period(price_slots, heating_before_start, heating_before_end)
                self._mark_heating_period(price_slots, heating_after_start, heating_after_end)

        # Convert marked slots to HeatingSlot objects
        slots = self._create_heating_slots(price_slots)

        _LOGGER.debug("Final schedule: %d heating slots", len(slots))
        for slot in slots:
            _LOGGER.debug(
                "  %s to %s (%s)",
                slot.start.strftime("%Y-%m-%d %H:%M"),
                slot.end.strftime("%Y-%m-%d %H:%M"),
                slot.reason,
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

    def _find_longest_unmarked_gap(
        self, price_slots: list[PriceSlot]
    ) -> dict | None:
        """Find the longest continuous gap of unmarked slots."""
        if not price_slots:
            return None

        longest_gap = None
        current_gap_start = None
        current_gap_end = None

        for ps in price_slots:
            if ps.status == SlotStatus.UNMARKED:
                if current_gap_start is None:
                    current_gap_start = ps.start
                current_gap_end = ps.end
            else:
                # Gap ended, check if it's the longest
                if current_gap_start is not None:
                    gap_duration = current_gap_end - current_gap_start
                    if longest_gap is None or gap_duration > longest_gap["duration"]:
                        longest_gap = {
                            "start": current_gap_start,
                            "end": current_gap_end,
                            "duration": gap_duration,
                        }
                current_gap_start = None
                current_gap_end = None

        # Check final gap
        if current_gap_start is not None:
            gap_duration = current_gap_end - current_gap_start
            if longest_gap is None or gap_duration > longest_gap["duration"]:
                longest_gap = {
                    "start": current_gap_start,
                    "end": current_gap_end,
                    "duration": gap_duration,
                }

        return longest_gap

    def _mark_heating_period(
        self,
        price_slots: list[PriceSlot],
        start: datetime,
        end: datetime,
    ) -> None:
        """Mark slots in a time range as HEATING (if not already COOLING)."""
        for ps in price_slots:
            # Check if this slot overlaps with the heating period
            if ps.start < end and ps.end > start:
                if ps.status != SlotStatus.COOLING:
                    ps.status = SlotStatus.HEATING

    def _create_heating_slots(
        self, price_slots: list[PriceSlot]
    ) -> list[HeatingSlot]:
        """Create HeatingSlot objects from consecutive HEATING slots."""
        slots: list[HeatingSlot] = []

        current_start = None
        current_end = None

        for ps in price_slots:
            if ps.status == SlotStatus.HEATING:
                if current_start is None:
                    current_start = ps.start
                current_end = ps.end
            else:
                # Heating block ended
                if current_start is not None:
                    slots.append(HeatingSlot(
                        start=current_start,
                        end=current_end,
                        reason="scheduled",
                    ))
                current_start = None
                current_end = None

        # Don't forget the last block
        if current_start is not None:
            slots.append(HeatingSlot(
                start=current_start,
                end=current_end,
                reason="scheduled",
            ))

        return slots
