"""Async client for the Goster HTTP API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import LOGGER_NAME

LOGGER = logging.getLogger(LOGGER_NAME)


class GosterError(Exception):
    """Base error for the Goster integration."""


class GosterAuthError(GosterError):
    """Raised when the configured token is rejected."""


class GosterConnectionError(GosterError):
    """Raised when the Goster server cannot be reached."""


class GosterApiError(GosterError):
    """Raised when Goster returns an unexpected response."""


class GosterClient:
    """Small stateful HTTP client.

    Goster authenticates with a token and then keeps the resulting
    ``mysession`` cookie. The client therefore owns its own aiohttp session so
    that the cookie jar is not shared with other integrations.
    """

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._session = aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            timeout=aiohttp.ClientTimeout(total=45),
            headers={"Accept": "application/json"},
        )
        self._login_lock = asyncio.Lock()
        self._logged_in = False

    @property
    def base_url(self) -> str:
        """Return the configured base URL."""
        return self._base_url

    async def async_close(self) -> None:
        """Close the underlying HTTP session."""
        await self._session.close()

    async def _async_login(self) -> None:
        """Authenticate and store the session cookie."""
        async with self._login_lock:
            if self._logged_in:
                return

            try:
                async with self._session.post(
                    f"{self._base_url}/api/login",
                    json={"token": self._token},
                ) as response:
                    body = await response.text()
                    if response.status in (400, 401, 403):
                        raise GosterAuthError("Goster rejected the configured token")
                    if response.status >= 400:
                        raise GosterApiError(
                            f"Goster login failed with HTTP {response.status}: {body[:200]}"
                        )
            except GosterError:
                raise
            except asyncio.TimeoutError as err:
                raise GosterConnectionError("Timeout while logging in to Goster") from err
            except aiohttp.ClientError as err:
                raise GosterConnectionError(f"Cannot connect to Goster: {err}") from err

            self._logged_in = True

    async def _async_request(self, path: str) -> Any:
        """Perform an authenticated GET request, retrying once after a 401."""
        for attempt in range(2):
            if not self._logged_in:
                await self._async_login()

            try:
                async with self._session.get(f"{self._base_url}{path}") as response:
                    body = await response.text()
                    if response.status == 401:
                        self._logged_in = False
                        if attempt == 0:
                            continue
                        raise GosterAuthError("Goster session expired")
                    if response.status == 403:
                        raise GosterApiError(f"Access denied for {path}")
                    if response.status >= 400:
                        raise GosterApiError(
                            f"Goster returned HTTP {response.status} for {path}: {body[:200]}"
                        )

                    try:
                        return await response.json(content_type=None)
                    except ValueError as err:
                        raise GosterApiError(
                            f"Goster returned invalid JSON for {path}"
                        ) from err
            except GosterError:
                raise
            except asyncio.TimeoutError as err:
                raise GosterConnectionError(
                    f"Timeout while requesting {path} from Goster"
                ) from err
            except aiohttp.ClientError as err:
                raise GosterConnectionError(
                    f"Cannot connect to Goster while requesting {path}: {err}"
                ) from err

        raise GosterAuthError("Goster session expired")

    async def async_validate(self) -> dict[str, Any]:
        """Validate the token and return the current user payload."""
        await self._async_login()
        payload = await self._async_request("/api/me")
        if not isinstance(payload, dict):
            raise GosterApiError("Unexpected /api/me response")
        return payload

    async def async_get_me(self) -> dict[str, Any]:
        """Return the current user, torrents, shares and requests."""
        payload = await self._async_request("/api/me")
        if not isinstance(payload, dict):
            raise GosterApiError("Unexpected /api/me response")
        return payload

    async def async_get_stats(self) -> dict[str, Any]:
        """Return the public library statistics."""
        payload = await self._async_request("/api/stats")
        if not isinstance(payload, dict):
            raise GosterApiError("Unexpected /api/stats response")
        return payload

    async def async_get_admin_info(self) -> dict[str, Any]:
        """Return the admin dashboard payload."""
        payload = await self._async_request("/api/admin/info")
        if not isinstance(payload, dict):
            raise GosterApiError("Unexpected /api/admin/info response")
        return payload

    async def async_get_live_stats(self) -> dict[str, Any]:
        """Return live CPU, memory, network and disk statistics."""
        payload = await self._async_request("/api/admin/live-stats")
        if not isinstance(payload, dict):
            raise GosterApiError("Unexpected /api/admin/live-stats response")
        return payload
