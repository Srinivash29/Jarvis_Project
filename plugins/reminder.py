import threading
import time

PLUGIN = {
    "name": "reminder",
    "description": "Sets a timer or reminder that will alert the user in the future.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "minutes": {
                "type": "NUMBER",
                "description": "Number of minutes to wait."
            },
            "message": {
                "type": "STRING",
                "description": "The reminder message."
            }
        },
        "required": ["minutes"]
    }
}

def _wait_and_remind(minutes, message, player):
    time.sleep(minutes * 60)
    
    # Try audio alert via Jarvis UI
    if player and hasattr(player, "request_say"):
        try:
            player.request_say(f"Sir, here is your reminder: {message}")
        except Exception:
            pass
            
    # Visual alert on Windows
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, "JARVIS Reminder", 0x40 | 0x1)
    except Exception:
        pass

def run(parameters: dict, player=None) -> str:
    minutes = parameters.get("minutes", 0)
    message = parameters.get("message", "Time's up!").strip()
    
    if minutes <= 0:
        return "Invalid time for reminder."
        
    t = threading.Thread(target=_wait_and_remind, args=(minutes, message, player), daemon=True)
    t.start()
    
    return f"Reminder set for {minutes} minutes."
