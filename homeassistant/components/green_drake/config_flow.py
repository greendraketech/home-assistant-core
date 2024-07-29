"""Config flow for Horizon integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .api_client import ApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=80): cv.port,
        vol.Required(
            CONF_TIMEOUT, default=10, description="Timeout"
        ): cv.positive_float,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data[CONF_USERNAME], data[CONF_PASSWORD]
    # )

    ApiClient(data[CONF_HOST], data[CONF_PORT], data[CONF_TIMEOUT])

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return STEP_USER_DATA_SCHEMA(data)


class HorizonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Green Drake Horizon config flow."""

    VERSION = 0
    MINOR_VERSION = 1

    async def async_setup_entry(
        self, saved_input: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Load the saved configuration."""
        return self.async_create_entry(
            title=_get_entity_tile(saved_input[CONF_HOST], saved_input[CONF_PORT]),
            data=saved_input,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Take the user through the UI config flow."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                validated_input = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=_get_entity_tile(
                        validated_input[CONF_HOST], validated_input[CONF_PORT]
                    ),
                    data=validated_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
        )


def _get_entity_tile(host: str, port: int):
    return f"Entity_Title: {host}:{port}"


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
