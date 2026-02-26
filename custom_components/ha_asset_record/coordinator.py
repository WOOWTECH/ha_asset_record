"""Data coordinator for Ha Asset Record."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
import logging
from types import MappingProxyType
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.storage import Store
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
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

# [M-01] Expected types for each mutable asset field, used for input validation.
_FIELD_TYPES: dict[str, tuple[type, ...]] = {
    FIELD_NAME: (str,),
    FIELD_BRAND: (str,),
    FIELD_CATEGORY: (str,),
    FIELD_VALUE: (int, float),
    FIELD_PURCHASE_AT: (datetime, type(None)),
    FIELD_WARRANTY_UNTIL: (datetime, type(None)),
    FIELD_MANUAL_MD: (str,),
    FIELD_MAINTENANCE_MD: (str,),
}


def _parse_datetime_safe(raw: str | None) -> datetime | None:
    """Parse an ISO datetime string, returning *None* on failure.

    [L-02] Individual field parsing is wrapped so that a single corrupt
    value does not prevent the entire asset from loading.
    [M-07] Ensures the result is always timezone-aware (UTC).
    """
    if not raw:
        return None
    try:
        parsed = dt_util.parse_datetime(raw)
        if parsed is None:
            return None
        # [M-07] Guarantee timezone-aware UTC datetime
        if parsed.tzinfo is None:
            return dt_util.as_utc(parsed.replace(tzinfo=dt_util.UTC))
        return dt_util.as_utc(parsed)
    except (ValueError, TypeError, OverflowError) as err:
        _LOGGER.warning("Failed to parse datetime '%s': %s", raw, err)
        return None


def _ensure_aware_utc(dt_value: datetime) -> datetime:
    """Ensure a datetime is timezone-aware and in UTC.

    [L-11] Unified datetime handling for create/update paths.
    """
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=dt_util.UTC)
    return dt_util.as_utc(dt_value)


@dataclass
class Asset:
    """Represents an asset."""

    id: str
    name: str
    brand: str = ""
    category: str = ""
    value: float = 0
    purchase_at: datetime | None = None
    warranty_until: datetime | None = None
    manual_md: str = ""
    maintenance_md: str = ""
    created_at: datetime = field(default_factory=dt_util.utcnow)
    updated_at: datetime = field(default_factory=dt_util.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert asset to dictionary for storage."""
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "value": self.value,
            "purchase_at": self.purchase_at.isoformat() if self.purchase_at else None,
            "warranty_until": (
                self.warranty_until.isoformat() if self.warranty_until else None
            ),
            "manual_md": self.manual_md,
            "maintenance_md": self.maintenance_md,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Asset:
        """Create asset from dictionary.

        [L-02] Each field is parsed defensively so that corrupt values
        degrade gracefully rather than preventing the asset from loading.
        [M-07] All datetime fields are guaranteed timezone-aware (UTC).
        """
        # [L-02] Parse optional datetime fields safely
        purchase_at = _parse_datetime_safe(data.get("purchase_at"))
        warranty_until = _parse_datetime_safe(data.get("warranty_until"))

        # [L-02] Parse timestamp fields with fallback to utcnow()
        created_raw = _parse_datetime_safe(data.get("created_at"))
        created_at = created_raw if created_raw is not None else dt_util.utcnow()

        updated_raw = _parse_datetime_safe(data.get("updated_at"))
        updated_at = updated_raw if updated_raw is not None else dt_util.utcnow()

        # [L-02] Parse numeric value defensively
        try:
            value = float(data.get("value", 0))
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Invalid value '%s' for asset %s, defaulting to 0",
                data.get("value"),
                data.get("id", "unknown"),
            )
            value = 0

        return cls(
            id=data["id"],
            name=data.get("name", ""),
            brand=data.get("brand", ""),
            category=data.get("category", ""),
            value=value,
            purchase_at=purchase_at,
            warranty_until=warranty_until,
            manual_md=data.get("manual_md", ""),
            maintenance_md=data.get("maintenance_md", ""),
            created_at=created_at,
            updated_at=updated_at,
        )


