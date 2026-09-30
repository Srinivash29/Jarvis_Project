import uiautomation as auto
import time
import re
import psutil
import platform
import ctypes
from ctypes import wintypes

# --- CONFIGURABLE OFFSETS FOR CALL BUTTONS ---
# Based on WhatsApp Desktop window geometry:
VOICE_CALL_X_OFFSET = 148
VIDEO_CALL_X_OFFSET = 205
CALL_BUTTON_Y_OFFSET = 70
# ---------------------------------------------

class WhatsAppDesktopController:
    def __init__(self):
        self.window = None
        self.diagnostic_log = []
        self.active_contact = None

    def log(self, msg):
        self.diagnostic_log.append(msg)


    @staticmethod
    def _whatsapp_process_pids():
        """Return PIDs for all known/current WhatsApp Windows processes."""
        names = {"whatsapp.exe", "whatsapp.root.exe", "whatsappservice.exe"}
        pids = set()
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = (proc.info.get("name") or "").lower()
                    if name in names or ("whatsapp" in name and name.endswith(".exe")):
                        pids.add(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return pids

    def _find_whatsapp_window_win32(self, pids):
        """Find a real top-level WhatsApp window, including Store-app windows."""
        if platform.system() != "Windows" or not pids:
            return None
        user32 = ctypes.windll.user32
        found = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        def callback(hwnd, _lparam):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value in pids:
                    found.append(hwnd)
                    return False
            except Exception:
                pass
            return True
        try:
            user32.EnumWindows(EnumWindowsProc(callback), 0)
        except Exception as e:
            self.log(f"Win32 window enumeration failed: {e}")
            return None
        if not found:
            return None
        try:
            return auto.ControlFromHandle(found[0])
        except Exception as e:
            self.log(f"Could not attach UIA to WhatsApp window: {e}")
            return None

    def find_or_focus_whatsapp(self):
        """Detect WhatsApp reliably, including Microsoft Store/WebView2 windows."""
        self.window = None
        pids = self._whatsapp_process_pids()

        # Primary path: enumerate real Windows top-level windows by PID.
        self.window = self._find_whatsapp_window_win32(pids)

        # Fallback: UI Automation top-level scan.
        if self.window is None:
            try:
                root = auto.GetRootControl()
                for win in root.GetChildren():
                    try:
                        pid = win.ProcessId
                        name = win.Name or ""
                        proc_name = psutil.Process(pid).name()
                        if (
                            pid in pids
                            or "whatsapp" in proc_name.lower()
                            or "whatsapp" in name.lower()
                        ):
                            self.window = win
                            break
                    except Exception:
                        continue
            except Exception as e:
                self.log(f"UIA root scan failed: {e}")

        if self.window is not None:
            try:
                if self.window.Exists(0, 0):
                    self.window.SetActive()
                    time.sleep(0.5)
                    self.log("WhatsApp window detected and focused.")
                    return True
            except Exception as e:
                self.log(f"WhatsApp window found but could not be focused: {e}")

        if pids:
            self.log(
                f"WhatsApp process detected (PID(s): {sorted(pids)}), "
                "but no usable top-level window was found."
            )
        else:
            self.log("WhatsApp process is not running.")
        return False

    def is_whatsapp_running(self):
        return self.find_or_focus_whatsapp()

    def search_contact(self, name):
        if not self.window:
            if not self.is_whatsapp_running():
                self.log("Search failed: WhatsApp window is not open or cannot be found.")
                return []
                
        normalized = name.lower().replace(" ", "")
        if getattr(self, 'active_contact', None) == normalized:
            self.log(f"No contact search required; target chat already open: {name}")
            return ["ALREADY_ACTIVE"]
                
        self.log(f"Initiating search for: '{name}'")
        
        layer1_success = False
        # Layer 1: Try finding EditControl inside the WebView2 (UIA)
        try:
            search_box = self.window.EditControl(searchDepth=12)
            if search_box.Exists(0.5, 1):
                search_box.Click(waitTime=0.1)
                search_box.SendKeys('{Ctrl}a{Delete}', waitTime=0.1)
                search_box.SendKeys(name, waitTime=1.5)
                self.log("Layer 1 (UIA): Search text entered via EditControl.")
                layer1_success = True
        except Exception as e:
            pass

        # Layer 2: Keyboard shortcuts (Highly reliable for Electron/WebView2 apps)
        if not layer1_success:
            try:
                self.window.SetActive()
                time.sleep(0.2)
                # Ctrl+F focuses the search in WhatsApp Desktop natively
                self.window.SendKeys('{Ctrl}f', waitTime=0.5)
                self.window.SendKeys('{Ctrl}a{Delete}', waitTime=0.1)
                self.window.SendKeys(name, waitTime=1.5)
                self.log("Layer 2 (Keyboard): Search text entered via Ctrl+F shortcut.")
                layer1_success = True
            except Exception as e:
                self.log(f"Layer 2 failed: {e}")
                
        # Layer 3: PyAutoGUI spatial fallback (last resort)
        if not layer1_success:
            try:
                import pyautogui
                rect = self.window.BoundingRectangle
                # Relative click at approx x=150, y=80 from top-left (typical search bar location)
                pyautogui.click(rect.left + 150, rect.top + 80)
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'a')
                pyautogui.press('delete')
                pyautogui.write(name, interval=0.05)
                self.log("Layer 3 (PyAutoGUI): Clicked relative coordinates for search box.")
            except Exception as e:
                self.log(f"Layer 3 failed: {e}")

        # Wait for rendering
        time.sleep(1.0)
            
        # Try to read the actual result controls inside WebView2 -> DocumentControl
        matches = []
        try:
            # We look for the main WebView area
            doc = self.window.DocumentControl(searchDepth=8)
            if doc.Exists(0.1, 1):
                # Search for texts that match the name
                normalized_target = name.lower().replace(" ", "")
                for c, d in auto.WalkControl(doc, maxDepth=10):
                    try:
                        if c.Name:
                            normalized_cname = c.Name.lower().replace(" ", "")
                            if normalized_target in normalized_cname:
                                matches.append(c.Name)
                    except:
                        pass
        except Exception:
            pass
            
        matches = list(set(matches))
        if matches:
            self.log(f"Contact search successful: {name}. Results detected via UIA inside WebView2: {matches}")
        else:
            self.log(f"Contact search successful: {name}. UIA blind to result list inside WebView2. Will rely on default top-result behavior.")
            
        return matches

    def _open_contact_keyboard_fallback(self, contact_name, is_uia_blind=False):
        if is_uia_blind:
            self.log("UIA blind search path detected.")
        try:
            self.window.SetActive()
            self.log("Keyboard fallback: selecting top search result.")
            self.window.SendKeys('{Enter}', waitTime=0.5)
            self.log("Keyboard fallback: waiting for chat transition.")
            time.sleep(1.0)
            return True
        except Exception as e:
            self.log(f"Keyboard fallback failed: {e}")
            return False

    def open_contact(self, name, uia_matches):
        if not self.window: return False
        
        normalized_name = name.lower().replace(" ", "")
        if uia_matches == ["ALREADY_ACTIVE"]:
            self.active_contact = normalized_name
            self.log(f"Active chat established: {name}")
            return True
        
        self.active_contact = None
        opened = False
        # Layer 1: Click the exact UIA match if it was detected
        if uia_matches:
            try:
                doc = self.window.DocumentControl(searchDepth=8)
                if doc.Exists(0.1, 1):
                    normalized_target = name.lower().replace(" ", "")
                    for c, d in auto.WalkControl(doc, maxDepth=10):
                        try:
                            if c.Name:
                                normalized_cname = c.Name.lower().replace(" ", "")
                                if normalized_target in normalized_cname:
                                    c.Click()
                                    time.sleep(0.5)
                                    self.log(f"Layer 1 (UIA): Clicked contact item '{c.Name}'.")
                                    opened = True
                                    break
                        except:
                            continue
            except Exception:
                pass

        # Determine if UIA was blind during search
        is_uia_blind = any("UIA blind" in msg for msg in self.diagnostic_log[-10:])
        
        # Layer 2: Keyboard 'Enter' to open top search result
        if not opened:
            opened = self._open_contact_keyboard_fallback(name, is_uia_blind)
                
        if opened:
            # Verification: Check if the contact name appears in the Window title or if call buttons exist
            verified = False
            
            # Check 1: Window Title
            try:
                if name.lower().replace(" ", "") in self.window.Name.lower().replace(" ", ""):
                    verified = True
                    self.log(f"Post-click verification: Window Title confirmed chat '{self.window.Name}'")
            except Exception:
                pass
                
            # Check 2: Call Buttons (if UIA works)
            if not verified:
                try:
                    v_btn = self.window.ButtonControl(searchDepth=12, Name="Voice call")
                    if v_btn.Exists(0.1, 1):
                        verified = True
                        self.log("Post-click verification: Call buttons detected via UIA.")
                except Exception:
                    pass
                    
            if not verified:
                if is_uia_blind:
                    self.log("Chat open assumed after successful blind WebView2 navigation.")
                elif uia_matches:
                    self.log("Post-click verification failed: UIA matches found but UI state didn't update.")
                    opened = False
                else:
                    self.log("Post-click verification failed: Chat did not open.")
                    opened = False
            else:
                self.log("Chat opened successfully.")
            
        if opened:
            self.active_contact = normalized_name
            self.log(f"Active chat established: {name}")
            
        return opened

    def _find_call_control(self, kind):
        """Find a WhatsApp call button even when WebView2 UIA names/search depth change."""
        if not self.window:
            return None

        if kind == "voice":
            candidates = ["Voice call", "Start voice call", "Audio call", "Start audio call", "Call"]
            terms = ("voice call", "start voice", "audio call")
        else:
            candidates = ["Video call", "Start video call", "Video"]
            terms = ("video call", "start video")

        for name in candidates:
            try:
                btn = self.window.ButtonControl(searchDepth=20, Name=name)
                if btn.Exists(0.2, 1):
                    return btn
            except Exception:
                continue

        try:
            for control, _depth in auto.WalkControl(self.window, maxDepth=20):
                try:
                    name = " ".join((control.Name or "").lower().split())
                    control_type = str(getattr(control, "ControlTypeName", "") or "").lower()
                    if not name or ("button" not in control_type and not hasattr(control, "Click")):
                        continue
                    if any(term in name for term in terms):
                        return control
                except Exception:
                    continue
        except Exception as e:
            self.log(f"Generic call-button scan failed: {e}")

        return None
    def check_call_buttons(self):
        """Diagnose whether WhatsApp exposes voice/video call controls in the active chat."""
        if not self.window:
            return False

        voice_btn = self._find_call_control("voice")
        video_btn = self._find_call_control("video")

        if voice_btn is not None or video_btn is not None:
            self.log("Call buttons detected in the active chat.")
            return True

        self.log("Call buttons not detected through UI Automation.")
        return False

    def _click_call_button(self, kind):
        """Click the requested call button using UIA first, then a geometry fallback."""
        button = self._find_call_control(kind)
        if button is not None:
            try:
                button.Click(waitTime=0.2)
                self.log(f"{kind.capitalize()} call button clicked via UI Automation.")
                return True
            except Exception as e:
                self.log(f"UIA {kind} call button click failed: {e}")

        # Last-resort geometry fallback. This is only used after the UIA search
        # cannot find a callable button.
        try:
            import pyautogui

            rect = self.window.BoundingRectangle
            width = rect.right - rect.left
            height = rect.bottom - rect.top

            if width < 500 or height < 400:
                self.log("WhatsApp window is too small for safe call-button positioning.")
                return False

            if kind == "voice":
                x_offset = VOICE_CALL_X_OFFSET
            else:
                x_offset = VIDEO_CALL_X_OFFSET

            # Current WhatsApp desktop places the call controls near the
            # upper-right area of the active-chat header.
            click_x = rect.right - x_offset
            click_y = rect.top + CALL_BUTTON_Y_OFFSET

            self.window.SetActive()
            time.sleep(0.3)
            pyautogui.click(click_x, click_y)
            self.log(
                f"{kind.capitalize()} call button clicked using spatial fallback "
                f"at ({click_x}, {click_y})."
            )
            return True
        except Exception as e:
            self.log(f"Spatial {kind} call-button click failed: {e}")
            return False

    def _verify_call_state(self, wait_seconds=3.0):
        """Wait briefly and verify that WhatsApp entered an outgoing/in-call UI."""
        self.log(f"Waiting {wait_seconds:.1f}s for WhatsApp call UI...")
        deadline = time.time() + wait_seconds

        while time.time() < deadline:
            state = self.get_call_state()
            if state == "CONNECTED":
                self.log("Call UI detected: WhatsApp is in an active/outgoing call state.")
                return "SUCCESS_VERIFIED"
            time.sleep(0.5)

        self.log("Call click completed, but no active/outgoing call UI was detected.")
        return "SUCCESS_UNVERIFIED"

    def start_voice_call(self, name):
        if not self.window:
            return False

        if not self._ensure_active_chat(name):
            self.log(f"Cannot start voice call: active chat is not confirmed for {name}.")
            return False

        self.log(f"Starting WhatsApp voice call to {name}.")
        time.sleep(1.0)

        if self._click_call_button("voice"):
            return self._verify_call_state()

        self.log(f"Voice call could not be started for {name}.")
        return False

    def start_video_call(self, name):
        if not self.window:
            return False

        if not self._ensure_active_chat(name):
            self.log(f"Cannot start video call: active chat is not confirmed for {name}.")
            return False

        self.log(f"Starting WhatsApp video call to {name}.")
        time.sleep(1.0)

        if self._click_call_button("video"):
            return self._verify_call_state()

        self.log(f"Video call could not be started for {name}.")
        return False

    def end_call(self):
        if not self.window: return False
        btn = self.window.ButtonControl(searchDepth=12, Name="End call")
        if btn.Exists(1, 1):
            btn.Click()
            return True
        return False

    def answer_call(self):
        if not self.window: return False
        btn = self.window.ButtonControl(searchDepth=12, Name="Accept")
        if btn.Exists(1, 1):
            btn.Click()
            return True
        return False

    def reject_call(self):
        if not self.window: return False
        btn = self.window.ButtonControl(searchDepth=12, Name="Decline")
        if btn.Exists(1, 1):
            btn.Click()
            return True
        return False

    def get_call_state(self):
        if not self.window:
            return "UNKNOWN"

        try:
            end_btn = self.window.ButtonControl(searchDepth=20, Name="End call")
            if end_btn.Exists(0.5, 1):
                return "CONNECTED"
        except Exception:
            pass

        try:
            accept_btn = self.window.ButtonControl(searchDepth=20, Name="Accept")
            if accept_btn.Exists(0.5, 1):
                return "INCOMING_CALL"
        except Exception:
            pass

        try:
            for control, _depth in auto.WalkControl(self.window, maxDepth=20):
                try:
                    name = " ".join((control.Name or "").lower().split())
                    if "end call" in name or "hang up" in name:
                        return "CONNECTED"
                    if name in {"accept", "answer"} or "answer call" in name:
                        return "INCOMING_CALL"
                except Exception:
                    continue
        except Exception:
            pass

        return "UNKNOWN"


