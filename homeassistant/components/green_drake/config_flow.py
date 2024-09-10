"""Config flow for Horizon integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_TIMEOUT, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.httpx_client

from .api_client import ApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, msg="Device URL", description="Device URL"): str,
        vol.Required(
            CONF_TIMEOUT, default=10, msg="MsgTimeout", description="Timeout"
        ): cv.positive_float,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # validate the data can be used to set up a connection.
    ApiClient(
        data[CONF_URL],
        data[CONF_TIMEOUT],
        httpx_client=homeassistant.helpers.httpx_client.get_async_client(hass),
    )

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

    # async def async_setup_entry(
    #     self, saved_input: Mapping[str, Any]
    # ) -> ConfigFlowResult:
    #     """Load the saved configuration."""
    #     return self.async_create_entry(
    #         title=_get_entity_tile(saved_input[CONF_HOST], saved_input[CONF_PORT]),
    #         data=saved_input,
    #     )

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
                api_client = ApiClient(
                    validated_input[CONF_URL],
                    20,
                    httpx_client=homeassistant.helpers.httpx_client.get_async_client(
                        self.hass
                    ),
                )
                unique_id = (await api_client.get_system_info()).unique_id
                await self.async_set_unique_id(unique_id)
                return self.async_create_entry(
                    title=validated_input[CONF_URL],
                    data=validated_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
