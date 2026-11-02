from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import slugify

DOMAIN = "urbanhello_remi"
MANUFACTURER = "UrbanHello"
MODEL = "Rémi Clock"
BRAND_NAME = "Rémi"

# Face name translation keys
FACE_MAP_API_TO_HA = {
    "sleepyFace": "sleepy_face",
    "awakeFace": "awake_face",
    "blankFace": "blank_face",
    "semiAwakeFace": "semi_awake_face",
    "smilyFace": "smily_face",
}

FACE_MAP_HA_TO_API = {v: k for k, v in FACE_MAP_API_TO_HA.items()}

# Music mode options: API integer value -> display label
MUSIC_MODE_OPTIONS: dict[int, str] = {
    0: "off",
    1: "music",
    2: "white_noise",
}

# Alarm clock constants
MAX_ALARMS_PER_DEVICE = 3
DEFAULT_ALARM_HOUR = 7
DEFAULT_ALARM_MINUTE = 0
DEFAULT_ALARM_VOLUME = 50
DEFAULT_ALARM_FACE = "awake_face"
ALARM_SNOOZE_DURATION = 9  # minutes

# Alarm clock service names
SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_SNOOZE_ALARM = "snooze_alarm"
SERVICE_STOP_ALARM = "stop_alarm"
SERVICE_CREATE_ALARM = "create_alarm"
SERVICE_DELETE_ALARM = "delete_alarm"
SERVICE_UPDATE_ALARM = "update_alarm"


def get_device_info(
    domain: str,
    device_id: str,
    device_name: str,
    device_data: dict[str, Any] | None = None,
) -> DeviceInfo:
    """Generate device info dictionary for Home Assistant."""
    device_data = device_data or {}
    raw_data = device_data.get("raw", {})
    return DeviceInfo(
        identifiers={(domain, device_id)},
        name=device_name,
        manufacturer=MANUFACTURER,
        model=MODEL,
        sw_version=raw_data.get("current_firmware_version"),
        hw_version=(
            str(raw_data["bt_hardware_version"])
            if raw_data.get("bt_hardware_version") is not None
            else None
        ),
        connections=(
            {("ip", raw_data.get("ipv4Address"))}
            if raw_data.get("ipv4Address")
            else set()
        ),
    )


def build_alarm_key(
    alarm_object_id: str,
    alarm_name: str | None,
    alarms: dict[str, Any],
) -> str:
    """Return a stable per-device key identifying an alarm.

    The Parse ``objectId`` of an ``Event`` is regenerated server-side whenever
    the alarm is edited from the UrbanHello app, so it must not be used as the
    basis of a unique_id: every edit would otherwise register a brand new set
    of entities and orphan the previous ones.

    The alarm name is stable across those rotations, so it is preferred. The
    objectId is only kept as a fallback when the name is empty or shared by
    several alarms of the same device, which keeps unique_ids collision-free.
    """
    slug = slugify(alarm_name or "")
    if not slug:
        return alarm_object_id

    same_name = [
        object_id
        for object_id, data in alarms.items()
        if slugify((data or {}).get("name") or "") == slug
    ]
    if len(same_name) > 1:
        return f"{slug}_{alarm_object_id}"
    return slug


def build_alarm_unique_id(
    device_id: str,
    alarm_object_id: str,
    alarm_name: str | None,
    alarms: dict[str, Any],
    suffix: str,
) -> str:
    """Return the unique_id of an alarm entity."""
    key = build_alarm_key(alarm_object_id, alarm_name, alarms)
    return f"{device_id}_alarm_{key}_{suffix}"


def build_alarm_suggested_object_id(
    device_name: str,
    alarm_name: str | None,
) -> str:
    """Return the suggested entity_id of an alarm entity.

    Device and alarm names can contain accents, spaces or punctuation that are
    not valid in an entity_id. Both parts go through the same ``slugify``
    normalization as the unique_id built by :func:`build_alarm_key`.
    """
    return f"{slugify(device_name)}_{slugify(alarm_name or 'alarm')}"
