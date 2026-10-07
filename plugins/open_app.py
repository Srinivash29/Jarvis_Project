import os
import subprocess

PLUGIN = {
    "name": "open_app",
    "description": "Opens a local system application, website, or file by name or path.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {
                "type": "STRING",
                "description": "The name of the application, file path, or URL to open."
            }
        },
        "required": ["app_name"]
    }
}

def find_app_path(name: str) -> str:
    name_lower = name.lower()
    
    # Common system apps that work directly
    if name_lower in ["notepad", "calc", "explorer", "cmd"]:
        return name_lower
        
    directories = [
        os.environ.get('PROGRAMDATA', 'C:\\ProgramData') + r'\Microsoft\Windows\Start Menu\Programs',
        os.environ.get('APPDATA', '') + r'\Microsoft\Windows\Start Menu\Programs',
        os.environ.get('USERPROFILE', '') + r'\Desktop',
        os.environ.get('PUBLIC', 'C:\\Users\\Public') + r'\Desktop'
    ]
    
    for d in directories:
        if not d or not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.lnk'):
                    file_name = file[:-4].lower()
                    if any(skip in file_name for skip in ["uninstall", "installer", "setup"]):
                        continue
                    if name_lower == file_name or name_lower in file_name:
                        return os.path.join(root, file)
    return None

def run(parameters: dict, player=None) -> str:
    app_name = parameters.get("app_name", "").strip()
    if not app_name:
        return "No application name provided."
    
    # Try to open website directly
    if app_name.startswith("http://") or app_name.startswith("https://"):
        try:
            os.startfile(app_name)
            return f"Opened website: {app_name}"
        except Exception as e:
            return f"Failed to open website {app_name}: {e}"
            
    app_name_lower = app_name.lower()
    # Common URI schemes for Windows Store apps
    uri_schemes = {
        "whatsapp": "whatsapp://",
        "spotify": "spotify:",
        "netflix": "netflix:",
        "settings": "ms-settings:",
        "store": "ms-windows-store:",
        "mail": "outlookmail:"
    }
    for key, uri in uri_schemes.items():
        if key in app_name_lower:
            try:
                os.startfile(uri)
                return f"Opened {app_name} successfully."
            except Exception as e:
                pass # Fallback to normal search if URI fails
    # Attempt 1: Direct startfile
    try:
        os.startfile(app_name)
        return f"Opened {app_name} successfully."
    except FileNotFoundError:
        pass
        
    # Attempt 2: Search Start Menu & Desktop for matching .lnk
    found_path = find_app_path(app_name)
    if found_path:
        try:
            os.startfile(found_path)
            # Just return the original app_name to keep the response natural
            return f"Opened {app_name} successfully."
        except Exception as e:
            return f"Found shortcut for {app_name}, but failed to open it: {e}"
            
    return f"Failed to find or open {app_name}. Please specify the full path if it's not in the Start Menu."
