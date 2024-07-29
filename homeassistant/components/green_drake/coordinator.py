"""DataUpdateCoordinator for the Green Drake Horizon integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_client import ApiClient

_LOGGER = logging.getLogger(__name__)


class HorizonDataUpdateCoordinator(DataUpdateCoordinator):
    """The Horizon update coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        update_interval: timedelta,
        api_client: ApiClient,
    ) -> None:
        """Initialize global data updater."""
        super().__init__(hass, _LOGGER, name=name, update_interval=update_interval)
        self.api_client = api_client

    async def _async_update_data(self) -> dict[str, Any]:
        return {
            "battery.voltage": await self.api_client.get_battery_voltage(),
            "ups.uptime": (await self.api_client.get_uptime()).total_seconds(),
        }
