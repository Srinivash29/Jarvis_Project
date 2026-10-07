PLUGIN = {
    "name": "code_helper",
    "description": "Helps with basic coding tasks, snippets, and formatting.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task": {
                "type": "STRING",
                "description": "The coding task to perform."
            },
            "language": {
                "type": "STRING",
                "description": "The programming language."
            }
        },
        "required": ["task"]
    }
}

def run(parameters: dict, player=None) -> str:
    task = parameters.get("task", "")
    lang = parameters.get("language", "python")
    return f"Code Helper invoked for {lang} task: {task}. (Advanced coding requires dev_agent)."
