"""
Test cases for the task in the afat module.
"""

# Standard Library
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest.mock import ANY, MagicMock, PropertyMock, patch

# Third Party
import kombu

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter
from esi.exceptions import HTTPClientError

# Alliance Auth AFAT
from afat.models import EsiFleetAutoTracking, FatLink
from afat.tasks import (
    _auto_detect_esi_fatlink,
    _check_for_esi_fleet,
    _close_esi_fleet,
    _esi_fatlinks_error_handling,
    _process_esi_fatlink,
    auto_detect_esi_fatlinks,
    logrotate,
    process_character,
    process_fats,
    update_esi_fatlinks,
)
from afat.tests import BaseTestCase
from afat.tests.fixtures.utils import create_user_from_evecharacter


class TestLogrotateTask(BaseTestCase):
    """
    Test cases for the logrotate task.
    """

    @patch("afat.tasks.Setting.get_setting")
    @patch("afat.tasks.Log.objects.filter")
    def test_logrotate_removes_old_logs(self, mock_filter, mock_get_setting):
        """
        Test that the logrotate task removes logs older than the specified duration.

        :param mock_filter:
        :type mock_filter:
        :param mock_get_setting:
        :type mock_get_setting:
        :return:
        :rtype:
        """

        mock_get_setting.return_value = 30
        mock_filter.return_value.delete.return_value = None

        logrotate()

        mock_filter.assert_called_once_with(log_time__lte=ANY)
        mock_filter.return_value.delete.assert_called_once()

    @patch("afat.tasks.Setting.get_setting")
    @patch("afat.tasks.Log.objects.filter")
    def test_logrotate_handles_no_old_logs(self, mock_filter, mock_get_setting):
        """
        Test that the logrotate task handles the case where there are no old logs.

        :param mock_filter:
        :type mock_filter:
        :param mock_get_setting:
        :type mock_get_setting:
        :return:
        :rtype:
        """

        mock_get_setting.return_value = 30
        mock_filter.return_value.delete.return_value = None

        logrotate()

        mock_filter.assert_called_once_with(log_time__lte=ANY)
        mock_filter.return_value.delete.assert_called_once()


class TestUpdateEsiFatlinks(BaseTestCase):
    """
    Test cases for the update_esi_fatlinks task.
    """

    @patch("afat.tasks._process_esi_fatlink")
    @patch("afat.tasks.FatLink.objects.select_related_default")
    def test_updates_esi_fatlinks(self, mock_select_related, mock_process_fatlink):
        """
        Test that the update_esi_fatlinks task updates ESI FAT links when ESI is operational.

        :param mock_select_related:
        :type mock_select_related:
        :param mock_process_fatlink:
        :type mock_process_fatlink:
        :return:
        :rtype:
        """

        mock_fatlink1 = MagicMock()
        mock_fatlink2 = MagicMock()

        mock_qs = MagicMock()
        mock_qs.exists.return_value = True
        mock_qs.count.return_value = 2
        mock_qs.__iter__.return_value = iter([mock_fatlink1, mock_fatlink2])

        mock_select_related.return_value.filter.return_value.distinct.return_value = (
            mock_qs
        )

        update_esi_fatlinks()

        mock_process_fatlink.assert_any_call(fatlink=mock_fatlink1)
        mock_process_fatlink.assert_any_call(fatlink=mock_fatlink2)

    @patch("afat.tasks.FatLink.objects.select_related_default")
    @patch("afat.tasks.logger")
    def test_logs_message_when_no_esi_fatlinks_to_process(
        self, mock_logger, mock_select_related
    ):
        mock_qs = MagicMock()
        mock_qs.exists.return_value = False
        mock_select_related.return_value.filter.return_value.distinct.return_value = (
            mock_qs
        )

        update_esi_fatlinks()

        mock_logger.debug.assert_called_once_with(msg="No ESI FAT links to process")


