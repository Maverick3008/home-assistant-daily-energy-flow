"""Calculation manager for Daily Energy Flow."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    BATTERY_MODE_COMBINED_CHARGE_POSITIVE,
    BATTERY_MODE_COMBINED_DISCHARGE_POSITIVE,
    BATTERY_MODE_NONE,
    BATTERY_MODE_SEPARATE,
    CONF_BATTERY_CHARGE_POWER_ENTITIES,
    CONF_BATTERY_DISCHARGE_POWER_ENTITIES,
    CONF_BATTERY_MODE,
    CONF_BATTERY_POWER_ENTITIES,
    CONF_GRID_EXPORT_POWER_ENTITIES,
    CONF_GRID_IMPORT_POWER_ENTITIES,
    CONF_GRID_MODE,
    CONF_GRID_POWER_ENTITIES,
    CONF_PRICE_ENTITY,
    CONF_PRICE_UNIT,
    CONF_SOLAR_POWER_ENTITIES,
    CONF_UPDATE_INTERVAL,
    DERIVED_AUTARKY_PERCENT,
    DERIVED_PV_SELF_CONSUMPTION_PERCENT,
    DOMAIN,
    GRID_MODE_COMBINED_EXPORT_POSITIVE,
    GRID_MODE_COMBINED_IMPORT_POSITIVE,
    GRID_MODE_SEPARATE,
    INVALID_STATES,
    POWER_TO_ENERGY,
    PRICE_UNIT_MINOR_PER_KWH,
    SAMPLE_BATTERY_CHARGE_POWER,
    SAMPLE_BATTERY_DISCHARGE_POWER,
    SAMPLE_GRID_EXPORT_POWER,
    SAMPLE_GRID_IMPORT_COST_RATE,
    SAMPLE_GRID_IMPORT_POWER,
    SAMPLE_HOUSE_CONSUMPTION_POWER,
    SAMPLE_KEYS,
    SAMPLE_PV_SELF_CONSUMPTION_POWER,
    SAMPLE_SOLAR_POWER,
    STORE_SAVE_INTERVAL_SECONDS,
    STORE_VERSION,
    TOTAL_GRID_IMPORT_COST,
    TOTAL_GRID_IMPORT_ENERGY,
    TOTAL_HOUSE_CONSUMPTION_ENERGY,
    TOTAL_KEYS,
    TOTAL_PV_SELF_CONSUMPTION_ENERGY,
    TOTAL_SOLAR_ENERGY,
)

Listener = Callable[[], None]


def _as_list(value: Any) -> list[str]:
    """Return a config value as a list of entity IDs."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a value."""
    return max(minimum, min(maximum, value))


