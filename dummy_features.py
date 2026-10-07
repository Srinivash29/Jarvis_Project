"""
dummy_features.py — Safe no-op stubs for removed JARVIS features.

This file exists solely to let main.py start without crashing.
Every function returns a harmless "not implemented" response so
that if the LLM calls a removed tool, JARVIS stays alive and
reports the tool as unavailable instead of raising NameError.

These stubs will be replaced one-by-one as real plugins are
rebuilt in the plugins/ directory.
"""

__all__ = [
    # Classes
    "SystemMonitor", "ProactiveEngine",
    # Tool-dispatch functions
    # Utility functions (underscore-prefixed — must be listed explicitly)
    "get_system_status", "monitor_check_all",
    "add_monitor", "remove_monitor", "list_monitors",
    "_capture_screen", "_capture_camera", "_fetch_news_sync",
]


# ─── Classes used by JarvisLive.__init__ ─────────────────────────────────


class SystemMonitor:
    """Stub: hardware threshold monitor (CPU temp, RAM, etc.)."""
    def check(self):
        return None


class ProactiveEngine:
    """Stub: decides when JARVIS should speak unprompted."""
    def should_trigger(self, *args, **kwargs):
        return False

    def mark_triggered(self):
        pass

    def build_prompt(self, *args, **kwargs):
        return ""


# ─── Tool-dispatch functions (called from _execute_tool) ─────────────────


# ─── Utility functions (called outside tool dispatch) ────────────────────


def get_system_status(*args, **kwargs):
    return "System status is not available yet."


def monitor_check_all(*args, **kwargs):
    return []


def add_monitor(*args, **kwargs):
    return "Monitor system is not implemented yet."


def remove_monitor(*args, **kwargs):
    return "Monitor system is not implemented yet."


def list_monitors(*args, **kwargs):
    return []


def _capture_screen():
    """Return (image_bytes, mime_type) — stub returns a tiny 1×1 PNG."""
    # Minimal valid 1×1 white PNG (67 bytes)
    import base64
    _TINY_PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQI12Ng"
        "AAIABQABNjN9GQAAAAlwSFlzAAAWJQAAFiUBSVIk8AAAAA0lEQVQI12P4"
        "z8BQDwAEgAF/QualIQAAAABJRU5ErkJggg=="
    )
    return _TINY_PNG, "image/png"


def _capture_camera():
    """Return (image_bytes, mime_type) — stub returns a tiny 1×1 PNG."""
    return _capture_screen()


def _fetch_news_sync(query: str = "") -> str:
    """Stub: returns empty string (no news available)."""
    return ""
