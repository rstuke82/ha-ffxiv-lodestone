"""Async Lodestone HTTP client."""

from __future__ import annotations

import asyncio

from aiohttp import ClientSession

from .const import BASE_URLS
from .models import CharacterData
from .parser import (
    parse_achievement_summary,
    parse_class_jobs,
    parse_collection_count,
    parse_profile,
    resolve_current_job,
    slugify,
)


class LodestoneError(Exception):
    """Base Lodestone error."""


class LodestoneNotFound(LodestoneError):
    """Character not found."""


class LodestoneClient:
    """Small async client for public Lodestone pages."""

    def __init__(self, session: ClientSession, character_id: str, region: str) -> None:
        self._session = session
        self.character_id = character_id
        self.base_url = BASE_URLS[region].rstrip("/")
        self.character_url = f"{self.base_url}/lodestone/character/{character_id}/"

    async def _get(self, suffix: str = "") -> str:
        url = f"{self.character_url}{suffix}"
        async with self._session.get(
            url,
            headers={"User-Agent": "HomeAssistant-FFXIV-Lodestone/0.4"},
            timeout=30,
        ) as response:
            if response.status == 404:
                raise LodestoneNotFound(self.character_id)
            response.raise_for_status()
            return await response.text()

    async def async_get_character(self) -> CharacterData:
        (
            profile_html,
            jobs_html,
            achievement_html,
            minion_html,
            mount_html,
            facewear_html,
        ) = await asyncio.gather(
            self._get(),
            self._get("class_job/"),
            self._get("achievement/"),
            self._get("minion/"),
            self._get("mount/"),
            self._get("faceaccessory/"),
        )

        profile = parse_profile(self.character_id, profile_html)
        displayed_profile = profile.jobs.get("_displayed_profile")

        jobs, progression = parse_class_jobs(jobs_html)
        profile.jobs = jobs

        profile.eureka = progression["eureka"]
        profile.bozja = progression["bozja"]
        profile.occult_crescent = progression["occult_crescent"]
        profile.achievements = parse_achievement_summary(achievement_html)
        profile.minion_count = parse_collection_count(minion_html)
        profile.mount_count = parse_collection_count(mount_html)
        profile.facewear_count = parse_collection_count(facewear_html)

        profile.current_job = resolve_current_job(
            profile.current_job,
            displayed_profile.icon_url if displayed_profile else None,
            jobs,
        )

        # Attach stats only to the job identified from the same displayed profile block.
        if profile.current_job and displayed_profile:
            job = profile.jobs.get(slugify(profile.current_job))
            if job:
                job.attributes.update(displayed_profile.attributes)

        return profile
