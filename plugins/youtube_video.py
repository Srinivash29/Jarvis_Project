import webbrowser
import urllib.parse

PLUGIN = {
    "name": "youtube_video",
    "description": "Searches for and opens a video on YouTube.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The topic, channel, or video name to search for."
            }
        },
        "required": ["query"]
    }
}

def run(parameters: dict, player=None) -> str:
    query = parameters.get("query", "").strip()
    if not query:
        return "No search query provided."
        
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        return f"Opened YouTube search for: {query}"
    except Exception as e:
        return f"Failed to open YouTube: {e}"
