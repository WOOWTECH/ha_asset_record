"""Base entity for Ha Asset Record."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .coordinator import Asset, AssetCoordinator


class AssetEntity(Entity):
    """Base class for asset entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AssetCoordinator,
        asset: Asset,
        field_name: str,
        translation_key: str,
    ) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self.asset = asset
        self.field_name = field_name
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}_{asset.id}_{field_name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.asset.id)},
            name=self.asset.name,
            manufacturer="Ha Asset Record",
            model="Asset",
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.add_listener(self._handle_coordinator_update)
        )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Refresh asset reference
        updated_asset = self.coordinator.get_asset(self.asset.id)
        if updated_asset:
            self.asset = updated_asset
        self.async_write_ha_state()