class AssetCoordinator:
    """Coordinator for managing assets.

    [M-05] The Store key is STORAGE_KEY (== DOMAIN == "ha_asset_record").
    Only a single config entry should use this store; multiple entries would
    overwrite each other's data because they share the same storage file.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        # [M-05] Single store instance keyed by STORAGE_KEY; only one config
        # entry should exist for this integration at a time.
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )
        self._assets: dict[str, Asset] = {}
        # [M-03] Dict-based listeners with integer keys for O(1) add/remove,
        # following the pattern from HA DataUpdateCoordinator.
        self._listeners: dict[int, Callable[[], None]] = {}
        self._last_listener_id: int = 0

    @property
    def assets(self) -> MappingProxyType[str, Asset]:
        """Return all assets as a read-only mapping.

        [M-04] Consumers cannot accidentally mutate the internal dict.
        """
        return MappingProxyType(self._assets)

    async def async_load(self) -> None:
        """Load assets from storage.

        [C-01] Wrapped in try/except so that a corrupt or inaccessible
        storage file logs a warning and continues with an empty asset
        dict instead of crashing. The caller (async_setup_entry) can
        then decide whether to raise ConfigEntryNotReady.
        """
        try:
            data = await self._store.async_load()
        except Exception:
            _LOGGER.warning(
                "Failed to load asset storage; starting with empty data",
                exc_info=True,
            )
            data = None

        if data is not None:
            for asset_data in data.get("assets", []):
                try:
                    asset = Asset.from_dict(asset_data)
                    self._assets[asset.id] = asset
                except Exception:
                    _LOGGER.warning(
                        "Skipping corrupt asset record: %s",
                        asset_data.get("id", "unknown"),
                        exc_info=True,
                    )
        _LOGGER.debug("Loaded %d assets", len(self._assets))

    async def _async_save(self) -> None:
        """Save assets to storage."""
        data = {
            "assets": [asset.to_dict() for asset in self._assets.values()]
        }
        await self._store.async_save(data)
        _LOGGER.debug("Saved %d assets", len(self._assets))

    @callback  # [M-02] Mark as @callback per HA convention
    def add_listener(
        self, listener: Callable[[], None]  # [H-02] Correct type hint
    ) -> Callable[[], None]:
        """Add a listener for updates.

        Returns a callable that removes the listener when invoked.
        [M-03] Uses dict + counter for O(1) add/remove.
        """
        self._last_listener_id += 1
        listener_id = self._last_listener_id
        self._listeners[listener_id] = listener
        # Return a bound removal callable (same pattern as DataUpdateCoordinator)
        return partial(self._async_remove_listener, listener_id)

    @callback  # [M-02] Mark as @callback per HA convention
    def _async_remove_listener(self, listener_id: int) -> None:
        """Remove a listener by its id."""
        self._listeners.pop(listener_id, None)

    @callback  # [M-02] Mark as @callback per HA convention
    def _notify_listeners(self) -> None:
        """Notify all listeners of an update."""
        for listener in list(self._listeners.values()):
            listener()

    async def async_create_asset(self, name: str) -> Asset:
        """Create a new asset."""
        # [H-04] Use full UUID (32 hex chars) to avoid collision risk
        asset_id = f"asset_{uuid.uuid4().hex}"
        # [L-11] Unified datetime via _ensure_aware_utc
        now = _ensure_aware_utc(dt_util.utcnow())
        asset = Asset(
            id=asset_id,
            name=name,
            created_at=now,
            updated_at=now,
        )
        self._assets[asset_id] = asset
        await self._async_save()
        self._notify_listeners()
        _LOGGER.info("Created asset: %s (%s)", name, asset_id)
        return asset

    async def async_create_asset_full(
        self,
        name: str,
        *,
        brand: str = "",
        category: str = "",
        value: float = 0,
        purchase_at: datetime | None = None,
        warranty_until: datetime | None = None,
        manual_md: str = "",
        maintenance_md: str = "",
    ) -> Asset:
        """Create a new asset with all fields in a single operation.

        [H-11] Sets all fields at once with a single save + single notify,
        avoiding the N saves + N notifies that would result from calling
        async_update_asset for each field after creation.
        """
        # [H-04] Use full UUID (32 hex chars)
        asset_id = f"asset_{uuid.uuid4().hex}"
        # [L-11] Unified datetime via _ensure_aware_utc
        now = _ensure_aware_utc(dt_util.utcnow())
        asset = Asset(
            id=asset_id,
            name=name,
            brand=brand,
            category=category,
            value=value,
            purchase_at=(
                _ensure_aware_utc(purchase_at) if purchase_at else None
            ),
            warranty_until=(
                _ensure_aware_utc(warranty_until) if warranty_until else None
            ),
            manual_md=manual_md,
            maintenance_md=maintenance_md,
            created_at=now,
            updated_at=now,
        )
        self._assets[asset_id] = asset
        await self._async_save()
        self._notify_listeners()
        _LOGGER.info("Created asset (full): %s (%s)", name, asset_id)
        return asset

    async def async_delete_asset(self, asset_id: str) -> bool:
        """Delete an asset."""
        if asset_id not in self._assets:
            return False
        asset = self._assets.pop(asset_id)
        await self._async_save()

        # Remove the device from the device registry so it no longer
        # appears in Device & Services after the asset is deleted.
        dev_reg = dr.async_get(self.hass)
        device = dev_reg.async_get_device(identifiers={(DOMAIN, asset_id)})
        if device is not None:
            dev_reg.async_remove_device(device.id)

        self._notify_listeners()
        _LOGGER.info("Deleted asset: %s (%s)", asset.name, asset_id)
        return True

    async def async_update_asset(
        self,
        asset_id: str,
        field_name: str,
        value: Any,
    ) -> bool:
        """Update an asset field.

        [M-01] Validates that the value type matches the expected type
        for the given field before applying the update.
        """
        if asset_id not in self._assets:
            return False

        # [M-01] Input validation: reject unknown fields
        expected_types = _FIELD_TYPES.get(field_name)
        if expected_types is None:
            _LOGGER.warning("Unknown field: %s", field_name)
            return False

        # [M-01] Input validation: reject mismatched types
        if not isinstance(value, expected_types):
            _LOGGER.warning(
                "Invalid type for field %s: expected %s, got %s",
                field_name,
                expected_types,
                type(value).__name__,
            )
            return False

        asset = self._assets[asset_id]

        if field_name == FIELD_NAME:
            asset.name = value
        elif field_name == FIELD_BRAND:
            asset.brand = value
        elif field_name == FIELD_CATEGORY:
            asset.category = value
        elif field_name == FIELD_VALUE:
            asset.value = value
        elif field_name == FIELD_PURCHASE_AT:
            # [L-11] Ensure timezone-aware UTC
            asset.purchase_at = (
                _ensure_aware_utc(value) if value is not None else None
            )
        elif field_name == FIELD_WARRANTY_UNTIL:
            # [L-11] Ensure timezone-aware UTC
            asset.warranty_until = (
                _ensure_aware_utc(value) if value is not None else None
            )
        elif field_name == FIELD_MANUAL_MD:
            asset.manual_md = value
        elif field_name == FIELD_MAINTENANCE_MD:
            asset.maintenance_md = value

        # [L-11] Unified datetime handling
        asset.updated_at = _ensure_aware_utc(dt_util.utcnow())
        await self._async_save()
        self._notify_listeners()
        _LOGGER.debug("Updated asset %s field %s", asset_id, field_name)
        return True

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get an asset by ID."""
        return self._assets.get(asset_id)
