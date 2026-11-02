"""Tests for the Rémi UrbanHello config flow."""

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.urbanhello_remi.const import DOMAIN


async def test_flow_user(hass: HomeAssistant) -> None:
    """Test the user step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.urbanhello_remi.api.RemiAPI.login",
        return_value={"sessionToken": "test_token"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"username": "test-user", "password": "test-password"},
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Rémi (test-user)"
    assert result["data"] == {"username": "test-user", "password": "test-password"}
