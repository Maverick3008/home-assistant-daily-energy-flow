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
    CONF_BATTERY_CHARGE_ENERGY_ENTITIES,
    CONF_BATTERY_CHARGE_POWER_ENTITIES,
    CONF_BATTERY_DISCHARGE_ENERGY_ENTITIES,
    CONF_BATTERY_DISCHARGE_POWER_ENTITIES,
    CONF_BATTERY_MODE,
    CONF_BATTERY_POWER_ENTITIES,
    CONF_GRID_EXPORT_ENERGY_ENTITIES,
    CONF_GRID_EXPORT_POWER_ENTITIES,
    CONF_GRID_IMPORT_ENERGY_ENTITIES,
    CONF_GRID_IMPORT_POWER_ENTITIES,
    CONF_GRID_MODE,
    CONF_GRID_POWER_ENTITIES,
    CONF_PRICE_ENTITY,
    CONF_PRICE_UNIT,
    CONF_SOLAR_ENERGY_ENTITIES,
    CONF_SOLAR_POWER_ENTITIES,
    CONF_UPDATE_INTERVAL,
    DERIVED_AUTARKY_PERCENT,
    DERIVED_PV_SELF_CONSUMPTION_PERCENT,
    DOMAIN,
    ENERGY_KEYS,
    GRID_MODE_COMBINED_EXPORT_POSITIVE,
    GRID_MODE_COMBINED_IMPORT_POSITIVE,
    GRID_MODE_SEPARATE,
    INVALID_STATES,
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
    TOTAL_BATTERY_CHARGE_ENERGY,
    TOTAL_BATTERY_DISCHARGE_ENERGY,
    TOTAL_GRID_EXPORT_ENERGY,
    TOTAL_GRID_IMPORT_COST,
    TOTAL_GRID_IMPORT_ENERGY,
    TOTAL_HOUSE_CONSUMPTION_ENERGY,
    TOTAL_PV_SELF_CONSUMPTION_ENERGY,
    TOTAL_SOLAR_ENERGY,
)

Listener = Callable[[], None]


