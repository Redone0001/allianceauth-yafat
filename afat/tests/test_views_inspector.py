"""
Test inspector view.
"""

# Standard Library
from http import HTTPStatus

# Third Party
from eve_sde.models import ItemType, SolarSystem

# Django
from django.urls import reverse

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# Alliance Auth AFAT
from afat.models import Fat, FatLink, FatTrackingEvent
from afat.tests import BaseTestCase
from afat.tests.fixtures.utils import create_user_from_evecharacter


class TestInspectorView(BaseTestCase):
    """
    Test the tracking event inspector view.
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
        cls.character_1003 = EveCharacter.objects.get(character_id=1003)

        cls.user_with_basic_access, _ = create_user_from_evecharacter(
            character_id=cls.character_1001.character_id,
            permissions=["afat.basic_access"],
        )
        cls.user_with_inspector, _ = create_user_from_evecharacter(
            character_id=cls.character_1002.character_id,
            permissions=["afat.basic_access", "afat.inspector"],
        )

        cls.system_one = SolarSystem.objects.get_or_create(
            id=920001,
            defaults={
                "name": "Inspector System One",
                "name_en": "Inspector System One",
            },
        )[0]
        cls.system_two = SolarSystem.objects.get_or_create(
            id=920002,
            defaults={
                "name": "Inspector System Two",
                "name_en": "Inspector System Two",
            },
        )[0]
        cls.ship_one = ItemType.objects.get_or_create(
            id=930001,
            defaults={
                "name": "Inspector Ship One",
                "name_en": "Inspector Ship One",
                "published": 1,
            },
        )[0]
        cls.ship_two = ItemType.objects.get_or_create(
            id=930002,
            defaults={
                "name": "Inspector Ship Two",
                "name_en": "Inspector Ship Two",
                "published": 1,
            },
        )[0]

    def setUp(self):
        """
        Setup each test.

        :return:
        :rtype:
        """

        self.fatlink = FatLink.objects.create(
            fleet="Inspector Fleet",
            hash=f"inspector-{self._testMethodName}",
            creator=self.user_with_inspector,
            character=self.character_1002,
        )
        self.fat_one = Fat.objects.create(
            fatlink=self.fatlink,
            character=self.character_1001,
            solar_system=self.system_one,
            ship=self.ship_one,
        )
        self.fat_two = Fat.objects.create(
            fatlink=self.fatlink,
            character=self.character_1003,
            solar_system=self.system_two,
            ship=self.ship_two,
        )
        FatTrackingEvent.objects.create(
            fat=self.fat_one,
            event=FatTrackingEvent.Event.JOIN,
            solar_system=self.system_one,
            ship=self.ship_one,
            source=FatTrackingEvent.Source.ESI,
        )
        FatTrackingEvent.objects.create(
            fat=self.fat_two,
            event=FatTrackingEvent.Event.SHIP_CHANGE,
            solar_system=self.system_two,
            ship=self.ship_two,
            source=FatTrackingEvent.Source.SNAPSHOT,
        )

    def test_denies_user_without_inspector_permission(self):
        """
        Test users without the inspector permission cannot open the inspector.

        :return:
        :rtype:
        """

        self.client.force_login(user=self.user_with_basic_access)

        response = self.client.get(path=reverse(viewname="afat:inspector_overview"))

        self.assertEqual(first=response.status_code, second=HTTPStatus.FOUND)

    def test_shows_tracking_events_for_inspector(self):
        """
        Test users with the inspector permission can open the inspector.

        :return:
        :rtype:
        """

        self.client.force_login(user=self.user_with_inspector)

        response = self.client.get(path=reverse(viewname="afat:inspector_overview"))

        self.assertEqual(first=response.status_code, second=HTTPStatus.OK)
        self.assertContains(response=response, text="Inspector System One")
        self.assertContains(response=response, text="Inspector Ship Two")
        self.assertContains(
            response=response,
            text=(
                "https://zkillboard.com/character/"
                f"{self.character_1001.character_id}/"
            ),
        )

    def test_filters_tracking_events(self):
        """
        Test inspector filters narrow the tracking event list.

        :return:
        :rtype:
        """

        self.client.force_login(user=self.user_with_inspector)

        response = self.client.get(
            path=reverse(viewname="afat:inspector_overview"),
            data={
                "event": [
                    FatTrackingEvent.Event.JOIN,
                    FatTrackingEvent.Event.SHIP_CHANGE,
                ],
            },
        )

        self.assertEqual(first=response.status_code, second=HTTPStatus.OK)
        self.assertContains(response=response, text="Inspector System One")
        self.assertContains(response=response, text="Inspector System Two")

    def test_filters_tracking_events_by_ship_and_location(self):
        """
        Test inspector text filters narrow the tracking event list.

        :return:
        :rtype:
        """

        self.client.force_login(user=self.user_with_inspector)

        response = self.client.get(
            path=reverse(viewname="afat:inspector_overview"),
            data={
                "location": "System Two",
                "ship": "Ship Two",
            },
        )

        self.assertEqual(first=response.status_code, second=HTTPStatus.OK)
        self.assertContains(response=response, text="Inspector System Two")
        self.assertNotContains(response=response, text="Inspector System One")
