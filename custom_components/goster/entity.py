"""Base entity for the Goster integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_APP_URL, DOMAIN
from .coordinator import GosterCoordinator


class GosterEntity(CoordinatorEntity[GosterCoordinator]):
    """Common device information and availability for Goster entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GosterCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Goster",
            model="Goster server",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.entry.data[CONF_APP_URL],
        )

    @property
    def available(self) -> bool:
        """Return whether the coordinator has usable data."""
        return super().available and self.coordinator.data is not None
