"""Lodestone HTML parser.

Lodestone is HTML rather than a stable JSON API. Keep markup-specific parsing
here so Home Assistant entity code remains stable.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from bs4 import BeautifulSoup, Tag

from .job_catalog import JOBS
from .models import AchievementSummary, CharacterData, JobData, ProgressionData


def slugify(value: str) -> str:
    """Convert a name to an HA-safe slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def _text(node) -> str | None:
    if node is None:
        return None
    value = " ".join(node.stripped_strings)
    return value or None


def _int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"[\d,]+", value)
    return int(match.group(0).replace(",", "")) if match else None


def _all_text(soup: BeautifulSoup) -> str:
    return "\n".join(s.strip() for s in soup.stripped_strings if s.strip())


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _value_after_label(text: str, label: str) -> str | None:
    lines = _lines(text)
    try:
        index = lines.index(label)
    except ValueError:
        return None
    return lines[index + 1] if index + 1 < len(lines) else None


def _first_text(soup: BeautifulSoup, selectors: Iterable[str]) -> str | None:
    for selector in selectors:
        value = _text(soup.select_one(selector))
        if value:
            return value
    return None


def _absolute_image_url(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("//"):
        return f"https:{value}"
    return value


def _img_src(img: Tag | None) -> str | None:
    if img is None:
        return None
    value = img.get("src") or img.get("data-src")
    return _absolute_image_url(value if isinstance(value, str) else None)


def _image_key(url: str | None) -> str | None:
    """Normalize an image URL for cross-page matching."""
    if not url:
        return None
    # Lodestone image URLs can be protocol-relative and can include query strings.
    path = url.split("?", 1)[0].rstrip("/")
    return path.rsplit("/", 1)[-1].casefold()


def _nearest_icon_for_text(text_node) -> str | None:
    """Find the nearest image belonging to a text node's logical entry."""
    parent = getattr(text_node, "parent", None)
    for _ in range(7):
        if not isinstance(parent, Tag):
            break

        images = parent.find_all("img")
        if images:
            # Prefer job/class-looking icon images rather than decorative images.
            for image in images:
                src = _img_src(image)
                classes = " ".join(image.get("class", []))
                alt = image.get("alt") or ""
                haystack = f"{src or ''} {classes} {alt}".casefold()
                if any(word in haystack for word in ("class", "job", "jobicon", "classjob")):
                    return src

            # Fallback: first image in a compact ancestor.
            if len(images) <= 3:
                src = _img_src(images[0])
                if src:
                    return src

        parent = parent.parent

    return None


def _parse_profile_job_icon(soup: BeautifulSoup) -> str | None:
    """Find the icon associated with the profile's displayed LEVEL/job block.

    On Lodestone the equipment image immediately before LEVEL is not the job icon.
    The displayed class/job icon is the first image after the LEVEL element.
    """
    level_node = soup.find(string=re.compile(r"^\s*LEVEL\s+\d+\s*$", re.I))
    if level_node is not None:
        level_tag = getattr(level_node, "parent", None)
        if isinstance(level_tag, Tag):
            next_image = level_tag.find_next("img")
            src = _img_src(next_image)
            if src:
                return src

    # Semantic selector fallbacks for future markup changes.
    for selector in (
        ".character__class img",
        ".character__job img",
        ".character__class__data img",
        "[class*='character__class'] img",
        "[class*='character__job'] img",
    ):
        icon = _img_src(soup.select_one(selector))
        if icon:
            return icon

    return None

def _parse_current_job_text_fallback(soup: BeautifulSoup) -> str | None:
    """Read the displayed job from the same local block as LEVEL.

    Lodestone includes every job name elsewhere on the character page, so broad
    page scans are unsafe. Walk outward from the displayed LEVEL node and stop
    at the first compact ancestor containing exactly one recognized job name.
    """
    level_node = soup.find(string=re.compile(r"^\s*LEVEL\s+\d+\s*$", re.I))

    if level_node is not None:
        parent = getattr(level_node, "parent", None)
        for _ in range(7):
            if not isinstance(parent, Tag):
                break

            candidates: set[str] = set()

            # Visible text in this local profile block.
            block_text = _text(parent) or ""
            for job_name in JOBS:
                if re.search(rf"\b{re.escape(job_name)}\b", block_text, re.I):
                    candidates.add(job_name)

            # Job name is often exposed in an image/title/data attribute even
            # when it is not rendered as visible text.
            for tag in parent.find_all(True):
                values: list[str] = []
                for attr in (
                    "alt",
                    "title",
                    "data-tooltip",
                    "data-name",
                    "aria-label",
                ):
                    attr_value = tag.get(attr)
                    if isinstance(attr_value, str):
                        values.append(attr_value)
                attr_text = " ".join(values)
                for job_name in JOBS:
                    if re.search(rf"\b{re.escape(job_name)}\b", attr_text, re.I):
                        candidates.add(job_name)

            if len(candidates) == 1:
                return next(iter(candidates))

            parent = parent.parent

    # Strict semantic selectors only; never scan the whole profile for names.
    for selector in (
        ".character__class__name",
        ".character__job__name",
        ".character__class__data .name",
        ".character__job .name",
        "[class*='character__class'] [class*='name']",
        "[class*='character__job'] [class*='name']",
    ):
        value = _text(soup.select_one(selector))
        if not value:
            continue
        for job_name in JOBS:
            if value.strip().casefold() == job_name.casefold():
                return job_name

    return None

def _parse_portrait(soup: BeautifulSoup) -> str | None:
    """Extract the large character portrait URL."""
    for selector in (
        ".character__detail__image img",
        ".frame__chara__image img",
        ".character__detail__image a img",
        "[class*='character__detail__image'] img",
        "[class*='frame__chara__image'] img",
    ):
        src = _img_src(soup.select_one(selector))
        if src and "finalfantasyxiv.com" in src:
            return src

    for image in soup.find_all("img"):
        src = _img_src(image)
        if (
            src
            and "finalfantasyxiv.com" in src
            and re.search(r"\.jpe?g(?:\?|$)", src, re.I)
        ):
            return src

    return None


def parse_profile(character_id: str, html: str) -> CharacterData:
    """Parse the public profile page."""
    soup = BeautifulSoup(html, "html.parser")
    text = _all_text(soup)
    lines = _lines(text)

    name = _first_text(
        soup,
        (
            ".frame__chara__name",
            ".character__name",
            "[class*='frame__chara__name']",
        ),
    ) or "Unknown Character"

    title = _first_text(
        soup,
        (
            ".frame__chara__title",
            ".character__title",
            "[class*='frame__chara__title']",
        ),
    )

    world_block = _first_text(
        soup,
        (
            ".frame__chara__world",
            ".character__world",
            "[class*='frame__chara__world']",
        ),
    ) or ""

    world = data_center = None
    match = re.search(r"(?P<world>[^\[]+)\[(?P<dc>[^\]]+)\]", world_block)
    if match:
        world = match.group("world").strip()
        data_center = match.group("dc").strip()

    race = _value_after_label(text, "Race/Clan/Gender")
    clan_gender = None
    if race:
        try:
            idx = lines.index("Race/Clan/Gender")
        except ValueError:
            idx = -1
        if idx >= 0 and idx + 2 < len(lines):
            race = lines[idx + 1]
            clan_gender = lines[idx + 2]

    clan = gender = None
    if clan_gender:
        parts = [part.strip() for part in clan_gender.split("/", 1)]
        clan = parts[0] if parts else None
        gender = parts[1] if len(parts) > 1 else None

    gc_line = _value_after_label(text, "Grand Company")
    gc = gc_rank = None
    if gc_line and " / " in gc_line:
        gc, gc_rank = [part.strip() for part in gc_line.split(" / ", 1)]

    level_match = re.search(r"\bLEVEL\s+(\d+)\b", text, re.I)
    current_level = int(level_match.group(1)) if level_match else None

    stats: dict[str, int] = {}
    for label in (
        "Strength",
        "Dexterity",
        "Vitality",
        "Intelligence",
        "Mind",
        "Critical Hit Rate",
        "Determination",
        "Direct Hit Rate",
        "Defense",
        "Magic Defense",
        "Attack Power",
        "Skill Speed",
        "Attack Magic Potency",
        "Healing Magic Potency",
        "Spell Speed",
        "Tenacity",
        "Piety",
    ):
        match = re.search(rf"{re.escape(label)}\s*(?:\||:)?\s*([\d,]+)", text, re.I)
        if match:
            stats[slugify(label)] = int(match.group(1).replace(",", ""))

    result = CharacterData(
        character_id=character_id,
        name=name,
        slug=slugify(name),
        world=world,
        data_center=data_center,
        title=title,
        race=race,
        clan=clan,
        gender=gender,
        nameday=_value_after_label(text, "Nameday"),
        guardian=_value_after_label(text, "Guardian"),
        city_state=_value_after_label(text, "City-state"),
        grand_company=gc,
        grand_company_rank=gc_rank,
        free_company=_value_after_label(text, "Free Company"),
        portrait_url=_parse_portrait(soup),
        current_job=_parse_current_job_text_fallback(soup),
        current_job_level=current_level,
    )

    # Temporary profile metadata used during the client-side merge.
    profile_meta = JobData(
        name="_displayed_profile",
        slug="_displayed_profile",
        level=current_level,
        icon_url=_parse_profile_job_icon(soup),
        attributes=stats,
    )
    result.jobs["_displayed_profile"] = profile_meta

    return result


def _find_job_entry_icon(soup: BeautifulSoup, job_name: str) -> str | None:
    """Find the image belonging to a job entry on the class/job page."""
    job_text = soup.find(string=lambda s: isinstance(s, str) and s.strip() == job_name)
    if job_text is None:
        return None
    return _nearest_icon_for_text(job_text)


def _nearby_ratio(lines: list[str], index: int, radius: int = 6) -> tuple[int | None, int | None]:
    """Find a current/max numeric ratio close to a progression label."""
    lo = max(0, index - radius)
    hi = min(len(lines), index + radius + 1)
    for value in lines[lo:hi]:
        match = re.fullmatch(r"([\d,]+|--|-)\s*/\s*([\d,]+|--|-)", value)
        if not match:
            continue
        current = (
            int(match.group(1).replace(",", ""))
            if match.group(1) not in {"--", "-"}
            else None
        )
        maximum = (
            int(match.group(2).replace(",", ""))
            if match.group(2) not in {"--", "-"}
            else None
        )
        return current, maximum
    return None, None


def _parse_special_progression(lines: list[str]) -> dict[str, ProgressionData]:
    """Parse Eureka, Bozja, and Occult Crescent progression."""
    result = {
        "eureka": ProgressionData(resource_name="xp"),
        "bozja": ProgressionData(resource_name="mettle"),
        "occult_crescent": ProgressionData(resource_name="knowledge"),
    }

    specs = (
        ("Elemental Level", "eureka"),
        ("Resistance Rank", "bozja"),
        ("Knowledge Level", "occult_crescent"),
    )

    for label, key in specs:
        try:
            idx = lines.index(label)
        except ValueError:
            continue

        # Lodestone renders the numeric rank/level immediately before the label.
        for back in range(1, 4):
            if idx - back >= 0 and re.fullmatch(r"\d+", lines[idx - back]):
                result[key].level = int(lines[idx - back])
                break

        current, maximum = _nearby_ratio(lines, idx)
        result[key].current = current
        result[key].maximum = maximum

    # Phantom Job details are retained as a single nested attribute on the
    # Occult Crescent entity. This intentionally avoids creating many HA entities.
    phantom_jobs: dict[str, dict[str, int | bool | None]] = {}
    phantom_heading = next(
        (
            i for i, value in enumerate(lines)
            if "Phantom Job" in value and ("Level" not in value)
        ),
        None,
    )
    if phantom_heading is not None:
        # Conservative generic scan of the following block. A row normally
        # contains a name, a level, and optionally current/max XP or MASTERED.
        window = lines[phantom_heading + 1 : phantom_heading + 120]
        i = 0
        while i < len(window):
            value = window[i]
            if (
                value
                and not re.fullmatch(r"[\d,]+", value)
                and "/" not in value
                and value.upper() != "MASTERED"
                and len(value) < 60
            ):
                name = value
                level = None
                current = maximum = None
                mastered = False
                for candidate in window[i + 1 : i + 5]:
                    if re.fullmatch(r"\d+", candidate) and level is None:
                        level = int(candidate)
                    ratio = re.fullmatch(
                        r"([\d,]+|--|-)\s*/\s*([\d,]+|--|-)",
                        candidate,
                    )
                    if ratio:
                        current = (
                            int(ratio.group(1).replace(",", ""))
                            if ratio.group(1) not in {"--", "-"}
                            else None
                        )
                        maximum = (
                            int(ratio.group(2).replace(",", ""))
                            if ratio.group(2) not in {"--", "-"}
                            else None
                        )
                    if candidate.upper() == "MASTERED":
                        mastered = True
                if level is not None or mastered:
                    phantom_jobs[slugify(name)] = {
                        "level": level,
                        "current_xp": current,
                        "max_xp": maximum,
                        "mastered": mastered,
                    }
            i += 1

    if phantom_jobs:
        result["occult_crescent"].extra["phantom_jobs"] = phantom_jobs

    return result


def parse_class_jobs(
    html: str,
) -> tuple[dict[str, JobData], dict[str, ProgressionData]]:
    """Parse levels/XP, icons, and exploratory-zone progression."""
    soup = BeautifulSoup(html, "html.parser")
    lines = _lines(_all_text(soup))
    jobs: dict[str, JobData] = {}

    for job_name, (abbr, role) in JOBS.items():
        try:
            idx = lines.index(job_name)
        except ValueError:
            continue

        level = current_xp = max_xp = None

        for back in range(1, 5):
            if idx - back >= 0 and re.fullmatch(r"\d+|-", lines[idx - back]):
                if lines[idx - back] != "-":
                    level = int(lines[idx - back])
                break

        for forward in range(1, 5):
            if idx + forward >= len(lines):
                break
            xp_match = re.fullmatch(
                r"([\d,]+|--|-)\s*/\s*([\d,]+|--|-)",
                lines[idx + forward],
            )
            if not xp_match:
                continue
            if xp_match.group(1) not in {"--", "-"}:
                current_xp = int(xp_match.group(1).replace(",", ""))
            if xp_match.group(2) not in {"--", "-"}:
                max_xp = int(xp_match.group(2).replace(",", ""))
            break

        jobs[slugify(job_name)] = JobData(
            name=job_name,
            slug=slugify(job_name),
            abbreviation=abbr.upper(),
            role=role,
            level=level,
            current_xp=current_xp,
            max_xp=max_xp,
            icon_url=_find_job_entry_icon(soup, job_name),
        )

    return jobs, _parse_special_progression(lines)

def resolve_current_job(
    profile_job_name: str | None,
    profile_icon_url: str | None,
    jobs: dict[str, JobData],
) -> str | None:
    """Resolve the currently displayed job.

    The localized profile-block job name is authoritative. Icon matching is only
    a fallback because Lodestone can use different icon variants across pages.
    """
    if profile_job_name:
        slug = slugify(profile_job_name)
        if slug in jobs:
            return jobs[slug].name

    profile_key = _image_key(profile_icon_url)
    if profile_key:
        matches = [
            job.name
            for job in jobs.values()
            if _image_key(job.icon_url) == profile_key
        ]
        if len(matches) == 1:
            return matches[0]

    return None

def parse_achievement_summary(html: str) -> AchievementSummary:
    """Parse current Lodestone achievement summary/history layout."""
    soup = BeautifulSoup(html, "html.parser")
    text = _all_text(soup)
    lines = _lines(text)

    points = None
    count = None

    try:
        idx = lines.index("Achievements")
    except ValueError:
        idx = -1

    if idx >= 0:
        for candidate in lines[idx + 1 : idx + 4]:
            if re.fullmatch(r"[\d,]+", candidate):
                points = _int(candidate)
                break

    total_match = re.search(r"\b([\d,]+)\s+Total\b", text, re.I)
    if total_match:
        count = int(total_match.group(1).replace(",", ""))

    if points is None:
        for pattern in (
            r"Achievement Points\s*(?:\||:)?\s*([\d,]+)",
            r"([\d,]+)\s*Achievement Points",
        ):
            match = re.search(pattern, text, re.I)
            if match:
                points = int(match.group(1).replace(",", ""))
                break

    latest_name = None
    latest_date = None
    history_pattern = re.compile(r'achievement\s+["“](.+?)["”]\s+earned!', re.I)

    for link in soup.find_all("a"):
        value = _text(link)
        if not value:
            continue
        match = history_pattern.search(value)
        if not match:
            continue
        latest_name = match.group(1).strip()
        parent_text = _text(link.parent)
        if parent_text:
            date_match = re.search(
                r"\b(\d{1,2}/\d{1,2}/\d{4}|\d{4}/\d{1,2}/\d{1,2})\b",
                parent_text,
            )
            if date_match:
                latest_date = date_match.group(1)
        break

    return AchievementSummary(
        count=count,
        points=points,
        latest_name=latest_name,
        latest_date=latest_date,
    )


def parse_collection_count(html: str) -> int | None:
    """Parse collection totals from the 'Total: N' Lodestone layout."""
    soup = BeautifulSoup(html, "html.parser")
    text = _all_text(soup)

    match = re.search(r"\bTotal\s*:\s*([\d,]+)\b", text, re.I)
    if match:
        return int(match.group(1).replace(",", ""))

    return None
