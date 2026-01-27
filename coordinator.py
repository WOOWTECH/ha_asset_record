"""Data coordinator for Ha Asset Record."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
            "warranty_until": self.warranty_until.isoformat() if self.warranty_until else None,
            "manual_md": self.manual_md,
            "maintenance_md": self.maintenance_md,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Asset:
        """Create asset from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            brand=data.get("brand", ""),
            category=data.get("category", ""),
            value=data.get("value", 0),
            purchase_at=dt_util.parse_datetime(data["purchase_at"]) if data.get("purchase_at") else None,
            warranty_until=dt_util.parse_datetime(data["warranty_until"]) if data.get("warranty_until") else None,
            manual_md=data.get("manual_md", ""),
            maintenance_md=data.get("maintenance_md", ""),
            created_at=dt_util.parse_datetime(data["created_at"]) if data.get("created_at") else dt_util.utcnow(),
            updated_at=dt_util.parse_datetime(data["updated_at"]) if data.get("updated_at") else dt_util.utcnow(),
        )


class AssetCoordinator:
    """Coordinator for managing assets."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )
        self._assets: dict[str, Asset] = {}
        self._listeners: list[Callable[[], None]] = []

    @property
    def assets(self) -> dict[str, Asset]:
        """Return all assets."""
        return self._assets

    async def async_load(self) -> None:
        """Load assets from storage."""
        data = await self._store.async_load()
        if data is not None:
            for asset_data in data.get("assets", []):
                asset = Asset.from_dict(asset_data)
                self._assets[asset.id] = asset
        _LOGGER.debug("Loaded %d assets", len(self._assets))

    async def _async_save(self) -> None:
        """Save assets to storage."""
        data = {
            "assets": [asset.to_dict() for asset in self._assets.values()]
        }
        await self._store.async_save(data)
        _LOGGER.debug("Saved %d assets", len(self._assets))

    def add_listener(self, listener: callback) -> callback:
        """Add a listener for updates."""
        self._listeners.append(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.remove(listener)

        return remove_listener

    def _notify_listeners(self) -> None:
        """Notify all listeners of an update."""
        for listener in self._listeners:
            listener()

    async def async_create_asset(self, name: str) -> Asset:
        """Create a new asset."""
        asset_id = f"asset_{uuid.uuid4().hex[:8]}"
        now = dt_util.utcnow()
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

    async def async_delete_asset(self, asset_id: str) -> bool:
        """Delete an asset."""
        if asset_id not in self._assets:
            return False
        asset = self._assets.pop(asset_id)
        await self._async_save()
        self._notify_listeners()
        _LOGGER.info("Deleted asset: %s (%s)", asset.name, asset_id)
        return True

    async def async_update_asset(
        self,
        asset_id: str,
        field_name: str,
        value: Any,
    ) -> bool:
        """Update an asset field."""
        if asset_id not in self._assets:
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
            asset.purchase_at = value
        elif field_name == FIELD_WARRANTY_UNTIL:
            asset.warranty_until = value
        elif field_name == FIELD_MANUAL_MD:
            asset.manual_md = value
        elif field_name == FIELD_MAINTENANCE_MD:
            asset.maintenance_md = value
        else:
            _LOGGER.warning("Unknown field: %s", field_name)
            return False

        asset.updated_at = dt_util.utcnow()
        await self._async_save()
        self._notify_listeners()
        _LOGGER.debug("Updated asset %s field %s", asset_id, field_name)
        return True

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get an asset by ID."""
        return self._assets.get(asset_id)