class TestProcessEsiFatlink(BaseTestCase):
    """
    Test cases for the _process_esi_fatlink function.
    """

    @patch("afat.utils.esi.__class__.client", new_callable=PropertyMock)
    @patch("afat.tasks._check_for_esi_fleet")
    @patch("afat.tasks._close_esi_fleet")
    @patch("afat.tasks.process_fats.delay")
    def test_processes_fatlink_with_valid_fleet(
        self, mock_process_fats, mock_close_fleet, mock_check_fleet, mock_client_prop
    ):
        """
        Test that the _process_esi_fatlink function processes a FAT link with a valid fleet.

        :param mock_process_fats:
        :type mock_process_fats:
        :param mock_close_fleet:
        :type mock_close_fleet:
        :param mock_check_fleet:
        :type mock_check_fleet:
        :param mock_client_prop:
        :type mock_client_prop:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_fatlink.hash = "valid_hash"
        mock_fatlink.creator.profile.main_character = True

        mock_esi_fleet = {"fleet": MagicMock(fleet_id=12345), "token": MagicMock()}
        mock_check_fleet.return_value = mock_esi_fleet

        mock_client = MagicMock()
        mock_client.Fleets.GetFleetsFleetIdMembers.return_value.result.return_value = [
            MagicMock(dict=lambda: {"character_id": 1})
        ]
        mock_client_prop.return_value = mock_client

        _process_esi_fatlink(mock_fatlink)

        mock_process_fats.assert_called_once()
        mock_close_fleet.assert_not_called()

    @patch("afat.utils.esi.__class__.client", new_callable=PropertyMock)
    @patch("afat.tasks._check_for_esi_fleet")
    @patch("afat.tasks._close_esi_fleet")
    def test_closes_fatlink_when_no_creator(
        self, mock_close_fleet, mock_check_fleet, mock_client_prop
    ):
        """
        Test that the _process_esi_fatlink function closes a FAT link when there is no creator.

        :param mock_close_fleet:
        :type mock_close_fleet:
        :param mock_check_fleet:
        :type mock_check_fleet:
        :param mock_client_prop:
        :type mock_client_prop:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_fatlink.hash = "no_creator_hash"
        mock_fatlink.creator.profile.main_character = None

        _process_esi_fatlink(mock_fatlink)

        mock_close_fleet.assert_called_once_with(
            fatlink=mock_fatlink, reason="No FAT link creator available."
        )
        mock_check_fleet.assert_not_called()

    @patch("afat.utils.esi.__class__.client", new_callable=PropertyMock)
    @patch("afat.tasks._check_for_esi_fleet")
    @patch("afat.tasks._esi_fatlinks_error_handling")
    def test_handles_error_when_not_fleetboss(
        self, mock_error_handling, mock_check_fleet, mock_client_prop
    ):
        mock_fatlink = MagicMock()
        mock_fatlink.hash = "not_fleetboss_hash"
        mock_fatlink.creator.profile.main_character = True

        mock_esi_fleet = {"fleet": MagicMock(fleet_id=12345), "token": MagicMock()}
        mock_check_fleet.return_value = mock_esi_fleet

        mock_client = MagicMock()
        mock_client.Fleets.GetFleetsFleetIdMembers.return_value.result.side_effect = (
            Exception
        )
        mock_client_prop.return_value = mock_client

        _process_esi_fatlink(mock_fatlink)

        mock_error_handling.assert_called_once_with(
            error_key=FatLink.EsiError.NOT_FLEETBOSS, fatlink=mock_fatlink
        )

    @patch("afat.utils.esi.__class__.client", new_callable=PropertyMock)
    @patch("afat.tasks._check_for_esi_fleet")
    @patch("afat.tasks._close_esi_fleet")
    def test_skips_processing_when_no_esi_fleet(
        self, mock_close_fleet, mock_check_fleet, mock_client_prop
    ):
        """
        Test that the _process_esi_fatlink function skips processing when there is no ESI fleet.

        :param mock_close_fleet:
        :type mock_close_fleet:
        :param mock_check_fleet:
        :type mock_check_fleet:
        :param mock_client_prop:
        :type mock_client_prop:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_fatlink.hash = "no_fleet_hash"
        mock_fatlink.creator.profile.main_character = True

        mock_check_fleet.return_value = None

        _process_esi_fatlink(mock_fatlink)

        mock_close_fleet.assert_not_called()


class TestAutoDetectEsiFatlink(BaseTestCase):
    """
    Test cases for automatic ESI FAT link detection.
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
            permissions=["afat.basic_access", "afat.add_fatlink"],
        )

    @patch("afat.tasks._auto_detect_esi_fatlink")
    def test_checks_enabled_auto_tracking_settings(self, mock_auto_detect):
        """
        Test the auto-detection task checks enabled opt-in settings.

        :param mock_auto_detect:
        :type mock_auto_detect:
        :return:
        :rtype:
        """

        enabled_tracking = EsiFleetAutoTracking.objects.create(
            user=self.user, character=self.character_1001
        )
        EsiFleetAutoTracking.objects.create(
            user=self.user,
            character=self.character_1002,
            is_enabled=False,
        )

        auto_detect_esi_fatlinks()

        mock_auto_detect.assert_called_once_with(auto_tracking=enabled_tracking)

    @patch("afat.tasks.process_fats.delay")
    @patch("afat.tasks.get_hash_on_save", return_value="auto_hash")
    @patch("afat.tasks.ESIHandler.result")
    @patch("esi.models.Token.get_token")
    @patch("afat.tasks.esi")
    def test_creates_fatlink_for_auto_detected_boss_fleet(
        self,
        mock_esi,
        mock_get_token,
        mock_esi_result,
        mock_get_hash,
        mock_process_fats,
    ):
        """
        Test auto detection creates an ESI FAT link for a fleet boss.

        :param mock_esi:
        :type mock_esi:
        :param mock_get_token:
        :type mock_get_token:
        :param mock_esi_result:
        :type mock_esi_result:
        :param mock_get_hash:
        :type mock_get_hash:
        :param mock_process_fats:
        :type mock_process_fats:
        :return:
        :rtype:
        """

        auto_tracking = EsiFleetAutoTracking.objects.create(
            user=self.user, character=self.character_1001
        )
        mock_token = MagicMock()
        mock_get_token.return_value = mock_token
        mock_esi_result.side_effect = [
            MagicMock(fleet_id=987654321),
            [
                MagicMock(
                    dict=lambda: {
                        "character_id": self.character_1001.character_id,
                        "solar_system_id": 30000142,
                        "ship_type_id": 587,
                    }
                )
            ],
        ]

        fatlink = _auto_detect_esi_fatlink(auto_tracking=auto_tracking)

        self.assertIsNotNone(fatlink)
        self.assertEqual(fatlink.hash, "auto_hash")
        self.assertTrue(fatlink.is_esilink)
        self.assertTrue(fatlink.is_registered_on_esi)
        self.assertEqual(fatlink.esi_fleet_id, 987654321)
        mock_get_token.assert_called_once_with(
            character_id=self.character_1001.character_id,
            scopes=["esi-fleets.read_fleet.v1"],
        )
        mock_esi.client.Fleets.GetCharactersCharacterIdFleet.assert_called_once()
        mock_esi.client.Fleets.GetFleetsFleetIdMembers.assert_called_once()
        mock_get_hash.assert_called_once()
        mock_process_fats.assert_called_once()

    @patch("afat.tasks.process_fats.delay")
    @patch("afat.tasks.ESIHandler.result")
    @patch("esi.models.Token.get_token")
    @patch("afat.tasks.esi")
    def test_does_not_recreate_existing_detected_fleet(
        self, mock_esi, mock_get_token, mock_esi_result, mock_process_fats
    ):
        """
        Test auto detection does not create duplicate FAT links.

        :param mock_esi:
        :type mock_esi:
        :param mock_get_token:
        :type mock_get_token:
        :param mock_esi_result:
        :type mock_esi_result:
        :param mock_process_fats:
        :type mock_process_fats:
        :return:
        :rtype:
        """

        auto_tracking = EsiFleetAutoTracking.objects.create(
            user=self.user, character=self.character_1001
        )
        FatLink.objects.create(
            fleet="Existing auto fleet",
            hash="existing_auto_hash",
            creator=self.user,
            character=self.character_1001,
            is_esilink=True,
            is_registered_on_esi=False,
            esi_fleet_id=987654321,
        )
        mock_get_token.return_value = MagicMock()
        mock_esi_result.return_value = MagicMock(fleet_id=987654321)

        fatlink = _auto_detect_esi_fatlink(auto_tracking=auto_tracking)

        self.assertIsNone(fatlink)
        mock_esi.client.Fleets.GetCharactersCharacterIdFleet.assert_called_once()
        mock_esi.client.Fleets.GetFleetsFleetIdMembers.assert_not_called()
        mock_process_fats.assert_not_called()


