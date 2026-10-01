import asyncio
import json
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard.server import DashboardServer
from core.telegram_bot import TelegramBotBridge


class TestPhoneConnect(unittest.TestCase):
    def setUp(self):
        self.server = DashboardServer()

    def test_dashboard_url_http_port_8000(self):
        """Verify that the primary URL is plain HTTP on port 8000 for instant, warning-free phone connection."""
        url = self.server.get_url()
        self.assertTrue(url.startswith("http://"))
        self.assertIn(":8000", url)

    def test_dashboard_manual_url(self):
        manual = self.server.get_manual_url()
        self.assertIn(":8000", manual)

    def test_dashboard_https_url(self):
        https_url = self.server.get_https_url()
        self.assertIn(":8001", https_url)

    def test_key_generation(self):
        key = self.server.new_key(expiry_secs=300)
        self.assertEqual(len(key), 6)
        self.assertEqual(self.server._latest_key, key)
        self.assertIn(key, self.server._pending_keys)

    def test_tool_declaration_exists(self):
        from main import TOOL_DECLARATIONS
        names = [t["name"] for t in TOOL_DECLARATIONS]
        self.assertIn("connect_phone", names)

    def test_telegram_bot_bridge_initialization(self):
        q = asyncio.Queue()
        tb = TelegramBotBridge(q)
        self.assertIsNotNone(tb)
        self.assertEqual(tb.asst_name, "JARVIS")


if __name__ == "__main__":
    unittest.main()
