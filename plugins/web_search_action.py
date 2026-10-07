import urllib.request
import urllib.parse
import json

PLUGIN = {
    "name": "web_search_action",
    "description": "Searches the web for information using Wikipedia summaries.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {
                "type": "STRING",
                "description": "The search query (preferably an entity or topic name)."
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
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return f"Search result for {query}:\n{data.get('extract', 'No summary found.')}"
    except Exception as e:
        return f"Web search for '{query}' failed (try a Wikipedia entity name): {e}"