class DailyEnergyFlowManager:
    """Track power states and integrate daily energy/cost totals."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}_{entry.entry_id}.json")
        self._lock = asyncio.Lock()
        self._unsubs: list[Callable[[], None]] = []
        self._listeners: list[Listener] = []
        self._last_update: datetime | None = None
        self._last_save: datetime | None = None
        self._sample: dict[str, float] = {key: 0.0 for key in SAMPLE_KEYS}
        self._last_sample: dict[str, float] | None = None
        self._totals: dict[str, float] = {key: 0.0 for key in TOTAL_KEYS}
        self._day: str = dt_util.now().date().isoformat()
        self.available = False

    @property
    def config(self) -> dict[str, Any]:
        """Return merged config entry data and options."""
        return {**self.entry.data, **self.entry.options}

    async def async_start(self) -> None:
        """Start tracking entities and timers."""
        now = dt_util.now()
        await self._async_restore(now)
        self._sample = self._read_sample()
        self._last_sample = self._sample.copy()
        self._last_update = now
        self.available = True

        entity_ids = self._source_entity_ids()
        if entity_ids:
            self._unsubs.append(async_track_state_change_event(self.hass, entity_ids, self._handle_state_change))

        interval = int(self.config.get(CONF_UPDATE_INTERVAL, 30))
        self._unsubs.append(async_track_time_interval(self.hass, self._handle_interval, timedelta(seconds=interval)))
        self._unsubs.append(async_track_time_change(self.hass, self._handle_midnight, hour=0, minute=0, second=0))

    async def async_unload(self) -> None:
        """Unload the manager."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self.async_update(force_save=True)
        self._listeners.clear()
        self.available = False

    @callback
    def async_add_listener(self, listener: Listener) -> Callable[[], None]:
        """Add a listener that is called whenever values change."""
        self._listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    @callback
    def _notify_listeners(self) -> None:
        """Notify sensor entities."""
        for listener in list(self._listeners):
            listener()

    @callback
    def _handle_state_change(self, event: Event) -> None:
        """Handle a source entity state change."""
        self.hass.async_create_task(self.async_update())

    @callback
    def _handle_interval(self, now: datetime) -> None:
        """Handle periodic integration."""
        self.hass.async_create_task(self.async_update(now=now))

    @callback
    def _handle_midnight(self, now: datetime) -> None:
        """Handle daily reset."""
        self.hass.async_create_task(self.async_reset_day(now=now))

    async def async_update(self, now: datetime | None = None, *, force_save: bool = False) -> None:
        """Integrate values from the last sample to the current sample."""
        async with self._lock:
            now = now or dt_util.now()

            if now.date().isoformat() != self._day:
                # If the midnight callback was missed, start a fresh day rather than
                # estimating energy across a long Home Assistant downtime.
                await self._async_reset_locked(now)
                self._notify_listeners()
                return

            current_sample = self._read_sample()
            if self._last_update is not None and self._last_sample is not None:
                seconds = max(0.0, (now - self._last_update).total_seconds())
                if 0 < seconds < 6 * 3600:
                    hours = seconds / 3600
                    self._integrate(self._last_sample, current_sample, hours)

            self._sample = current_sample
            self._last_sample = current_sample.copy()
            self._last_update = now
            await self._async_save_if_needed(now, force=force_save)

        self._notify_listeners()

    async def async_reset_day(self, now: datetime | None = None) -> None:
        """Reset daily totals at midnight."""
        async with self._lock:
            now = now or dt_util.now()
            await self._async_reset_locked(now)
        self._notify_listeners()

    async def _async_reset_locked(self, now: datetime) -> None:
        """Reset totals. The lock must already be held."""
        self._day = now.date().isoformat()
        self._totals = {key: 0.0 for key in TOTAL_KEYS}
        self._sample = self._read_sample()
        self._last_sample = self._sample.copy()
        self._last_update = now
        await self._async_save_if_needed(now, force=True)

    async def _async_restore(self, now: datetime) -> None:
        """Restore today's totals from storage."""
        stored = await self.store.async_load()
        if not stored or stored.get("day") != now.date().isoformat():
            self._totals = {key: 0.0 for key in TOTAL_KEYS}
            self._day = now.date().isoformat()
            return

        self._day = stored.get("day", now.date().isoformat())
        raw_totals = stored.get("totals", {})
        self._totals = {key: float(raw_totals.get(key, 0.0)) for key in TOTAL_KEYS}

    async def _async_save_if_needed(self, now: datetime, *, force: bool = False) -> None:
        """Persist totals occasionally and on unload/reset."""
        if not force and self._last_save is not None:
            if (now - self._last_save).total_seconds() < STORE_SAVE_INTERVAL_SECONDS:
                return

        await self.store.async_save({"day": self._day, "totals": self._totals})
        self._last_save = now

    def _integrate(self, previous: dict[str, float], current: dict[str, float], hours: float) -> None:
        """Integrate power and cost values with the trapezoidal method."""
        for power_key, total_key in POWER_TO_ENERGY.items():
            average_watts = (previous.get(power_key, 0.0) + current.get(power_key, 0.0)) / 2
            self._totals[total_key] += max(0.0, average_watts) / 1000 * hours

        average_cost_rate = (
            previous.get(SAMPLE_GRID_IMPORT_COST_RATE, 0.0) + current.get(SAMPLE_GRID_IMPORT_COST_RATE, 0.0)
        ) / 2
        self._totals[TOTAL_GRID_IMPORT_COST] += max(0.0, average_cost_rate) * hours

    def _source_entity_ids(self) -> list[str]:
        """Return all source entity IDs used by the integration."""
        config = self.config
        entity_ids: list[str] = []
        entity_ids.extend(_as_list(config.get(CONF_PRICE_ENTITY)))
        entity_ids.extend(_as_list(config.get(CONF_SOLAR_POWER_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_GRID_POWER_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_GRID_IMPORT_POWER_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_GRID_EXPORT_POWER_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_BATTERY_POWER_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_BATTERY_CHARGE_POWER_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_BATTERY_DISCHARGE_POWER_ENTITIES)))
        return sorted(set(entity_ids))

    def _state_float(self, entity_id: str | None) -> float:
        """Return a state as float, or 0 for missing/unavailable values."""
        if not entity_id:
            return 0.0
        state = self.hass.states.get(entity_id)
        if state is None or state.state in INVALID_STATES:
            return 0.0
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return 0.0

    def _sum_entities(self, config_key: str) -> float:
        """Sum numeric states from a config entity list."""
        return sum(self._state_float(entity_id) for entity_id in _as_list(self.config.get(config_key)))

    def _read_price(self) -> float:
        """Read and normalize electricity price to currency/kWh."""
        price = self._state_float(str(self.config.get(CONF_PRICE_ENTITY, "")))
        if self.config.get(CONF_PRICE_UNIT) == PRICE_UNIT_MINOR_PER_KWH:
            return price / 100
        return price

    def _read_grid_power(self) -> tuple[float, float]:
        """Return grid import and export power in W."""
        mode = self.config.get(CONF_GRID_MODE)

        if mode == GRID_MODE_SEPARATE:
            return (
                max(0.0, self._sum_entities(CONF_GRID_IMPORT_POWER_ENTITIES)),
                max(0.0, self._sum_entities(CONF_GRID_EXPORT_POWER_ENTITIES)),
            )

        net_power = self._sum_entities(CONF_GRID_POWER_ENTITIES)
        if mode == GRID_MODE_COMBINED_EXPORT_POSITIVE:
            return max(0.0, -net_power), max(0.0, net_power)

        # Default: positive import, negative export.
        if mode == GRID_MODE_COMBINED_IMPORT_POSITIVE:
            return max(0.0, net_power), max(0.0, -net_power)

        return max(0.0, net_power), max(0.0, -net_power)

    def _read_battery_power(self) -> tuple[float, float]:
        """Return battery charging and discharging power in W."""
        mode = self.config.get(CONF_BATTERY_MODE)

        if mode == BATTERY_MODE_NONE:
            return 0.0, 0.0

        if mode == BATTERY_MODE_SEPARATE:
            return (
                max(0.0, self._sum_entities(CONF_BATTERY_CHARGE_POWER_ENTITIES)),
                max(0.0, self._sum_entities(CONF_BATTERY_DISCHARGE_POWER_ENTITIES)),
            )

        charge_power = 0.0
        discharge_power = 0.0
        for entity_id in _as_list(self.config.get(CONF_BATTERY_POWER_ENTITIES)):
            value = self._state_float(entity_id)
            if mode == BATTERY_MODE_COMBINED_CHARGE_POSITIVE:
                charge_power += max(0.0, value)
                discharge_power += max(0.0, -value)
            elif mode == BATTERY_MODE_COMBINED_DISCHARGE_POSITIVE:
                discharge_power += max(0.0, value)
                charge_power += max(0.0, -value)

        return charge_power, discharge_power

    def _read_sample(self) -> dict[str, float]:
        """Read all current source values and calculate derived power values."""
        solar_power = max(0.0, self._sum_entities(CONF_SOLAR_POWER_ENTITIES))
        grid_import_power, grid_export_power = self._read_grid_power()
        battery_charge_power, battery_discharge_power = self._read_battery_power()
        price = self._read_price()

        house_consumption_power = max(
            0.0,
            solar_power + grid_import_power - grid_export_power + battery_discharge_power - battery_charge_power,
        )
        pv_self_consumption_power = _clamp(solar_power - grid_export_power, 0.0, solar_power)
        grid_import_cost_rate = (grid_import_power / 1000) * price

        return {
            SAMPLE_SOLAR_POWER: solar_power,
            SAMPLE_GRID_IMPORT_POWER: grid_import_power,
            SAMPLE_GRID_EXPORT_POWER: grid_export_power,
            SAMPLE_BATTERY_CHARGE_POWER: battery_charge_power,
            SAMPLE_BATTERY_DISCHARGE_POWER: battery_discharge_power,
            SAMPLE_HOUSE_CONSUMPTION_POWER: house_consumption_power,
            SAMPLE_PV_SELF_CONSUMPTION_POWER: pv_self_consumption_power,
            SAMPLE_GRID_IMPORT_COST_RATE: grid_import_cost_rate,
        }

    def value(self, key: str) -> float | None:
        """Return a sample, total or derived value."""
        if key in self._sample:
            return self._sample[key]
        if key in self._totals:
            return self._totals[key]

        if key == DERIVED_AUTARKY_PERCENT:
            house = self._totals[TOTAL_HOUSE_CONSUMPTION_ENERGY]
            grid_import = self._totals[TOTAL_GRID_IMPORT_ENERGY]
            if house <= 0:
                return 0.0
            return _clamp((1 - (grid_import / house)) * 100, 0.0, 100.0)

        if key == DERIVED_PV_SELF_CONSUMPTION_PERCENT:
            solar = self._totals[TOTAL_SOLAR_ENERGY]
            self_consumed = self._totals[TOTAL_PV_SELF_CONSUMPTION_ENERGY]
            if solar <= 0:
                return 0.0
            return _clamp((self_consumed / solar) * 100, 0.0, 100.0)

        return None
