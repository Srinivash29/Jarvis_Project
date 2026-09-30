import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import tempfile
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins import whatsapp_monitor

class TestWhatsAppMonitor(unittest.TestCase):
    def setUp(self):
        # Use a temporary file for history during tests
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_history_file = Path(self.tmp_dir.name) / "whatsapp_replies.json"
        self._orig_history_file = whatsapp_monitor._HISTORY_FILE
        whatsapp_monitor._HISTORY_FILE = self.tmp_history_file
        whatsapp_monitor._monitoring_active = False

    def tearDown(self):
        whatsapp_monitor._HISTORY_FILE = self._orig_history_file
        whatsapp_monitor._monitoring_active = False
        self.tmp_dir.cleanup()

    def test_record_and_load_history(self):
        entry = whatsapp_monitor._record_incoming_message(
            sender="Sabari",
            message="Hello, I am fine!",
            notif_id="123",
            time_str="07:15 PM"
        )
        self.assertEqual(entry["sender"], "Sabari")
        self.assertEqual(entry["message"], "Hello, I am fine!")

        history = whatsapp_monitor._load_replies_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["sender"], "Sabari")

    def test_check_replies_empty(self):
        with patch.object(whatsapp_monitor, '_get_whatsapp_notifications', return_value=[]):
            res = whatsapp_monitor.run({"action": "check"})
            self.assertIn("no new replies", res.lower())

    def test_check_replies_with_sender_filter_found(self):
        whatsapp_monitor._record_incoming_message(
            sender="Sabari",
            message="Hey Deepak, let's meet tomorrow.",
            time_str="07:20 PM"
        )
        with patch.object(whatsapp_monitor, '_get_whatsapp_notifications', return_value=[]):
            res = whatsapp_monitor.run({"action": "check", "sender": "sabari"})
            self.assertIn("Sabari replied", res)
            self.assertIn("Hey Deepak, let's meet tomorrow.", res)

    def test_check_replies_with_sender_filter_not_found(self):
        whatsapp_monitor._record_incoming_message(
            sender="Alex",
            message="See you later!",
            time_str="07:10 PM"
        )
        with patch.object(whatsapp_monitor, '_get_whatsapp_notifications', return_value=[]):
            res = whatsapp_monitor.run({"action": "check", "sender": "sabari"})
            self.assertIn("no new replies have arrived from sabari", res.lower())

    def test_check_replies_from_live_notification(self):
        fake_notif = [{
            "id": 999,
            "sender": "Sabari",
            "message": "Yes, I got your message.",
            "time_str": "07:25 PM"
        }]
        with patch.object(whatsapp_monitor, '_get_whatsapp_notifications', return_value=fake_notif):
            res = whatsapp_monitor.run({"action": "check", "sender": "sabari"})
            self.assertIn("Sabari replied", res)
            self.assertIn("Yes, I got your message.", res)

            # Check that it got saved into history
            history = whatsapp_monitor._load_replies_history()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["message"], "Yes, I got your message.")

    def test_history_and_clear_action(self):
        whatsapp_monitor._record_incoming_message(sender="Arun", message="Call me back", time_str="06:00 PM")
        res = whatsapp_monitor.run({"action": "history"})
        self.assertIn("Arun", res)
        self.assertIn("Call me back", res)

        clear_res = whatsapp_monitor.run({"action": "clear"})
        self.assertIn("cleared", clear_res.lower())
        self.assertEqual(len(whatsapp_monitor._load_replies_history()), 0)

    def test_turn_on_and_off(self):
        with patch('threading.Thread') as mock_thread:
            res_on = whatsapp_monitor.run({"action": "on"})
            self.assertIn("monitoring enabled", res_on.lower())
            self.assertTrue(whatsapp_monitor._monitoring_active)

            res_off = whatsapp_monitor.run({"action": "off"})
            self.assertIn("stopped monitoring", res_off.lower())
            self.assertFalse(whatsapp_monitor._monitoring_active)

if __name__ == '__main__':
    unittest.main()