WH_UNITS = {"wh", "watt hour", "watt-hour", "watt_hours"}
KWH_UNITS = {"kwh", "kilowatt hour", "kilowatt-hour", "kilowatt_hours"}
MWH_UNITS = {"mwh", "megawatt hour", "megawatt-hour", "megawatt_hours"}


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
    """Read live power values and calculate daily values from existing energy sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the manager."""
        self.hass = hass
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}_{entry.entry_id}.json")
        self._lock = asyncio.Lock()
        self._unsubs: list[Callable[[], None]] = []
        self._listeners: list[Listener] = []
        self._last_save: datetime | None = None
        self._sample: dict[str, float] = {key: 0.0 for key in SAMPLE_KEYS}
        self._energy: dict[str, float] = {key: 0.0 for key in ENERGY_KEYS}
        self._grid_import_cost: float = 0.0
        self._last_grid_import_energy_kwh: float | None = None
        self._last_price: float = 0.0
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
        self._energy = self._read_energy()
        self._last_price = self._read_price()
        if self._last_grid_import_energy_kwh is None:
            self._last_grid_import_energy_kwh = self._energy[TOTAL_GRID_IMPORT_ENERGY]
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
        """Handle periodic updates and variable-price cost accumulation."""
        self.hass.async_create_task(self.async_update(now=now))

    @callback
    def _handle_midnight(self, now: datetime) -> None:
        """Handle daily cost reset."""
        self.hass.async_create_task(self.async_reset_day(now=now))

    async def async_update(self, now: datetime | None = None, *, force_save: bool = False) -> None:
        """Update live values, read daily energy values and accumulate import cost."""
        async with self._lock:
            now = now or dt_util.now()

            if now.date().isoformat() != self._day:
                await self._async_reset_locked(now)
                self._notify_listeners()
                return

            current_energy = self._read_energy()
            current_sample = self._read_sample()
            current_price = self._read_price()

            self._accumulate_grid_import_cost(current_energy[TOTAL_GRID_IMPORT_ENERGY])

            self._energy = current_energy
            self._sample = current_sample
            self._last_price = current_price
            self._last_grid_import_energy_kwh = current_energy[TOTAL_GRID_IMPORT_ENERGY]
            await self._async_save_if_needed(now, force=force_save)

        self._notify_listeners()

    async def async_reset_day(self, now: datetime | None = None) -> None:
        """Reset the daily cost accumulator at midnight."""
        async with self._lock:
            now = now or dt_util.now()
            await self._async_reset_locked(now)
        self._notify_listeners()

    async def _async_reset_locked(self, now: datetime) -> None:
        """Reset daily cost. The lock must already be held."""
        self._day = now.date().isoformat()
        self._sample = self._read_sample()
        self._energy = self._read_energy()
        self._grid_import_cost = 0.0
        self._last_grid_import_energy_kwh = self._energy[TOTAL_GRID_IMPORT_ENERGY]
        self._last_price = self._read_price()
        await self._async_save_if_needed(now, force=True)

    async def _async_restore(self, now: datetime) -> None:
        """Restore today's variable-price grid import cost from storage."""
        stored = await self.store.async_load()
        if not stored or stored.get("day") != now.date().isoformat():
            self._day = now.date().isoformat()
            self._grid_import_cost = 0.0
            self._last_grid_import_energy_kwh = None
            self._last_price = 0.0
            return

        self._day = stored.get("day", now.date().isoformat())
        self._grid_import_cost = float(stored.get("grid_import_cost", 0.0))
        last_import = stored.get("last_grid_import_energy_kwh")
        self._last_grid_import_energy_kwh = float(last_import) if last_import is not None else None
        self._last_price = float(stored.get("last_price", 0.0))

    async def _async_save_if_needed(self, now: datetime, *, force: bool = False) -> None:
        """Persist variable-price cost state occasionally and on unload/reset."""
        if not force and self._last_save is not None:
            if (now - self._last_save).total_seconds() < STORE_SAVE_INTERVAL_SECONDS:
                return

        await self.store.async_save(
            {
                "day": self._day,
                "grid_import_cost": self._grid_import_cost,
                "last_grid_import_energy_kwh": self._last_grid_import_energy_kwh,
                "last_price": self._last_price,
            }
        )
        self._last_save = now

    def _accumulate_grid_import_cost(self, current_import_energy_kwh: float) -> None:
        """Accumulate grid import cost from the delta of an existing daily import energy sensor."""
        if self._last_grid_import_energy_kwh is None:
            self._last_grid_import_energy_kwh = current_import_energy_kwh
            return

        delta_kwh = current_import_energy_kwh - self._last_grid_import_energy_kwh
        if delta_kwh < -0.001:
            # A daily sensor may reset while Home Assistant is running. Treat the
            # new value as the current day's import since the reset.
            delta_kwh = max(0.0, current_import_energy_kwh)

        if 0.0 < delta_kwh < 1000.0:
            self._grid_import_cost += delta_kwh * max(0.0, self._last_price)

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
        entity_ids.extend(_as_list(config.get(CONF_SOLAR_ENERGY_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_GRID_IMPORT_ENERGY_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_GRID_EXPORT_ENERGY_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_BATTERY_CHARGE_ENERGY_ENTITIES)))
        entity_ids.extend(_as_list(config.get(CONF_BATTERY_DISCHARGE_ENERGY_ENTITIES)))
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

    def _state_energy_kwh(self, entity_id: str | None) -> float:
        """Return an energy state converted to kWh."""
        if not entity_id:
            return 0.0
        state = self.hass.states.get(entity_id)
        if state is None or state.state in INVALID_STATES:
            return 0.0
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return 0.0

        unit = str(state.attributes.get("unit_of_measurement", "kWh")).strip().lower()
        if unit in WH_UNITS:
            return value / 1000
        if unit in MWH_UNITS:
            return value * 1000
        # kWh is the expected unit. If the source has no unit, assume kWh.
        return value

    def _sum_entities(self, config_key: str) -> float:
        """Sum numeric states from a config entity list."""
        return sum(self._state_float(entity_id) for entity_id in _as_list(self.config.get(config_key)))

    def _sum_energy_entities(self, config_key: str) -> float:
        """Sum energy states from a config entity list and convert them to kWh."""
        return sum(self._state_energy_kwh(entity_id) for entity_id in _as_list(self.config.get(config_key)))

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

    def _read_energy(self) -> dict[str, float]:
        """Read existing daily energy sensors and calculate derived daily energy values."""
        solar_energy = max(0.0, self._sum_energy_entities(CONF_SOLAR_ENERGY_ENTITIES))
        grid_import_energy = max(0.0, self._sum_energy_entities(CONF_GRID_IMPORT_ENERGY_ENTITIES))
        grid_export_energy = max(0.0, self._sum_energy_entities(CONF_GRID_EXPORT_ENERGY_ENTITIES))

        if self.config.get(CONF_BATTERY_MODE) == BATTERY_MODE_NONE:
            battery_charge_energy = 0.0
            battery_discharge_energy = 0.0
        else:
            battery_charge_energy = max(0.0, self._sum_energy_entities(CONF_BATTERY_CHARGE_ENERGY_ENTITIES))
            battery_discharge_energy = max(0.0, self._sum_energy_entities(CONF_BATTERY_DISCHARGE_ENERGY_ENTITIES))

        house_consumption_energy = max(
            0.0,
            solar_energy
            + grid_import_energy
            - grid_export_energy
            + battery_discharge_energy
            - battery_charge_energy,
        )
        pv_self_consumption_energy = _clamp(solar_energy - grid_export_energy, 0.0, solar_energy)

        return {
            TOTAL_SOLAR_ENERGY: solar_energy,
            TOTAL_GRID_IMPORT_ENERGY: grid_import_energy,
            TOTAL_GRID_EXPORT_ENERGY: grid_export_energy,
            TOTAL_BATTERY_CHARGE_ENERGY: battery_charge_energy,
            TOTAL_BATTERY_DISCHARGE_ENERGY: battery_discharge_energy,
            TOTAL_HOUSE_CONSUMPTION_ENERGY: house_consumption_energy,
            TOTAL_PV_SELF_CONSUMPTION_ENERGY: pv_self_consumption_energy,
        }

    def value(self, key: str) -> float | None:
        """Return a sample, daily energy, cost or derived value."""
        if key in self._sample:
            return self._sample[key]
        if key in self._energy:
            return self._energy[key]
        if key == TOTAL_GRID_IMPORT_COST:
            return self._grid_import_cost

        if key == DERIVED_AUTARKY_PERCENT:
            house = self._energy[TOTAL_HOUSE_CONSUMPTION_ENERGY]
            grid_import = self._energy[TOTAL_GRID_IMPORT_ENERGY]
            if house <= 0:
                return 0.0
            return _clamp((1 - (grid_import / house)) * 100, 0.0, 100.0)

        if key == DERIVED_PV_SELF_CONSUMPTION_PERCENT:
            solar = self._energy[TOTAL_SOLAR_ENERGY]
            self_consumed = self._energy[TOTAL_PV_SELF_CONSUMPTION_ENERGY]
            if solar <= 0:
                return 0.0
            return _clamp((self_consumed / solar) * 100, 0.0, 100.0)

        return None
