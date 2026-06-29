"""Sensor platform for Daily Energy Flow."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CURRENCY,
    DERIVED_AUTARKY_PERCENT,
    DERIVED_PV_SELF_CONSUMPTION_PERCENT,
    DOMAIN,
    SAMPLE_BATTERY_CHARGE_POWER,
    SAMPLE_BATTERY_DISCHARGE_POWER,
    SAMPLE_GRID_EXPORT_POWER,
    SAMPLE_GRID_IMPORT_COST_RATE,
    SAMPLE_GRID_IMPORT_POWER,
    SAMPLE_HOUSE_CONSUMPTION_POWER,
    SAMPLE_PV_SELF_CONSUMPTION_POWER,
    SAMPLE_SOLAR_POWER,
    TOTAL_BATTERY_CHARGE_ENERGY,
    TOTAL_BATTERY_DISCHARGE_ENERGY,
    TOTAL_GRID_EXPORT_ENERGY,
    TOTAL_GRID_IMPORT_COST,
    TOTAL_GRID_IMPORT_ENERGY,
    TOTAL_HOUSE_CONSUMPTION_ENERGY,
    TOTAL_PV_SELF_CONSUMPTION_ENERGY,
    TOTAL_SOLAR_ENERGY,
)
from .manager import DailyEnergyFlowManager


@dataclass(frozen=True, kw_only=True)
class DailyEnergyFlowSensorEntityDescription(SensorEntityDescription):
    """Entity description for Daily Energy Flow sensors."""

    value_key: str
    precision: int = 2


POWER_SENSOR_DESCRIPTIONS: tuple[DailyEnergyFlowSensorEntityDescription, ...] = (
    DailyEnergyFlowSensorEntityDescription(
        key=SAMPLE_HOUSE_CONSUMPTION_POWER,
        translation_key=SAMPLE_HOUSE_CONSUMPTION_POWER,
        value_key=SAMPLE_HOUSE_CONSUMPTION_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-lightning-bolt",
        precision=0,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=SAMPLE_SOLAR_POWER,
        translation_key=SAMPLE_SOLAR_POWER,
        value_key=SAMPLE_SOLAR_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power-variant",
        precision=0,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=SAMPLE_GRID_IMPORT_POWER,
        translation_key=SAMPLE_GRID_IMPORT_POWER,
        value_key=SAMPLE_GRID_IMPORT_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-import",
        precision=0,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=SAMPLE_GRID_EXPORT_POWER,
        translation_key=SAMPLE_GRID_EXPORT_POWER,
        value_key=SAMPLE_GRID_EXPORT_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:transmission-tower-export",
        precision=0,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=SAMPLE_BATTERY_CHARGE_POWER,
        translation_key=SAMPLE_BATTERY_CHARGE_POWER,
        value_key=SAMPLE_BATTERY_CHARGE_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-up",
        precision=0,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=SAMPLE_BATTERY_DISCHARGE_POWER,
        translation_key=SAMPLE_BATTERY_DISCHARGE_POWER,
        value_key=SAMPLE_BATTERY_DISCHARGE_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-down",
        precision=0,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=SAMPLE_PV_SELF_CONSUMPTION_POWER,
        translation_key=SAMPLE_PV_SELF_CONSUMPTION_POWER,
        value_key=SAMPLE_PV_SELF_CONSUMPTION_POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        precision=0,
    ),
)

ENERGY_SENSOR_DESCRIPTIONS: tuple[DailyEnergyFlowSensorEntityDescription, ...] = (
    DailyEnergyFlowSensorEntityDescription(
        key=TOTAL_HOUSE_CONSUMPTION_ENERGY,
        translation_key=TOTAL_HOUSE_CONSUMPTION_ENERGY,
        value_key=TOTAL_HOUSE_CONSUMPTION_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:home-lightning-bolt-outline",
        precision=3,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=TOTAL_SOLAR_ENERGY,
        translation_key=TOTAL_SOLAR_ENERGY,
        value_key=TOTAL_SOLAR_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power-variant-outline",
        precision=3,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=TOTAL_GRID_IMPORT_ENERGY,
        translation_key=TOTAL_GRID_IMPORT_ENERGY,
        value_key=TOTAL_GRID_IMPORT_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-import",
        precision=3,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=TOTAL_GRID_EXPORT_ENERGY,
        translation_key=TOTAL_GRID_EXPORT_ENERGY,
        value_key=TOTAL_GRID_EXPORT_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:transmission-tower-export",
        precision=3,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=TOTAL_BATTERY_CHARGE_ENERGY,
        translation_key=TOTAL_BATTERY_CHARGE_ENERGY,
        value_key=TOTAL_BATTERY_CHARGE_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-up-outline",
        precision=3,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=TOTAL_BATTERY_DISCHARGE_ENERGY,
        translation_key=TOTAL_BATTERY_DISCHARGE_ENERGY,
        value_key=TOTAL_BATTERY_DISCHARGE_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-arrow-down-outline",
        precision=3,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=TOTAL_PV_SELF_CONSUMPTION_ENERGY,
        translation_key=TOTAL_PV_SELF_CONSUMPTION_ENERGY,
        value_key=TOTAL_PV_SELF_CONSUMPTION_ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:solar-power",
        precision=3,
    ),
)

PERCENT_SENSOR_DESCRIPTIONS: tuple[DailyEnergyFlowSensorEntityDescription, ...] = (
    DailyEnergyFlowSensorEntityDescription(
        key=DERIVED_AUTARKY_PERCENT,
        translation_key=DERIVED_AUTARKY_PERCENT,
        value_key=DERIVED_AUTARKY_PERCENT,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-percent",
        precision=1,
    ),
    DailyEnergyFlowSensorEntityDescription(
        key=DERIVED_PV_SELF_CONSUMPTION_PERCENT,
        translation_key=DERIVED_PV_SELF_CONSUMPTION_PERCENT,
        value_key=DERIVED_PV_SELF_CONSUMPTION_PERCENT,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:solar-power",
        precision=1,
    ),
)

COST_RATE_DESCRIPTION = DailyEnergyFlowSensorEntityDescription(
    key=SAMPLE_GRID_IMPORT_COST_RATE,
    translation_key=SAMPLE_GRID_IMPORT_COST_RATE,
    value_key=SAMPLE_GRID_IMPORT_COST_RATE,
    native_unit_of_measurement=None,
    state_class=SensorStateClass.MEASUREMENT,
    icon="mdi:cash-clock",
    precision=4,
)

COST_TOTAL_DESCRIPTION = DailyEnergyFlowSensorEntityDescription(
    key=TOTAL_GRID_IMPORT_COST,
    translation_key=TOTAL_GRID_IMPORT_COST,
    value_key=TOTAL_GRID_IMPORT_COST,
    native_unit_of_measurement=None,
    device_class=SensorDeviceClass.MONETARY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    icon="mdi:cash",
    precision=2,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Daily Energy Flow sensors."""
    manager: DailyEnergyFlowManager = hass.data[DOMAIN][entry.entry_id]

    currency = str({**entry.data, **entry.options}.get(CONF_CURRENCY, "EUR"))
    entities: list[DailyEnergyFlowSensor] = []

    for description in POWER_SENSOR_DESCRIPTIONS + ENERGY_SENSOR_DESCRIPTIONS + PERCENT_SENSOR_DESCRIPTIONS:
        entities.append(DailyEnergyFlowSensor(manager, entry, description))

    cost_rate_description = replace(COST_RATE_DESCRIPTION, native_unit_of_measurement=f"{currency}/h")
    cost_total_description = replace(COST_TOTAL_DESCRIPTION, native_unit_of_measurement=currency)
    entities.append(DailyEnergyFlowSensor(manager, entry, cost_rate_description))
    entities.append(DailyEnergyFlowSensor(manager, entry, cost_total_description))

    async_add_entities(entities)


class DailyEnergyFlowSensor(SensorEntity):
    """Daily Energy Flow sensor entity."""

    entity_description: DailyEnergyFlowSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        manager: DailyEnergyFlowManager,
        entry: ConfigEntry,
        description: DailyEnergyFlowSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.manager = manager
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Maverick3008",
            model="Daily Energy Flow",
        )
        self._attr_suggested_display_precision = description.precision

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.manager.available

    @property
    def native_value(self) -> float | None:
        """Return the native sensor value."""
        value = self.manager.value(self.entity_description.value_key)
        if value is None:
            return None
        return round(value, self.entity_description.precision)

    async def async_added_to_hass(self) -> None:
        """Subscribe to manager updates."""
        self.async_on_remove(self.manager.async_add_listener(self._handle_manager_update))

    @callback
    def _handle_manager_update(self) -> None:
        """Handle updated manager data."""
        self.async_write_ha_state()
