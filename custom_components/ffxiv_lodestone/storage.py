"""Persistent snapshot helpers for FFXIV Lodestone."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .models import AchievementSummary, CharacterData, JobData, ProgressionData

STORAGE_VERSION = 1


def snapshot_store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    """Return the per-config-entry snapshot store."""
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")


def snapshot_to_dict(data: CharacterData) -> dict[str, Any]:
    """Serialize a snapshot."""
    return asdict(data)


def snapshot_from_dict(raw: dict[str, Any] | None) -> CharacterData | None:
    """Deserialize a snapshot."""
    if not raw:
        return None

    achievements_raw = raw.get("achievements") or {}
    eureka_raw = raw.get("eureka") or {}
    bozja_raw = raw.get("bozja") or {}
    occult_raw = raw.get("occult_crescent") or {}
    jobs_raw = raw.get("jobs") or {}

    jobs = {
        slug: JobData(
            name=value.get("name", slug),
            slug=value.get("slug", slug),
            abbreviation=value.get("abbreviation"),
            role=value.get("role"),
            level=value.get("level"),
            current_xp=value.get("current_xp"),
            max_xp=value.get("max_xp"),
            icon_url=value.get("icon_url"),
            attributes=value.get("attributes") or {},
            equipment=value.get("equipment") or {},
        )
        for slug, value in jobs_raw.items()
        if isinstance(value, dict)
    }

    return CharacterData(
        character_id=str(raw.get("character_id", "")),
        name=raw.get("name") or "Unknown Character",
        slug=raw.get("slug") or "unknown_character",
        world=raw.get("world"),
        data_center=raw.get("data_center"),
        title=raw.get("title"),
        race=raw.get("race"),
        clan=raw.get("clan"),
        gender=raw.get("gender"),
        nameday=raw.get("nameday"),
        guardian=raw.get("guardian"),
        city_state=raw.get("city_state"),
        grand_company=raw.get("grand_company"),
        grand_company_rank=raw.get("grand_company_rank"),
        free_company=raw.get("free_company"),
        portrait_url=raw.get("portrait_url"),
        current_job=raw.get("current_job"),
        current_job_level=raw.get("current_job_level"),
        achievements=AchievementSummary(
            count=achievements_raw.get("count"),
            points=achievements_raw.get("points"),
            latest_name=achievements_raw.get("latest_name"),
            latest_date=achievements_raw.get("latest_date"),
        ),
        minion_count=raw.get("minion_count"),
        mount_count=raw.get("mount_count"),
        facewear_count=raw.get("facewear_count"),
        eureka=ProgressionData(
            level=eureka_raw.get("level"),
            current=eureka_raw.get("current"),
            maximum=eureka_raw.get("maximum"),
            resource_name=eureka_raw.get("resource_name") or "xp",
            extra=eureka_raw.get("extra") or {},
        ),
        bozja=ProgressionData(
            level=bozja_raw.get("level"),
            current=bozja_raw.get("current"),
            maximum=bozja_raw.get("maximum"),
            resource_name=bozja_raw.get("resource_name") or "mettle",
            extra=bozja_raw.get("extra") or {},
        ),
        occult_crescent=ProgressionData(
            level=occult_raw.get("level"),
            current=occult_raw.get("current"),
            maximum=occult_raw.get("maximum"),
            resource_name=occult_raw.get("resource_name") or "knowledge",
            extra=occult_raw.get("extra") or {},
        ),
        jobs=jobs,
        last_successful_update=raw.get("last_successful_update"),
        stale=bool(raw.get("stale", False)),
    )
