import threading
import time
import asyncio
import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# Add core actions to path so we can reuse built-in send_message
_BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(_BASE_DIR))
try:
    from actions.send_message import _send_whatsapp
except ImportError:
    _send_whatsapp = None

# Try importing winsdk for native Windows Notification reading
try:
    from winsdk.windows.ui.notifications.management import UserNotificationListener
    from winsdk.windows.ui.notifications import NotificationKinds
    _WINSDK_AVAILABLE = True
except ImportError:
    _WINSDK_AVAILABLE = False


PLUGIN = {
    "name": "whatsapp_monitor",
    "description": (
        "Check what WhatsApp replies or incoming messages have arrived, check message history, "
        "or turn the WhatsApp background monitor/auto-responder on or off. "
        "Use this tool whenever the user asks 'check what replies came', 'did Sabari reply?', "
        "'what did they say on WhatsApp?', 'any new messages on WhatsApp', 'check WhatsApp messages', "
        "or to start/stop WhatsApp background monitoring."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "Action to perform: "
                    "'check' (default) to check current and recent replies/messages, "
                    "'history' to view recent message logs, "
                    "'on' or 'start' to start background monitoring, "
                    "'off' or 'stop' to stop background monitoring, "
                    "'clear' to clear recent message history."
                ),
            },
            "sender": {
                "type": "STRING",
                "description": "Optional contact name to filter replies for (e.g., 'sabari')."
            },
            "status": {
                "type": "STRING",
                "description": "Legacy parameter: 'on' or 'off' (maps to action='on' or 'off')."
            },
            "auto_reply": {
                "type": "BOOLEAN",
                "description": (
                    "If true when starting background monitoring, Jarvis will automatically "
                    "generate and send AI replies. Default is false (listen and alert user only)."
                ),
            },
        },
    },
}

_monitor_thread = None
_monitoring_active = False
_replied_notification_ids = set()
_history_lock = threading.Lock()
_HISTORY_FILE = _BASE_DIR / "memory" / "whatsapp_replies.json"


def _get_user_name() -> str:
    try:
        config_path = _BASE_DIR / "config" / "api_keys.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("user_name", "Sir").strip() or "Sir"
    except Exception:
        pass
    return "Sir"


def _load_replies_history() -> list[dict]:
    with _history_lock:
        if not _HISTORY_FILE.exists():
            return []
        try:
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"[WhatsApp Monitor] Error loading history: {e}")
            return []


