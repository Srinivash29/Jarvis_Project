"""
dashboard/client.py — Proxy connecting main.py to the standalone background DashboardServer daemon.

When jarvis_service.py is running on port 8000, main.py connects as an agent client
through this proxy rather than failing to bind port 8000. It receives phone commands
and phone audio, and relays JARVIS status and speech back to mobile clients.
"""

import asyncio
import base64
import json
import socket
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PORT = 8000


def _local_ip() -> str:
    """Return best LAN IP address for dashboard access."""
    for probe in ("8.8.8.8", "1.1.1.1", "192.168.1.1"):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((probe, 80))
            ip = s.getsockname()[0]
            s.close()
            if not ip.startswith("127."):
                return ip
        except Exception:
            pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


class DashboardClientProxy:
    """Proxy object implementing the exact same interface as DashboardServer for main.py."""

    def __init__(self, host: str = "127.0.0.1", port: int = PORT):
        self._host = host
        self._port = port
        self._ip = _local_ip()
        self._command_queue: asyncio.Queue = asyncio.Queue()
        self._phone_audio_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._connect_callback = None
        self._wake_callback = None
        self._ws = None
        self._running = False
        self._latest_key = ""
        self._pending_keys: dict[str, float] = {}

    def get_url(self) -> str:
        return f"http://{self._ip}:{self._port}"

    def get_manual_url(self) -> str:
        return f"{self._ip}:{self._port}"

    def get_https_url(self) -> str:
        return f"https://{self._ip}:{self._port + 1}"

    def set_wake_callback(self, fn) -> None:
        self._wake_callback = fn

    def set_connect_callback(self, fn) -> None:
        self._connect_callback = fn

    def new_key(self, expiry_secs: int = 600) -> str:
        """Request a fresh key from the daemon via HTTP POST."""
        try:
            req = urllib.request.Request(
                f"http://{self._host}:{self._port}/api/new-key",
                data=json.dumps({"expiry_secs": expiry_secs}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                key = data.get("key", "")
                self._latest_key = key
                return key
        except Exception as e:
            print(f"[DashboardProxy] Error getting new key from daemon: {e}")
            import secrets, string
            chars = [c for c in (string.ascii_uppercase + string.digits) if c not in ('O', 'I', 'L', '0', '1')]
            key = ''.join(secrets.choice(chars) for _ in range(6))
            self._latest_key = key
            return key

    async def broadcast(self, msg: dict) -> None:
        """Send broadcast payload to the daemon over WebSocket."""
        if self._ws and not getattr(self._ws, "closed", True):
            try:
                await self._ws.send(json.dumps({"type": "broadcast", "payload": msg}))
            except Exception as e:
                print(f"[DashboardProxy] Broadcast failed: {e}")

    async def serve(self) -> None:
        """Connect to daemon /ws/agent and maintain the live link."""
        import websockets
        self._running = True
        ws_url = f"ws://{self._host}:{self._port}/ws/agent"
        print(f"[DashboardProxy] Connecting to background service at {ws_url}...")

        while self._running:
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                    self._ws = ws
                    print("[DashboardProxy] Connected to background daemon. JARVIS is now LIVE on mobile.")
                    if self._connect_callback:
                        try:
                            self._connect_callback()
                        except Exception:
                            pass

                    # Inform daemon of active status
                    await ws.send(json.dumps({"type": "status", "state": "active"}))

                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                            mtype = data.get("type")
                            if mtype == "command":
                                text = data.get("text", "")
                                if text:
                                    await self._command_queue.put(text)
                                    if self._wake_callback:
                                        self._wake_callback()
                            elif mtype == "wake":
                                if self._wake_callback:
                                    self._wake_callback()
                            elif mtype == "phone_audio":
                                b64 = data.get("data", "")
                                if b64:
                                    raw_pcm = base64.b64decode(b64)
                                    try:
                                        self._phone_audio_queue.put_nowait({
                                            "data": raw_pcm,
                                            "mime_type": "audio/pcm"
                                        })
                                    except asyncio.QueueFull:
                                        pass
                        except Exception as e:
                            print(f"[DashboardProxy] Error processing daemon message: {e}")
            except Exception as e:
                self._ws = None
                if not self._running:
                    break
                print(f"[DashboardProxy] Daemon connection dropped ({e}) — retrying in 2s...")
                await asyncio.sleep(2.0)
