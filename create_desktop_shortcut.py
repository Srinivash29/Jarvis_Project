"""
Create a Windows Desktop Shortcut for JARVIS with the custom icon.
"""
import os
import sys
import subprocess
from pathlib import Path

# Safe stdout/stderr encoding on Windows
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def create_shortcut():
    project_dir = Path(__file__).resolve().parent
    main_py = project_dir / "main.py"
    icon_path = project_dir / "config" / "jarvis.ico"

    # Select Python executable (prefer pythonw.exe to launch GUI without opening a console window)
    venv_pyw = project_dir / ".venv" / "Scripts" / "pythonw.exe"
    sys_pyw = Path(sys.executable).parent / "pythonw.exe"
    if venv_pyw.exists():
        py_exe = str(venv_pyw)
    elif sys_pyw.exists():
        py_exe = str(sys_pyw)
    elif (project_dir / ".venv" / "Scripts" / "python.exe").exists():
        py_exe = str(project_dir / ".venv" / "Scripts" / "python.exe")
    else:
        py_exe = sys.executable

    # Find Desktop path
    desktop = None
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = shell.SpecialFolders("Desktop")
    except Exception:
        pass

    if not desktop or not os.path.exists(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if os.path.exists(onedrive_desktop) and not os.path.exists(desktop):
            desktop = onedrive_desktop

    shortcut_file = os.path.join(desktop, "JARVIS.lnk")

    # Build PowerShell command to create Windows shortcut
    ps_cmd = (
        f'$WshShell = New-Object -ComObject WScript.Shell; '
        f'$Shortcut = $WshShell.CreateShortcut("{shortcut_file}"); '
        f'$Shortcut.TargetPath = "{py_exe}"; '
        f'$Shortcut.Arguments = \'"{main_py}"\'; '
        f'$Shortcut.WorkingDirectory = "{project_dir}"; '
        f'$Shortcut.Description = "JARVIS (MARK LI) AI Assistant"; '
    )

    if icon_path.exists():
        ps_cmd += f'$Shortcut.IconLocation = "{icon_path},0"; '

    ps_cmd += '$Shortcut.Save()'

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        print("[SUCCESS] JARVIS desktop shortcut created successfully!")
        print(f"Location: {shortcut_file}")
        print(f"Target:   {py_exe} main.py")
        if icon_path.exists():
            print(f"Icon:     {icon_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create shortcut: {e}")
        return False

if __name__ == "__main__":
    create_shortcut()
