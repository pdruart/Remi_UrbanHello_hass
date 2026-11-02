"""Switch platform for Rémi UrbanHello alarm clocks."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    build_alarm_suggested_object_id,
    build_alarm_unique_id,
    get_device_info,
)
from .coordinator import RemiCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    _entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rémi alarm clock switch entities."""
    api = hass.data[DOMAIN]["api"]
    devices = hass.data[DOMAIN]["devices"]
    coordinators = hass.data[DOMAIN]["coordinators"]

    entities = []
    for device in devices:
        device_id = device["objectId"]
        device_name = device.get("name", "Rémi")
        coordinator = coordinators.get(device_id)

        if not coordinator:
            _LOGGER.error(
                "No coordinator found for device %s (%s)", device_name, device_id
            )
            continue

        # Get alarms from coordinator data
        alarms_dict = coordinator.data.get("alarms", {}) if coordinator.data else {}
        _LOGGER.info(
            "Found %d alarms for device %s (%s)",
            len(alarms_dict),
            device_name,
            device_id,
        )

        # Create switch entities for each alarm
        for alarm_object_id, _alarm_data in alarms_dict.items():
            entities.append(
                RemiAlarmSwitch(
                    coordinator=coordinator,
                    api=api,
                    device_id=device_id,
                    device_name=device_name,
                    device_data=device,
                    alarm_object_id=alarm_object_id,
                )
            )

    async_add_entities(entities)


class RemiAlarmSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Rémi alarm clock enable/disable switch."""

    _attr_translation_key = "alarm"

    def __init__(
        self,
        coordinator: RemiCoordinator,
        api,
        device_id: str,
        device_name: str,
        device_data: dict,
        alarm_object_id: str,
    ) -> None:
        """Initialize the alarm clock switch entity."""
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._device_name = device_name
        self._device_data = device_data
        self._alarm_object_id = alarm_object_id

        # Set entity attributes with correct objectId-based unique_id
        # Entity naming must match remi-card expectations:
        # remi-card looks for time.{device_name}_* and expects matching switch.{device_name}_*
        alarms = coordinator.data.get("alarms", {}) if coordinator.data else {}
        alarm_data = alarms.get(alarm_object_id, {})
        alarm_name = alarm_data.get("name") or "Alarm"

        self._attr_name = f"{device_name} {alarm_name}"
        self._attr_unique_id = build_alarm_unique_id(
            device_id, alarm_object_id, alarm_name, alarms, "enabled"
        )
        self._attr_suggested_object_id = build_alarm_suggested_object_id(
            device_name, alarm_name
        )

    @property
    def alarm_data(self) -> dict:
        """Get current alarm data from coordinator."""
        if self.coordinator.data and "alarms" in self.coordinator.data:
            return self.coordinator.data["alarms"].get(self._alarm_object_id, {})
        return {}

    @property
    def is_on(self) -> bool:
        """Return true if alarm is enabled."""
        return bool(self.alarm_data.get("enabled", False))

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        alarm_name = self.alarm_data.get("name", "Alarm")
        _LOGGER.info(
            "Initialized alarm switch '%s' (objectId: %s) for device %s - State: %s",
            alarm_name,
            self._alarm_object_id,
            self._device_id,
            "enabled" if self.is_on else "disabled",
        )

    @property
    def device_info(self):
        """Return device information."""
        return get_device_info(
            DOMAIN, self._device_id, self._device_name, self._device_data
        )

    @property
    def icon(self) -> str:
        """Return the icon."""
        if self.is_on:
            return "mdi:alarm-check"
        return "mdi:alarm-off"

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn the alarm clock on."""
        try:
            # Update via API
            await self._api.enable_alarm(self._device_id, self._alarm_object_id)

            _LOGGER.info(
                "Enabled alarm '%s' (objectId: %s) for device %s",
                self.alarm_data.get("name", "Alarm"),
                self._alarm_object_id,
                self._device_id,
            )

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error(
                "Failed to enable alarm %s: %s",
                self._alarm_object_id,
                e,
            )
            raise

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the alarm clock off."""
        try:
            # Update via API
            await self._api.disable_alarm(self._device_id, self._alarm_object_id)

            _LOGGER.info(
                "Disabled alarm '%s' (objectId: %s) for device %s",
                self.alarm_data.get("name", "Alarm"),
                self._alarm_object_id,
                self._device_id,
            )

            # Request immediate refresh from coordinator
            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error(
                "Failed to disable alarm %s: %s",
                self._alarm_object_id,
                e,
            )
            raise

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes for the alarm."""
        alarm_data = self.alarm_data
        attributes = {}

        alarm_name = alarm_data.get("name")
        if alarm_name is not None:
            attributes["name"] = alarm_name

        if self._alarm_object_id is not None:
            attributes["alarm_id"] = self._alarm_object_id

        brightness = alarm_data.get("brightness")
        if brightness is not None:
            attributes["brightness"] = brightness

        volume = alarm_data.get("volume")
        if volume is not None:
            attributes["volume"] = volume

        # Resolve face name from face pointer
        face_obj = alarm_data.get("face")
        if isinstance(face_obj, dict) and face_obj.get("objectId"):
            face_id = face_obj.get("objectId")
            # Look up face name from API faces cache
            face_name = None
            for name, fid in self._api.faces.items():
                if fid == face_id:
                    face_name = name
                    break
            if face_name:
                attributes["face"] = face_name

        lightnight = alarm_data.get("lightnight")
        if lightnight is not None:
            attributes["lightnight"] = lightnight

        days = alarm_data.get("days")
        if days is not None:
            # Convert day indices to day names
            day_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            selected_days = [day_names[i] for i in days if i < len(day_names)]
            attributes["days"] = selected_days
            attributes["days_indices"] = days

        recurrence = alarm_data.get("recurrence")
        if recurrence is not None:
            attributes["recurrence"] = recurrence

        return attributes