class TestEsiFatlinksErrorHandling(BaseTestCase):
    """
    Test cases for the _esi_fatlinks_error_handling function.
    """

    @patch("afat.tasks.timezone.now")
    @patch("afat.tasks._close_esi_fleet")
    def test_handles_error_within_grace_period(self, mock_close_fleet, mock_now):
        """
        Test that the _esi_fatlinks_error_handling function handles the case when an error occurs within the grace period.

        :param mock_close_fleet:
        :type mock_close_fleet:
        :param mock_now:
        :type mock_now:
        :return:
        :rtype:
        """

        fatlink = MagicMock(spec=FatLink)
        error_key = MagicMock()
        error_key.label = "Test Error"
        now = datetime(2023, 10, 1, 12, 0, 0)
        mock_now.return_value = now
        fatlink.last_esi_error = error_key
        fatlink.last_esi_error_time = now - timedelta(seconds=30)
        fatlink.esi_error_count = 3

        _esi_fatlinks_error_handling(error_key, fatlink)

        mock_close_fleet.assert_called_once_with(
            fatlink=fatlink, reason=error_key.label
        )
        fatlink.save.assert_not_called()

    @patch("afat.tasks.timezone.now")
    def test_increments_error_count(self, mock_now):
        """
        Test that the _esi_fatlinks_error_handling function increments the error count.

        :param mock_now:
        :type mock_now:
        :return:
        :rtype:
        """

        fatlink = MagicMock(spec=FatLink)
        error_key = MagicMock()
        error_key.label = "Test Error"
        now = datetime(2023, 10, 1, 12, 0, 0)
        mock_now.return_value = now
        fatlink.last_esi_error = error_key
        fatlink.last_esi_error_time = now - timedelta(seconds=30)
        fatlink.esi_error_count = 2

        _esi_fatlinks_error_handling(error_key, fatlink)

        self.assertEqual(fatlink.esi_error_count, 3)
        fatlink.save.assert_called_once()

    @patch("afat.tasks.timezone.now")
    def test_resets_error_count_after_grace_period(self, mock_now):
        """
        Test that the _esi_fatlinks_error_handling function resets the error count after the grace period.

        :param mock_now:
        :type mock_now:
        :return:
        :rtype:
        """

        fatlink = MagicMock(spec=FatLink)
        error_key = MagicMock()
        error_key.label = "Test Error"
        now = datetime(2023, 10, 1, 12, 0, 0)
        mock_now.return_value = now
        fatlink.last_esi_error = error_key
        fatlink.last_esi_error_time = now - timedelta(seconds=100)
        fatlink.esi_error_count = 2

        _esi_fatlinks_error_handling(error_key, fatlink)

        self.assertEqual(fatlink.esi_error_count, 1)
        fatlink.save.assert_called_once()

    @patch("afat.tasks.timezone.now")
    def test_handles_new_error(self, mock_now):
        """
        Test that the _esi_fatlinks_error_handling function handles a new error.

        :param mock_now:
        :type mock_now:
        :return:
        :rtype:
        """

        fatlink = MagicMock(spec=FatLink)
        error_key = MagicMock()
        error_key.label = "Test Error"
        now = datetime(2023, 10, 1, 12, 0, 0)
        mock_now.return_value = now
        fatlink.last_esi_error = None
        fatlink.last_esi_error_time = None
        fatlink.esi_error_count = 0

        _esi_fatlinks_error_handling(error_key, fatlink)

        self.assertEqual(fatlink.esi_error_count, 1)
        self.assertEqual(fatlink.last_esi_error, error_key)
        self.assertEqual(fatlink.last_esi_error_time, mock_now.return_value)
        fatlink.save.assert_called_once()


