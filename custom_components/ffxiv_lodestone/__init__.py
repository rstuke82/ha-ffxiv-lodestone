"""FFXIV Lodestone integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LodestoneClient
from .const import CONF_CHARACTER_ID, CONF_REGION, DOMAIN, PLATFORMS
from .coordinator import FFXIVLodestoneCoordinator
from .storage import snapshot_from_dict, snapshot_store


async def _async_options_updated(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload when polling options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_remove_legacy_current_job_entity(
    hass: HomeAssistant,
    character_id: str,
) -> None:
    """Remove the pre-0.5 Current Job entity from the registry."""
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor",
        DOMAIN,
        f"{character_id}_current_job",
    )
    if entity_id:
        registry.async_remove(entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an FFXIV Lodestone config entry."""
    session = async_get_clientsession(hass)
    character_id = entry.data[CONF_CHARACTER_ID]

    client = LodestoneClient(
        session=session,
        character_id=character_id,
        region=entry.data[CONF_REGION],
    )

    raw_cache = await snapshot_store(hass, entry.entry_id).async_load()
    cached_data = snapshot_from_dict(raw_cache)

    coordinator = FFXIVLodestoneCoordinator(
        hass,
        entry,
        client,
        cached_data=cached_data,
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    await _async_remove_legacy_current_job_entity(hass, character_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an FFXIV Lodestone config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
