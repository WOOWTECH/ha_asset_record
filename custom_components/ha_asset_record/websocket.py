"""WebSocket API for Ha Asset Record."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    DOMAIN,
    FIELD_BRAND,
    FIELD_CATEGORY,
    FIELD_MAINTENANCE_MD,
    FIELD_MANUAL_MD,
    FIELD_NAME,
    FIELD_PURCHASE_AT,
    FIELD_VALUE,
    FIELD_WARRANTY_UNTIL,
)
from .coordinator import AssetCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse datetime string safely."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as err:
        _LOGGER.warning("Invalid datetime format: %s - %s", value, err)
        return None


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register websocket commands."""
    websocket_api.async_register_command(hass, ws_list_assets)
    websocket_api.async_register_command(hass, ws_create_asset)
    websocket_api.async_register_command(hass, ws_update_asset)
    websocket_api.async_register_command(hass, ws_delete_asset)


def _get_coordinator(hass: HomeAssistant) -> AssetCoordinator | None:
    """Get the coordinator from hass data."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if hasattr(entry, "runtime_data") and entry.runtime_data:
            return entry.runtime_data
    return None


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_asset_record/list",
    }
)
@websocket_api.async_response
async def ws_list_assets(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle list assets command."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    assets = [asset.to_dict() for asset in coordinator.assets.values()]
    connection.send_result(msg["id"], {"assets": assets})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_asset_record/create",
        vol.Required("name"): str,
        vol.Optional("brand"): str,
        vol.Optional("category"): str,
        vol.Optional("value"): vol.Coerce(float),
        vol.Optional("purchase_at"): str,
        vol.Optional("warranty_until"): str,
        vol.Optional("manual_md"): str,
        vol.Optional("maintenance_md"): str,
    }
)
@websocket_api.async_response
async def ws_create_asset(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle create asset command."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    # Validate name
    name = msg["name"].strip() if msg["name"] else ""
    if not name:
        connection.send_error(msg["id"], "invalid_input", "Asset name is required")
        return

    # Create asset with name
    asset = await coordinator.async_create_asset(name)

    # Update optional fields
    if "brand" in msg:
        await coordinator.async_update_asset(asset.id, FIELD_BRAND, msg["brand"])
    if "category" in msg:
        await coordinator.async_update_asset(asset.id, FIELD_CATEGORY, msg["category"])
    if "value" in msg:
        await coordinator.async_update_asset(asset.id, FIELD_VALUE, msg["value"])
    if "purchase_at" in msg and msg["purchase_at"]:
        purchase_at = _parse_datetime(msg["purchase_at"])
        if purchase_at:
            await coordinator.async_update_asset(asset.id, FIELD_PURCHASE_AT, purchase_at)
    if "warranty_until" in msg and msg["warranty_until"]:
        warranty_until = _parse_datetime(msg["warranty_until"])
        if warranty_until:
            await coordinator.async_update_asset(asset.id, FIELD_WARRANTY_UNTIL, warranty_until)
    if "manual_md" in msg:
        await coordinator.async_update_asset(asset.id, FIELD_MANUAL_MD, msg["manual_md"])
    if "maintenance_md" in msg:
        await coordinator.async_update_asset(asset.id, FIELD_MAINTENANCE_MD, msg["maintenance_md"])

    # Get updated asset
    updated_asset = coordinator.get_asset(asset.id)
    connection.send_result(msg["id"], {"asset": updated_asset.to_dict() if updated_asset else None})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_asset_record/update",
        vol.Required("asset_id"): str,
        vol.Optional("name"): str,
        vol.Optional("brand"): str,
        vol.Optional("category"): str,
        vol.Optional("value"): vol.Coerce(float),
        vol.Optional("purchase_at"): vol.Any(str, None),
        vol.Optional("warranty_until"): vol.Any(str, None),
        vol.Optional("manual_md"): str,
        vol.Optional("maintenance_md"): str,
    }
)
@websocket_api.async_response
async def ws_update_asset(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle update asset command."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    asset_id = msg["asset_id"]
    asset = coordinator.get_asset(asset_id)
    if asset is None:
        connection.send_error(msg["id"], "not_found", f"Asset {asset_id} not found")
        return

    # Update name if provided (now properly persisted via FIELD_NAME)
    if "name" in msg:
        name = msg["name"].strip() if msg["name"] else ""
        if not name:
            connection.send_error(msg["id"], "invalid_input", "Asset name cannot be empty")
            return
        await coordinator.async_update_asset(asset_id, FIELD_NAME, name)

    # Update other fields
    if "brand" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_BRAND, msg["brand"])
    if "category" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_CATEGORY, msg["category"])
    if "value" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_VALUE, msg["value"])
    if "purchase_at" in msg:
        purchase_at = _parse_datetime(msg["purchase_at"])
        await coordinator.async_update_asset(asset_id, FIELD_PURCHASE_AT, purchase_at)
    if "warranty_until" in msg:
        warranty_until = _parse_datetime(msg["warranty_until"])
        await coordinator.async_update_asset(asset_id, FIELD_WARRANTY_UNTIL, warranty_until)
    if "manual_md" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_MANUAL_MD, msg["manual_md"])
    if "maintenance_md" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_MAINTENANCE_MD, msg["maintenance_md"])

    connection.send_result(msg["id"], {"success": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_asset_record/delete",
        vol.Required("asset_id"): str,
    }
)
@websocket_api.async_response
async def ws_delete_asset(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle delete asset command."""
    coordinator = _get_coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    success = await coordinator.async_delete_asset(msg["asset_id"])
    if not success:
        connection.send_error(msg["id"], "not_found", f"Asset {msg['asset_id']} not found")
        return

    connection.send_result(msg["id"], {"success": True})
