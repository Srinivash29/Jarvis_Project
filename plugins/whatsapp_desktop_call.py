"""
WhatsApp Desktop calling plugin for JARVIS.

Designed for WhatsApp for Windows.
Uses the official desktop keyboard shortcuts to open a chat and
UI Automation to locate the call controls. A geometry fallback is
used only when WebView2 does not expose the buttons to UI Automation.
"""

import ctypes
import platform
import re
import time
from ctypes import wintypes

import psutil
import uiautomation as auto


# WhatsApp's current Windows UI normally places the two call buttons
# near the upper-right corner of the active chat header.
# These are only fallback values; UI Automation is preferred.
VOICE_X_FROM_RIGHT = 112
VIDEO_X_FROM_RIGHT = 66
HEADER_Y = 58


def _clean(value):
    return " ".join(str(value or "").lower().split())


def _same_text(a, b):
    return _clean(a) == _clean(b)


class WhatsAppDesktopController:
    def __init__(self):
        self.window = None
        self.active_contact = None
        self.diagnostic_log = []

    def log(self, message):
        self.diagnostic_log.append(str(message))

    @staticmethod
    def _whatsapp_pids():
        pids = set()
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if "whatsapp" in name and name.endswith(".exe"):
                        pids.add(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return pids

    def _find_window_by_pid(self, pids):
        if platform.system() != "Windows" or not pids:
            return None

        user32 = ctypes.windll.user32
        hwnds = []

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )

        def callback(hwnd, _):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True

                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

                if pid.value in pids:
                    hwnds.append(hwnd)
                    return False
            except Exception:
                pass
            return True

        try:
            user32.EnumWindows(EnumWindowsProc(callback), 0)
        except Exception as exc:
            self.log(f"Win32 window scan failed: {exc}")
            return None

        for hwnd in hwnds:
            try:
                return auto.ControlFromHandle(hwnd)
            except Exception:
                continue

        return None

    def find_or_focus_whatsapp(self):
        self.window = None
        pids = self._whatsapp_pids()

        self.window = self._find_window_by_pid(pids)

        if self.window is None:
            try:
                root = auto.GetRootControl()
                for win in root.GetChildren():
                    try:
                        pid = win.ProcessId
                        title = _clean(win.Name)
                        if pid in pids or "whatsapp" in title:
                            self.window = win
                            break
                    except Exception:
                        continue
            except Exception as exc:
                self.log(f"UI Automation root scan failed: {exc}")

        if self.window is None:
            self.log("WhatsApp Desktop window was not found.")
            return False

        try:
            self.window.SetActive()
            time.sleep(0.5)
            self.log("WhatsApp Desktop focused.")
            return True
        except Exception as exc:
            self.log(f"Could not focus WhatsApp Desktop: {exc}")
            return False

    def _all_controls(self, max_depth=18):
        if not self.window:
            return

        try:
            for control, _depth in auto.WalkControl(
                self.window, maxDepth=max_depth
            ):
                yield control
        except Exception as exc:
            self.log(f"UI Automation scan failed: {exc}")

    def _find_named_control(self, names):
        wanted = [_clean(name) for name in names]

        # Direct lookup first.
        for name in names:
            for control_type in (
                "ButtonControl",
                "HyperlinkControl",
                "TextControl",
            ):
                try:
                    control = getattr(self.window, control_type)(
                        searchDepth=25, Name=name
                    )
                    if control.Exists(0.15, 1):
                        return control
                except Exception:
                    pass

        # Full accessibility-tree scan.
        for control in self._all_controls():
            try:
                cname = _clean(control.Name)
                if not cname:
                    continue

                if any(
                    cname == item or item in cname
                    for item in wanted
                ):
                    if hasattr(control, "Click"):
                        return control
            except Exception:
                continue

        return None

    def _search_field(self):
        # WhatsApp Web/Windows exposes the search input differently
        # across WebView2 builds, so check both direct and generic controls.
        for control_type in ("EditControl", "DocumentControl"):
            try:
                control = getattr(self.window, control_type)(searchDepth=18)
                if control.Exists(0.2, 1):
                    return control
            except Exception:
                pass

        for control in self._all_controls(max_depth=12):
            try:
                name = _clean(control.Name)
                ctype = _clean(getattr(control, "ControlTypeName", ""))
                if "search" in name and hasattr(control, "Click"):
                    return control
                if "edit" in ctype and hasattr(control, "Click"):
                    return control
            except Exception:
                continue

        return None

    def _type_into_search(self, contact_name):
        self.window.SetActive()
        time.sleep(0.2)

        # Official WhatsApp for Windows shortcut: Ctrl+Alt+N = New chat.
        # This is preferable to Ctrl+F because Ctrl+F is chat-search in
        # some WhatsApp builds.
        try:
            self.window.SendKeys("{Ctrl}{Alt}n", waitTime=0.7)
            time.sleep(0.7)
            self.log("Opened New Chat using Ctrl+Alt+N.")
        except Exception as exc:
            self.log(f"New Chat shortcut failed: {exc}")

        search = self._search_field()

        if search is not None:
            try:
                search.Click()
                search.SendKeys("{Ctrl}a{Delete}", waitTime=0.1)
                search.SendKeys(contact_name, waitTime=0.8)
                self.log("Contact entered through UI Automation.")
                return True
            except Exception as exc:
                self.log(f"UIA search input failed: {exc}")

        # Keyboard fallback: the New Chat dialog normally puts focus
        # directly in the contact search field.
        try:
            self.window.SendKeys("{Ctrl}a{Delete}", waitTime=0.1)
            self.window.SendKeys(contact_name, waitTime=1.0)
            self.log("Contact entered through keyboard fallback.")
            return True
        except Exception as exc:
            self.log(f"Keyboard contact entry failed: {exc}")
            return False

    def _find_contact_result(self, contact_name):
        target = _clean(contact_name)

        # Search the accessibility tree for an exact/partial matching item.
        candidates = []

        for control in self._all_controls(max_depth=20):
            try:
                name = _clean(control.Name)
                if not name or name == target:
                    if name == target and hasattr(control, "Click"):
                        candidates.append(control)
                    continue

                if target in name and hasattr(control, "Click"):
                    candidates.append(control)
            except Exception:
                continue

        if candidates:
            # Prefer the shortest matching name, which is usually the
            # actual contact result rather than a surrounding container.
            candidates.sort(key=lambda c: len(_clean(c.Name)))
            return candidates[0]

        return None

    def open_contact(self, contact_name):
        normalized = _clean(contact_name)

        if self.active_contact == normalized:
            self.log(f"'{contact_name}' is already the active chat.")
            return True

        if not self._type_into_search(contact_name):
            return False

        time.sleep(1.2)

        result = self._find_contact_result(contact_name)

        if result is not None:
            try:
                result.Click(waitTime=0.3)
                time.sleep(1.0)
                self.log(f"Selected WhatsApp contact: {contact_name}.")
            except Exception as exc:
                self.log(f"Could not click contact result: {exc}")
                result = None

        if result is None:
            # WhatsApp normally selects the first result when Enter is used.
            try:
                self.window.SendKeys("{Enter}", waitTime=0.6)
                time.sleep(1.2)
                self.log("Selected top WhatsApp search result with Enter.")
            except Exception as exc:
                self.log(f"Could not select search result: {exc}")
                return False

        self.active_contact = normalized

        # The call buttons are the most useful confirmation that the
        # individual chat is actually open.
        if self._find_call_control("voice") or self._find_call_control("video"):
            self.log("Active chat confirmed: call controls are available.")
            return True

        self.log(
            "Chat selection completed, but WhatsApp did not expose call "
            "controls yet. Waiting once and checking again."
        )
        time.sleep(1.0)

        if self._find_call_control("voice") or self._find_call_control("video"):
            self.log("Call controls appeared after the second check.")
            return True

        return True

    def _find_call_control(self, kind):
        if kind == "voice":
            names = [
                "Voice call",
                "Start voice call",
                "Audio call",
                "Start audio call",
                "Call",
                "Voice",
            ]
        else:
            names = [
                "Video call",
                "Start video call",
                "Video",
                "Start video",
            ]

        return self._find_named_control(names)

    def _geometry_call(self, kind):
        try:
            import pyautogui

            rect = self.window.BoundingRectangle
            width = rect.right - rect.left
            height = rect.bottom - rect.top

            if width < 600 or height < 400:
                self.log("WhatsApp window is too small for geometry fallback.")
                return False

            offset = (
                VOICE_X_FROM_RIGHT
                if kind == "voice"
                else VIDEO_X_FROM_RIGHT
            )

            x = rect.right - offset
            y = rect.top + HEADER_Y

            self.window.SetActive()
            time.sleep(0.2)
            pyautogui.click(x, y)

            self.log(
                f"{kind.capitalize()} call clicked using dynamic "
                f"header position ({x}, {y})."
            )
            return True
        except Exception as exc:
            self.log(f"Geometry fallback failed: {exc}")
            return False

    def click_call(self, kind):
        button = self._find_call_control(kind)

        if button is not None:
            try:
                button.Click(waitTime=0.25)
                self.log(
                    f"{kind.capitalize()} call button clicked through UI Automation."
                )
                return True
            except Exception as exc:
                self.log(f"UIA call click failed: {exc}")

        self.log(
            f"{kind.capitalize()} call button is not exposed through UI "
            "Automation. Trying dynamic mouse fallback."
        )
        return self._geometry_call(kind)

    def get_call_state(self):
        if not self.window:
            return "UNKNOWN"

        if self._find_named_control(
            ["End call", "Hang up", "End voice call", "End video call"]
        ):
            return "CONNECTED"

        if self._find_named_control(
            ["Accept", "Answer", "Accept call", "Answer call"]
        ):
            return "INCOMING_CALL"

        return "UNKNOWN"

    def wait_for_call(self, timeout=5.0):
        deadline = time.time() + timeout

        while time.time() < deadline:
            state = self.get_call_state()
            if state == "CONNECTED":
                self.log("WhatsApp call UI confirmed.")
                return "SUCCESS_VERIFIED"
            time.sleep(0.5)

        self.log(
            "The call button was clicked, but WhatsApp did not expose "
            "an End call control within the verification period."
        )
        return "SUCCESS_UNVERIFIED"

    def start_call(self, contact_name, kind="voice"):
        if not self.find_or_focus_whatsapp():
            return False

        if not self.open_contact(contact_name):
            self.log(f"Could not open chat for '{contact_name}'.")
            return False

        time.sleep(0.5)

        if not self.click_call(kind):
            self.log(f"Could not start {kind} call.")
            return False

        return self.wait_for_call()

    def end_call(self):
        if not self.find_or_focus_whatsapp():
            return False

        button = self._find_named_control(
            ["End call", "Hang up", "End voice call", "End video call"]
        )

        if button is None:
            self.log("End call button not found.")
            return False

        try:
            button.Click(waitTime=0.2)
            self.log("Call ended.")
            return True
        except Exception as exc:
            self.log(f"Could not end call: {exc}")
            return False

    def answer_call(self):
        if not self.find_or_focus_whatsapp():
            return False

        button = self._find_named_control(
            ["Accept", "Answer", "Accept call", "Answer call"]
        )

        if button is None:
            self.log("Accept/Answer button not found.")
            return False

        try:
            button.Click(waitTime=0.2)
            self.log("Incoming call accepted.")
            return True
        except Exception as exc:
            self.log(f"Could not accept call: {exc}")
            return False

    def reject_call(self):
        if not self.find_or_focus_whatsapp():
            return False

        button = self._find_named_control(
            ["Decline", "Reject", "Decline call", "Reject call"]
        )

        if button is None:
            self.log("Decline/Reject button not found.")
            return False

        try:
            button.Click(waitTime=0.2)
            self.log("Incoming call rejected.")
            return True
        except Exception as exc:
            self.log(f"Could not reject call: {exc}")
            return False


