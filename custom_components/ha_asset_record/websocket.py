"""WebSocket API for Ha Asset Record."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

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

# [L-13] Regex pattern for asset_id validation.
# Asset IDs are generated as "asset_" + uuid4().hex (32 hex chars).
ASSET_ID_PATTERN = r"^asset_[a-f0-9]+$"


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse a datetime string using HA's dt_util.

    [H-10] Uses dt_util.parse_datetime() instead of datetime.fromisoformat().
    Returns the parsed datetime (timezone-aware UTC) or None if the value is
    empty/None.  Raises ValueError if the string is non-empty but unparseable
    so the caller can send a proper error to the client ([H-09]).
    """
    if not value:
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid datetime format: {value!r}")
    # Ensure timezone-aware UTC
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt_util.UTC)
    return dt_util.as_utc(parsed)


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register websocket commands."""
    websocket_api.async_register_command(hass, ws_list_assets)
    websocket_api.async_register_command(hass, ws_create_asset)
    websocket_api.async_register_command(hass, ws_update_asset)
    websocket_api.async_register_command(hass, ws_delete_asset)


def _get_coordinator_from_hass(hass: HomeAssistant) -> AssetCoordinator | None:
    """Get the coordinator from hass.data.

    [H-12] Direct lookup via hass.data[DOMAIN] instead of iterating config entries.
    """
    return hass.data.get(DOMAIN)


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
    coordinator = _get_coordinator_from_hass(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    assets = [asset.to_dict() for asset in coordinator.assets.values()]
    connection.send_result(msg["id"], {"assets": assets})


# [L-12] Write commands require admin access.
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_asset_record/create",
        # [M-11] String length validation
        vol.Required("name"): vol.All(str, vol.Length(max=255)),
        vol.Optional("brand"): vol.All(str, vol.Length(max=255)),
        vol.Optional("category"): vol.All(str, vol.Length(max=255)),
        vol.Optional("value"): vol.Coerce(float),
        vol.Optional("purchase_at"): vol.Any(str, None),
        vol.Optional("warranty_until"): vol.Any(str, None),
        vol.Optional("manual_md"): vol.All(str, vol.Length(max=65535)),
        vol.Optional("maintenance_md"): vol.All(str, vol.Length(max=65535)),
    }
)
@websocket_api.async_response
async def ws_create_asset(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle create asset command."""
    coordinator = _get_coordinator_from_hass(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    # Validate name
    name = msg["name"].strip() if msg["name"] else ""
    if not name:
        connection.send_error(msg["id"], "invalid_input", "Asset name is required")
        return

    # [H-09] Parse datetime fields with error responses for invalid values
    purchase_at: datetime | None = None
    if "purchase_at" in msg and msg["purchase_at"]:
        try:
            purchase_at = _parse_datetime(msg["purchase_at"])
        except ValueError:
            connection.send_error(
                msg["id"],
                "invalid_format",
                f"Invalid purchase_at datetime: {msg['purchase_at']!r}",
            )
            return

    warranty_until: datetime | None = None
    if "warranty_until" in msg and msg["warranty_until"]:
        try:
            warranty_until = _parse_datetime(msg["warranty_until"])
        except ValueError:
            connection.send_error(
                msg["id"],
                "invalid_format",
                f"Invalid warranty_until datetime: {msg['warranty_until']!r}",
            )
            return

    # [H-11] Use async_create_asset_full() for single save + single notify
    asset = await coordinator.async_create_asset_full(
        name,
        brand=msg.get("brand", ""),
        category=msg.get("category", ""),
        value=msg.get("value", 0),
        purchase_at=purchase_at,
        warranty_until=warranty_until,
        manual_md=msg.get("manual_md", ""),
        maintenance_md=msg.get("maintenance_md", ""),
    )

    connection.send_result(msg["id"], {"asset": asset.to_dict()})


# [L-12] Write commands require admin access.
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_asset_record/update",
        # [L-13] Validate asset_id format
        vol.Required("asset_id"): vol.All(str, vol.Match(ASSET_ID_PATTERN)),
        # [M-11] String length validation
        vol.Optional("name"): vol.All(str, vol.Length(max=255)),
        vol.Optional("brand"): vol.All(str, vol.Length(max=255)),
        vol.Optional("category"): vol.All(str, vol.Length(max=255)),
        vol.Optional("value"): vol.Coerce(float),
        vol.Optional("purchase_at"): vol.Any(str, None),
        vol.Optional("warranty_until"): vol.Any(str, None),
        vol.Optional("manual_md"): vol.All(str, vol.Length(max=65535)),
        vol.Optional("maintenance_md"): vol.All(str, vol.Length(max=65535)),
    }
)
@websocket_api.async_response
async def ws_update_asset(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle update asset command."""
    coordinator = _get_coordinator_from_hass(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    asset_id = msg["asset_id"]
    asset = coordinator.get_asset(asset_id)
    if asset is None:
        connection.send_error(msg["id"], "not_found", f"Asset {asset_id} not found")
        return

    # Update name if provided
    if "name" in msg:
        name = msg["name"].strip() if msg["name"] else ""
        if not name:
            connection.send_error(
                msg["id"], "invalid_input", "Asset name cannot be empty"
            )
            return
        await coordinator.async_update_asset(asset_id, FIELD_NAME, name)

    # Update other fields
    if "brand" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_BRAND, msg["brand"])
    if "category" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_CATEGORY, msg["category"])
    if "value" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_VALUE, msg["value"])

    # [H-09] Parse datetime fields with error responses for invalid values
    if "purchase_at" in msg:
        try:
            purchase_at = _parse_datetime(msg["purchase_at"])
        except ValueError:
            connection.send_error(
                msg["id"],
                "invalid_format",
                f"Invalid purchase_at datetime: {msg['purchase_at']!r}",
            )
            return
        await coordinator.async_update_asset(asset_id, FIELD_PURCHASE_AT, purchase_at)

    if "warranty_until" in msg:
        try:
            warranty_until = _parse_datetime(msg["warranty_until"])
        except ValueError:
            connection.send_error(
                msg["id"],
                "invalid_format",
                f"Invalid warranty_until datetime: {msg['warranty_until']!r}",
            )
            return
        await coordinator.async_update_asset(
            asset_id, FIELD_WARRANTY_UNTIL, warranty_until
        )

    if "manual_md" in msg:
        await coordinator.async_update_asset(asset_id, FIELD_MANUAL_MD, msg["manual_md"])
    if "maintenance_md" in msg:
        await coordinator.async_update_asset(
            asset_id, FIELD_MAINTENANCE_MD, msg["maintenance_md"]
        )

    # [M-12] Return updated asset dict (consistent with ws_create_asset)
    updated_asset = coordinator.get_asset(asset_id)
    connection.send_result(
        msg["id"],
        {"asset": updated_asset.to_dict() if updated_asset else None},
    )


# [L-12] Write commands require admin access.
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_asset_record/delete",
        # [L-13] Validate asset_id format
        vol.Required("asset_id"): vol.All(str, vol.Match(ASSET_ID_PATTERN)),
    }
)
@websocket_api.async_response
async def ws_delete_asset(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle delete asset command."""
    coordinator = _get_coordinator_from_hass(hass)
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "Integration not configured")
        return

    success = await coordinator.async_delete_asset(msg["asset_id"])
    if not success:
        connection.send_error(
            msg["id"], "not_found", f"Asset {msg['asset_id']} not found"
        )
        return

    connection.send_result(msg["id"], {"success": True})
