"""Base entities for FFXIV Lodestone."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FFXIVLodestoneCoordinator


class FFXIVLodestoneEntity(CoordinatorEntity[FFXIVLodestoneCoordinator]):
    """Base entity tied to a single Lodestone character."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FFXIVLodestoneCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        data = coordinator.data
        self._attr_unique_id = f"{data.character_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, data.character_id)},
            name=data.name,
            model="FINAL FANTASY XIV Character",
            configuration_url=self.coordinator.client.character_url,
        )
