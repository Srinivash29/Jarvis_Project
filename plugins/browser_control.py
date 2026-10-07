import webbrowser
import urllib.parse

PLUGIN = {
    "name": "browser_control",
    "description": "Opens a web browser with a specific URL or search query.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "url": {
                "type": "STRING",
                "description": "The URL to open."
            },
            "query": {
                "type": "STRING",
                "description": "Search query if no URL is provided."
            }
        },
        "required": []
    }
}

def run(parameters: dict, player=None) -> str:
    url = parameters.get("url", "").strip()
    query = parameters.get("query", "").strip()
    
    if not url and not query:
        return "No URL or search query provided."
        
    try:
        target = url
        if not target:
            target = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        elif not (target.startswith("http://") or target.startswith("https://")):
            target = "https://" + target
            
        webbrowser.open(target)
        return f"Opened browser for: {target}"
    except Exception as e:
        return f"Failed to open browser: {e}"
