"""
Fleet tracking helpers.
"""

# Standard Library
from dataclasses import dataclass

# Third Party
from eve_sde.models import ItemType, SolarSystem

# Django
from django.db import transaction
from django.utils import timezone

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# Alliance Auth AFAT
from afat.models import Fat, FatLink, FatTrackingEvent


@dataclass(frozen=True)
class FleetMemberObservation:
    """
    A single observed fleet member state.
    """

    character: EveCharacter
    solar_system: SolarSystem
    ship: ItemType


@dataclass(frozen=True)
class TrackingResult:
    """
    Result of recording one fleet member observation.
    """

    fat: Fat
    event: FatTrackingEvent | None
    created: bool


def _latest_event(fat: Fat) -> FatTrackingEvent | None:
    """
    Return the latest tracking event for a FAT.

    :param fat:
    :type fat:
    :return:
    :rtype:
    """

    return fat.tracking_events.order_by("-observed", "-pk").first()


def _is_active(fat: Fat) -> bool:
    """
    Return whether a FAT is currently considered active in fleet.

    :param fat:
    :type fat:
    :return:
    :rtype:
    """

    latest_event = _latest_event(fat=fat)

    return latest_event is None or latest_event.event != FatTrackingEvent.Event.LEAVE


def _change_event(
    latest_event: FatTrackingEvent | None, solar_system: SolarSystem, ship: ItemType
) -> str | None:
    """
    Determine the tracking event type for an observation.

    :param latest_event:
    :type latest_event:
    :param solar_system:
    :type solar_system:
    :param ship:
    :type ship:
    :return:
    :rtype:
    """

    if latest_event is None or latest_event.event == FatTrackingEvent.Event.LEAVE:
        return FatTrackingEvent.Event.JOIN

    system_changed = latest_event.solar_system_id != solar_system.id
    ship_changed = latest_event.ship_id != ship.id

    if system_changed and ship_changed:
        return FatTrackingEvent.Event.SYSTEM_AND_SHIP_CHANGE

    if system_changed:
        return FatTrackingEvent.Event.SYSTEM_CHANGE

    if ship_changed:
        return FatTrackingEvent.Event.SHIP_CHANGE

    return None


def record_fat_observation(  # pylint: disable=too-many-arguments
    fatlink: FatLink,
    character: EveCharacter,
    solar_system: SolarSystem,
    ship: ItemType,
    source: str = FatTrackingEvent.Source.ESI,
    observed=None,
) -> TrackingResult:
    """
    Record the observed state for one pilot in a fleet.

    :param fatlink:
    :type fatlink:
    :param character:
    :type character:
    :param solar_system:
    :type solar_system:
    :param ship:
    :type ship:
    :param source:
    :type source:
    :param observed:
    :type observed:
    :return:
    :rtype:
    """

    observed = observed or timezone.now()

    with transaction.atomic():
        fat, created = Fat.objects.get_or_create(
            fatlink=fatlink,
            character=character,
            defaults={
                "solar_system": solar_system,
                "system": solar_system.name,
                "ship": ship,
                "shiptype": ship.name,
                "corporation_eve_id": character.corporation_id,
                "alliance_eve_id": character.alliance_id,
            },
        )

        latest_event = _latest_event(fat=fat)
        event_type = _change_event(
            latest_event=latest_event, solar_system=solar_system, ship=ship
        )

        fields_to_update = []

        for field_name, value in {
            "solar_system": solar_system,
            "system": solar_system.name,
            "ship": ship,
            "shiptype": ship.name,
            "corporation_eve_id": character.corporation_id,
            "alliance_eve_id": character.alliance_id,
        }.items():
            if getattr(fat, field_name) != value:
                setattr(fat, field_name, value)
                fields_to_update.append(field_name)

        if fields_to_update:
            fat.save(update_fields=fields_to_update)

        event = None
        if event_type:
            event = FatTrackingEvent.objects.create(
                fat=fat,
                observed=observed,
                event=event_type,
                solar_system=solar_system,
                ship=ship,
                source=source,
            )

    return TrackingResult(fat=fat, event=event, created=created)


def record_fat_leave(
    fat: Fat, source: str = FatTrackingEvent.Source.ESI, observed=None
) -> FatTrackingEvent | None:
    """
    Record a pilot leaving the fleet.

    :param fat:
    :type fat:
    :param source:
    :type source:
    :param observed:
    :type observed:
    :return:
    :rtype:
    """

    observed = observed or timezone.now()

    with transaction.atomic():
        latest_event = _latest_event(fat=fat)

        if latest_event is not None and latest_event.event == FatTrackingEvent.Event.LEAVE:
            return None

        return FatTrackingEvent.objects.create(
            fat=fat,
            observed=observed,
            event=FatTrackingEvent.Event.LEAVE,
            solar_system=getattr(latest_event, "solar_system", None)
            or fat.solar_system,
            ship=getattr(latest_event, "ship", None) or fat.ship,
            source=source,
        )


def record_fleet_observation(
    fatlink: FatLink,
    observations: list[FleetMemberObservation],
    source: str = FatTrackingEvent.Source.ESI,
    observed=None,
) -> list[FatTrackingEvent]:
    """
    Record a complete fleet observation, including detected leaves.

    :param fatlink:
    :type fatlink:
    :param observations:
    :type observations:
    :param source:
    :type source:
    :param observed:
    :type observed:
    :return:
    :rtype:
    """

    observed = observed or timezone.now()
    current_character_ids = {
        observation.character.character_id for observation in observations
    }
    events = []

    existing_fats = (
        Fat.objects.select_related_default()
        .filter(fatlink=fatlink)
        .prefetch_related("tracking_events")
    )

    for fat in existing_fats:
        if fat.character.character_id not in current_character_ids and _is_active(
            fat=fat
        ):
            event = record_fat_leave(fat=fat, source=source, observed=observed)

            if event:
                events.append(event)

    for observation in observations:
        result = record_fat_observation(
            fatlink=fatlink,
            character=observation.character,
            solar_system=observation.solar_system,
            ship=observation.ship,
            source=source,
            observed=observed,
        )

        if result.event:
            events.append(result.event)

    return events
