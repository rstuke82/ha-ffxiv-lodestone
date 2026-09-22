"""Image platform for FFXIV Lodestone."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FFXIVLodestoneCoordinator
from .entity import FFXIVLodestoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: FFXIVLodestoneCoordinator = entry.runtime_data
    async_add_entities([FFXIVPortraitImage(coordinator)])


class FFXIVPortraitImage(FFXIVLodestoneEntity, ImageEntity):
    """Lodestone character portrait."""

    _attr_name = "Portrait"

    def __init__(self, coordinator: FFXIVLodestoneCoordinator) -> None:
        ImageEntity.__init__(self, coordinator.hass)
        FFXIVLodestoneEntity.__init__(self, coordinator, "portrait")
        self._attr_suggested_object_id = f"{coordinator.data.slug}_portrait"
        self._attr_image_url = coordinator.data.portrait_url

    def _handle_coordinator_update(self) -> None:
        self._attr_image_url = self.coordinator.data.portrait_url
        super()._handle_coordinator_update()
