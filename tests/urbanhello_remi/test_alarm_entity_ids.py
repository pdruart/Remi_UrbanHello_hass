"""Tests for alarm entity_id and unique_id derivation."""

from unittest.mock import MagicMock

import pytest

from custom_components.urbanhello_remi.const import (
    build_alarm_suggested_object_id,
    build_alarm_unique_id,
)
from custom_components.urbanhello_remi.switch import RemiAlarmSwitch
from custom_components.urbanhello_remi.time import RemiAlarmTime

DEVICE_ID = "device-object-id"
DEVICE_NAME = "Rémi Chambre"
ALARM_ID = "alarm-object-id"
ALARM_NAME = "Réveil École"


@pytest.fixture
def coordinator() -> MagicMock:
    """Return a coordinator stub exposing one accented alarm."""
    coordinator = MagicMock()
    coordinator.data = {
        "alarms": {
            ALARM_ID: {"name": ALARM_NAME, "time": "07:30", "enabled": True},
        }
    }
    return coordinator


@pytest.fixture
def api() -> MagicMock:
    """Return an API stub."""
    api = MagicMock()
    api.faces = {}
    return api


def _build_entity(entity_class, coordinator: MagicMock, api: MagicMock):
    return entity_class(
        coordinator=coordinator,
        api=api,
        device_id=DEVICE_ID,
        device_name=DEVICE_NAME,
        device_data={"objectId": DEVICE_ID, "name": DEVICE_NAME},
        alarm_object_id=ALARM_ID,
    )


@pytest.mark.parametrize(
    ("device_name", "alarm_name", "expected"),
    [
        ("Rémi Chambre", "Réveil École", "remi_chambre_reveil_ecole"),
        ("Rémi", "Wake up!", "remi_wake_up"),
        # A blank alarm name has no word characters left: HA's slugify
        # falls back to "unknown", mirroring build_alarm_key's unique_id.
        ("Rémi Salon", "  ", "remi_salon_unknown"),
        ("Rémi Salon", None, "remi_salon_alarm"),
    ],
)
def test_build_alarm_suggested_object_id(
    device_name: str, alarm_name: str | None, expected: str
) -> None:
    """Device and alarm names are slugified into a valid entity_id."""
    assert build_alarm_suggested_object_id(device_name, alarm_name) == expected


def test_switch_uses_slugified_entity_id(
    coordinator: MagicMock, api: MagicMock
) -> None:
    """The switch entity_id is derived from slugified names, not the objectId."""
    entity = _build_entity(RemiAlarmSwitch, coordinator, api)

    assert entity._attr_suggested_object_id == "remi_chambre_reveil_ecole"
    assert ALARM_ID not in entity._attr_suggested_object_id
    assert entity._attr_unique_id == f"{DEVICE_ID}_alarm_reveil_ecole_enabled"


def test_time_uses_slugified_entity_id(coordinator: MagicMock, api: MagicMock) -> None:
    """The time entity_id matches the switch entity_id for the same alarm."""
    entity = _build_entity(RemiAlarmTime, coordinator, api)

    assert entity._attr_suggested_object_id == "remi_chambre_reveil_ecole"
    assert ALARM_ID not in entity._attr_suggested_object_id
    assert entity._attr_unique_id == f"{DEVICE_ID}_alarm_reveil_ecole_time"


def test_duplicate_alarm_names_keep_unique_ids_distinct(
    api: MagicMock,
) -> None:
    """Duplicate names share an entity_id but get distinct unique_ids."""
    second_alarm_id = "second-alarm-object-id"
    alarms = {
        ALARM_ID: {"name": ALARM_NAME},
        second_alarm_id: {"name": ALARM_NAME},
    }
    coordinator = MagicMock()
    coordinator.data = {"alarms": alarms}

    first = _build_entity(RemiAlarmSwitch, coordinator, api)
    second = RemiAlarmSwitch(
        coordinator=coordinator,
        api=api,
        device_id=DEVICE_ID,
        device_name=DEVICE_NAME,
        device_data={"objectId": DEVICE_ID, "name": DEVICE_NAME},
        alarm_object_id=second_alarm_id,
    )

    assert first._attr_suggested_object_id == second._attr_suggested_object_id
    assert first._attr_unique_id != second._attr_unique_id
    assert (
        build_alarm_unique_id(DEVICE_ID, ALARM_ID, ALARM_NAME, alarms, "enabled")
        == first._attr_unique_id
    )
