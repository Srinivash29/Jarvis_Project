import sys
import re

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

pattern = r"_c_lay\.addSpacing\(10\)"
NEW_CODE = """_c_lay.addSpacing(10)
        _c_lay.addLayout(self._build_input_row())
        _c_lay.addSpacing(10)"""
code = code.replace("_c_lay.addSpacing(10)", NEW_CODE, 1)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patch 4 done")
