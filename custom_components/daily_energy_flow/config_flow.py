"""Config flow for Daily Energy Flow."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import slugify

from .const import (
    BATTERY_MODE_COMBINED_CHARGE_POSITIVE,
    BATTERY_MODE_COMBINED_DISCHARGE_POSITIVE,
    BATTERY_MODE_NONE,
    BATTERY_MODE_SEPARATE,
    CONF_BATTERY_CHARGE_POWER_ENTITIES,
    CONF_BATTERY_DISCHARGE_POWER_ENTITIES,
    CONF_BATTERY_MODE,
    CONF_BATTERY_POWER_ENTITIES,
    CONF_CURRENCY,
    CONF_GRID_EXPORT_POWER_ENTITIES,
    CONF_GRID_IMPORT_POWER_ENTITIES,
    CONF_GRID_MODE,
    CONF_GRID_POWER_ENTITIES,
    CONF_NAME,
    CONF_PRICE_ENTITY,
    CONF_PRICE_UNIT,
    CONF_SOLAR_POWER_ENTITIES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    GRID_MODE_COMBINED_EXPORT_POSITIVE,
    GRID_MODE_COMBINED_IMPORT_POSITIVE,
    GRID_MODE_SEPARATE,
    PRICE_UNIT_CURRENCY_PER_KWH,
    PRICE_UNIT_MINOR_PER_KWH,
)

POWER_ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["sensor", "number", "input_number"], multiple=True)
)

PRICE_ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["sensor", "number", "input_number"])
)


def _as_list(value: Any) -> list[str]:
    """Return a config value as a list of entity IDs."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _select(translation_key: str, options: list[str]) -> selector.SelectSelector:
    """Build a translated dropdown selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=selector.SelectSelectorMode.DROPDOWN,
            translation_key=translation_key,
        )
    )


def _basic_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the first step schema."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_UPDATE_INTERVAL, default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)): selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=300, step=5, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Required(CONF_CURRENCY, default=defaults.get(CONF_CURRENCY, "EUR")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["EUR", "USD", "GBP", "CHF", "DKK", "NOK", "SEK", "PLN", "CZK"],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    custom_value=True,
                )
            ),
            vol.Required(CONF_PRICE_UNIT, default=defaults.get(CONF_PRICE_UNIT, PRICE_UNIT_CURRENCY_PER_KWH)): _select(
                CONF_PRICE_UNIT,
                [PRICE_UNIT_CURRENCY_PER_KWH, PRICE_UNIT_MINOR_PER_KWH],
            ),
            vol.Required(CONF_GRID_MODE, default=defaults.get(CONF_GRID_MODE, GRID_MODE_COMBINED_IMPORT_POSITIVE)): _select(
                CONF_GRID_MODE,
                [GRID_MODE_COMBINED_IMPORT_POSITIVE, GRID_MODE_COMBINED_EXPORT_POSITIVE, GRID_MODE_SEPARATE],
            ),
            vol.Required(CONF_BATTERY_MODE, default=defaults.get(CONF_BATTERY_MODE, BATTERY_MODE_COMBINED_DISCHARGE_POSITIVE)): _select(
                CONF_BATTERY_MODE,
                [
                    BATTERY_MODE_COMBINED_DISCHARGE_POSITIVE,
                    BATTERY_MODE_COMBINED_CHARGE_POSITIVE,
                    BATTERY_MODE_SEPARATE,
                    BATTERY_MODE_NONE,
                ],
            ),
        }
    )


def _sources_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the source entity schema for the selected modes."""
    fields: dict[Any, Any] = {
        vol.Required(CONF_PRICE_ENTITY, default=defaults.get(CONF_PRICE_ENTITY)): PRICE_ENTITY_SELECTOR,
        vol.Required(CONF_SOLAR_POWER_ENTITIES, default=_as_list(defaults.get(CONF_SOLAR_POWER_ENTITIES))): POWER_ENTITY_SELECTOR,
    }

    if defaults.get(CONF_GRID_MODE) == GRID_MODE_SEPARATE:
        fields[vol.Required(CONF_GRID_IMPORT_POWER_ENTITIES, default=_as_list(defaults.get(CONF_GRID_IMPORT_POWER_ENTITIES)))] = POWER_ENTITY_SELECTOR
        fields[vol.Optional(CONF_GRID_EXPORT_POWER_ENTITIES, default=_as_list(defaults.get(CONF_GRID_EXPORT_POWER_ENTITIES)))] = POWER_ENTITY_SELECTOR
    else:
        fields[vol.Required(CONF_GRID_POWER_ENTITIES, default=_as_list(defaults.get(CONF_GRID_POWER_ENTITIES)))] = POWER_ENTITY_SELECTOR

    battery_mode = defaults.get(CONF_BATTERY_MODE)
    if battery_mode == BATTERY_MODE_SEPARATE:
        fields[vol.Optional(CONF_BATTERY_CHARGE_POWER_ENTITIES, default=_as_list(defaults.get(CONF_BATTERY_CHARGE_POWER_ENTITIES)))] = POWER_ENTITY_SELECTOR
        fields[vol.Optional(CONF_BATTERY_DISCHARGE_POWER_ENTITIES, default=_as_list(defaults.get(CONF_BATTERY_DISCHARGE_POWER_ENTITIES)))] = POWER_ENTITY_SELECTOR
    elif battery_mode != BATTERY_MODE_NONE:
        fields[vol.Optional(CONF_BATTERY_POWER_ENTITIES, default=_as_list(defaults.get(CONF_BATTERY_POWER_ENTITIES)))] = POWER_ENTITY_SELECTOR

    return vol.Schema(fields)


