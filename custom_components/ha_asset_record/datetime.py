"""Datetime platform for Ha Asset Record."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ASSET_ID,
    DOMAIN,
    FIELD_PURCHASE_AT,
    FIELD_WARRANTY_UNTIL,
)
from .coordinator import Asset, AssetCoordinator
from .entity import AssetEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up datetime entities."""
    coordinator: AssetCoordinator = entry.runtime_data

    entities: list[AssetDateTimeEntity] = []
    for asset in coordinator.assets.values():
        entities.extend(_create_datetime_entities(coordinator, asset))

    async_add_entities(entities)

    # Listen for new assets
    def _async_add_asset_entities() -> None:
        """Add entities for new assets."""
        existing_ids = {e.unique_id for e in entities}
        new_entities: list[AssetDateTimeEntity] = []

        for asset in coordinator.assets.values():
            for entity in _create_datetime_entities(coordinator, asset):
                if entity.unique_id not in existing_ids:
                    new_entities.append(entity)
                    entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.add_listener(_async_add_asset_entities))


def _create_datetime_entities(
    coordinator: AssetCoordinator, asset: Asset
) -> list[AssetDateTimeEntity]:
    """Create datetime entities for an asset."""
    return [
        AssetDateTimeEntity(coordinator, asset, FIELD_PURCHASE_AT, "purchase_at"),
        AssetDateTimeEntity(coordinator, asset, FIELD_WARRANTY_UNTIL, "warranty_until"),
    ]


class AssetDateTimeEntity(AssetEntity, DateTimeEntity):
    """Datetime entity for asset dates."""

    @property
    def native_value(self) -> datetime | None:
        """Return the current datetime value."""
        if self.field_name == FIELD_PURCHASE_AT:
            return self.asset.purchase_at
        if self.field_name == FIELD_WARRANTY_UNTIL:
            return self.asset.warranty_until
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        return {ATTR_ASSET_ID: self.asset.id}

    async def async_set_value(self, value: datetime) -> None:
        """Set the datetime value."""
        await self.coordinator.async_update_asset(
            self.asset.id, self.field_name, value
        )
