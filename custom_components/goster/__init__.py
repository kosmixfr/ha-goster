"""Home Assistant integration for Goster."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import GosterClient
from .const import (
    CONF_APP_URL,
    LEGACY_CONF_BASE_URL,
    CONF_TOKEN,
    DOMAIN,
    LOGGER_NAME,
    PLATFORMS,
)
from .coordinator import GosterCoordinator

LOGGER = logging.getLogger(LOGGER_NAME)

type GosterConfigEntry = ConfigEntry[GosterCoordinator]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries that used the base_url key."""
    if entry.version == 1:
        data = dict(entry.data)
        if LEGACY_CONF_BASE_URL in data and CONF_APP_URL not in data:
            data[CONF_APP_URL] = data.pop(LEGACY_CONF_BASE_URL)
        hass.config_entries.async_update_entry(entry, data=data, version=2)
        LOGGER.info("Migrated Goster config entry to version 2")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GosterConfigEntry) -> bool:
    """Set up Goster from a config entry."""
    client = GosterClient(entry.data[CONF_APP_URL], entry.data[CONF_TOKEN])
    coordinator = GosterCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GosterConfigEntry) -> bool:
    """Unload a Goster config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.async_close()
    return unloaded


async def _async_update_listener(
    hass: HomeAssistant, entry: GosterConfigEntry
) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
