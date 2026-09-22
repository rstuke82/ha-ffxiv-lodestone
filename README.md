# FFXIV Lodestone for Home Assistant

A HACS-ready custom integration that reads public FINAL FANTASY XIV character
data from the Lodestone.

## Features

Each configured Lodestone character becomes one Home Assistant device.

Entity IDs use the full character name slug:

- `sensor.firstname_surname`
- `sensor.firstname_surname_achievement_points`
- `sensor.firstname_surname_paladin`
- `image.firstname_surname_portrait`

Job-dependent data belongs to the job entity, not character-level entities.

The integration polls Lodestone every 30 minutes with Home Assistant's shared
aiohttp session.

## Current entities

Character-level:

- Primary character sensor (state = current job; profile details as attributes)
- Achievement points
- Achievement count
- Latest achievement
- Mount count
- Minion count
- Facewear count
- Eureka (level as state; XP in attributes)
- Bozja (rank as state; mettle in attributes)
- Occult Crescent (knowledge level as state; knowledge and Phantom Jobs in attributes)

Job-level:

- One sensor per combat/crafting/gathering job
- State = level
- Attributes = abbreviation, role, XP, and current displayed-job stats when available
- Each job sensor uses a transparent/plain class/job PNG as its entity picture

Large collections are intentionally not written into recorder-heavy entity
attributes.

## Installation

### HACS custom repository

1. In HACS, open **Integrations**.
2. Open the menu and choose **Custom repositories**.
3. Add this repository URL and select **Integration** as the category.
4. Install **FFXIV Lodestone**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add Integration** and select **FFXIV Lodestone**.

### Manual installation

Copy `custom_components/ffxiv_lodestone` to
`<config>/custom_components/ffxiv_lodestone`, restart Home Assistant, then add
**FFXIV Lodestone** from Devices & Services.

## Notes

Lodestone is an HTML site rather than a stable public JSON API. Parsing is isolated
in `parser.py` so Lodestone markup changes can be handled without changing the
Home Assistant entity model.

## Refresh interval

The default polling interval is 30 minutes. It can be changed from the
integration's **Configure** dialog to any 5-minute increment from 5 to 60 minutes.

Each refresh currently retrieves six public Lodestone pages per character.

## Branding

Home Assistant 2026.3+ loads the custom integration icon/logo from the local
`custom_components/ffxiv_lodestone/brand/` directory.

## Primary character entity

Each character has a primary sensor using the character's full slug, for example:

`sensor.firstname_surname`

Its state is the currently displayed job. Character profile information such as
world, data center, title, race, clan, gender, nameday, guardian, city-state,
Grand Company/rank, Free Company, character ID, and Lodestone URL is exposed as
attributes.

## Last-known-value behavior

Successful snapshots are persisted in Home Assistant storage. If Lodestone
temporarily omits a field, the integration keeps the previous known value. If a
refresh fails entirely, the previous snapshot remains available and entities are
marked with `stale: true`.

`last_successful_update` records when fresh Lodestone data was last successfully
stored.

## Job icon fallback

Job entities use plain class/job pictures where available. Beastmaster currently
uses the official Lodestone-provided job image until the plain icon source used
by the integration includes a matching Beastmaster asset.


