"""Constants for FFXIV Lodestone."""

DOMAIN = "ffxiv_lodestone"

CONF_CHARACTER_ID = "character_id"
CONF_REGION = "region"
CONF_REFRESH_MINUTES = "refresh_minutes"

DEFAULT_REGION = "na"
DEFAULT_REFRESH_MINUTES = 30
MIN_REFRESH_MINUTES = 5
MAX_REFRESH_MINUTES = 60

SUPPORTED_REGIONS = ("na", "eu", "fr", "de", "jp")

PLATFORMS = ["sensor", "image"]

BASE_URLS = {
    "na": "https://na.finalfantasyxiv.com",
    "eu": "https://eu.finalfantasyxiv.com",
    "fr": "https://fr.finalfantasyxiv.com",
    "de": "https://de.finalfantasyxiv.com",
    "jp": "https://jp.finalfantasyxiv.com",
}

# Transparent/plain class/job PNGs from the XIVAPI classjob-icons repository.
CLEAN_JOB_ICON_BASE = "https://raw.githubusercontent.com/xivapi/classjob-icons/master/icons"
