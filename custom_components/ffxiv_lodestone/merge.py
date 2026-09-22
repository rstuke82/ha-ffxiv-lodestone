"""Merge fresh Lodestone data with a previous snapshot."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import fields, is_dataclass
from typing import Any

from .models import CharacterData, JobData, ProgressionData


def _merge_value(old: Any, new: Any) -> Any:
    """Use new when meaningful, otherwise preserve old."""
    if new is None:
        return deepcopy(old)

    if isinstance(new, dict):
        merged = deepcopy(old) if isinstance(old, dict) else {}
        for key, value in new.items():
            if value is None and key in merged:
                continue
            merged[key] = deepcopy(value)
        return merged

    return deepcopy(new)


def _merge_progression(
    old: ProgressionData,
    new: ProgressionData,
) -> ProgressionData:
    return ProgressionData(
        level=_merge_value(old.level, new.level),
        current=_merge_value(old.current, new.current),
        maximum=_merge_value(old.maximum, new.maximum),
        resource_name=_merge_value(old.resource_name, new.resource_name),
        extra=_merge_value(old.extra, new.extra),
    )


def _merge_job(old: JobData | None, new: JobData) -> JobData:
    if old is None:
        return deepcopy(new)

    return JobData(
        name=_merge_value(old.name, new.name),
        slug=_merge_value(old.slug, new.slug),
        abbreviation=_merge_value(old.abbreviation, new.abbreviation),
        role=_merge_value(old.role, new.role),
        level=_merge_value(old.level, new.level),
        current_xp=_merge_value(old.current_xp, new.current_xp),
        max_xp=_merge_value(old.max_xp, new.max_xp),
        icon_url=_merge_value(old.icon_url, new.icon_url),
        attributes=_merge_value(old.attributes, new.attributes),
        equipment=_merge_value(old.equipment, new.equipment),
    )


def merge_character(
    old: CharacterData | None,
    new: CharacterData,
) -> CharacterData:
    """Merge a fresh partial snapshot over the last known snapshot."""
    if old is None:
        return new

    result = deepcopy(new)

    # Scalar profile fields.
    for attr in (
        "name",
        "slug",
        "world",
        "data_center",
        "title",
        "race",
        "clan",
        "gender",
        "nameday",
        "guardian",
        "city_state",
        "grand_company",
        "grand_company_rank",
        "free_company",
        "portrait_url",
        "current_job",
        "current_job_level",
        "minion_count",
        "mount_count",
        "facewear_count",
    ):
        setattr(result, attr, _merge_value(getattr(old, attr), getattr(new, attr)))

    # Achievement values.
    result.achievements.count = _merge_value(
        old.achievements.count, new.achievements.count
    )
    result.achievements.points = _merge_value(
        old.achievements.points, new.achievements.points
    )
    result.achievements.latest_name = _merge_value(
        old.achievements.latest_name, new.achievements.latest_name
    )
    result.achievements.latest_date = _merge_value(
        old.achievements.latest_date, new.achievements.latest_date
    )

    result.eureka = _merge_progression(old.eureka, new.eureka)
    result.bozja = _merge_progression(old.bozja, new.bozja)
    result.occult_crescent = _merge_progression(
        old.occult_crescent, new.occult_crescent
    )

    merged_jobs: dict[str, JobData] = deepcopy(old.jobs)
    for slug, job in new.jobs.items():
        merged_jobs[slug] = _merge_job(old.jobs.get(slug), job)
    result.jobs = merged_jobs

    return result
