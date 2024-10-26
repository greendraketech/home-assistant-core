"""Provides a sensor to track a UPS."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HorizonConfigEntry
from .coordinator import HorizonData, HorizonDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class HorizonSensorEntityDescription(SensorEntityDescription):
    """Describes Green Drake Horizaon sensory entity."""

    value_fn: Callable[[HorizonData], StateType]


SENSORS: list[HorizonSensorEntityDescription] = [
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.CURRENT,
        key="battery.charge_current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery.charge_current,
    ),
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.CURRENT,
        key="battery.discharge_current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery.discharge_current,
    ),
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.VOLTAGE,
        key="battery.voltage",
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda data: data.battery.voltage,
    ),
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.CURRENT,
        key="ups.current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.current,
    ),
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.ENERGY,
        key="ups.energy consumption",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.energy_consumption,
    ),
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.POWER,
        key="ups.power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.power.value / 1_000,
    ),
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.TEMPERATURE,
        key="ups.temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.temperature.value / 1_000,
    ),
    HorizonSensorEntityDescription(
        device_class=SensorDeviceClass.DURATION,
        key="ups.uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda data: data.uptime.total_seconds(),
    ),
]


class HorizonSensor(CoordinatorEntity[HorizonDataUpdateCoordinator], SensorEntity):
    """A Horizon sensor."""

    entity_description: HorizonSensorEntityDescription

    def __init__(
        self,
        coordinator: HorizonDataUpdateCoordinator,
        description: HorizonSensorEntityDescription,
        unique_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{unique_id}_{description.key}"

    @property
    def native_value(self) -> StateType:
        """Return entity data from UPS."""
        data = self.coordinator.data
        _LOGGER.debug("what data do coordinator have? %s", data)
        _LOGGER.debug(
            "what the value_fn? %s -> %s",
            self.entity_description.value_fn,
            self.entity_description.value_fn(data),
        )
        return self.entity_description.value_fn(data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HorizonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors from a config entry created in the UI."""
    _LOGGER.debug("What in the heck is stored: %s", entry)
    coordinator = entry.runtime_data
    sys_entities = [
        HorizonSensor(coordinator, entity_description, entry.unique_id)
        for entity_description in SENSORS
    ]
    # TODO do an async_add_entities per: system->card->powerstage->port
    extra_entities: list[HorizonSensor] = []
    for card_idx in range(4):
        for power_stage_idx in range(1):
            extra_entities.append(
                HorizonSensor(
                    coordinator,
                    HorizonSensorEntityDescription(
                        device_class=SensorDeviceClass.TEMPERATURE,
                        key=f"card[{card_idx}].power_stage[{power_stage_idx}].temperature",
                        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                        state_class=SensorStateClass.MEASUREMENT,
                        value_fn=partial(
                            lambda data, card, ps: data.cards[f"Card {card}"]
                            .power_stages[ps]
                            .temperature.value,
                            card=card_idx,
                            ps=power_stage_idx,
                        ),
                    ),
                    entry.unique_id,
                )
            )
            extra_entities.append(
                HorizonSensor(
                    coordinator,
                    HorizonSensorEntityDescription(
                        device_class=SensorDeviceClass.VOLTAGE,
                        key=f"card[{card_idx}].power_stage[{power_stage_idx}].voltage",
                        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
                        state_class=SensorStateClass.MEASUREMENT,
                        value_fn=partial(
                            lambda data, card, ps: data.cards[f"Card {card}"]
                            .power_stages[ps]
                            .voltage.value,
                            card=card_idx,
                            ps=power_stage_idx,
                        ),
                    ),
                    entry.unique_id,
                )
            )
            for _port in range(2):
                pass

    async_add_entities(sys_entities + extra_entities)
