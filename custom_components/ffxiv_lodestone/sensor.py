"""Sensor platform for FFXIV Lodestone."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CLEAN_JOB_ICON_BASE
from .coordinator import FFXIVLodestoneCoordinator
from .entity import FFXIVLodestoneEntity
from .parser import slugify


@dataclass(frozen=True, kw_only=True)
class CharacterSensorDescription(SensorEntityDescription):
    """Character sensor definition."""

    value_fn: Callable[[Any], Any]


CHARACTER_SENSORS = (
    CharacterSensorDescription(
        key="achievement_points",
        name="Achievement points",
        native_unit_of_measurement="points",
        value_fn=lambda d: d.achievements.points,
        icon="mdi:trophy",
    ),
    CharacterSensorDescription(
        key="achievements",
        name="Achievements",
        value_fn=lambda d: d.achievements.count,
        icon="mdi:trophy",
    ),
    CharacterSensorDescription(
        key="latest_achievement",
        name="Latest achievement",
        value_fn=lambda d: d.achievements.latest_name,
        icon="mdi:trophy-award",
    ),
    CharacterSensorDescription(
        key="mounts",
        name="Mounts",
        value_fn=lambda d: d.mount_count,
        icon="mdi:horse",
    ),
    CharacterSensorDescription(
        key="minions",
        name="Minions",
        value_fn=lambda d: d.minion_count,
        icon="mdi:paw",
    ),
    CharacterSensorDescription(
        key="facewear",
        name="Facewear",
        value_fn=lambda d: d.facewear_count,
        icon="mdi:glasses",
    ),
    CharacterSensorDescription(
        key="eureka",
        name="Eureka",
        value_fn=lambda d: d.eureka.level,
        icon="mdi:lightning-bolt",
    ),
    CharacterSensorDescription(
        key="bozja",
        name="Bozja",
        value_fn=lambda d: d.bozja.level,
        icon="mdi:shield-sword",
    ),
    CharacterSensorDescription(
        key="occult_crescent",
        name="Occult Crescent",
        value_fn=lambda d: d.occult_crescent.level,
        icon="mdi:weather-night",
    ),
)


def _clean_job_picture(job) -> str | None:
    """Return the preferred job picture.

    Beastmaster uses the official Lodestone-provided job image until the
    plain-icon source has a matching BST asset.
    """
    if job is None:
        return None

    if job.abbreviation == "BST":
        return job.icon_url

    clean_name = job.name.lower().replace(" ", "").replace("'", "")
    return f"{CLEAN_JOB_ICON_BASE}/{clean_name}.png"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: FFXIVLodestoneCoordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        FFXIVCharacterProfileSensor(coordinator),
        *[
            FFXIVCharacterSensor(coordinator, description)
            for description in CHARACTER_SENSORS
        ],
    ]

    entities.extend(
        FFXIVJobSensor(coordinator, job_slug)
        for job_slug in coordinator.data.jobs
        if not job_slug.startswith("_")
    )

    async_add_entities(entities)


class FFXIVCharacterProfileSensor(FFXIVLodestoneEntity, SensorEntity):
    """Primary character entity."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: FFXIVLodestoneCoordinator) -> None:
        super().__init__(coordinator, "character")
        self._attr_name = coordinator.data.name
        self._attr_suggested_object_id = coordinator.data.slug

    @property
    def native_value(self):
        """Use current job as the character entity state."""
        return self.coordinator.data.current_job

    @property
    def entity_picture(self) -> str | None:
        """Show the currently displayed job icon."""
        current_job = self.coordinator.data.current_job
        if not current_job:
            return None
        job = self.coordinator.data.jobs.get(slugify(current_job))
        return _clean_job_picture(job)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data

        attrs = {
            "current_job": data.current_job,
            "current_job_level": data.current_job_level,
            "world": data.world,
            "data_center": data.data_center,
            "title": data.title,
            "race": data.race,
            "clan": data.clan,
            "gender": data.gender,
            "nameday": data.nameday,
            "guardian": data.guardian,
            "city_state": data.city_state,
            "grand_company": data.grand_company,
            "grand_company_rank": data.grand_company_rank,
            "free_company": data.free_company,
            "character_id": data.character_id,
            "lodestone_url": self.coordinator.client.character_url,
            "last_successful_update": data.last_successful_update,
            "stale": data.stale,
        }

        return {
            key: value
            for key, value in attrs.items()
            if value is not None
        }


class FFXIVCharacterSensor(FFXIVLodestoneEntity, SensorEntity):
    """A character-level measurement sensor."""

    entity_description: CharacterSensorDescription

    def __init__(
        self,
        coordinator: FFXIVLodestoneCoordinator,
        description: CharacterSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_suggested_object_id = (
            f"{coordinator.data.slug}_{description.key}"
        )

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        key = self.entity_description.key

        if key == "latest_achievement":
            attrs = {"date": data.achievements.latest_date}
        else:
            progression = {
                "eureka": data.eureka,
                "bozja": data.bozja,
                "occult_crescent": data.occult_crescent,
            }.get(key)

            if progression is None:
                attrs = {}
            else:
                attrs = {
                    "current": progression.current,
                    "maximum": progression.maximum,
                    "resource": progression.resource_name,
                }
                attrs.update(progression.extra)

        attrs["last_successful_update"] = data.last_successful_update
        attrs["stale"] = data.stale

        return {
            attr_key: value
            for attr_key, value in attrs.items()
            if value is not None
        }


class FFXIVJobSensor(FFXIVLodestoneEntity, SensorEntity):
    """One sensor per FFXIV job."""

    def __init__(
        self,
        coordinator: FFXIVLodestoneCoordinator,
        job_slug: str,
    ) -> None:
        self.job_slug = job_slug
        job = coordinator.data.jobs[job_slug]
        super().__init__(coordinator, f"job_{job_slug}")
        self._attr_name = job.name
        self._attr_suggested_object_id = f"{coordinator.data.slug}_{job_slug}"

    @property
    def entity_picture(self) -> str | None:
        job = self.coordinator.data.jobs.get(self.job_slug)
        return _clean_job_picture(job)

    @property
    def native_value(self):
        job = self.coordinator.data.jobs.get(self.job_slug)
        return job.level if job else None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        job = data.jobs.get(self.job_slug)
        if job is None:
            return None

        attrs = {
            "abbreviation": job.abbreviation,
            "role": job.role,
            "current_xp": job.current_xp,
            "max_xp": job.max_xp,
            "lodestone_icon_url": job.icon_url,
            "last_successful_update": data.last_successful_update,
            "stale": data.stale,
        }

        attrs.update(job.attributes)

        if job.equipment:
            attrs["equipment"] = job.equipment

        return {key: value for key, value in attrs.items() if value is not None}
