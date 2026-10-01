"""
core/telegram_bot.py — JARVIS Telegram Remote Phone Bridge

Allows remote 2-way control of JARVIS from anywhere in the world via Telegram.
Works on cellular data (4G/5G) and any Wi-Fi network without requiring local port forwarding.

To enable:
Add to config/api_keys.json:
{
    "telegram_bot_token": "YOUR_BOT_TOKEN_FROM_BOTFATHER",
    "telegram_chat_id": ""   (optional: auto-detected upon first /start from your phone)
}
"""

import asyncio
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


def _load_telegram_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "token": data.get("telegram_bot_token", "").strip(),
                "chat_id": str(data.get("telegram_chat_id", "")).strip(),
                "assistant_name": data.get("assistant_name", "JARVIS"),
            }
    except Exception:
        return {}


def _save_chat_id(chat_id: str) -> None:
    try:
        data = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["telegram_chat_id"] = str(chat_id)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"[Telegram] Auto-registered chat_id {chat_id} in config.")
    except Exception as e:
        print(f"[Telegram] Failed to save chat_id: {e}")


class TelegramBotBridge:
    def __init__(self, command_queue: asyncio.Queue, logger=None):
        self.queue = command_queue
        self.logger = logger or print
        self._cfg = _load_telegram_config()
        self.token = self._cfg.get("token", "")
        self.chat_id = self._cfg.get("chat_id", "")
        self.asst_name = self._cfg.get("assistant_name", "JARVIS")
        self._offset = 0
        self._active = bool(self.token)

    def is_configured(self) -> bool:
        return bool(self.token)

    async def send_message(self, text: str, chat_id: str = "") -> bool:
        cid = chat_id or self.chat_id
        if not self.token or not cid:
            return False
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": cid,
            "text": text,
            "parse_mode": "Markdown",
        }).encode("utf-8")

        def _do():
            req = urllib.request.Request(url, data=payload, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200

        try:
            return await asyncio.to_thread(_do)
        except Exception as e:
            # Fallback without markdown if parse error
            try:
                payload_plain = urllib.parse.urlencode({
                    "chat_id": cid,
                    "text": text,
                }).encode("utf-8")
                return await asyncio.to_thread(
                    lambda: urllib.request.urlopen(
                        urllib.request.Request(url, data=payload_plain, method="POST"),
                        timeout=10
                    ).status == 200
                )
            except Exception:
                return False

    async def send_photo(self, photo_bytes: bytes, caption: str = "", chat_id: str = "") -> bool:
        cid = chat_id or self.chat_id
        if not self.token or not cid:
            return False

        boundary = "----JARVISFormBoundary" + str(int(time.time()))
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"

        body = bytearray()
        # chat_id
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{cid}\r\n'.encode())
        # caption
        if caption:
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode())
        # photo file
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="photo"; filename="screenshot.jpg"\r\n'.encode())
        body.extend(b'Content-Type: image/jpeg\r\n\r\n')
        body.extend(photo_bytes)
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        def _do():
            req = urllib.request.Request(
                url,
                data=bytes(body),
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status == 200

        try:
            return await asyncio.to_thread(_do)
        except Exception as e:
            print(f"[Telegram] Failed to send photo: {e}")
            return False

    async def _handle_command(self, text: str, cid: str) -> None:
        cmd = text.strip()
        cmd_lower = cmd.lower()

        if cmd_lower in ("/start", "/help"):
            msg = (
                f"🤖 *{self.asst_name} Mobile Bridge Online*\n\n"
                "Your phone is linked to your desktop assistant!\n\n"
                "*Available Controls:*\n"
                "• Type *any request* (e.g. _open youtube_, _check weather_, _flight to paris_)\n"
                "• `/status` — View CPU, RAM, GPU, and system performance\n"
                "• `/screen` — Receive an instant screenshot of your PC\n"
                "• `/lock` — Lock your PC workstation\n"
                "• `/vol <level>` — Set system volume (e.g. `/vol 50`)\n"
                "• Send photos/files — Saves them to your PC uploads folder"
            )
            await self.send_message(msg, cid)

        elif cmd_lower in ("/status", "status", "system status"):
            try:
                from actions.system_monitor import get_system_status
                stats = await asyncio.to_thread(get_system_status)
                reply = (
                    f"🖥️ *Desktop Telemetry ({self.asst_name})*\n\n"
                    f"• *CPU:* {stats.get('cpu_percent', 'N/A')}%\n"
                    f"• *RAM:* {stats.get('ram_percent', 'N/A')}% ({stats.get('ram_used_gb', 0):.1f}/{stats.get('ram_total_gb', 0):.1f} GB)\n"
                    f"• *Uptime:* {stats.get('uptime', 'N/A')}\n"
                    f"• *Processes:* {stats.get('process_count', 'N/A')}"
                )
                await self.send_message(reply, cid)
            except Exception as e:
                await self.send_message(f"⚠️ Failed to retrieve status: {e}", cid)

        elif cmd_lower in ("/screen", "screenshot", "/screenshot"):
            try:
                import mss
                import mss.tools
                from PIL import Image

                def _capture():
                    with mss.mss() as sct:
                        mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                        sct_img = sct.grab(mon)
                        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                        # resize slightly for faster transmission if large
                        if img.width > 1920:
                            img.thumbnail((1920, 1080))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=80)
                        return buf.getvalue()

                raw = await asyncio.to_thread(_capture)
                await self.send_photo(raw, caption=f"📸 PC Screen at {time.strftime('%H:%M:%S')}", chat_id=cid)
            except Exception as e:
                await self.send_message(f"⚠️ Screenshot capture failed: {e}", cid)

        elif cmd_lower in ("/lock", "lock pc", "lock computer"):
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                await self.send_message("🔒 Computer workstation locked, Sir.", cid)
            except Exception as e:
                await self.send_message(f"⚠️ Could not lock PC: {e}", cid)

        elif cmd_lower.startswith("/vol"):
            parts = cmd.split()
            if len(parts) > 1 and parts[1].isdigit():
                val = int(parts[1])
                await self.queue.put(f"set computer volume to {val}")
                await self.send_message(f"🔊 Setting volume to {val}%...", cid)
            else:
                await self.send_message("Usage: `/vol 50` (0-100)", cid)

        else:
            # Forward text directly to JARVIS session command queue
            await self.queue.put(cmd)
            await self.send_message(f"⚡ Command sent to {self.asst_name}: \"{cmd}\"", cid)

    async def start(self) -> None:
        if not self._active:
            print("[Telegram] Inactive (Optional: configure 'telegram_bot_token' in config/api_keys.json to chat from anywhere).")
            return

        print(f"[Telegram] Bot bridge starting for {self.asst_name}...")
        while True:
            try:
                url = f"https://api.telegram.org/bot{self.token}/getUpdates?offset={self._offset}&timeout=20"
                
                def _fetch():
                    req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-Assistant"})
                    with urllib.request.urlopen(req, timeout=30) as r:
                        return json.loads(r.read().decode("utf-8"))

                data = await asyncio.to_thread(_fetch)
                if data.get("ok"):
                    for item in data.get("result", []):
                        self._offset = max(self._offset, item["update_id"] + 1)
                        msg = item.get("message") or item.get("channel_post")
                        if not msg:
                            continue
                        
                        sender_id = str(msg.get("chat", {}).get("id", ""))
                        # Auto-pair first user if chat_id not configured
                        if not self.chat_id:
                            self.chat_id = sender_id
                            _save_chat_id(sender_id)

                        # Only process from authorized chat
                        if self.chat_id and sender_id != self.chat_id:
                            continue

                        text = msg.get("text", "")
                        if text:
                            asyncio.create_task(self._handle_command(text, sender_id))

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Network glitch or timeout, back off briefly
                await asyncio.sleep(4)
