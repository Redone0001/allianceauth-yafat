"""
Test fleet tracking helpers.
"""

# Third Party
from eve_sde.models import ItemType, SolarSystem

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# Alliance Auth AFAT
from afat.helper.tracking import (
    FleetMemberObservation,
    record_fat_observation,
    record_fleet_observation,
)
from afat.models import Fat, FatLink, FatTrackingEvent
from afat.tests import BaseTestCase
from afat.tests.fixtures.utils import create_user_from_evecharacter


class TestTrackingHelpers(BaseTestCase):
    """
    Tests for fleet tracking helpers.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup the test class.

        :return:
        :rtype:
        """

        super().setUpClass()

        cls.character_1001 = EveCharacter.objects.get(character_id=1001)
        cls.character_1002 = EveCharacter.objects.get(character_id=1002)
        cls.user, _ = create_user_from_evecharacter(
            character_id=cls.character_1001.character_id,
            permissions=["afat.basic_access", "afat.manage_afat"],
        )
        cls.system_one = SolarSystem.objects.get_or_create(
            id=900001, defaults={"name": "System One", "name_en": "System One"}
        )[0]
        cls.system_two = SolarSystem.objects.get_or_create(
            id=900002, defaults={"name": "System Two", "name_en": "System Two"}
        )[0]
        cls.ship_one = ItemType.objects.get_or_create(
            id=910001,
            defaults={"name": "Ship One", "name_en": "Ship One", "published": 1},
        )[0]
        cls.ship_two = ItemType.objects.get_or_create(
            id=910002,
            defaults={"name": "Ship Two", "name_en": "Ship Two", "published": 1},
        )[0]

    def setUp(self):
        """
        Setup each test.

        :return:
        :rtype:
        """

        self.fatlink = FatLink.objects.create(
            fleet="Tracking Fleet",
            hash=f"tracking-{self._testMethodName}",
            creator=self.user,
            character=self.character_1001,
            is_esilink=True,
        )

    def test_records_join_for_first_observation(self):
        """
        Test first observation creates a FAT and join event.

        :return:
        :rtype:
        """

        result = record_fat_observation(
            fatlink=self.fatlink,
            character=self.character_1002,
            solar_system=self.system_one,
            ship=self.ship_one,
            source=FatTrackingEvent.Source.ESI,
        )

        self.assertTrue(result.created)
        self.assertEqual(result.event.event, FatTrackingEvent.Event.JOIN)
        self.assertTrue(
            Fat.objects.filter(
                fatlink=self.fatlink, character=self.character_1002
            ).exists()
        )

    def test_does_not_record_duplicate_when_observation_is_unchanged(self):
        """
        Test unchanged observations do not create duplicate tracking events.

        :return:
        :rtype:
        """

        record_fat_observation(
            fatlink=self.fatlink,
            character=self.character_1002,
            solar_system=self.system_one,
            ship=self.ship_one,
            source=FatTrackingEvent.Source.ESI,
        )
        result = record_fat_observation(
            fatlink=self.fatlink,
            character=self.character_1002,
            solar_system=self.system_one,
            ship=self.ship_one,
            source=FatTrackingEvent.Source.ESI,
        )

        self.assertFalse(result.created)
        self.assertIsNone(result.event)
        self.assertEqual(
            FatTrackingEvent.objects.filter(fat=result.fat).count(), 1
        )

    def test_records_system_and_ship_changes(self):
        """
        Test system and ship changes are stored as tracking events.

        :return:
        :rtype:
        """

        result = record_fat_observation(
            fatlink=self.fatlink,
            character=self.character_1002,
            solar_system=self.system_one,
            ship=self.ship_one,
            source=FatTrackingEvent.Source.ESI,
        )
        result = record_fat_observation(
            fatlink=self.fatlink,
            character=self.character_1002,
            solar_system=self.system_two,
            ship=self.ship_two,
            source=FatTrackingEvent.Source.ESI,
        )

        result.fat.refresh_from_db()
        self.assertEqual(
            result.event.event, FatTrackingEvent.Event.SYSTEM_AND_SHIP_CHANGE
        )
        self.assertEqual(result.fat.solar_system, self.system_two)
        self.assertEqual(result.fat.ship, self.ship_two)

    def test_records_leave_and_rejoin_from_fleet_observations(self):
        """
        Test complete fleet observations track leave and rejoin cycles.

        :return:
        :rtype:
        """

        observation = FleetMemberObservation(
            character=self.character_1002,
            solar_system=self.system_one,
            ship=self.ship_one,
        )
        record_fleet_observation(
            fatlink=self.fatlink,
            observations=[observation],
            source=FatTrackingEvent.Source.SNAPSHOT,
        )
        leave_events = record_fleet_observation(
            fatlink=self.fatlink,
            observations=[],
            source=FatTrackingEvent.Source.SNAPSHOT,
        )
        rejoin_events = record_fleet_observation(
            fatlink=self.fatlink,
            observations=[observation],
            source=FatTrackingEvent.Source.SNAPSHOT,
        )

        fat = Fat.objects.get(fatlink=self.fatlink, character=self.character_1002)
        events = list(fat.tracking_events.values_list("event", flat=True))

        self.assertEqual(leave_events[0].event, FatTrackingEvent.Event.LEAVE)
        self.assertEqual(rejoin_events[0].event, FatTrackingEvent.Event.JOIN)
        self.assertEqual(
            events,
            [
                FatTrackingEvent.Event.JOIN,
                FatTrackingEvent.Event.LEAVE,
                FatTrackingEvent.Event.JOIN,
            ],
        )
