import pathlib
p = pathlib.Path('main.py')
src = p.read_text('utf-8')
old_block = """            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":"""
new_block = """            if name == "weather_report":"""

# Handle potential CRLF
old_block_crlf = old_block.replace('\n', '\r\n')
if old_block in src:
    p.write_text(src.replace(old_block, new_block), 'utf-8')
    print('Replaced successfully (LF)')
elif old_block_crlf in src:
    p.write_text(src.replace(old_block_crlf, new_block.replace('\n', '\r\n')), 'utf-8')
    print('Replaced successfully (CRLF)')
else:
    print('Block not found!')
