"""Number platform for Ha Asset Record."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ASSET_ID,
    FIELD_VALUE,
    VALUE_MAX,
    VALUE_MIN,
    VALUE_STEP,
)
from .coordinator import Asset, AssetCoordinator
from .entity import AssetEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator: AssetCoordinator = entry.runtime_data

    entities: list[AssetNumberEntity] = []
    for asset in coordinator.assets.values():
        entities.append(_create_number_entity(coordinator, asset))

    async_add_entities(entities)

    # Listen for new assets
    def _async_add_asset_entities() -> None:
        """Add entities for new assets."""
        existing_ids = {e.unique_id for e in entities}
        new_entities: list[AssetNumberEntity] = []

        for asset in coordinator.assets.values():
            entity = _create_number_entity(coordinator, asset)
            if entity.unique_id not in existing_ids:
                new_entities.append(entity)
                entities.append(entity)

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.add_listener(_async_add_asset_entities))


def _create_number_entity(
    coordinator: AssetCoordinator, asset: Asset
) -> AssetNumberEntity:
    """Create number entity for an asset."""
    return AssetNumberEntity(coordinator, asset, FIELD_VALUE, "value")


class AssetNumberEntity(AssetEntity, NumberEntity):
    """Number entity for asset value."""

    _attr_native_min_value = VALUE_MIN
    _attr_native_max_value = VALUE_MAX
    _attr_native_step = VALUE_STEP
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.asset.value

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return extra state attributes."""
        return {ATTR_ASSET_ID: self.asset.id}

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.coordinator.async_update_asset(
            self.asset.id, self.field_name, value
        )
