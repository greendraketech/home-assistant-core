"""The Horizon integration."""

from __future__ import annotations

import datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .api_client import ApiClient
from .const import COORDINATOR, DOMAIN, UNIQUE_ID
from .coordinator import HorizonDataUpdateCoordinator

DEFAULT_SCAN_INTERVAL = 60
PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Horizon from a config entry."""

    config = entry.data

    host = config[CONF_HOST]
    port = config[CONF_PORT]

    name = "Horizon resource status"
    # TODO 1. Create API instance
    api_client = ApiClient(host, port, 10)
    coordinator = HorizonDataUpdateCoordinator(
        hass,
        name,
        datetime.timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        api_client,
    )

    # TODO 2. Validate the API connection (and authentication)
    _LOGGER.debug("getting first data refresh")
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})

    unique_device_id = (await api_client.get_system_info()).unique_id
    unique_id = f"{unique_device_id}"
    _LOGGER.debug("async_setup_entry: unique_id = %s", unique_id)
    # TODO 3. Store an API object for your platforms to access
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
        UNIQUE_ID: unique_id,
    }

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
