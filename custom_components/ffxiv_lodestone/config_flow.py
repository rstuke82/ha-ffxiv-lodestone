"""Config flow for FFXIV Lodestone."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
)

from .api import LodestoneClient, LodestoneNotFound
from .const import (
    CONF_CHARACTER_ID,
    CONF_REFRESH_MINUTES,
    CONF_REGION,
    DEFAULT_REFRESH_MINUTES,
    DEFAULT_REGION,
    DOMAIN,
    MAX_REFRESH_MINUTES,
    MIN_REFRESH_MINUTES,
    SUPPORTED_REGIONS,
)


class FFXIVLodestoneConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a character by Lodestone character ID."""
        errors: dict[str, str] = {}

        if user_input is not None:
            character_id = str(user_input[CONF_CHARACTER_ID]).strip()
            region = user_input[CONF_REGION]

            await self.async_set_unique_id(f"{region}:{character_id}")
            self._abort_if_unique_id_configured()

            client = LodestoneClient(
                async_get_clientsession(self.hass),
                character_id=character_id,
                region=region,
            )

            try:
                character = await client.async_get_character()
            except LodestoneNotFound:
                errors["base"] = "character_not_found"
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"{character.name} ({character.world or 'Unknown World'})",
                    data={
                        CONF_CHARACTER_ID: character_id,
                        CONF_REGION: region,
                    },
                    options={
                        CONF_REFRESH_MINUTES: DEFAULT_REFRESH_MINUTES,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHARACTER_ID): str,
                    vol.Required(CONF_REGION, default=DEFAULT_REGION): SelectSelector(
                        SelectSelectorConfig(options=list(SUPPORTED_REGIONS))
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "character_search_url": "https://na.finalfantasyxiv.com/lodestone/character/"
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> FFXIVLodestoneOptionsFlow:
        return FFXIVLodestoneOptionsFlow(config_entry)


class FFXIVLodestoneOptionsFlow(config_entries.OptionsFlow):
    """Configure integration options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_REFRESH_MINUTES,
            DEFAULT_REFRESH_MINUTES,
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_REFRESH_MINUTES,
                        default=current,
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_REFRESH_MINUTES,
                            max=MAX_REFRESH_MINUTES,
                            step=5,
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
