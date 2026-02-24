"""Text platform for Ha Asset Record."""

from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ASSET_ID,
    ATTR_RAW_CONTENT,
    FIELD_BRAND,
    FIELD_CATEGORY,
    FIELD_MAINTENANCE_MD,
    FIELD_MANUAL_MD,
    TEXT_MAX_LENGTH,
)
from .coordinator import Asset, AssetCoordinator
from .entity import AssetEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up text entities."""
    coordinator: AssetCoordinator = entry.runtime_data

    entities: list[AssetTextEntity] = []
    for asset in coordinator.assets.values():
        entities.extend(_create_text_entities(coordinator, asset))

    async_add_entities(entities)

    # Listen for new assets
    def _async_add_asset_entities() -> None:
        """Add entities for new assets."""
        existing_ids = {e.unique_id for e in entities}
        new_entities: list[AssetTextEntity] = []

        for asset in coordinator.assets.values():
            for entity in _create_text_entities(coordinator, asset):
                if entity.unique_id not in existing_ids:
                    new_entities.append(entity)
                    entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.add_listener(_async_add_asset_entities))


def _create_text_entities(
    coordinator: AssetCoordinator, asset: Asset
) -> list[AssetTextEntity]:
    """Create text entities for an asset."""
    return [
        AssetTextEntity(coordinator, asset, FIELD_BRAND, "brand", is_multiline=False),
        AssetTextEntity(coordinator, asset, FIELD_CATEGORY, "category", is_multiline=False),
        AssetTextEntity(coordinator, asset, FIELD_MANUAL_MD, "manual_md", is_multiline=True),
        AssetTextEntity(coordinator, asset, FIELD_MAINTENANCE_MD, "maintenance_md", is_multiline=True),
    ]


class AssetTextEntity(AssetEntity, TextEntity):
    """Text entity for asset text fields."""

    _attr_native_max = 65535  # Allow long text via service call

    def __init__(
        self,
        coordinator: AssetCoordinator,
        asset: Asset,
        field_name: str,
        translation_key: str,
        is_multiline: bool = False,
    ) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, asset, field_name, translation_key)
        self._is_multiline = is_multiline
        self._attr_mode = TextMode.TEXT

    @property
    def native_value(self) -> str | None:
        """Return the current text value (truncated for state)."""
        value = self._get_full_value()
        if value and len(value) > TEXT_MAX_LENGTH:
            return value[: TEXT_MAX_LENGTH - 3] + "..."
        return value

    def _get_full_value(self) -> str:
        """Get the full value for this field."""
        if self.field_name == FIELD_BRAND:
            return self.asset.brand
        if self.field_name == FIELD_CATEGORY:
            return self.asset.category
        if self.field_name == FIELD_MANUAL_MD:
            return self.asset.manual_md
        if self.field_name == FIELD_MAINTENANCE_MD:
            return self.asset.maintenance_md
        return ""

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        attrs = {ATTR_ASSET_ID: self.asset.id}
        # For multiline fields, store full content in raw_content
        if self._is_multiline:
            attrs[ATTR_RAW_CONTENT] = self._get_full_value()
        return attrs

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        await self.coordinator.async_update_asset(
            self.asset.id, self.field_name, value
        )
