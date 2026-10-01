"""
Tests for WhatsApp Desktop call logic (controller internals).

Tests the controller's state machine, contact handling, call button detection,
verification logic, and error paths without needing real WhatsApp.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import time

import importlib.util
plugin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'whatsapp_desktop_call.py'))
spec = importlib.util.spec_from_file_location("whatsapp_desktop_call", plugin_path)
wa_plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wa_plugin)


class TestControllerChatVerification(unittest.TestCase):
    """Test chat opening and verification logic."""

    def setUp(self):
        self.controller = wa_plugin.WhatsAppDesktopController()
        self.controller.window = MagicMock()

    def test_window_title_verification(self):
        """Window title containing contact name → verified."""
        self.controller.window.Name = "WhatsApp - My World"
        self.assertTrue(self.controller._verify_chat_opened("My World", "myworld"))
        self.assertIn("Window Title confirmed", " ".join(self.controller.diagnostic_log))

    def test_window_title_wrong_contact(self):
        """Window title with different contact → not verified."""
        self.controller.window.Name = "WhatsApp - Someone Else"
        # Mock ButtonControl to also fail
        self.controller.window.ButtonControl.return_value.Exists.return_value = False
        result = self.controller._verify_chat_opened("My World", "myworld")
        self.assertFalse(result)

    def test_call_buttons_verification(self):
        """Call buttons detected → chat is open."""
        self.controller.window.Name = "WhatsApp"  # generic title
        btn = MagicMock()
        btn.Exists.return_value = True
        self.controller.window.ButtonControl.return_value = btn
        result = self.controller._verify_chat_opened("My World", "myworld")
        self.assertTrue(result)

    def test_open_contact_already_active(self):
        """Already active chat returns True immediately."""
        self.controller.active_contact = "myworld"
        self.assertTrue(self.controller.open_contact("My World", []))

    def test_open_contact_with_marker(self):
        """ALREADY_ACTIVE marker sets active_contact."""
        self.controller.open_contact("Rahul", ["ALREADY_ACTIVE"])
        self.assertEqual(self.controller.active_contact, "rahul")

    def test_open_contact_blind_mode_succeeds(self):
        """In UIA blind mode, chat open is assumed successful."""
        self.controller._uia_blind = True
        self.controller.window.Name = "WhatsApp"  # generic, no contact name
        self.controller.window.ButtonControl.return_value.Exists.return_value = False

        result = self.controller.open_contact("My World", [])
        self.assertTrue(result)
        self.assertIn("UIA blind", " ".join(self.controller.diagnostic_log))


class TestEnsureActiveChat(unittest.TestCase):
    """Test _ensure_active_chat logic."""

    def setUp(self):
        self.controller = wa_plugin.WhatsAppDesktopController()

    def test_no_active_contact(self):
        self.assertFalse(self.controller._ensure_active_chat("Rahul"))

    def test_exact_match(self):
        self.controller.active_contact = "rahul"
        self.assertTrue(self.controller._ensure_active_chat("Rahul"))

    def test_partial_match(self):
        self.controller.active_contact = "rahulsharma"
        self.assertTrue(self.controller._ensure_active_chat("Rahul"))

    def test_no_match(self):
        self.controller.active_contact = "arun"
        self.assertFalse(self.controller._ensure_active_chat("Rahul"))


class TestCallControlDetection(unittest.TestCase):
    """Test call button detection strategies."""

    def setUp(self):
        self.controller = wa_plugin.WhatsAppDesktopController()
        self.controller.window = MagicMock()

    def test_uia_button_found_directly(self):
        """Direct ButtonControl search finds the button."""
        btn = MagicMock()
        btn.Exists.return_value = True
        self.controller.window.ButtonControl.return_value = btn

        result = self.controller._find_call_control("voice")
        self.assertIsNotNone(result)

    def test_uia_button_not_found(self):
        """ButtonControl search fails → None returned."""
        btn = MagicMock()
        btn.Exists.return_value = False
        self.controller.window.ButtonControl.return_value = btn

        result = self.controller._find_call_control("voice")
        self.assertIsNone(result)


class TestCallStateDetection(unittest.TestCase):
    """Test call state detection."""

    def setUp(self):
        self.controller = wa_plugin.WhatsAppDesktopController()
        self.controller.window = MagicMock()

    def test_unknown_state(self):
        """No call buttons → UNKNOWN."""
        self.controller.window.ButtonControl.return_value.Exists.return_value = False
        self.controller.window.HyperlinkControl.return_value.Exists.return_value = False
        self.controller.window.TextControl.return_value.Exists.return_value = False
        self.controller.window.Name = "WhatsApp"
        state = self.controller.get_call_state()
        self.assertEqual(state, "UNKNOWN")

    def test_no_window(self):
        """No window → UNKNOWN."""
        self.controller.window = None
        self.assertEqual(self.controller.get_call_state(), "UNKNOWN")


class TestInvokeControl(unittest.TestCase):
    """Test the multi-method control invocation."""

    def setUp(self):
        self.controller = wa_plugin.WhatsAppDesktopController()
        self.controller.window = MagicMock()

    def test_invoke_pattern_succeeds(self):
        """InvokePattern.Invoke() is tried first."""
        button = MagicMock()
        pattern = MagicMock()
        button.GetInvokePattern.return_value = pattern

        result = self.controller._invoke_control(button, "voice")
        self.assertTrue(result)
        pattern.Invoke.assert_called_once()

    def test_invoke_fallback_to_focus_space(self):
        """When Invoke pattern fails, SetFocus+Space is tried."""
        button = MagicMock()
        button.GetInvokePattern.side_effect = Exception("no pattern")

        result = self.controller._invoke_control(button, "voice")
        self.assertTrue(result)
        button.SetFocus.assert_called_once()

    def test_invoke_fallback_to_click(self):
        """When both Invoke and SetFocus fail, Click is tried."""
        button = MagicMock()
        button.GetInvokePattern.side_effect = Exception("no pattern")
        button.SetFocus.side_effect = Exception("no focus")

        result = self.controller._invoke_control(button, "voice")
        self.assertTrue(result)
        button.Click.assert_called_once()


class TestVerifyCallStarted(unittest.TestCase):
    """Test call verification logic."""

    def setUp(self):
        self.controller = wa_plugin.WhatsAppDesktopController()
        self.controller.window = MagicMock()

    @patch('time.time')
    def test_verified_when_end_call_found(self, mock_time):
        """Call is verified when End-call button appears."""
        # Simulate: first check returns UNKNOWN, second returns CONNECTED
        call_count = [0]
        times = [0, 0.5, 1.0, 1.5, 2.0, 2.5]

        def fake_time():
            idx = min(call_count[0], len(times) - 1)
            call_count[0] += 1
            return times[idx]

        mock_time.side_effect = fake_time

        states = ["UNKNOWN", "CONNECTED"]
        state_idx = [0]

        def fake_get_state():
            idx = min(state_idx[0], len(states) - 1)
            state_idx[0] += 1
            return states[idx]

        self.controller.get_call_state = fake_get_state

        result = self.controller.verify_call_started(timeout=5.0)
        self.assertEqual(result, "SUCCESS_VERIFIED")

    @patch('time.time')
    def test_unverified_on_timeout(self, mock_time):
        """Call is unverified when timeout expires."""
        call_count = [0]

        def fake_time():
            val = call_count[0]
            call_count[0] += 1
            return val  # Each call increments by 1 second

        mock_time.side_effect = fake_time

        self.controller.get_call_state = MagicMock(return_value="UNKNOWN")

        result = self.controller.verify_call_started(timeout=3.0)
        self.assertEqual(result, "SUCCESS_UNVERIFIED")


class TestDiagnosticInspection(unittest.TestCase):
    """Test the diagnostic inspection function."""

    def test_no_window(self):
        controller = wa_plugin.WhatsAppDesktopController()
        result = controller.inspect_whatsapp_call_controls()
        self.assertIn("error", result)

    def test_with_window(self):
        controller = wa_plugin.WhatsAppDesktopController()
        controller.window = MagicMock()
        controller.window.Name = "WhatsApp"
        # Mock to return no controls
        controller.window.ButtonControl.return_value.Exists.return_value = False
        result = controller.inspect_whatsapp_call_controls()
        self.assertIn("window_name", result)
        self.assertIn("uia_blind", result)
        self.assertIn("controls", result)


class TestGeometryFallback(unittest.TestCase):
    """Test geometry-based click fallback."""

    def setUp(self):
        self.controller = wa_plugin.WhatsAppDesktopController()
        self.controller.window = MagicMock()

    @patch('pyautogui.click')
    def test_geometry_voice_call(self, mock_click):
        rect = MagicMock()
        rect.left = 0
        rect.top = 0
        rect.right = 1600
        rect.bottom = 852
        self.controller.window.BoundingRectangle = rect

        result = self.controller._geometry_call("voice")
        self.assertTrue(result)
        mock_click.assert_called_once()
        args = mock_click.call_args
        click_x, click_y = args[0]
        # Voice call button should be at ~8% from right edge
        self.assertGreater(click_x, 1400)
        self.assertLess(click_x, 1600)

    @patch('pyautogui.click')
    def test_geometry_video_call(self, mock_click):
        rect = MagicMock()
        rect.left = 0
        rect.top = 0
        rect.right = 1600
        rect.bottom = 852
        self.controller.window.BoundingRectangle = rect

        result = self.controller._geometry_call("video")
        self.assertTrue(result)
        mock_click.assert_called_once()

    @patch('pyautogui.click')
    def test_geometry_window_too_small(self, mock_click):
        rect = MagicMock()
        rect.left = 0
        rect.top = 0
        rect.right = 100
        rect.bottom = 100
        self.controller.window.BoundingRectangle = rect

        result = self.controller._geometry_call("voice")
        self.assertFalse(result)
        mock_click.assert_not_called()


class TestStatusCheck(unittest.TestCase):
    """Test status check intent."""

    def test_status_when_not_running(self):
        with patch.object(wa_plugin.WhatsAppDesktopController, 'is_whatsapp_running', return_value=False):
            res = wa_plugin.run({"intent": "status"})
            self.assertIn("NOT_RUNNING", res)

    def test_status_when_running(self):
        with patch.object(wa_plugin, 'WhatsAppDesktopController') as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.is_whatsapp_running.return_value = True
            mock_instance.get_call_state.return_value = "UNKNOWN"

            res = wa_plugin.run({"intent": "status"})
            self.assertIn("UNKNOWN", res)


if __name__ == '__main__':
    unittest.main()
