"""Binary sensor platform for the Goster integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import GosterCoordinator
from .entity import GosterEntity


@dataclass(frozen=True, kw_only=True)
class GosterBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a Goster binary sensor."""

    value_fn: Callable[[GosterCoordinator], bool | None]
    admin_only: bool = False


BINARY_SENSORS: tuple[GosterBinarySensorEntityDescription, ...] = (
    GosterBinarySensorEntityDescription(
        key="bittorrent_reachable",
        translation_key="bittorrent_reachable",
        icon="mdi:swan",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        admin_only=True,
        value_fn=lambda coordinator: (
            coordinator.admin.get("bittorrent_status") == "reachable"
            if coordinator.admin
            else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Goster binary sensors."""
    coordinator: GosterCoordinator = entry.runtime_data

    entities = [
        GosterBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if not description.admin_only or coordinator.is_admin
    ]
    async_add_entities(entities)


class GosterBinarySensor(GosterEntity, BinarySensorEntity):
    """A binary sensor backed by the Goster coordinator."""

    entity_description: GosterBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: GosterCoordinator,
        description: GosterBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the current binary state."""
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the raw Goster reachability value."""
        status = self.coordinator.admin.get("bittorrent_reachability")
        return {"goster_status": status} if status else None
