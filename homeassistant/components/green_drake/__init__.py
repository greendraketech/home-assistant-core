"""The Horizon integration."""

from __future__ import annotations

import datetime
import logging
import random

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .api_client import ApiClient
from .const import COORDINATOR, DOMAIN
from .coordinator import HorizonDataUpdateCoordinator

DEFAULT_SCAN_INTERVAL = 60
PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


class HorizonData:
    """Stores the data retrieved from a Horizon UPS."""

    def __init__(self, host: str, port: int) -> None:
        self._client = ApiClient(host, port, 10)

    async def async_update(self):
        batt_volt = await self._client.get_battery_voltage()
        uptime = await self._client.get_uptime()
        return {
            "battery.voltage": batt_volt,
            "ups.uptime": uptime,
        }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Horizon from a config entry."""

    config = entry.data

    host = config[CONF_HOST]
    port = config[CONF_PORT]

    name = "Horizon resource status"
    coordinator = HorizonDataUpdateCoordinator(
        hass,
        name,
        datetime.timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        ApiClient(host, port, 10),
    )
    _LOGGER.debug("getting first data refresh")
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    # TODO 1. Create API instance
    unique_device_id = str(f"{host}:{port}-{random.randint(0, 9999)}")
    unique_id = f"{unique_device_id}"
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        # UNIQUE_ID: unique_id,
    }
    # TODO 2. Validate the API connection (and authentication)
    # TODO 3. Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, unique_id)},
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_setup(hass: HomeAssistant, config: ConfigEntry) -> bool:
    """Set up component from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
