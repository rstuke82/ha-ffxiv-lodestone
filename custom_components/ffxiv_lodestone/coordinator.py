"""Data update coordinator for FFXIV Lodestone."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LodestoneClient, LodestoneError
from .const import CONF_REFRESH_MINUTES, DEFAULT_REFRESH_MINUTES, DOMAIN
from .merge import merge_character
from .models import CharacterData
from .storage import snapshot_store, snapshot_to_dict


class FFXIVLodestoneCoordinator(DataUpdateCoordinator[CharacterData]):
    """Coordinate all Lodestone requests for one character."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: LodestoneClient,
        cached_data: CharacterData | None = None,
    ) -> None:
        refresh_minutes = entry.options.get(
            CONF_REFRESH_MINUTES,
            DEFAULT_REFRESH_MINUTES,
        )

        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(minutes=refresh_minutes),
            config_entry=entry,
        )
        self.client = client
        self._store = snapshot_store(hass, entry.entry_id)

        if cached_data is not None:
            cached_data.stale = True
            self.data = cached_data

    async def _async_update_data(self) -> CharacterData:
        previous = self.data

        try:
            fresh = await self.client.async_get_character()
        except LodestoneError as err:
            if previous is not None:
                previous.stale = True
                return previous
            raise UpdateFailed(f"Lodestone update failed: {err}") from err
        except Exception as err:
            if previous is not None:
                previous.stale = True
                return previous
            raise UpdateFailed(f"Unexpected Lodestone error: {err}") from err

        merged = merge_character(previous, fresh)
        merged.last_successful_update = dt_util.utcnow().isoformat()
        merged.stale = False

        await self._store.async_save(snapshot_to_dict(merged))
        return merged
