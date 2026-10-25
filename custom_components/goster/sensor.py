"""Sensor platform for the Goster integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GosterCoordinator
from .entity import GosterEntity


def _stats(key: str) -> Callable[[GosterCoordinator], Any]:
    return lambda coordinator: coordinator.stats.get(key)


def _admin(key: str) -> Callable[[GosterCoordinator], Any]:
    return lambda coordinator: coordinator.admin.get(key)


def _live(key: str) -> Callable[[GosterCoordinator], Any]:
    return lambda coordinator: coordinator.live.get(key)


def _library_size_gb(coordinator: GosterCoordinator) -> float | None:
    size = coordinator.stats.get("size")
    if size is None:
        return None
    return round(float(size) / 1_000_000_000, 2)


def _network_speed(direction: str) -> Callable[[GosterCoordinator], float | None]:
    def value(coordinator: GosterCoordinator) -> float | None:
        interface = coordinator.network_interface_stats()
        if interface is None:
            return None
        return round(float(interface.get(direction) or 0) * 8 / 1_000_000, 3)

    return value


def _disk_speed(direction: str) -> Callable[[GosterCoordinator], float | None]:
    def value(coordinator: GosterCoordinator) -> float | None:
        read, write = coordinator.disk_totals()
        speed = read if direction == "read_speed" else write
        return round(speed / 1_000_000, 3)

    return value


def _me(key: str) -> Callable[[GosterCoordinator], Any]:
    return lambda coordinator: coordinator.me.get(key)


def _count_requests(coordinator: GosterCoordinator) -> int:
    requests = coordinator.me.get("requests") or []
    return len(requests) if isinstance(requests, list) else 0


def _count_shares(coordinator: GosterCoordinator) -> int:
    shares = coordinator.me.get("shares") or []
    return len(shares) if isinstance(shares, list) else 0


@dataclass(frozen=True, kw_only=True)
class GosterSensorEntityDescription(SensorEntityDescription):
    """Describe a Goster sensor."""

    value_fn: Callable[[GosterCoordinator], Any]
    admin_only: bool = False


SENSORS: tuple[GosterSensorEntityDescription, ...] = (
    GosterSensorEntityDescription(
        key="movies",
        translation_key="movies",
        icon="mdi:movie-open",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_stats("movies"),
    ),
    GosterSensorEntityDescription(
        key="series",
        translation_key="series",
        icon="mdi:television-classic",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_stats("tv"),
    ),
    GosterSensorEntityDescription(
        key="episodes",
        translation_key="episodes",
        icon="mdi:play-box-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_stats("episodes"),
    ),
    GosterSensorEntityDescription(
        key="files",
        translation_key="files",
        icon="mdi:file-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_stats("files"),
    ),
    GosterSensorEntityDescription(
        key="library_size",
        translation_key="library_size",
        icon="mdi:database",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_library_size_gb,
    ),
    GosterSensorEntityDescription(
        key="torrents",
        translation_key="torrents",
        icon="mdi:download-network",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_stats("torrents"),
    ),
    GosterSensorEntityDescription(
        key="users",
        translation_key="users",
        icon="mdi:account-multiple",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_stats("users"),
    ),
    GosterSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_stats("uptime_seconds"),
    ),
    GosterSensorEntityDescription(
        key="active_downloads",
        translation_key="active_downloads",
        icon="mdi:download",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda coordinator: coordinator.active_download_count(),
    ),
    GosterSensorEntityDescription(
        key="pending_requests",
        translation_key="pending_requests",
        icon="mdi:clipboard-clock-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_count_requests,
    ),
    GosterSensorEntityDescription(
        key="active_shares",
        translation_key="active_shares",
        icon="mdi:share-variant",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_count_shares,
    ),
    GosterSensorEntityDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        admin_only=True,
        value_fn=_live("cpu_percent"),
    ),
    GosterSensorEntityDescription(
        key="memory_usage",
        translation_key="memory_usage",
        icon="mdi:memory",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        admin_only=True,
        value_fn=_live("ram_percent"),
    ),
    GosterSensorEntityDescription(
        key="load_1m",
        translation_key="load_1m",
        icon="mdi:chart-line",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        admin_only=True,
        value_fn=_live("load1"),
    ),
    GosterSensorEntityDescription(
        key="network_download",
        translation_key="network_download",
        icon="mdi:download-network-outline",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        admin_only=True,
        value_fn=_network_speed("rx_speed"),
    ),
    GosterSensorEntityDescription(
        key="network_upload",
        translation_key="network_upload",
        icon="mdi:upload-network-outline",
        native_unit_of_measurement=UnitOfDataRate.MEGABITS_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        admin_only=True,
        value_fn=_network_speed("tx_speed"),
    ),
    GosterSensorEntityDescription(
        key="disk_read",
        translation_key="disk_read",
        icon="mdi:harddisk-remove",
        native_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        admin_only=True,
        value_fn=_disk_speed("read_speed"),
    ),
    GosterSensorEntityDescription(
        key="disk_write",
        translation_key="disk_write",
        icon="mdi:harddisk-plus",
        native_unit_of_measurement=UnitOfDataRate.MEGABYTES_PER_SECOND,
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        admin_only=True,
        value_fn=_disk_speed("write_speed"),
    ),
    GosterSensorEntityDescription(
        key="active_transcodes",
        translation_key="active_transcodes",
        icon="mdi:transcode",
        state_class=SensorStateClass.MEASUREMENT,
        admin_only=True,
        value_fn=_admin("current_transcode"),
    ),
    GosterSensorEntityDescription(
        key="public_ipv4",
        translation_key="public_ipv4",
        icon="mdi:ip-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        admin_only=True,
        value_fn=_admin("ipv4"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Goster sensors."""
    coordinator: GosterCoordinator = entry.runtime_data

    entities = [
        GosterSensor(coordinator, description)
        for description in SENSORS
        if not description.admin_only or coordinator.is_admin
    ]
    async_add_entities(entities)


class GosterSensor(GosterEntity, SensorEntity):
    """A sensor backed by the Goster coordinator."""

    entity_description: GosterSensorEntityDescription

    def __init__(
        self,
        coordinator: GosterCoordinator,
        description: GosterSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the sampled network interface for the speed sensors."""
        if self.entity_description.key in ("network_download", "network_upload"):
            interface = self.coordinator.network_interface_stats()
            if interface is not None:
                return {"interface": interface.get("iface")}
        return None
