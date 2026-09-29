"""JARVIS Phase 1: read-only system diagnostics for the HUD."""

from __future__ import annotations

import platform
import time
from datetime import timedelta

import psutil


PLUGIN = {
    "name": "system_diagnostics",
    "description": (
        "Runs a read-only system diagnostic and reports current CPU, memory, disk, "
        "battery, uptime, and process information. Use for requests such as "
        "'run system diagnostics', 'check system health', or 'how is my PC doing'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
        "required": [],
    },
}


def _fmt_bytes(value: int) -> str:
    return f"{value / (1024 ** 3):.1f} GB"


def run(parameters: dict, player=None, session_memory=None) -> str:
    """Collect a safe read-only snapshot and optionally display it in the HUD."""
    try:
        cpu = psutil.cpu_percent(interval=0.25)
        memory = psutil.virtual_memory()
        disk_root = "C:\\" if platform.system() == "Windows" else "/"
        disk = psutil.disk_usage(disk_root)
        battery = psutil.sensors_battery()
        uptime = str(timedelta(seconds=max(0, int(time.time() - psutil.boot_time()))))
        process_count = len(psutil.pids())

        rows = [
            "JARVIS // SYSTEM DIAGNOSTICS",
            "────────────────────────────",
            f"CPU LOAD       {cpu:.0f}%",
            f"MEMORY         {memory.percent:.0f}%  ({_fmt_bytes(memory.used)} / {_fmt_bytes(memory.total)})",
            f"DISK ({disk_root})      {disk.percent:.0f}%  ({_fmt_bytes(disk.free)} free)",
            f"UPTIME         {uptime}",
            f"ACTIVE PROCESSES  {process_count}",
        ]
        if battery is not None:
            power = f"{battery.percent:.0f}%"
            if battery.power_plugged is True:
                power += " • AC connected"
            elif battery.power_plugged is False:
                power += " • on battery"
            rows.append(f"BATTERY        {power}")
        else:
            rows.append("BATTERY        Not available")

        report = "\n".join(rows)
        if player:
            try:
                player.show_content("SYSTEM DIAGNOSTICS", report)
                player.write_log("SYS: System diagnostics completed.")
            except Exception:
                pass
        return report
    except Exception as exc:
        return f"Sir, system diagnostics could not complete: {exc}"
