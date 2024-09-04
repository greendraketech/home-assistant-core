from dataclasses import dataclass, field
from datetime import timedelta
import logging
import operator
from typing import Any, Union

import httpx

_LOGGER = logging.getLogger(__name__)


@dataclass
class Threshold:
    """A class representing a threshold of some value."""

    comparator: Union[operator.lt, operator.le, operator.ge, operator.gt]
    """The comparison operator to use between the real value and this error or warning threshold."""
    error: Any
    """The threshold at which an alert is raised."""
    value: Any
    """The real value."""
    warning: Any
    """The threshold at which some action must be taken."""

    def in_error(self) -> bool:
        return bool(self.comparator(self.value, self.error))

    def in_warning(self) -> bool:
        return bool(self.comparator(self.value, self.warning))


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
    voltage: Threshold = field(metadata={"unit": "millivolt"})


@dataclass
class SystemInfo:
    battery: Battery
    current: int
    firmware_version: str
    inputs: list[PowerInput]
    """The live/"mains" power inputs."""
    mac_addr: str
    "Media Access Control address"
    power: Threshold = field(metadata={"unit": "milliwatt"})
    temperature: Threshold = field(metadata={"unit": "milli degree Celsius"})
    unique_id: str
    uptime: timedelta


class ApiClient:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str, port: int, timeout: int) -> None:
        """Initialize.

        timeout: seconds
        """
        self.host = host
        self.port = port
        self._http_client = httpx.AsyncClient(
            base_url=f"http://{self.host}:{self.port}",
            follow_redirects=True,
            limits=httpx.Limits(max_connections=1),
            timeout=httpx.Timeout(timeout),
        )

    async def shutdown(self):
        """Shutdown the client."""
        await self._http_client.aclose()

    async def get_system_info(self) -> SystemInfo:
        """Fetch overall system information."""
        resp = await self._http_client.get("/api")
        datas = resp.json()
        # _LOGGER.debug(f"api response: {resp.status_code}, {datas}")
        battery = datas["Bat"]
        device = datas["Dev"]
        uptime = datas["up_time"]
        sys_info = SystemInfo(
            battery=Battery(
                charge_current=battery["CCharge"],
                charge_max=battery["SocMax"],
                charge_min=battery["SocMin"],
                chemistry=battery["chemistry"],
                discharge_current=battery["CDischarge"],
                voltage=battery["V"],
            ),
            current=datas["C"],
            inputs=[
                PowerInput(datas["V1"]),
                PowerInput(datas["V2"]),
            ],
            firmware_version=device["FwVer"],
            mac_addr=device["Mac"],
            power=Threshold(
                comparator=operator.ge,
                error=datas["PE"],
                value=datas["P"],
                warning=datas["PW"],
            ),
            temperature=Threshold(
                comparator=operator.ge,
                error=datas["TE"],
                value=datas["T"],
                warning=datas["TW"],
            ),
            unique_id=device["UUID"],
            uptime=timedelta(days=uptime["days"], seconds=uptime["seconds"]),
        )
        _LOGGER.debug("system info: %s", sys_info)
        return sys_info