def _validate_sources(data: dict[str, Any]) -> dict[str, str]:
    """Validate source fields."""
    errors: dict[str, str] = {}

    if not data.get(CONF_PRICE_ENTITY):
        errors[CONF_PRICE_ENTITY] = "required_entity"
    if not _as_list(data.get(CONF_SOLAR_POWER_ENTITIES)):
        errors[CONF_SOLAR_POWER_ENTITIES] = "required_entity"

    if data.get(CONF_GRID_MODE) == GRID_MODE_SEPARATE:
        if not _as_list(data.get(CONF_GRID_IMPORT_POWER_ENTITIES)):
            errors[CONF_GRID_IMPORT_POWER_ENTITIES] = "required_entity"
    elif not _as_list(data.get(CONF_GRID_POWER_ENTITIES)):
        errors[CONF_GRID_POWER_ENTITIES] = "required_entity"

    return errors


class DailyEnergyFlowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daily Energy Flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data.update(user_input)
            await self.async_set_unique_id(slugify(str(user_input[CONF_NAME])))
            self._abort_if_unique_id_configured()
            return await self.async_step_sources()

        return self.async_show_form(step_id="user", data_schema=_basic_schema(self._data), errors=errors)

    async def async_step_sources(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle source entity selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {**self._data, **user_input}
            errors = _validate_sources(data)
            if not errors:
                return self.async_create_entry(title=str(data[CONF_NAME]), data=data)

        return self.async_show_form(step_id="sources", data_schema=_sources_schema(self._data), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> DailyEnergyFlowOptionsFlow:
        """Create the options flow."""
        return DailyEnergyFlowOptionsFlow(config_entry)


class DailyEnergyFlowOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Daily Energy Flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._data: dict[str, Any] = {**config_entry.data, **config_entry.options}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Start options flow."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle general options."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_sources()

        return self.async_show_form(step_id="user", data_schema=_basic_schema(self._data), errors={})

    async def async_step_sources(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle source entity options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {**self._data, **user_input}
            errors = _validate_sources(data)
            if not errors:
                return self.async_create_entry(title="", data=data)

        return self.async_show_form(step_id="sources", data_schema=_sources_schema(self._data), errors=errors)
