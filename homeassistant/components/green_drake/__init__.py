"""The Horizon integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.httpx_client

from .api_client import ApiClient
from .const import DOMAIN
from .coordinator import HorizonDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
_LOGGER = logging.getLogger(__name__)


type HorizonConfigEntry = ConfigEntry[HorizonDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HorizonConfigEntry) -> bool:
    """Set up Horizon from a config entry."""

    config = entry.data

    url = config[CONF_URL]

    # Create API instance
    api_client = ApiClient(
        url,
        10,
        httpx_client=homeassistant.helpers.httpx_client.get_async_client(hass),
    )
    coordinator = HorizonDataUpdateCoordinator(
        hass,
        api_client,
    )

    # Validate the API connection (and authentication)
    _LOGGER.debug("getting first data refresh")
    await coordinator.async_config_entry_first_refresh()

    unique_device_id = (await api_client.get_system_info()).unique_id
    unique_id = f"{unique_device_id}"
    _LOGGER.debug("async_setup_entry: unique_id = %s", unique_id)

    # Store an API object for your platforms to access
    entry.runtime_data = coordinator

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, unique_id)},
        manufacturer="Green Drake",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
