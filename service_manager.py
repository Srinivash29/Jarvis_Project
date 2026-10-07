"""
service_manager.py — Control utility for JARVIS 24/7 Mobile Background Service.

Commands:
    python service_manager.py start      - Start mobile service in background (headless)
    python service_manager.py stop       - Stop mobile service
    python service_manager.py status     - Show status of mobile service & JARVIS engine
    python service_manager.py restart    - Restart mobile service
    python service_manager.py install    - Enable auto-start on Windows boot (Startup folder)
    python service_manager.py uninstall  - Disable auto-start on Windows boot
"""

import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / "config" / "jarvis_service.pid"
SERVICE_PY = BASE_DIR / "jarvis_service.py"

def _get_pythonw() -> Path:
    """Find pythonw.exe to run without a console window."""
    venv_pyw = BASE_DIR / ".venv" / "Scripts" / "pythonw.exe"
    if venv_pyw.exists():
        return venv_pyw
    py_dir = Path(sys.executable).parent
    pythonw = py_dir / "pythonw.exe"
    if pythonw.exists():
        return pythonw
    return Path(sys.executable)

def _get_startup_file() -> Path | None:
    """Return path to Windows Startup folder runner if on Windows."""
    if sys.platform != "win32":
        return None
    startup_dir = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
    if startup_dir.exists():
        return startup_dir / "JARVIS_Mobile_Service.vbs"
    return None

def is_service_running() -> bool:
    """Check if the daemon is currently running on port 8000."""
    try:
        from dashboard.server import is_daemon_running
        return is_daemon_running()
    except Exception:
        return False

def get_service_pid() -> int | None:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
            import psutil
            if psutil.pid_exists(pid):
                return pid
        except Exception:
            pass
    return None

def is_jarvis_app_running() -> bool:
    """Check if main.py is running."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any("main.py" in str(arg) for arg in cmdline):
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False

def start():
    print("[*] Checking JARVIS Mobile Background Service...")
    if is_service_running():
        print("[+] Service is ALREADY RUNNING on port 8000.")
        status()
        return

    pythonw = _get_pythonw()
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    proc = subprocess.Popen(
        [str(pythonw), str(SERVICE_PY)],
        cwd=str(BASE_DIR),
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )

    print(f"[*] Starting service via {pythonw.name}...")
    for _ in range(15):
        time.sleep(0.4)
        if is_service_running():
            print(f"[+] SUCCESS: JARVIS Mobile Service is RUNNING in background (PID: {proc.pid}).")
            status()
            return

    print("[!] Service launched, checking status...")
    status()

def stop():
    print("[*] Stopping JARVIS Mobile Service...")
    stopped = False

    pid = get_service_pid()
    if pid:
        try:
            import psutil
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=3)
            stopped = True
        except Exception:
            pass

    # Also check any python processes running jarvis_service.py
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if any("jarvis_service.py" in str(arg) for arg in cmdline):
                    proc.terminate()
                    stopped = True
            except Exception:
                continue
    except Exception:
        pass

    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass

    if stopped:
        print("[+] JARVIS Mobile Service stopped.")
    else:
        print("[-] Service was not running.")

def status():
    from dashboard.server import _local_ip, PORT
    ip = _local_ip()
    srv_ok = is_service_running()
    app_ok = is_jarvis_app_running()
    pid = get_service_pid()

    print("\n" + "=" * 55)
    print("        JARVIS SYSTEM & MOBILE ACCESS STATUS")
    print("=" * 55)
    print(f"  Mobile Service (Port {PORT}) : {'[ONLINE]' if srv_ok else '[OFFLINE]'}")
    if srv_ok and pid:
        print(f"  Service Process PID        : {pid}")
    print(f"  JARVIS Desktop Voice App   : {'[ONLINE]' if app_ok else '[STANDBY / OFFLINE]'}")
    print(f"  Phone Browser URL          : http://{ip}:{PORT}")
    print(f"  Phone Audio / HTTPS        : https://{ip}:{PORT + 1}")
    print("=" * 55)
    if srv_ok:
        if app_ok:
            print("  State: Full voice agent active. Connected phones talk to JARVIS.")
        else:
            print("  State: Standby Mode. Phone can execute PC actions & launch JARVIS.")
    else:
        print("  Tip: Run 'python service_manager.py start' for 24/7 phone access.")
    print("=" * 55 + "\n")

def install_startup():
    startup_file = _get_startup_file()
    if not startup_file:
        print("[-] Auto-start installation is currently supported on Windows.")
        return

    pythonw = _get_pythonw()
    vbs_content = (
        f'Set WshShell = CreateObject("WScript.Shell")\r\n'
        f'WshShell.CurrentDirectory = "{BASE_DIR}"\r\n'
        f'WshShell.Run """{pythonw}"" ""{SERVICE_PY}""", 0, False\r\n'
    )
    try:
        startup_file.write_text(vbs_content, encoding="utf-8")
        print(f"[+] Auto-start enabled successfully!")
        print(f"[+] Startup script written to: {startup_file}")
        print("[+] The JARVIS Mobile Service will now run silently every time your PC boots up.")
    except Exception as e:
        print(f"[-] Failed to write startup file: {e}")

def uninstall_startup():
    startup_file = _get_startup_file()
    if startup_file and startup_file.exists():
        try:
            startup_file.unlink()
            print("[+] Auto-start disabled. Startup file removed.")
        except Exception as e:
            print(f"[-] Failed to remove startup file: {e}")
    else:
        print("[-] Startup entry was not installed.")

if __name__ == "__main__":
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd in ("restart", "reload"):
        stop()
        time.sleep(1)
        start()
    elif cmd == "status":
        status()
    elif cmd in ("install", "enable", "autostart"):
        install_startup()
    elif cmd in ("uninstall", "disable"):
        uninstall_startup()
    else:
        print(__doc__)
