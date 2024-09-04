"""Provides a sensor to track a UPS."""

from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfElectricPotential, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import COORDINATOR, DOMAIN
from .coordinator import HorizonDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=1)

SENSORS: list[SensorEntityDescription] = [
    SensorEntityDescription(
        device_class=SensorDeviceClass.VOLTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        key="battery.voltage",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        name="battery voltage",
    ),
    SensorEntityDescription(
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        key="ups.uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        name="UPS uptime",
    ),
]


class HorizonSensor(CoordinatorEntity[HorizonDataUpdateCoordinator], SensorEntity):
    """A Horizon sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: HorizonDataUpdateCoordinator,
        description: SensorEntityDescription,
        unique_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{unique_id}_{description.key}"

    # @property
    # def unique_id(self) -> str:
    #     """Return a unique identifier for this sensor."""
    #     _LOGGER.debug("Greetings, unique_id wanter")
    #     sys_info = await self.coordinator.api_client.get_system_info()
    #     return sys_info.unique_id

    @property
    def native_value(self) -> StateType:
        """Return entity data from UPS."""
        data = self.coordinator.data
        _LOGGER.info("what data do coordinator have? %s", data)
        return data.get(self.entity_description.key)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the UI."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.info("What in the heck is stored: %s", entry)
    coordinator = entry[COORDINATOR]
    async_add_entities(
        HorizonSensor(coordinator, entity_description, config_entry.unique_id)
        for entity_description in SENSORS
    )
