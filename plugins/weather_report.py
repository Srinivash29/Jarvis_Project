import urllib.request
import urllib.parse

PLUGIN = {
    "name": "weather_report",
    "description": "Gets the current weather for a specified city.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "location": {
                "type": "STRING",
                "description": "The city or location to get the weather for."
            }
        },
        "required": ["location"]
    }
}

def run(parameters: dict, player=None) -> str:
    location = parameters.get("location", "").strip()
    if not location:
        return "No location provided for the weather report."
    
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=%C+%t"
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.88.1'})
        with urllib.request.urlopen(req, timeout=5) as response:
            weather_data = response.read().decode('utf-8').strip()
        return f"Weather for {location}: {weather_data}"
    except Exception as e:
        return f"Failed to get weather for {location}: {e}"
