"""Provides a sensor to track a UPS."""

from datetime import timedelta
import logging
import random

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
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this sensor."""
        _LOGGER.debug("Greetings, unique_id wanter")
        a = self.coordinator.api_client
        return f"{a.host}:{a.port}-{random.randint(1, 9999)}"

    @property
    def native_value(self) -> StateType:
        """Return entity data from UPS."""
        data = self.coordinator.data
        return data.get(self.entity_description.key)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the UI."""
    _LOGGER.debug(
        "What in the heck is stored: %s", hass.data[DOMAIN][config_entry.entry_id]
    )
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    # horizon_data = hass.data[DOMAIN][config_entry.entry_id][DATA]
    async_add_entities(
        HorizonSensor(
            coordinator,
            entity_description,
        )
        for entity_description in SENSORS
    )
