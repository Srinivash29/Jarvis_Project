import os
from pathlib import Path

PLUGIN = {
    "name": "file_controller",
    "description": "Basic file operations: read or write a small text file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "'read' or 'write'"
            },
            "filepath": {
                "type": "STRING",
                "description": "Absolute or relative path to the file."
            },
            "content": {
                "type": "STRING",
                "description": "Content to write (only for 'write' action)."
            }
        },
        "required": ["action", "filepath"]
    }
}

def run(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower()
    filepath = parameters.get("filepath", "")
    content = parameters.get("content", "")
    
    if not filepath:
        return "No filepath provided."
        
    p = Path(filepath)
    
    try:
        if action == "read":
            if not p.exists():
                return f"File not found: {filepath}"
            data = p.read_text(encoding="utf-8")
            if len(data) > 5000:
                data = data[:5000] + "\n...[truncated]"
            return f"Content of {filepath}:\n{data}"
            
        elif action == "write":
            # Ensure parent exists
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Successfully wrote to {filepath}"
            
        else:
            return f"Unknown action: {action}. Use 'read' or 'write'."
            
    except Exception as e:
        return f"File operation failed: {e}"
