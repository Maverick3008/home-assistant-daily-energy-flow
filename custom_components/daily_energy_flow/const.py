"""Constants for the Daily Energy Flow integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "daily_energy_flow"
DEFAULT_NAME: Final = "Daily Energy Flow"
DEFAULT_UPDATE_INTERVAL: Final = 30
STORE_VERSION: Final = 1
STORE_SAVE_INTERVAL_SECONDS: Final = 300

CONF_NAME: Final = "name"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_CURRENCY: Final = "currency"
CONF_PRICE_ENTITY: Final = "price_entity"
CONF_PRICE_UNIT: Final = "price_unit"

# Live power sources in W. These are used only for the current power sensors.
CONF_SOLAR_POWER_ENTITIES: Final = "solar_power_entities"
CONF_GRID_MODE: Final = "grid_mode"
CONF_GRID_POWER_ENTITIES: Final = "grid_power_entities"
CONF_GRID_IMPORT_POWER_ENTITIES: Final = "grid_import_power_entities"
CONF_GRID_EXPORT_POWER_ENTITIES: Final = "grid_export_power_entities"
CONF_BATTERY_MODE: Final = "battery_mode"
CONF_BATTERY_POWER_ENTITIES: Final = "battery_power_entities"
CONF_BATTERY_CHARGE_POWER_ENTITIES: Final = "battery_charge_power_entities"
CONF_BATTERY_DISCHARGE_POWER_ENTITIES: Final = "battery_discharge_power_entities"

# Existing daily energy sources in kWh/Wh. These are used for all daily kWh,
# percentage and cost calculations.
CONF_SOLAR_ENERGY_ENTITIES: Final = "solar_energy_entities"
CONF_GRID_IMPORT_ENERGY_ENTITIES: Final = "grid_import_energy_entities"
CONF_GRID_EXPORT_ENERGY_ENTITIES: Final = "grid_export_energy_entities"
CONF_BATTERY_CHARGE_ENERGY_ENTITIES: Final = "battery_charge_energy_entities"
CONF_BATTERY_DISCHARGE_ENERGY_ENTITIES: Final = "battery_discharge_energy_entities"

PRICE_UNIT_CURRENCY_PER_KWH: Final = "currency_per_kwh"
PRICE_UNIT_MINOR_PER_KWH: Final = "minor_per_kwh"

GRID_MODE_COMBINED_IMPORT_POSITIVE: Final = "combined_import_positive"
GRID_MODE_COMBINED_EXPORT_POSITIVE: Final = "combined_export_positive"
GRID_MODE_SEPARATE: Final = "separate"

BATTERY_MODE_NONE: Final = "none"
BATTERY_MODE_COMBINED_DISCHARGE_POSITIVE: Final = "combined_discharge_positive"
BATTERY_MODE_COMBINED_CHARGE_POSITIVE: Final = "combined_charge_positive"
BATTERY_MODE_SEPARATE: Final = "separate"

SAMPLE_SOLAR_POWER: Final = "solar_production_power"
SAMPLE_GRID_IMPORT_POWER: Final = "grid_import_power"
SAMPLE_GRID_EXPORT_POWER: Final = "grid_export_power"
SAMPLE_BATTERY_CHARGE_POWER: Final = "battery_charge_power"
SAMPLE_BATTERY_DISCHARGE_POWER: Final = "battery_discharge_power"
SAMPLE_HOUSE_CONSUMPTION_POWER: Final = "house_consumption_power"
SAMPLE_PV_SELF_CONSUMPTION_POWER: Final = "pv_self_consumption_power"
SAMPLE_GRID_IMPORT_COST_RATE: Final = "grid_import_cost_rate"

TOTAL_SOLAR_ENERGY: Final = "solar_production_energy"
TOTAL_GRID_IMPORT_ENERGY: Final = "grid_import_energy"
TOTAL_GRID_EXPORT_ENERGY: Final = "grid_export_energy"
TOTAL_BATTERY_CHARGE_ENERGY: Final = "battery_charge_energy"
TOTAL_BATTERY_DISCHARGE_ENERGY: Final = "battery_discharge_energy"
TOTAL_HOUSE_CONSUMPTION_ENERGY: Final = "house_consumption_energy"
TOTAL_PV_SELF_CONSUMPTION_ENERGY: Final = "pv_self_consumption_energy"
TOTAL_GRID_IMPORT_COST: Final = "grid_import_cost"

DERIVED_AUTARKY_PERCENT: Final = "autarky_percent"
DERIVED_PV_SELF_CONSUMPTION_PERCENT: Final = "pv_self_consumption_percent"

SAMPLE_KEYS = [
    SAMPLE_SOLAR_POWER,
    SAMPLE_GRID_IMPORT_POWER,
    SAMPLE_GRID_EXPORT_POWER,
    SAMPLE_BATTERY_CHARGE_POWER,
    SAMPLE_BATTERY_DISCHARGE_POWER,
    SAMPLE_HOUSE_CONSUMPTION_POWER,
    SAMPLE_PV_SELF_CONSUMPTION_POWER,
    SAMPLE_GRID_IMPORT_COST_RATE,
]

ENERGY_KEYS = [
    TOTAL_SOLAR_ENERGY,
    TOTAL_GRID_IMPORT_ENERGY,
    TOTAL_GRID_EXPORT_ENERGY,
    TOTAL_BATTERY_CHARGE_ENERGY,
    TOTAL_BATTERY_DISCHARGE_ENERGY,
    TOTAL_HOUSE_CONSUMPTION_ENERGY,
    TOTAL_PV_SELF_CONSUMPTION_ENERGY,
]

INVALID_STATES: Final = {"unknown", "unavailable", "none", "None", ""}
