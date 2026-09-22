"""Snapshot merge tests."""

from custom_components.ffxiv_lodestone.merge import merge_character
from custom_components.ffxiv_lodestone.models import (
    AchievementSummary,
    CharacterData,
    JobData,
)


def _character(**kwargs):
    base = dict(
        character_id="123",
        name="Example Character",
        slug="example_character",
    )
    base.update(kwargs)
    return CharacterData(**base)


def test_partial_refresh_preserves_previous_values():
    old = _character(
        current_job="Sage",
        world="Example",
        minion_count=300,
        achievements=AchievementSummary(count=1500, points=13000),
        jobs={
            "sage": JobData(
                name="Sage",
                slug="sage",
                level=100,
                attributes={"mind": 6200},
            )
        },
    )

    fresh = _character(
        current_job=None,
        world="Example",
        minion_count=None,
        achievements=AchievementSummary(count=None, points=13010),
        jobs={
            "sage": JobData(
                name="Sage",
                slug="sage",
                level=100,
                attributes={},
            )
        },
    )

    merged = merge_character(old, fresh)

    assert merged.current_job == "Sage"
    assert merged.minion_count == 300
    assert merged.achievements.count == 1500
    assert merged.achievements.points == 13010
    assert merged.jobs["sage"].attributes["mind"] == 6200
