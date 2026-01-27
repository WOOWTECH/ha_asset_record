"""Panel registration for Ha Asset Record."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "ha-asset-record"
PANEL_COMPONENT_NAME = "ha-asset-panel"
PANEL_TITLE = "Device Record"
PANEL_TITLE_ZH = "設備紀錄"
PANEL_ICON = "mdi:devices"
PANEL_VERSION = "1.1.0"


def _get_panel_title(hass: HomeAssistant) -> str:
    """Get panel title based on HA language setting."""
    language = hass.config.language or "en"
    if language.startswith("zh"):
        return PANEL_TITLE_ZH
    return PANEL_TITLE


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the panel."""
    # Get the frontend directory path
    frontend_dir = Path(__file__).parent / "frontend"

    # Register static path for frontend files
    await hass.http.async_register_static_paths([
        StaticPathConfig(
            f"/{DOMAIN}/frontend",
            str(frontend_dir),
            cache_headers=False,
        )
    ])

    # Register the panel
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT_NAME,
        frontend_url_path=PANEL_URL_PATH,
        sidebar_title=_get_panel_title(hass),
        sidebar_icon=PANEL_ICON,
        module_url=f"/{DOMAIN}/frontend/ha-asset-panel.js?v={PANEL_VERSION}",
        require_admin=False,
        config={},
    )

    _LOGGER.info("Registered Ha Asset Record panel")


async def async_unregister_panel(hass: HomeAssistant) -> bool:
    """Unregister the panel."""
    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
        _LOGGER.info("Unregistered Ha Asset Record panel")
        return True
    return False
