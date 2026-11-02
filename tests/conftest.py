"""Shared pytest fixtures for the Rémi UrbanHello integration tests."""

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # noqa: ARG001
    """Enable custom integrations defined in custom_components/ for every test."""
    return
