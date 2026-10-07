import pathlib

# 1. Patch main.py
p = pathlib.Path('main.py')
src = p.read_text('utf-8')

# Reminder & YouTube
old1 = """            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "screen_process":"""
new1 = """            elif name == "screen_process":"""

# Desktop Control
old2 = """            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":"""
new2 = """            elif name == "code_helper":"""

def patch_file(content, old, new, name):
    old_crlf = old.replace('\n', '\r\n')
    if old in content:
        print(f'{name} patched successfully (LF)')
        return content.replace(old, new)
    elif old_crlf in content:
        print(f'{name} patched successfully (CRLF)')
        return content.replace(old_crlf, new.replace('\n', '\r\n'))
    else:
        print(f'{name} block not found!')
        return content

src = patch_file(src, old1, new1, 'main.py (reminder/youtube)')
src = patch_file(src, old2, new2, 'main.py (desktop_control)')
p.write_text(src, 'utf-8')


# 2. Patch dummy_features.py
p2 = pathlib.Path('dummy_features.py')
src2 = p2.read_text('utf-8')

old_dummy1 = """def reminder(*args, **kwargs):
    return "reminder is not implemented yet."


def youtube_video(*args, **kwargs):
    return "youtube_video is not implemented yet."


def computer_settings(*args, **kwargs):"""
new_dummy1 = """def computer_settings(*args, **kwargs):"""

old_dummy2 = """def desktop_control(*args, **kwargs):
    return "desktop_control is not implemented yet."


def code_helper(*args, **kwargs):"""
new_dummy2 = """def code_helper(*args, **kwargs):"""

old_exports = """    # Tool-dispatch functions
    "send_message", "reminder", "youtube_video", "computer_settings",
    "desktop_control", "code_helper", """
new_exports = """    # Tool-dispatch functions
    "send_message", "computer_settings",
    "code_helper", """

src2 = patch_file(src2, old_dummy1, new_dummy1, 'dummy_features.py (reminder/youtube)')
src2 = patch_file(src2, old_dummy2, new_dummy2, 'dummy_features.py (desktop_control)')
src2 = patch_file(src2, old_exports, new_exports, 'dummy_features.py (exports)')
p2.write_text(src2, 'utf-8')