class TestCloseEsiFleet(BaseTestCase):
    """
    Test cases for the _close_esi_fleet function.
    """

    @patch("afat.tasks.logger.info")
    def test_closes_fleet_successfully(self, mock_logger_info):
        """
        Test that the _close_esi_fleet function closes the fleet successfully.

        :param mock_logger_info:
        :type mock_logger_info:
        :return:
        :rtype:
        """

        fatlink = MagicMock(spec=FatLink)
        fatlink.hash = "test_hash"

        _close_esi_fleet(fatlink=fatlink, reason="Test Reason")

        fatlink.is_registered_on_esi = False
        fatlink.save.assert_called_once()
        mock_logger_info.assert_called_once_with(
            msg='Closing ESI FAT link with hash "test_hash". Reason: Test Reason'
        )

    @patch("afat.tasks.logger.info")
    def test_handles_empty_reason(self, mock_logger_info):
        """
        Test that the _close_esi_fleet function handles an empty reason.

        :param mock_logger_info:
        :type mock_logger_info:
        :return:
        :rtype:
        """

        fatlink = MagicMock(spec=FatLink)
        fatlink.hash = "test_hash"

        _close_esi_fleet(fatlink=fatlink, reason="")

        fatlink.is_registered_on_esi = False
        fatlink.save.assert_called_once()
        mock_logger_info.assert_called_once_with(
            msg='Closing ESI FAT link with hash "test_hash". Reason: '
        )

    @patch("afat.tasks.logger.info")
    def test_handles_none_reason(self, mock_logger_info):
        """
        Test that the _close_esi_fleet function handles a None reason.

        :param mock_logger_info:
        :type mock_logger_info:
        :return:
        :rtype:
        """

        fatlink = MagicMock(spec=FatLink)
        fatlink.hash = "test_hash"

        _close_esi_fleet(fatlink=fatlink, reason=None)

        fatlink.is_registered_on_esi = False
        fatlink.save.assert_called_once()
        mock_logger_info.assert_called_once_with(
            msg='Closing ESI FAT link with hash "test_hash". Reason: None'
        )


