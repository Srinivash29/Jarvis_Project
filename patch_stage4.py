import pathlib

p = pathlib.Path('main.py')
src = p.read_text('utf-8')

# 1. Remove send_message block
old1 = """            if name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "screen_process":"""
new1 = """            if name == "screen_process":"""

# 2. Remove all dummy blocks from computer_settings down to flight_finder
old2 = """            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."
                # Mirror results to the on-screen content panel
                _mode = args.get("mode", "search")
                if r and not r.startswith("No results") and not r.startswith("Search failed"):
                    _query = args.get("query") or ", ".join(args.get("items", []))
                    _label = f"{_mode.upper()} — {_query[:38]}" if _query else _mode.upper()
                    self.ui.show_content(_label, r)
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "system_status":"""
new2 = """            elif name == "system_status":"""

def patch(content, old, new, label):
    crlf_old = old.replace('\n', '\r\n')
    if old in content:
        print(f"Patched {label} (LF)")
        return content.replace(old, new)
    elif crlf_old in content:
        print(f"Patched {label} (CRLF)")
        return content.replace(crlf_old, new.replace('\n', '\r\n'))
    else:
        print(f"Failed to patch {label}!")
        return content

src = patch(src, old1, new1, 'main.py send_message')
src = patch(src, old2, new2, 'main.py massive dummy block')
p.write_text(src, 'utf-8')


p2 = pathlib.Path('dummy_features.py')
src2 = p2.read_text('utf-8')

old_dummy_block = """def send_message(*args, **kwargs):
    return "send_message is not implemented yet."


def computer_settings(*args, **kwargs):
    return "computer_settings is not implemented yet."


def code_helper(*args, **kwargs):
    return "code_helper is not implemented yet."


def dev_agent(*args, **kwargs):
    return "dev_agent is not implemented yet."


def web_search_action(*args, **kwargs):
    return "web_search_action is not implemented yet."


def file_processor(*args, **kwargs):
    return "file_processor is not implemented yet."


def computer_control(*args, **kwargs):
    return "computer_control is not implemented yet."


def game_updater(*args, **kwargs):
    return "game_updater is not implemented yet."


def flight_finder(*args, **kwargs):
    return "flight_finder is not implemented yet."


# ─── Utility functions"""
new_dummy_block = """# ─── Utility functions"""

old_exports = """    # Tool-dispatch functions
    "send_message", "computer_settings",
    "code_helper", "dev_agent", "web_search_action",
    "file_processor", "computer_control", "game_updater", "flight_finder",
    # Utility functions"""
new_exports = """    # Tool-dispatch functions
    # Utility functions"""

src2 = patch(src2, old_dummy_block, new_dummy_block, 'dummy_features funcs')
src2 = patch(src2, old_exports, new_exports, 'dummy_features exports')
p2.write_text(src2, 'utf-8')
