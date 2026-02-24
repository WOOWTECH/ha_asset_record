"""Base entity for Ha Asset Record."""

from __future__ import annotations

import logging

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .coordinator import Asset, AssetCoordinator

_LOGGER = logging.getLogger(__name__)


class AssetEntity(Entity):
    """Base class for asset entities."""

    _attr_has_entity_name = True
    # [H-08] Entities are coordinator-driven, not polled.
    _attr_should_poll = False

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

    @callback  # [H-06] Called from the event loop.
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        updated_asset = self.coordinator.get_asset(self.asset.id)

        # [H-05] Asset was deleted -- self-remove from entity registry.
        if updated_asset is None:
            _LOGGER.debug(
                "Asset %s was deleted, removing entity %s",
                self.asset.id,
                self.entity_id,
            )
            self.hass.async_create_task(self.async_remove())
            return

        # [M-10] If the asset name changed, update the device registry name
        # so the HA UI reflects the rename immediately.
        if updated_asset.name != self.asset.name:
            dev_reg = dr.async_get(self.hass)
            device = dev_reg.async_get_device(
                identifiers={(DOMAIN, self.asset.id)}
            )
            if device is not None:
                dev_reg.async_update_device(device.id, name=updated_asset.name)

        # Refresh the cached asset reference.
        self.asset = updated_asset
        self.async_write_ha_state()
