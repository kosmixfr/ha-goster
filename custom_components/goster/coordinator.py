"""Data coordinator for the Goster integration."""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    GosterApiError,
    GosterAuthError,
    GosterClient,
    GosterConnectionError,
)
from .const import (
    CONF_NETWORK_INTERFACE,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER_NAME,
)

LOGGER = logging.getLogger(LOGGER_NAME)

PHYSICAL_DISK_RE = re.compile(r"^(?:sd[a-z]+|nvme\d+n\d+|vd[a-z]+|xvd[a-z]+|mmcblk\d+)$")


class GosterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch data from one Goster server."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: GosterClient,
    ) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=interval),
        )
        self.entry = entry
        self.client = client
        self.is_admin = False
        self._network_interface: str | None = (
            entry.options.get(CONF_NETWORK_INTERFACE) or None
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest Goster state."""
        try:
            me = await self.client.async_get_me()
            self.is_admin = bool(me.get("admin"))

            data: dict[str, Any] = {
                "me": me,
                "stats": await self.client.async_get_stats(),
            }

            if self.is_admin:
                # These endpoints are admin-only. A token may lose its admin
                # flag while Home Assistant is running, so do not fail the
                # whole update if one of them becomes unavailable.
                try:
                    data["admin"] = await self.client.async_get_admin_info()
                except GosterApiError as err:
                    LOGGER.debug("Goster admin info unavailable: %s", err)
                try:
                    data["live"] = await self.client.async_get_live_stats()
                except GosterApiError as err:
                    LOGGER.debug("Goster live stats unavailable: %s", err)

            return data
        except GosterAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (GosterConnectionError, GosterApiError) as err:
            raise UpdateFailed(str(err)) from err

    @property
    def stats(self) -> dict[str, Any]:
        """Return library statistics."""
        return self.data.get("stats", {}) if self.data else {}

    @property
    def me(self) -> dict[str, Any]:
        """Return the current user payload."""
        return self.data.get("me", {}) if self.data else {}

    @property
    def admin(self) -> dict[str, Any]:
        """Return the admin dashboard payload."""
        return self.data.get("admin", {}) if self.data else {}

    @property
    def live(self) -> dict[str, Any]:
        """Return the live stats payload."""
        return self.data.get("live", {}) if self.data else {}

    @property
    def torrents(self) -> list[dict[str, Any]]:
        """Return the torrents attached to the configured user."""
        torrents = self.me.get("Torrents") or []
        return torrents if isinstance(torrents, list) else []

    def network_interface_stats(self) -> dict[str, Any] | None:
        """Return stats for the selected or best network interface."""
        interfaces = self.live.get("network") or []
        if not isinstance(interfaces, list) or not interfaces:
            return None

        if self._network_interface:
            for interface in interfaces:
                if interface.get("iface") == self._network_interface:
                    return interface
            return None

        for preferred in ("tun0", "wg0", "eth0", "enp0s3"):
            for interface in interfaces:
                if interface.get("iface") == preferred:
                    return interface

        for interface in interfaces:
            if interface.get("iface") != "lo":
                return interface
        return interfaces[0]

    def disk_totals(self) -> tuple[float, float]:
        """Return aggregate disk read/write speed in bytes per second."""
        devices = self.live.get("disk_io") or []
        if not isinstance(devices, list):
            return 0.0, 0.0

        physical = [
            device
            for device in devices
            if PHYSICAL_DISK_RE.match(str(device.get("device", "")))
        ]
        selected = physical or devices
        read = sum(float(device.get("read_speed") or 0) for device in selected)
        write = sum(float(device.get("write_speed") or 0) for device in selected)
        return read, write

    def active_download_count(self) -> int:
        """Return the number of torrents currently downloading."""
        return sum(
            1
            for torrent in self.torrents
            if str(torrent.get("status", "")).startswith("downloading")
            and not torrent.get("paused")
        )