PLUGIN = {
    "name": "whatsapp_desktop_call",
    "description": (
        "Controls WhatsApp Desktop calling features. "
        "Supports voice calls, video calls, answering, rejecting, "
        "ending calls, and call status."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "intent": {
                "type": "STRING",
                "description": (
                    "voice_call, video_call, end_call, answer_call, "
                    "reject_call, status"
                ),
            },
            "contact_name": {
                "type": "STRING",
                "description": "WhatsApp contact name.",
            },
        },
        "required": ["intent"],
    },
}


def extract_contact_name(text):
    text = str(text or "").strip()

    patterns = [
        r"call\s+(.+?)\s+on\s+whatsapp",
        r"whatsapp\s+video\s+call\s+to\s+(.+)",
        r"whatsapp\s+video\s+call\s+(.+)",
        r"whatsapp\s+call\s+to\s+(.+)",
        r"whatsapp\s+call\s+(.+)",
        r"whatsapp\s+la\s+(.+?)\s+ku\s+call",
        r"call\s+(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            name = re.sub(r"(?i)\bpannu\b", "", name).strip()
            name = re.sub(r"(?i)\bplease\b", "", name).strip()
            if name:
                return name

    return None


def _write_log(player, message):
    if player:
        try:
            player.write_log(message)
        except Exception:
            pass


def run(parameters: dict, player=None, session_memory=None) -> str:
    raw_intent = str(parameters.get("intent", "") or "").strip().lower()
    contact_name = str(parameters.get("contact_name", "") or "").strip()

    if not contact_name and ("call" in raw_intent):
        contact_name = extract_contact_name(raw_intent) or ""

    if "end" in raw_intent or "hang" in raw_intent or "cut" in raw_intent:
        intent = "end_call"
    elif (
        "answer" in raw_intent
        or "attend" in raw_intent
        or "accept" in raw_intent
    ):
        intent = "answer_call"
    elif "reject" in raw_intent or "decline" in raw_intent:
        intent = "reject_call"
    elif "video" in raw_intent:
        intent = "video_call"
    elif "status" in raw_intent:
        intent = "status"
    elif "voice" in raw_intent or "call" in raw_intent:
        intent = "voice_call"
    else:
        return "Error: Ambiguous WhatsApp command."

    controller = WhatsAppDesktopController()

    if intent == "end_call":
        return (
            "Successfully ended the WhatsApp call."
            if controller.end_call()
            else "Unable to end the WhatsApp call.\n"
            + "\n".join(controller.diagnostic_log)
        )

    if intent == "answer_call":
        return (
            "Successfully answered the WhatsApp call."
            if controller.answer_call()
            else "Unable to answer the WhatsApp call.\n"
            + "\n".join(controller.diagnostic_log)
        )

    if intent == "reject_call":
        return (
            "Successfully rejected the WhatsApp call."
            if controller.reject_call()
            else "Unable to reject the WhatsApp call.\n"
            + "\n".join(controller.diagnostic_log)
        )

    if intent == "status":
        if not controller.find_or_focus_whatsapp():
            return "WhatsApp Desktop is not running."

        return f"WhatsApp Call State: {controller.get_call_state()}"

    if not contact_name:
        return "Error: Contact name not specified."

    _write_log(player, f"JARVIS: Preparing WhatsApp {intent.replace('_', ' ')} to {contact_name}.")

    kind = "video" if intent == "video_call" else "voice"
    result = controller.start_call(contact_name, kind)

    logs = "\n".join(controller.diagnostic_log)

    if result == "SUCCESS_VERIFIED":
        message = (
            f"Successfully initiated {kind} call to {contact_name}.\n"
            f"Logs:\n{logs}"
        )
        _write_log(player, f"JARVIS: {kind.capitalize()} call started for {contact_name}.")
        return message

    if result == "SUCCESS_UNVERIFIED":
        return (
            f"{kind.capitalize()} call button was clicked for {contact_name}, "
            "but WhatsApp did not expose enough UI information to verify "
            "the call state.\n"
            f"Logs:\n{logs}"
        )

    return (
        f"Unable to start the WhatsApp {kind} call to {contact_name}.\n"
        f"Logs:\n{logs}"
    )
