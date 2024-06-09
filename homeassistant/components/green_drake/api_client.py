from datetime import timedelta
import logging

import httpx

_LOGGER = logging.getLogger(__name__)


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
        self._http_client.aclose()

    async def get_system_info(self):
        """Fetch overall system information."""
        resp = await self._http_client.get("/api")
        datas = resp.json()
        _LOGGER.debug(f"api response: {resp.status_code}, {datas}")
        return datas

    async def get_battery_voltage(self) -> int:
        """Fetch the connected battery's voltage."""
        data = await self.get_system_info()
        _LOGGER.debug("battery_voltage = %d", data["battery_voltage"])
        return data["battery_voltage"]

    async def get_uptime(self) -> timedelta:
        """Fetch the uptime of the device."""
        resp = await self.get_system_info()
        uptime = resp["up_time"]
        _LOGGER.debug("uptime: %s", uptime)
        return timedelta(days=uptime["days"], seconds=uptime["seconds"])
