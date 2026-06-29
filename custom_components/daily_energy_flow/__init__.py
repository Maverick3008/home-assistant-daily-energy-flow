"""The Daily Energy Flow integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .manager import DailyEnergyFlowManager

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Daily Energy Flow from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    manager = DailyEnergyFlowManager(hass, entry)
    await manager.async_start()
    hass.data[DOMAIN][entry.entry_id] = manager

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    manager: DailyEnergyFlowManager | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if manager is not None:
        await manager.async_unload()

    if unload_ok and not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)