class TestProcessFats(BaseTestCase):
    """
    Test cases for the process_fats function.
    """

    @patch("afat.tasks.process_character.si")
    @patch("afat.tasks.group")
    def test_processes_fat_link_data_from_esi(
        self, mock_group, mock_process_character_si
    ):
        """
        Test that the process_fats function processes FAT link data from ESI.

        :param mock_group:
        :type mock_group:
        :param mock_process_character_si:
        :type mock_process_character_si:
        :return:
        :rtype:
        """

        data_list = [
            {"character_id": 1, "solar_system_id": 100, "ship_type_id": 200},
            {"character_id": 2, "solar_system_id": 101, "ship_type_id": 201},
        ]
        fatlink_hash = "test_hash"
        mock_group.return_value.delay = MagicMock()

        process_fats(data_list, "esi", fatlink_hash)

        self.assertEqual(mock_process_character_si.call_count, 2)
        mock_group.assert_called_once()
        mock_group.return_value.delay.assert_called_once()

    @patch("afat.tasks.process_character.si")
    @patch("afat.tasks.group")
    def test_processes_fat_link_data_with_no_tasks(
        self, mock_group, mock_process_character_si
    ):
        """
        Test that the process_fats function handles the case when there are no tasks to process.

        :param mock_group:
        :type mock_group:
        :param mock_process_character_si:
        :type mock_process_character_si:
        :return:
        :rtype:
        """

        data_list = []
        fatlink_hash = "test_hash"

        process_fats(data_list, "esi", fatlink_hash)

        mock_process_character_si.assert_not_called()
        mock_group.assert_not_called()

    @patch("afat.tasks.process_character.si")
    @patch("afat.tasks.group")
    def test_handles_kombu_encode_error(self, mock_group, mock_process_character_si):
        data_list = [
            {"character_id": 1, "solar_system_id": 100, "ship_type_id": 200},
        ]
        fatlink_hash = "test_hash"
        mock_group.return_value.delay.side_effect = kombu.exceptions.EncodeError

        process_fats(data_list, "esi", fatlink_hash)

        self.assertEqual(mock_process_character_si.call_count, 1)
        mock_group.assert_called_once()
        mock_group.return_value.delay.assert_called_once()

    @patch("afat.tasks.logger")
    def test_logs_warning_for_unknown_data_source(self, mock_logger):
        """
        Test that the process_fats function logs a warning for an unknown data source.

        :param mock_logger:
        :type mock_logger:
        :return:
        :rtype:
        """

        process_fats(
            data_list=[], data_source="unknown_source", fatlink_hash="test_hash"
        )

        mock_logger.warning.assert_called_once_with(
            msg='Unknown data source "unknown_source" for FAT link hash "test_hash"'
        )

    @patch("afat.tasks.logger")
    def test_does_not_process_for_unknown_data_source(self, mock_logger):
        with patch("afat.tasks.group") as mock_group:
            process_fats(
                data_list=[], data_source="unknown_source", fatlink_hash="test_hash"
            )

            mock_group.assert_not_called()


