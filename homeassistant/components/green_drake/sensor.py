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
from .api_client import OutputPowerStage
from .coordinator import HorizonData, HorizonDataUpdateCoordinator

CardLabel = type[str]

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

    def _get_card_power_stage(
        data: HorizonData, card_label: str, power_stage: int
    ) -> OutputPowerStage | None:
        card_data = data.cards[card_label]
        if card_data is None:
            return None
        return card_data.power_stages[power_stage]

    def _get_power_stage_temperature(
        data: HorizonData, card_label: str, power_stage: int
    ):
        ps_data = _get_card_power_stage(data, card_label, power_stage)
        return ps_data.temperature.value

    def _get_power_stage_voltage(data: HorizonData, card_label: str, power_stage: int):
        ps_data = _get_card_power_stage(data, card_label, power_stage)
        return ps_data.voltage.value

    extra_entities: list[HorizonSensor] = []

    current_cards: set[CardLabel] = set()

    def _async_card_listener() -> None:
        """Add sensors for OutputCards when discovered."""
        _LOGGER.debug("async card listener!!!")
        received_cards = coordinator.data.cards
        _LOGGER.debug("recieved_cards = %s", received_cards)
        rcvd_card_labels = set(received_cards.keys())
        new_labels = rcvd_card_labels - current_cards
        # old_labels = current_cards - rcvd_card_labels
        _LOGGER.debug("new labels = %s", new_labels)
        for new_label in new_labels:
            card = received_cards[new_label]
            _LOGGER.debug(
                "card = %s; other way = %s", card, received_cards.get(new_label)
            )
            card_entities: list[HorizonSensor] = []
            for ps_idx, _power_stage in enumerate(card.power_stages):
                card_entities.append(
                    HorizonSensor(
                        coordinator,
                        HorizonSensorEntityDescription(
                            device_class=SensorDeviceClass.CURRENT,
                            key=f"card[{new_label}].power_stage[{ps_idx}].current",
                            native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
                            state_class=SensorStateClass.MEASUREMENT,
                            value_fn=partial(
                                lambda data, card_label, ps: data.cards[card_label]
                                .power_stages[ps]
                                .current.value,
                                card_label=new_label,
                                ps=ps_idx,
                            ),
                        ),
                        entry.unique_id,
                    )
                )
                card_entities.append(
                    HorizonSensor(
                        coordinator,
                        HorizonSensorEntityDescription(
                            device_class=SensorDeviceClass.POWER,
                            key=f"card[{new_label}].power_stage[{ps_idx}].power",
                            native_unit_of_measurement=UnitOfPower.WATT,
                            state_class=SensorStateClass.MEASUREMENT,
                            value_fn=partial(
                                lambda data, card_label, ps: data.cards[card_label]
                                .power_stages[ps]
                                .power.value
                                / 1000,
                                card_label=new_label,
                                ps=ps_idx,
                            ),
                        ),
                        entry.unique_id,
                    )
                )
                card_entities.append(
                    HorizonSensor(
                        coordinator,
                        HorizonSensorEntityDescription(
                            device_class=SensorDeviceClass.TEMPERATURE,
                            key=f"card[{new_label}].power_stage[{ps_idx}].temperature",
                            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                            state_class=SensorStateClass.MEASUREMENT,
                            value_fn=partial(
                                lambda data, card_label, ps: data.cards[card_label]
                                .power_stages[ps]
                                .temperature.value
                                / 1000,
                                card_label=new_label,
                                ps=ps_idx,
                            ),
                        ),
                        entry.unique_id,
                    )
                )
                card_entities.append(
                    HorizonSensor(
                        coordinator,
                        HorizonSensorEntityDescription(
                            device_class=SensorDeviceClass.VOLTAGE,
                            key=f"card[{new_label}].power_stage[{ps_idx}].voltage",
                            native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
                            state_class=SensorStateClass.MEASUREMENT,
                            value_fn=partial(
                                lambda data, card_label, ps: data.cards[card_label]
                                .power_stages[ps]
                                .voltage.value,
                                card_label=new_label,
                                ps=ps_idx,
                            ),
                        ),
                        entry.unique_id,
                    )
                )
            async_add_entities(card_entities)
            current_cards.add(card.label)

    coordinator.async_add_listener(_async_card_listener)
    _async_card_listener()

    # TODO do an async_add_entities per: system->card->powerstage->port

    async_add_entities(sys_entities + extra_entities)
