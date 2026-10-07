import re

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

pattern = r"        self._date_lbl\.setAlignment\(Qt\.AlignmentFlag\.AlignRight\)\n        right_col\.addWidget\(self\._date_lbl\)\n        lay\.addLayout\(right_col\)"
NEW_DATE_LOC = """        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)
        
        self._loc_lbl = QLabel("LOCATION: LOCKED")
        self._loc_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._loc_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
        self._loc_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._loc_lbl)
        
        lay.addLayout(right_col)"""

code = re.sub(pattern, NEW_DATE_LOC, code)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patch 6 done")
