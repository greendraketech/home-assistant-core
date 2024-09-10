"""DataUpdateCoordinator for the Green Drake Horizon integration."""

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api_client import ApiClient, Battery, PowerInput, Threshold

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class HorizonData:
    """Class for Horizon data."""

    battery: Battery
    # cards: Mapping[str, OutputCardInfo]
    current: int
    power: Threshold[int]
    power_inputs: list[PowerInput]
    temperature: Threshold[int]
    uptime: timedelta


class HorizonDataUpdateCoordinator(DataUpdateCoordinator[HorizonData]):
    """The Horizon update coordinator."""

    api_client: ApiClient

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: ApiClient,
    ) -> None:
        """Initialize global data updater."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Green Drake Horizon {api_client.url}",
            update_interval=timedelta(minutes=1),
        )
        self.api_client = api_client

    async def _async_update_data(self) -> HorizonData:
        _LOGGER.debug("HorizonDataUpdateCoordinator._async_update_data")
        data = await self.api_client.get_system_info()
        _LOGGER.debug("data = %s", data)
        return HorizonData(
            battery=data.battery,
            current=data.current,
            power=data.power,
            power_inputs=data.inputs,
            temperature=data.temperature,
            uptime=data.uptime,
        )
