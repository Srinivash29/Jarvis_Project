import subprocess

PLUGIN = {
    "name": "desktop_control",
    "description": "Controls desktop features like locking the screen, sleeping, or minimizing windows.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Action to perform: 'lock', 'sleep', 'minimize_all'"
            }
        },
        "required": ["action"]
    }
}

def run(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    
    try:
        if action == "lock":
            subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            return "Workstation locked."
        elif action == "sleep":
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "Going to sleep."
        elif action == "minimize_all":
            # Using PowerShell to minimize all windows
            ps_script = "(New-Object -ComObject Shell.Application).MinimizeAll()"
            subprocess.run(["powershell", "-Command", ps_script])
            return "Minimized all windows."
        else:
            return f"Unknown desktop action: {action}"
    except Exception as e:
        return f"Failed to perform desktop control {action}: {e}"
