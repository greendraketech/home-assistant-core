from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
import logging
import operator

import httpx

_LOGGER = logging.getLogger(__name__)


@dataclass
class Threshold[T]:
    """A class representing a threshold of some value."""

    comparator: Callable[[T, T], bool]
    """The comparison operator to use between the real value and this error or warning threshold."""
    error: T
    """The threshold at which an alert is raised."""
    value: T
    """The real value."""
    warning: T
    """The threshold at which some action must be taken."""

    def in_error(self) -> bool:
        return bool(self.comparator(self.value, self.error))

    def in_warning(self) -> bool:
        return bool(self.comparator(self.value, self.warning))


@dataclass
class RelativeThreshold[T]:
    max: T
    """The maximum value `value` can be."""
    relative_error: int = field(metadata={"unit": "per cent mille"})
    """The relative threshold of `max` at which `value` enters the "error" state."""
    relative_warning: int = field(metadata={"unit": "per cent mille"})
    """The relative threshold of `max` at which `value` enters the "warning" state."""
    value: T
    """The real value."""

    @property
    def error(self) -> T:
        return self.max * (self.relative_error / 100_000)

    @property
    def warning(self) -> T:
        return self.max * (self.relative_warning / 100_000)

    def in_error(self) -> bool:
        """Determine if the value has entered the "error" region.

        >>> threshold = RelativeThreshold[int]()
        """
        return self.value >= self.error

    def in_warning(self) -> bool:
        return self.value >= self.warning


@dataclass
class Range[T]:
    """A class representing a value and the range that value is allowed to be in."""

    min: T
    value: T
    max: T


@dataclass
class PowerInput:
    voltage: int = field(metadata={"unit": "millivolt"})


@dataclass
class Battery:
    charge_current: int = field(metadata={"unit": "milliamp"})
    charge_max: int = field(metadata={"unit": "per cent mille"})
    charge_min: int = field(metadata={"unit": "per cent mille"})
    chemistry: str
    discharge_current: int = field(metadata={"unit": "milliamp"})
    voltage: int = field(metadata={"unit": "millivolt"})


@dataclass
class SystemInfo:
    battery: Battery
    current: int
    firmware_version: str
    inputs: list[PowerInput]
    """The live/"mains" power inputs."""
    mac_addr: str
    "Media Access Control address"
    power: Threshold[int] = field(metadata={"unit": "milliwatt"})
    temperature: Threshold[int] = field(metadata={"unit": "milli degree Celsius"})
    unique_id: str
    uptime: timedelta


@dataclass
class OutputPowerStage:
    # current: Range[int] = field(metadata={"unit": "milliamp"})
    # power: Range[int] = field(metadata={"unit": "milliwatt"})
    temperature: Threshold[int] = field(metadata={"unit": "milli degree Celsius"})
    voltage: Range[int] = field(metadata={"unit": "millivolt"})


@dataclass
class CleanShutdown:
    channel: int
    pulse_delay: int = field(metadata={"unit": "millisecond"})
    pulse_width: int = field(metadata={"unit": "millisecond"})


@dataclass
class OutputPort:
    clean_shutdown: CleanShutdown
    enabled: bool
    label: str
    min_battery_charge: int
    priority: int


class OutputCardStatus(StrEnum):
    INIT = "Init!"
    OK = "OK!"
    UNKOWN_CARD = "No ID Match!"


@dataclass
class OutputCardInfo:
    """Information about an installed output card."""

    label: str
    model: str
    power_stages: list[OutputPowerStage]
    priority: int
    status: OutputCardStatus


class ApiClient:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(
        self,
        url: str,
        timeout: int,
        *,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize.

                url: the URL where the device can be reached
        timeout: seconds
        httpx_client: an `httpx.AsyncClient` used to make HTTP requests
        """
        self.url = url
        self._http_client = (
            httpx_client if httpx_client is not None else httpx.AsyncClient()
        )
        self._http_client.base_url = self.url
        self._http_client.follow_redirects = True
        self._http_client.timeout = httpx.Timeout(timeout)

    async def shutdown(self):
        """Shutdown the client."""
        await self._http_client.aclose()

    async def get_system_info(self) -> SystemInfo:
        """Fetch overall system information."""
        resp = await self._http_client.get("/api")
        data = resp.json()
        _LOGGER.debug("API response body = %s", data)
        battery = data["Bat"]
        device = data["Dev"]
        uptime = data["up_time"]
        return SystemInfo(
            battery=Battery(
                charge_current=battery["CCharge"],
                charge_max=battery["SocMax"],
                charge_min=battery["SocMin"],
                chemistry=battery["chemistry"],
                discharge_current=battery["CDischarge"],
                voltage=battery["V"],
            ),
            current=data["C"],
            inputs=[
                PowerInput(data["V1"]),
                PowerInput(data["V2"]),
            ],
            firmware_version=device["FwVer"],
            mac_addr=device["Mac"],
            power=Threshold(
                comparator=operator.ge,
                error=data["PE"],
                value=data["P"],
                warning=data["PW"],
            ),
            temperature=Threshold(
                comparator=operator.ge,
                error=data["TE"],  # codespell:ignore TE
                value=data["T"],
                warning=data["TW"],
            ),
            unique_id=device["UUID"] or device["Id"],
            uptime=timedelta(days=uptime["days"], seconds=uptime["seconds"]),
        )

    async def get_card_info(self, card_num: int) -> OutputCardInfo:
        """Fetch information about card `card_num`."""
        resp = await self._http_client.get(f"/api/card/{card_num}")
        data = resp.json()
        _LOGGER.debug("Card info response = %s", data)
        power_stages = [
            OutputPowerStage(
                temperature=Threshold(
                    comparator=operator.ge,
                    error=value["TE"],
                    value=3,  # TODO
                    warning=value["TW"],
                ),
                voltage=Range(
                    min=value["VMin"],
                    value=7,  # TODO
                    max=value["VMax"],
                ),
            )
            for key, value in data["Pwr"].items()
        ]
        return OutputCardInfo(
            label=data["label"],
            model="TODO",  # TODO
            power_stages=power_stages,
            priority=data["Pri"],
            status=data["status"],
        )
