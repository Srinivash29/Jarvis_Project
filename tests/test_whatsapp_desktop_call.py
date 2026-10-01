"""
Tests for whatsapp_desktop_call.py plugin.

These tests verify the pure logic (state machine, intent routing, contact
extraction, error handling) without requiring a live WhatsApp Desktop instance.
Tests that require real WhatsApp UI interaction are marked as such and should
be run manually on Windows with WhatsApp Desktop open.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Load the plugin
import importlib.util
plugin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'whatsapp_desktop_call.py'))
spec = importlib.util.spec_from_file_location("whatsapp_desktop_call", plugin_path)
wa_plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wa_plugin)


class TestContactExtraction(unittest.TestCase):
    """Test contact name extraction from natural language."""

    def test_call_name_on_whatsapp(self):
        self.assertEqual(wa_plugin.extract_contact_name("call Rahul on WhatsApp"), "Rahul")

    def test_whatsapp_call_name(self):
        self.assertEqual(wa_plugin.extract_contact_name("whatsapp call Rahul"), "Rahul")

    def test_video_call(self):
        self.assertEqual(wa_plugin.extract_contact_name("whatsapp video call Rahul"), "Rahul")

    def test_call_with_please(self):
        self.assertEqual(wa_plugin.extract_contact_name("call Rahul on whatsapp please"), "Rahul")

    def test_tanglish(self):
        self.assertEqual(wa_plugin.extract_contact_name("whatsapp la amma ku call"), "amma")

    def test_empty_input(self):
        self.assertIsNone(wa_plugin.extract_contact_name(""))

    def test_none_input(self):
        self.assertIsNone(wa_plugin.extract_contact_name(None))

    def test_tamil_name(self):
        name = wa_plugin.extract_contact_name("call Srinivasan on WhatsApp")
        self.assertEqual(name, "Srinivasan")

    def test_name_with_spaces(self):
        name = wa_plugin.extract_contact_name("call My World on WhatsApp")
        self.assertEqual(name, "My World")


class TestIntentRouting(unittest.TestCase):
    """Test that intents are correctly identified."""

    def test_whatsapp_not_running(self):
        with patch.object(wa_plugin.WhatsAppDesktopController, 'is_whatsapp_running', return_value=False):
            res = wa_plugin.run({"intent": "call", "contact_name": "Arun"})
            self.assertIn("not running", res.lower())

    def test_ambiguous_command(self):
        res = wa_plugin.run({"intent": "random garbage intent"})
        self.assertIn("Ambiguous", res)

    def test_end_call_intent(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.end_call.return_value = True

            res = wa_plugin.run({"intent": "end_call"})
            self.assertIn("Successfully executed end_call", res)
            mock_instance.end_call.assert_called_once()

    def test_answer_call_intent(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.answer_call.return_value = True

            res = wa_plugin.run({"intent": "answer_call"})
            self.assertIn("Successfully executed answer_call", res)

    def test_reject_call_intent(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.reject_call.return_value = True

            res = wa_plugin.run({"intent": "reject_call"})
            self.assertIn("Successfully executed reject_call", res)

    def test_video_intent_routed_correctly(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["Rahul"]
            mock_instance.open_contact.return_value = True
            mock_instance.start_call.return_value = "SUCCESS_VERIFIED"
            mock_instance.diagnostic_log = []
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "video_call", "contact_name": "Rahul"})
            mock_instance.start_call.assert_called_once_with("Rahul", kind="video")

    def test_voice_intent_routed_correctly(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["Rahul"]
            mock_instance.open_contact.return_value = True
            mock_instance.start_call.return_value = "SUCCESS_VERIFIED"
            mock_instance.diagnostic_log = []
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "voice_call", "contact_name": "Rahul"})
            mock_instance.start_call.assert_called_once_with("Rahul", kind="voice")

    def test_missing_contact_name(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True

            res = wa_plugin.run({"intent": "voice_call"})
            self.assertIn("Contact name not specified", res)


class TestMultipleContacts(unittest.TestCase):
    """Test handling of multiple matching contacts."""

    def test_multiple_contacts_returns_error(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["Arun 1", "Arun 2"]
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "voice_call", "contact_name": "Arun"})
            self.assertIn("Multiple contacts found", res)
            mock_instance.open_contact.assert_not_called()


class TestCallFlow(unittest.TestCase):
    """Test the complete call flow."""

    def test_voice_call_success_verified(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["Rahul"]
            mock_instance.open_contact.return_value = True
            mock_instance.start_call.return_value = "SUCCESS_VERIFIED"
            mock_instance.diagnostic_log = []
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "voice_call", "contact_name": "Rahul"})
            self.assertIn("Successfully initiated voice_call", res)

    def test_voice_call_success_unverified(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["Rahul"]
            mock_instance.open_contact.return_value = True
            mock_instance.start_call.return_value = "SUCCESS_UNVERIFIED"
            mock_instance.diagnostic_log = []
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "voice_call", "contact_name": "Rahul"})
            self.assertIn("could not be independently verified", res)

    def test_voice_call_failure(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["Rahul"]
            mock_instance.open_contact.return_value = True
            mock_instance.start_call.return_value = False
            mock_instance.diagnostic_log = []
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "voice_call", "contact_name": "Rahul"})
            self.assertIn("Failed", res)

    def test_chat_open_failure(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["Rahul"]
            mock_instance.open_contact.return_value = False
            mock_instance.diagnostic_log = ["chat not opened"]
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "voice_call", "contact_name": "Rahul"})
            self.assertIn("Failed to open chat", res)


class TestTanglishNLP(unittest.TestCase):
    """Test Tamil/Tanglish command handling."""

    def test_tanglish_call_command(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["amma"]
            mock_instance.open_contact.return_value = True
            mock_instance.start_call.return_value = "SUCCESS_VERIFIED"
            mock_instance.diagnostic_log = []
            mock_instance._uia_blind = False

            res = wa_plugin.run({"intent": "whatsapp la amma ku call pannu"})
            self.assertIn("Successfully initiated voice_call", res)
            mock_instance.search_contact.assert_called_once_with("amma")


class TestDiagnosticSearch(unittest.TestCase):
    """Test the search diagnostic mode."""

    def test_search_test_mode(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.search_contact.return_value = ["My World"]
            mock_instance.open_contact.return_value = True
            mock_instance.check_call_buttons.return_value = True
            mock_instance.inspect_whatsapp_call_controls.return_value = {
                "uia_blind": False,
                "controls": [],
            }
            mock_instance.diagnostic_log = ["test log entry"]

            res = wa_plugin.run({"intent": "whatsapp_search_test", "contact_name": "My World"})
            self.assertIn("Diagnostic Search Test Completed", res)
            mock_instance.start_call.assert_not_called()


class TestCallStage(unittest.TestCase):
    """Test the CallStage enum."""

    def test_all_stages_exist(self):
        expected = [
            "IDLE", "OPEN_WHATSAPP", "WAIT_FOR_WHATSAPP_READY",
            "FIND_SEARCH_CONTROL", "SEARCH_CONTACT", "WAIT_FOR_SEARCH_RESULTS",
            "SELECT_CONTACT", "VERIFY_CHAT_OPENED", "INSPECT_CHAT_UI",
            "FIND_CALL_BUTTON", "TRIGGER_CALL", "VERIFY_CALL_UI",
            "CALL_STARTED", "FAILED",
        ]
        for stage_name in expected:
            self.assertTrue(
                hasattr(wa_plugin.CallStage, stage_name),
                f"CallStage.{stage_name} should exist"
            )


class TestControllerLogging(unittest.TestCase):
    """Test that the controller logs correctly."""

    def test_log_appends_to_diagnostic_log(self):
        controller = wa_plugin.WhatsAppDesktopController()
        controller.log("test message")
        self.assertEqual(len(controller.diagnostic_log), 1)
        self.assertIn("test message", controller.diagnostic_log[0])

    def test_log_includes_stage(self):
        controller = wa_plugin.WhatsAppDesktopController()
        controller._current_stage = wa_plugin.CallStage.SEARCH_CONTACT
        controller.log("searching")
        self.assertIn("SEARCH_CONTACT", controller.diagnostic_log[0])

    def test_log_includes_level(self):
        controller = wa_plugin.WhatsAppDesktopController()
        controller.log("something failed", "ERROR")
        self.assertIn("ERROR", controller.diagnostic_log[0])


class TestPollFunction(unittest.TestCase):
    """Test the _poll helper."""

    def test_poll_returns_on_success(self):
        calls = [0]
        def checker():
            calls[0] += 1
            return calls[0] >= 3  # True on 3rd call

        result = wa_plugin._poll(checker, timeout=5.0, interval=0.01)
        self.assertTrue(result)
        self.assertEqual(calls[0], 3)

    def test_poll_returns_none_on_timeout(self):
        result = wa_plugin._poll(lambda: False, timeout=0.1, interval=0.02)
        self.assertIsNone(result)


class TestNormalizeName(unittest.TestCase):
    """Test name normalization."""

    def test_basic(self):
        self.assertEqual(wa_plugin._normalize_name("My World"), "myworld")

    def test_extra_spaces(self):
        self.assertEqual(wa_plugin._normalize_name("My   World"), "my   world".replace(" ", ""))

    def test_mixed_case(self):
        self.assertEqual(wa_plugin._normalize_name("RaHuL"), "rahul")


class TestControllerInitialState(unittest.TestCase):
    """Test controller initial state."""

    def test_initial_state(self):
        controller = wa_plugin.WhatsAppDesktopController()
        self.assertIsNone(controller.window)
        self.assertIsNone(controller.active_contact)
        self.assertEqual(controller.diagnostic_log, [])
        self.assertFalse(controller._uia_blind)
        self.assertEqual(controller._current_stage, wa_plugin.CallStage.IDLE)


if __name__ == '__main__':
    unittest.main()
