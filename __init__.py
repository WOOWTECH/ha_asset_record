"""Ha Asset Record - Home Assistant Custom Component for asset management."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import AssetCoordinator
from .panel import async_register_panel, async_unregister_panel
from .websocket import async_register_websocket_commands

_LOGGER = logging.getLogger(__name__)

type AssetConfigEntry = ConfigEntry[AssetCoordinator]

# Track if panel and websocket are registered (only once per HA instance)
DATA_PANEL_REGISTERED = f"{DOMAIN}_panel_registered"


async def async_setup_entry(hass: HomeAssistant, entry: AssetConfigEntry) -> bool:
    """Set up Ha Asset Record from a config entry."""
    coordinator = AssetCoordinator(hass, entry)
    await coordinator.async_load()

    entry.runtime_data = coordinator

    # Register websocket commands and panel (only once)
    if not hass.data.get(DATA_PANEL_REGISTERED):
        async_register_websocket_commands(hass)
        await async_register_panel(hass)
        hass.data[DATA_PANEL_REGISTERED] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: AssetConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Unregister panel if this is the last entry
    if unload_ok:
        remaining_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if not remaining_entries and hass.data.get(DATA_PANEL_REGISTERED):
            await async_unregister_panel(hass)
            hass.data[DATA_PANEL_REGISTERED] = False

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: AssetConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