PLUGIN = {
    "name": "whatsapp_desktop_call",
    "description": (
        "Controls WhatsApp Desktop calling features. "
        "Use this tool when the user asks to call someone on WhatsApp, answer a call, or end a call."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "intent": {
                "type": "STRING", 
                "description": "The specific intent (e.g., 'voice_call', 'video_call', 'end_call', 'answer_call', 'reject_call', 'status', 'whatsapp_search_test')."
            },
            "contact_name": {
                "type": "STRING",
                "description": "The name of the contact to call, if applicable."
            }
        },
        "required": ["intent"],
    },
}

def extract_contact_name(text):
    patterns = [
        r"call\s+(.+?)\s+on\s+whatsapp",
        r"whatsapp\s+video\s+call\s+to\s+(.+)",
        r"whatsapp\s+video\s+call\s+(.+)",
        r"whatsapp\s+call\s+(.+)",
        r"whatsapp\s+la\s+(.+?)\s*ku\s+call",
        r"whatsapp\s+search\s+(.+)",
        r"search\s+(.+?)\s+on\s+whatsapp",
        r"call\s+(.+)"
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            name = re.sub(r'(?i)\bpannu\b', '', name).strip()
            name = re.sub(r'(?i)\bplease\b', '', name).strip()
            if name: return name
    return None


def run(parameters: dict, player=None, session_memory=None) -> str:
    raw_intent = parameters.get("intent", "").lower().strip()
    contact_name = parameters.get("contact_name", "").strip()

    controller = WhatsAppDesktopController()
    
    if not contact_name and ("call" in raw_intent or "search" in raw_intent):
        contact_name = extract_contact_name(raw_intent) or ""
        
    if "whatsapp_search_test" in raw_intent or "search" in raw_intent:
        logical_intent = "whatsapp_search_test"
    elif "end" in raw_intent or "cut" in raw_intent or "hang" in raw_intent:
        logical_intent = "end_call"
    elif "answer" in raw_intent or "attend" in raw_intent or "accept" in raw_intent:
        logical_intent = "answer_call"
    elif "reject" in raw_intent or "decline" in raw_intent:
        logical_intent = "reject_call"
    elif "video" in raw_intent:
        logical_intent = "video_call"
    elif "voice" in raw_intent or "call" in raw_intent:
        logical_intent = "voice_call"
    elif "status" in raw_intent:
        logical_intent = "status"
    else:
        return "Error: Ambiguous WhatsApp command."

    if not controller.is_whatsapp_running():
        return "Error: WhatsApp Desktop is not running."

    if logical_intent == "status":
        state = controller.get_call_state()
        return f"WhatsApp Call State: {state}"

    if logical_intent in ["end_call", "answer_call", "reject_call"]:
        if logical_intent == "end_call":
            success = controller.end_call()
        elif logical_intent == "answer_call":
            success = controller.answer_call()
        elif logical_intent == "reject_call":
            success = controller.reject_call()
            
        if success:
            return f"Successfully executed {logical_intent}."
        else:
            return f"Failed to {logical_intent}. UI elements not found."

    if not contact_name:
        return "Error: Contact name not specified."

    if player and logical_intent != "whatsapp_search_test":
        try:
            player.write_log(f"JARVIS: Searching WhatsApp for '{contact_name}'...")
        except:
            pass

    matches = controller.search_contact(contact_name)
    
    if logical_intent == "whatsapp_search_test":
        controller.open_contact(contact_name, matches)
        controller.check_call_buttons()
        log_output = "\n".join(controller.diagnostic_log)
        return f"--- WhatsApp Diagnostic Search Test Completed ---\nLog Trace:\n{log_output}\n\nSearch complete, no call initiated."
            
    # For actual calls, we handle multiple matches if UIA is NOT blind
    if len(matches) > 1:
        return f"Multiple contacts found for '{contact_name}'. Matches: {matches}. Please be more specific."
    elif len(matches) == 0 and len(controller.diagnostic_log) > 0 and "UIA blind" not in controller.diagnostic_log[-1]:
        # If UIA works and found nothing
        return f"Contact '{contact_name}' not found on WhatsApp Desktop."

    if player:
        try:
            player.write_log(f"JARVIS: Calling {contact_name} on WhatsApp.")
        except:
            pass
            
    success_open = controller.open_contact(contact_name, matches)
    if not success_open:
        log_output = "\n".join(controller.diagnostic_log)
        return f"Failed to open chat for {contact_name}.\nLogs:\n{log_output}"

    if logical_intent == "video_call":
        success_call = controller.start_video_call(contact_name)
    else:
        success_call = controller.start_voice_call(contact_name)
        
    log_output = "\n".join(controller.diagnostic_log)
    
    if success_call == "SUCCESS_VERIFIED":
        return f"Successfully initiated {logical_intent} to {contact_name}.\nLogs:\n{log_output}"
    elif success_call == "SUCCESS_UNVERIFIED":
        return f"{logical_intent.replace('_', ' ').capitalize()} button click executed; call state could not be independently verified.\nLogs:\n{log_output}"
    else:
        return f"Failed to click the call button for {contact_name}. UI elements not found.\nLogs:\n{log_output}"

