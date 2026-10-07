import re

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

pattern = r"    def _build_center_sub_header\(self\) -> QWidget:.*?        return w"
NEW_SUB_HEADER = r"""    def _build_center_sub_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(120)
        w.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(40, 20, 40, 0)
        
        # Left Text
        left_lbl = QLabel("The best protection\nis prevention...")
        left_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        left_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; font-style: italic;")
        left_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        lay.addWidget(left_lbl)
        
        lay.addStretch(1)
        
        # Right Text List
        right_lbl = QLabel("LISTENING...\nTHINKING...\nPROCESSING...\nREADY")
        right_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        right_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; line-height: 1.5;")
        right_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        lay.addWidget(right_lbl)
        
        return w"""

code = re.sub(pattern, NEW_SUB_HEADER, code, flags=re.DOTALL)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patch 7b done")