class TestCheckForEsiFleet(BaseTestCase):
    """
    Test cases for the _check_for_esi_fleet function.
    """

    @patch("afat.utils.esi.__class__.client", new_callable=MagicMock)
    @patch("esi.models.Token.get_token")
    def test_returns_fleet_and_token_when_fleet_is_registered(
        self, mock_get_token, mock_client
    ):
        """
        Test that the _check_for_esi_fleet function returns the fleet and token when the fleet is registered.

        :param mock_get_token:
        :type mock_get_token:
        :param mock_client:
        :type mock_client:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_fatlink.character.character_id = 12345
        mock_fatlink.esi_fleet_id = 67890

        mock_token = MagicMock()
        mock_get_token.return_value = mock_token

        mock_fleet = MagicMock(fleet_id=67890)
        mock_client.Fleets.GetCharactersCharacterIdFleet.return_value.result.return_value = (
            mock_fleet
        )

        result = _check_for_esi_fleet(fatlink=mock_fatlink)

        self.assertDictEqual(result, {"fleet": mock_fleet, "token": mock_token})

    @patch("afat.utils.esi.__class__.client", new_callable=MagicMock)
    @patch("afat.tasks._esi_fatlinks_error_handling")
    @patch("esi.models.Token.get_token")
    def test_handles_http_client_error_with_status_404(
        self, mock_get_token, mock_error_handling, mock_client
    ):
        """
        Test that the _check_for_esi_fleet function handles a generic error.

        :param mock_get_token:
        :type mock_get_token:
        :param mock_error_handling:
        :type mock_error_handling:
        :param mock_client:
        :type mock_client:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_fatlink.character.character_id = 12345
        mock_fatlink.esi_fleet_id = 67890

        mock_get_token.return_value = MagicMock()
        mock_client.Fleets.GetCharactersCharacterIdFleet.return_value.result.side_effect = HTTPClientError(
            HTTPStatus.NOT_FOUND, headers={}, data={}
        )

        result = _check_for_esi_fleet(fatlink=mock_fatlink)

        self.assertIsNone(result)
        mock_error_handling.assert_called_once_with(
            error_key=FatLink.EsiError.NO_FLEET, fatlink=mock_fatlink
        )

    @patch("afat.utils.esi.__class__.client", new_callable=MagicMock)
    @patch("afat.tasks._esi_fatlinks_error_handling")
    @patch("esi.models.Token.get_token")
    def test_handles_http_client_error_with_other_status(
        self, mock_get_token, mock_error_handling, mock_client
    ):
        """
        Test that the _check_for_esi_fleet function handles a generic error.

        :param mock_get_token:
        :type mock_get_token:
        :param mock_error_handling:
        :type mock_error_handling:
        :param mock_client:
        :type mock_client:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_fatlink.character.character_id = 12345
        mock_fatlink.esi_fleet_id = 67890

        mock_get_token.return_value = MagicMock()
        mock_client.Fleets.GetCharactersCharacterIdFleet.return_value.result.side_effect = HTTPClientError(
            HTTPStatus.FORBIDDEN, headers={}, data={}
        )

        result = _check_for_esi_fleet(fatlink=mock_fatlink)

        self.assertIsNone(result)
        mock_error_handling.assert_called_once_with(
            error_key=FatLink.EsiError.NO_FLEET, fatlink=mock_fatlink
        )

    @patch("afat.utils.esi.__class__.client", new_callable=MagicMock)
    @patch("afat.tasks._esi_fatlinks_error_handling")
    @patch("esi.models.Token.get_token")
    def test_handles_generic_error(
        self, mock_get_token, mock_error_handling, mock_client
    ):
        """
        Test that the _check_for_esi_fleet function handles a generic error.

        :param mock_get_token:
        :type mock_get_token:
        :param mock_error_handling:
        :type mock_error_handling:
        :param mock_client:
        :type mock_client:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_fatlink.character.character_id = 12345
        mock_fatlink.esi_fleet_id = 67890

        mock_get_token.return_value = MagicMock()
        mock_client.Fleets.GetCharactersCharacterIdFleet.return_value.result.side_effect = (
            Exception
        )

        result = _check_for_esi_fleet(fatlink=mock_fatlink)

        self.assertIsNone(result)
        mock_error_handling.assert_called_once_with(
            error_key=FatLink.EsiError.NO_FLEET, fatlink=mock_fatlink
        )

    @patch("afat.utils.esi.__class__.client", new_callable=MagicMock)
    @patch("afat.tasks._esi_fatlinks_error_handling")
    @patch("esi.models.Token.get_token")
    def test_returns_none_when_fleet_id_does_not_match(
        self, mock_get_token, mock_error_handling, mock_client
    ):
        mock_fatlink = MagicMock()
        mock_fatlink.character.character_id = 12345
        mock_fatlink.esi_fleet_id = 67890

        mock_token = MagicMock()
        mock_get_token.return_value = mock_token

        mock_fleet = MagicMock(fleet_id=11111)
        mock_client.Fleets.GetCharactersCharacterIdFleet.return_value.result.return_value = (
            mock_fleet
        )

        result = _check_for_esi_fleet(fatlink=mock_fatlink)

        self.assertIsNone(result)
        mock_error_handling.assert_called_once_with(
            error_key=FatLink.EsiError.FC_WRONG_FLEET, fatlink=mock_fatlink
        )


