"""
jarvis_service.py — JARVIS 24/7 Mobile Background Service

Runs the HTTP/HTTPS dashboard daemon on port 8000/8001 even when the main JARVIS desktop app is closed.
Allows mobile access, PC monitoring, quick system controls, offline AI queries,
and remote wake/launch of the full JARVIS desktop app.
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / "config" / "jarvis_service.pid"


def _write_pid():
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def _remove_pid():
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass


async def main():
    _write_pid()
    try:
        from dashboard.server import DashboardServer
        server = DashboardServer(is_daemon=True)
        print("=" * 60)
        print("  JARVIS 24/7 MOBILE BACKGROUND SERVICE")
        print("=" * 60)
        print(f"[*] Local Mobile Web App: {server.get_url()}")
        print(f"[*] Network Endpoint:     {server.get_manual_url()}")
        print("[*] Status: Ready for mobile phone connections 24/7.")
        print("[*] When main.py is closed, phone connects in Standby Mode.")
        print("[*] Tapping 'Wake' on phone launches main.py on desktop.")
        print("=" * 60)
        await server.serve()
    finally:
        _remove_pid()


if __name__ == "__main__":
    def _sig_handler(sig, frame):
        _remove_pid()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sig_handler)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _sig_handler)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        _remove_pid()
        print("\n[JARVIS Service] Shutdown complete.")
    except Exception as e:
        _remove_pid()
        print(f"\n[JARVIS Service] Fatal error: {e}")
        sys.exit(1)