def _save_replies_history(records: list[dict]):
    with _history_lock:
        try:
            _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(records[-50:], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[WhatsApp Monitor] Error saving history: {e}")


def _record_incoming_message(
    sender: str,
    message: str,
    notif_id=None,
    time_str: str = None,
    auto_replied: bool = False,
    reply_text: str = None,
) -> dict:
    records = _load_replies_history()
    now = datetime.now()
    if not time_str:
        time_str = now.strftime("%I:%M %p")

    # Check if this exact message is already in recent records (deduplication)
    for r in reversed(records[-10:]):
        if r.get("sender", "").lower() == sender.lower() and r.get("message", "") == message:
            return r

    entry = {
        "id": str(notif_id) if notif_id is not None else str(int(time.time() * 1000)),
        "sender": sender,
        "message": message,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "time_str": time_str,
        "auto_replied": auto_replied,
        "reply_text": reply_text,
    }
    records.append(entry)
    _save_replies_history(records)
    return entry


def _generate_dynamic_reply(sender: str, message: str) -> str:
    user_name = _get_user_name()
    if not _GENAI_AVAILABLE:
        return f"Hello, I am Jarvis, {user_name}'s AI assistant. He is currently occupied. I will inform him of your message."

    try:
        config_path = _BASE_DIR / "config" / "api_keys.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        api_key = cfg.get("gemini_api_key")

        if not api_key:
            raise ValueError("No Gemini API Key found.")

        client = genai.Client(api_key=api_key)

        prompt = (
            f"You are Jarvis, {user_name}'s personal AI assistant. {user_name} is currently busy. "
            f"You received a WhatsApp message from '{sender}' which says: '{message}'. "
            f"Write a short, natural, and polite reply on {user_name}'s behalf. "
            f"Acknowledge what they said. If it is an important update or question, "
            f"let them know you will convey it to {user_name} immediately. "
            f"Keep it under 2 sentences. Reply directly as Jarvis."
        )

        # Try gemini-3.8-flash first, fallback to gemini-2.0-flash
        for model_name in ('gemini-3.8-flash', 'gemini-2.0-flash'):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as model_err:
                print(f"[WhatsApp Monitor] Model {model_name} failed: {model_err}")
                continue

        return f"Hello, I am Jarvis. {user_name} is currently occupied, but I have noted your message and will convey it to him."
    except Exception as e:
        print(f"[WhatsApp Monitor] AI generation failed: {e}")
        return f"Hello, I am Jarvis. {user_name} is currently busy, but I will convey your message to him."


async def _get_whatsapp_notifications_async() -> list[dict]:
    if not _WINSDK_AVAILABLE:
        return []

    try:
        listener = UserNotificationListener.current
        access = await listener.request_access_async()
        if access != 1:  # 1 == Allowed
            print("[WhatsApp Monitor] Windows Notification access denied by user/system.")
            return []

        notifs = await listener.get_notifications_async(NotificationKinds.TOAST)
        results = []

        for n in notifs:
            try:
                app_info = n.app_info
                display_name = (app_info.display_info.display_name or "") if (app_info and app_info.display_info) else ""
                app_id = getattr(app_info, "id", "") or ""
                aumid = getattr(app_info, "app_user_model_id", "") or ""

                is_wa = any("whatsapp" in x.lower() for x in (display_name, app_id, aumid))
                if not is_wa:
                    continue

                bindings = n.notification.visual.bindings
                texts = []
                for b in bindings:
                    for t in b.get_text_elements():
                        val = (t.text or "").strip()
                        if val:
                            texts.append(val)

                if texts:
                    if len(texts) == 1:
                        sender = "WhatsApp"
                        msg = texts[0]
                    else:
                        sender = texts[0]
                        msg = " \n".join(texts[1:])

                    # Format creation time if available
                    creation_time = getattr(n, "creation_time", None)
                    time_str = ""
                    if creation_time:
                        try:
                            # Convert to local time string
                            local_dt = creation_time.astimezone() if hasattr(creation_time, "astimezone") else creation_time
                            time_str = local_dt.strftime("%I:%M %p")
                        except Exception:
                            time_str = ""

                    results.append({
                        "id": n.id,
                        "sender": sender,
                        "message": msg,
                        "time_str": time_str,
                    })
            except Exception:
                pass

        return results
    except Exception as e:
        print(f"[WhatsApp Monitor] Error reading toast notifications: {e}")
        return []


def _get_whatsapp_notifications() -> list[dict]:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        notifs = loop.run_until_complete(_get_whatsapp_notifications_async())
        loop.close()
        return notifs
    except Exception as e:
        print(f"[WhatsApp Monitor] Event loop error: {e}")
        return []


def _check_replies(sender_filter: str = None, player=None) -> str:
    """
    Check for current notifications and recent history of incoming WhatsApp replies.
    Optionally filters by sender contact name (e.g. 'sabari').
    """
    # 1. Fetch live Windows notifications
    live_notifs = _get_whatsapp_notifications()
    for notif in live_notifs:
        _record_incoming_message(
            sender=notif["sender"],
            message=notif["message"],
            notif_id=notif["id"],
            time_str=notif.get("time_str"),
        )

    # 2. Load unified history
    all_replies = _load_replies_history()

    # Filter by sender if requested
    target_sender = (sender_filter or "").strip().lower()
    if target_sender:
        matched = [
            r for r in all_replies
            if target_sender in r.get("sender", "").lower() or r.get("sender", "").lower() in target_sender
        ]
        if matched:
            # Latest messages first
            matched_sorted = sorted(matched, key=lambda x: x.get("timestamp", ""), reverse=True)
            latest = matched_sorted[0]
            actual_sender = latest.get("sender", sender_filter)
            msg_text = latest.get("message", "")
            msg_time = latest.get("time_str") or "recently"

            if len(matched_sorted) == 1:
                res = f"Sir, {actual_sender} replied: \"{msg_text}\" at {msg_time}."
            else:
                lines = [f"Sir, here are the recent replies from {actual_sender}:"]
                for i, m in enumerate(matched_sorted[:3], 1):
                    t = m.get("time_str") or "recently"
                    lines.append(f"{i}. \"{m.get('message')}\" ({t})")
                res = "\n".join(lines)

            if latest.get("auto_replied") and latest.get("reply_text"):
                res += f"\n(Auto-replied: \"{latest.get('reply_text')}\")"

            if player:
                player.write_log(f"JARVIS: 📨 {res}")
            return res
        else:
            return f"Sir, I checked WhatsApp, but no new replies have arrived from {sender_filter} yet."

    # If no sender specified, return all recent replies
    if all_replies:
        recent = sorted(all_replies, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]
        lines = ["Sir, here are the recent incoming WhatsApp messages:"]
        for i, r in enumerate(recent, 1):
            s = r.get("sender", "Unknown")
            m = r.get("message", "")
            t = r.get("time_str") or "recently"
            lines.append(f"{i}. {s}: \"{m}\" ({t})")
        res = "\n".join(lines)
        if player:
            player.write_log(f"JARVIS: 📨 Checked WhatsApp: {len(recent)} recent reply/replies found.")
        return res

    return "Sir, I checked WhatsApp notifications and recent logs, but there are no new replies or messages."


def _whatsapp_monitor_loop(player, auto_reply: bool = False):
    global _monitoring_active, _replied_notification_ids

    mode_label = "Auto-Reply ON" if auto_reply else "Alerts Only"
    print(f"[WhatsApp Monitor] Background thread started ({mode_label}).")

    if player:
        try:
            player.write_log(f"JARVIS: WhatsApp monitor active ({mode_label}).")
        except Exception:
            pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while _monitoring_active:
        if _WINSDK_AVAILABLE:
            try:
                notifications = loop.run_until_complete(_get_whatsapp_notifications_async())

                for notif in notifications:
                    notif_id = notif["id"]
                    sender = notif["sender"]
                    message = notif["message"]
                    time_str = notif.get("time_str")

                    if notif_id not in _replied_notification_ids:
                        _replied_notification_ids.add(notif_id)
                        user_name = _get_user_name()
                        print(f"[WhatsApp Monitor] New message from {sender}: {message}")

                        if auto_reply and _send_whatsapp:
                            # 1. Generate Smart Reply
                            reply_text = _generate_dynamic_reply(sender, message)

                            # 2. Open WhatsApp and send
                            _send_whatsapp(sender, reply_text)

                            # 3. Record in history
                            _record_incoming_message(
                                sender=sender,
                                message=message,
                                notif_id=notif_id,
                                time_str=time_str,
                                auto_replied=True,
                                reply_text=reply_text,
                            )

                            # 4. WhatsApp is automatically closed by _send_whatsapp.
                            # Fallback: close WhatsApp window via Win32 WM_CLOSE (no cursor needed).
                            try:
                                import ctypes
                                import psutil
                                time.sleep(0.3)
                                WM_CLOSE = 0x0010
                                user32 = ctypes.windll.user32
                                for proc in psutil.process_iter(["pid", "name"]):
                                    try:
                                        if "whatsapp" in (proc.info.get("name") or "").lower():
                                            hwnd = user32.FindWindowExW(0, 0, None, None)
                                            # Post WM_CLOSE to all visible WhatsApp top-level windows
                                            def _close_cb(h, _):
                                                pid = ctypes.c_ulong()
                                                user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
                                                if pid.value == proc.info["pid"] and user32.IsWindowVisible(h):
                                                    user32.PostMessageW(h, WM_CLOSE, 0, 0)
                                                return True
                                            EnumCB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                                            user32.EnumWindows(EnumCB(_close_cb), 0)
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                            # 5. Notify user via UI
                            alert_msg = f"Sir, '{sender}' messaged: '{message}'. I auto-replied: '{reply_text}'"
                            if player:
                                player.write_log(f"JARVIS: 📨 {alert_msg}")
                                if hasattr(player, 'on_text_command') and callable(player.on_text_command):
                                    user_name = _get_user_name()
                                    internal_memory = (
                                        f"[SYSTEM_ALERT] Automatically replied to WhatsApp message from {sender}: '{message}' with '{reply_text}'. "
                                        f"Keep this in memory for {user_name}."
                                    )
                                    try:
                                        player.on_text_command(internal_memory)
                                    except Exception:
                                        pass
                        else:
                            # Listen and Notify mode (No auto-send)
                            _record_incoming_message(
                                sender=sender,
                                message=message,
                                notif_id=notif_id,
                                time_str=time_str,
                                auto_replied=False,
                            )

                            alert_msg = f"Sir, '{sender}' sent you a WhatsApp message: '{message}'"
                            if player:
                                player.write_log(f"JARVIS: 📨 {alert_msg}")
                                # If Live session audio or proactive announcement is supported
                                if hasattr(player, 'request_say') and callable(player.request_say):
                                    try:
                                        player.request_say(alert_msg)
                                    except Exception:
                                        pass
                                elif hasattr(player, 'on_text_command') and callable(player.on_text_command):
                                    try:
                                        player.on_text_command(f"[SYSTEM_ALERT] New WhatsApp message from {sender}: '{message}'. Inform {user_name} naturally.")
                                    except Exception:
                                        pass

            except Exception as e:
                print(f"[WhatsApp Monitor] Error processing notifications: {e}")
        else:
            time.sleep(5)

        time.sleep(3)

    loop.close()
    print("[WhatsApp Monitor] Background thread stopped.")


def run(parameters: dict, player=None, session_memory=None) -> str:
    global _monitor_thread, _monitoring_active

    params = parameters or {}
    action = params.get("action", "").lower().strip()
    status = params.get("status", "").lower().strip()
    sender = params.get("sender", "").strip()
    auto_reply = bool(params.get("auto_reply", False))

    # Normalize action / status
    if not action and status:
        action = status

    # 1. Start monitoring
    if action in ("on", "start", "enable"):
        if _monitoring_active:
            return "WhatsApp monitor is already active."

        _monitoring_active = True
        _monitor_thread = threading.Thread(
            target=_whatsapp_monitor_loop,
            args=(player, auto_reply),
            daemon=True
        )
        _monitor_thread.start()

        missing = []
        if not _WINSDK_AVAILABLE:
            missing.append("winsdk")
        if auto_reply and not _GENAI_AVAILABLE:
            missing.append("google-genai")

        mode = "auto-reply enabled" if auto_reply else "listening and notification mode"
        if missing:
            return f"WhatsApp monitoring started in {mode}, but missing: {', '.join(missing)}."

        return f"WhatsApp monitoring enabled ({mode}). I will watch for incoming messages."

    # 2. Stop monitoring
    elif action in ("off", "stop", "disable"):
        if not _monitoring_active:
            return "WhatsApp monitoring is currently off."

        _monitoring_active = False
        return "I have stopped monitoring WhatsApp."

    # 3. View history
    elif action in ("history", "log", "logs"):
        records = _load_replies_history()
        if not records:
            return "No recorded WhatsApp messages in history."
        lines = ["Recent WhatsApp message history:"]
        for r in records[-8:]:
            ar = " [Auto-replied]" if r.get("auto_replied") else ""
            lines.append(f"- {r.get('sender')}: \"{r.get('message')}\" ({r.get('time_str', '')}){ar}")
        return "\n".join(lines)

    # 4. Clear history
    elif action in ("clear", "reset"):
        _save_replies_history([])
        return "WhatsApp message history has been cleared."

    # 5. Default / 'check' / 'read' -> Check what replies came
    return _check_replies(sender_filter=sender, player=player)