class TestProcessCharacterTask(BaseTestCase):
    """
    Test cases for the process_character task.
    """

    @patch("afat.tasks.get_or_create_character")
    @patch("afat.models.FatLink.objects.get")
    @patch("afat.tasks.SolarSystem.objects.get")
    @patch("afat.tasks.ItemType.objects.get")
    @patch("afat.tasks.record_fat_observation")
    def test_processes_character_when_fatlink_exists(
        self,
        mock_record_observation,
        mock_get_or_create_ship,
        mock_get_or_create_system,
        mock_get_fatlink,
        mock_get_character,
    ):
        """
        Test that the process_character task processes a character when the FAT link exists.

        :param mock_record_observation:
        :type mock_record_observation:
        :param mock_get_or_create_ship:
        :type mock_get_or_create_ship:
        :param mock_get_or_create_system:
        :type mock_get_or_create_system:
        :param mock_get_fatlink:
        :type mock_get_fatlink:
        :param mock_get_character:
        :type mock_get_character:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_character = MagicMock(corporation_id=1, alliance_id=2)
        mock_system = MagicMock(name="SolarSystem")
        mock_ship = MagicMock(name="ShipType")
        mock_fat = MagicMock(pk=1)
        mock_get_fatlink.return_value = mock_fatlink
        mock_get_character.return_value = mock_character
        mock_get_or_create_system.return_value = mock_system
        mock_get_or_create_ship.return_value = mock_ship
        mock_record_observation.return_value = MagicMock(
            fat=mock_fat, created=True, event=None
        )

        process_character(1, 2, 3, "valid_hash")

        mock_get_fatlink.assert_called_once_with(hash="valid_hash")
        mock_get_character.assert_called_once_with(character_id=1)
        mock_get_or_create_system.assert_called_once_with(id=2)
        mock_get_or_create_ship.assert_called_once_with(id=3)
        mock_record_observation.assert_called_once()

    @patch("afat.tasks.get_or_create_character")
    @patch("afat.models.FatLink.objects.get")
    def test_skips_character_when_fatlink_does_not_exist(
        self, mock_get_fatlink, mock_get_character
    ):
        """
        Test that the process_character task skips a character when the FAT link does not exist.

        :param mock_get_fatlink:
        :type mock_get_fatlink:
        :param mock_get_character:
        :type mock_get_character:
        :return:
        :rtype:
        """

        mock_get_fatlink.side_effect = FatLink.DoesNotExist

        process_character(1, 2, 3, "invalid_hash")

        mock_get_fatlink.assert_called_once_with(hash="invalid_hash")
        mock_get_character.assert_not_called()

    @patch("afat.tasks.get_or_create_character")
    @patch("afat.models.FatLink.objects.get")
    @patch("afat.tasks.SolarSystem.objects.get")
    @patch("afat.tasks.ItemType.objects.get")
    @patch("afat.tasks.record_fat_observation")
    def test_does_not_create_duplicate_fat_entry(
        self,
        mock_record_observation,
        mock_get_or_create_ship,
        mock_get_or_create_system,
        mock_get_fatlink,
        mock_get_character,
    ):
        """
        Test that the process_character task does not create a duplicate FAT entry when one already exists.

        :param mock_record_observation:
        :type mock_record_observation:
        :param mock_get_or_create_ship:
        :type mock_get_or_create_ship:
        :param mock_get_or_create_system:
        :type mock_get_or_create_system:
        :param mock_get_fatlink:
        :type mock_get_fatlink:
        :param mock_get_character:
        :type mock_get_character:
        :return:
        :rtype:
        """

        mock_fatlink = MagicMock()
        mock_character = MagicMock(corporation_id=1, alliance_id=2)
        mock_system = MagicMock(name="SolarSystem")
        mock_ship = MagicMock(name="ShipType")
        mock_fat = MagicMock(pk=1)
        mock_get_fatlink.return_value = mock_fatlink
        mock_get_character.return_value = mock_character
        mock_get_or_create_system.return_value = mock_system
        mock_get_or_create_ship.return_value = mock_ship
        mock_record_observation.return_value = MagicMock(
            fat=mock_fat, created=False, event=None
        )

        process_character(1, 2, 3, "valid_hash")

        mock_get_fatlink.assert_called_once_with(hash="valid_hash")
        mock_get_character.assert_called_once_with(character_id=1)
        mock_get_or_create_system.assert_called_once_with(id=2)
        mock_get_or_create_ship.assert_called_once_with(id=3)
        mock_record_observation.assert_called_once()
