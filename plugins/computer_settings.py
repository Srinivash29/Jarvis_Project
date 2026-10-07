import subprocess

PLUGIN = {
    "name": "computer_settings",
    "description": "Opens Windows system settings.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "setting_name": {
                "type": "STRING",
                "description": "The setting to open (e.g., 'display', 'bluetooth', 'wifi', 'sound')."
            }
        },
        "required": []
    }
}

def run(parameters: dict, player=None) -> str:
    setting = parameters.get("setting_name", "").lower()
    
    mapping = {
        "display": "ms-settings:display",
        "bluetooth": "ms-settings:bluetooth",
        "wifi": "ms-settings:network-wifi",
        "sound": "ms-settings:sound",
        "power": "ms-settings:powersleep"
    }
    
    uri = mapping.get(setting, "ms-settings:")
    try:
        subprocess.run(f"start {uri}", shell=True)
        return f"Opened settings: {setting or 'main'}"
    except Exception as e:
        return f"Failed to open settings: {e}"
