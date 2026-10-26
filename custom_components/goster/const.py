"""Constants for the Goster integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "goster"
DEFAULT_NAME = "Goster"
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 3600

CONF_APP_URL = "app_url"
LEGACY_CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_NETWORK_INTERFACE = "network_interface"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

LOGGER_NAME = "custom_components.goster"
