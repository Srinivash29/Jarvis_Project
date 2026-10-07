import pathlib

# 1. Patch main.py
p = pathlib.Path('main.py')
src = p.read_text('utf-8')
old_block_main = """            if name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":"""
new_block_main = """            if name == "send_message":"""

old_block_main_crlf = old_block_main.replace('\n', '\r\n')
if old_block_main in src:
    p.write_text(src.replace(old_block_main, new_block_main), 'utf-8')
    print('main.py patched successfully (LF)')
elif old_block_main_crlf in src:
    p.write_text(src.replace(old_block_main_crlf, new_block_main.replace('\n', '\r\n')), 'utf-8')
    print('main.py patched successfully (CRLF)')
else:
    print('main.py block not found!')

# 2. Patch dummy_features.py
p2 = pathlib.Path('dummy_features.py')
src2 = p2.read_text('utf-8')

old_block_dummy = """def weather_action(*args, **kwargs):
    return "weather_action is not implemented yet."


def browser_control(*args, **kwargs):
    return "browser_control is not implemented yet."


def file_controller(*args, **kwargs):
    return "file_controller is not implemented yet."


def send_message(*args, **kwargs):"""
new_block_dummy = """def send_message(*args, **kwargs):"""

old_block_dummy_crlf = old_block_dummy.replace('\n', '\r\n')
if old_block_dummy in src2:
    src2 = src2.replace(old_block_dummy, new_block_dummy)
    print('dummy_features.py funcs patched (LF)')
elif old_block_dummy_crlf in src2:
    src2 = src2.replace(old_block_dummy_crlf, new_block_dummy.replace('\n', '\r\n'))
    print('dummy_features.py funcs patched (CRLF)')
else:
    print('dummy_features.py funcs block not found!')

old_exports = """    # Tool-dispatch functions
    "weather_action", "browser_control", "file_controller",
    "send_message", """
new_exports = """    # Tool-dispatch functions
    "send_message", """

old_exports_crlf = old_exports.replace('\n', '\r\n')
if old_exports in src2:
    src2 = src2.replace(old_exports, new_exports)
    print('dummy_features.py exports patched (LF)')
elif old_exports_crlf in src2:
    src2 = src2.replace(old_exports_crlf, new_exports.replace('\n', '\r\n'))
    print('dummy_features.py exports patched (CRLF)')
else:
    print('dummy_features.py exports block not found!')

p2.write_text(src2, 'utf-8')
