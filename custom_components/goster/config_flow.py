"""Config flow for the Goster integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import selector

from .api import (
    GosterApiError,
    GosterAuthError,
    GosterClient,
    GosterConnectionError,
)
from .const import (
    CONF_APP_URL,
    CONF_NETWORK_INTERFACE,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER_NAME,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

LOGGER = logging.getLogger(LOGGER_NAME)


def _normalize_app_url(value: str) -> str:
    """Normalize a user supplied Goster URL."""
    value = value.strip().rstrip("/")
    if "://" not in value:
        value = f"https://{value}"
    return value


def _url_is_valid(value: str) -> bool:
    """Return whether the URL has a scheme and a host."""
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


async def _async_validate(hass: HomeAssistant, base_url: str, token: str) -> dict[str, Any]:
    """Validate credentials and return the Goster user payload."""
    client = GosterClient(base_url, token)
    try:
        return await client.async_validate()
    finally:
        await client.async_close()


class GosterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Goster."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            app_url = _normalize_app_url(user_input[CONF_APP_URL])
            token = user_input[CONF_TOKEN].strip()

            if not _url_is_valid(app_url):
                errors[CONF_APP_URL] = "invalid_url"
            elif not token:
                errors[CONF_TOKEN] = "invalid_token"
            else:
                try:
                    me = await _async_validate(self.hass, app_url, token)
                except GosterAuthError:
                    errors["base"] = "invalid_auth"
                except GosterConnectionError:
                    errors["base"] = "cannot_connect"
                except GosterApiError:
                    errors["base"] = "invalid_response"
                except Exception:  # noqa: BLE001 - surface unexpected failures in the UI
                    LOGGER.exception("Unexpected error while validating Goster")
                    errors["base"] = "unknown"
                else:
                    host = urlparse(app_url).netloc.lower()
                    await self.async_set_unique_id(f"{host}:{me.get('id', 'unknown')}")
                    self._abort_if_unique_id_configured()

                    username = me.get("username")
                    title = f"Goster - {username}" if username else f"Goster - {host}"
                    return self.async_create_entry(
                        title=title,
                        data={CONF_APP_URL: app_url, CONF_TOKEN: token},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_APP_URL): str,
                    vol.Required(CONF_TOKEN): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle expired credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new token after authentication fails."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            try:
                await _async_validate(self.hass, entry.data[CONF_APP_URL], token)
            except GosterAuthError:
                errors["base"] = "invalid_auth"
            except GosterConnectionError:
                errors["base"] = "cannot_connect"
            except GosterApiError:
                errors["base"] = "invalid_response"
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unexpected error while re-authenticating Goster")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_TOKEN: token},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TOKEN): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    )
                }
            ),
            description_placeholders={
                CONF_APP_URL: entry.data[CONF_APP_URL],
            },
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(entry: ConfigEntry) -> GosterOptionsFlow:
        """Return the options flow."""
        return GosterOptionsFlow()


class GosterOptionsFlow(OptionsFlow):
    """Options for a Goster entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage polling and network options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Optional(
                        CONF_NETWORK_INTERFACE,
                        default=options.get(CONF_NETWORK_INTERFACE, ""),
                    ): str,
                }
            ),
        )
