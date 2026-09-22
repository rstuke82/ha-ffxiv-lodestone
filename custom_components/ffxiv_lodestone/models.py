"""Data models for FFXIV Lodestone."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class JobData:
    """A class/job entry."""

    name: str
    slug: str
    abbreviation: str | None = None
    role: str | None = None
    level: int | None = None
    current_xp: int | None = None
    max_xp: int | None = None
    icon_url: str | None = None
    attributes: dict[str, int | str | float | None] = field(default_factory=dict)
    equipment: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProgressionData:
    """One exploratory-zone progression system."""

    level: int | None = None
    current: int | None = None
    maximum: int | None = None
    resource_name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AchievementSummary:
    """Achievement summary."""

    count: int | None = None
    points: int | None = None
    latest_name: str | None = None
    latest_date: str | None = None


@dataclass(slots=True)
class CharacterData:
    """Complete normalized character snapshot."""

    character_id: str
    name: str
    slug: str
    world: str | None = None
    data_center: str | None = None
    title: str | None = None
    race: str | None = None
    clan: str | None = None
    gender: str | None = None
    nameday: str | None = None
    guardian: str | None = None
    city_state: str | None = None
    grand_company: str | None = None
    grand_company_rank: str | None = None
    free_company: str | None = None
    portrait_url: str | None = None
    current_job: str | None = None
    current_job_level: int | None = None
    achievements: AchievementSummary = field(default_factory=AchievementSummary)
    minion_count: int | None = None
    mount_count: int | None = None
    facewear_count: int | None = None
    eureka: ProgressionData = field(default_factory=lambda: ProgressionData(resource_name="xp"))
    bozja: ProgressionData = field(default_factory=lambda: ProgressionData(resource_name="mettle"))
    occult_crescent: ProgressionData = field(
        default_factory=lambda: ProgressionData(resource_name="knowledge")
    )
    jobs: dict[str, JobData] = field(default_factory=dict)

    # Freshness metadata managed by the coordinator.
    last_successful_update: str | None = None
    stale: bool = False
