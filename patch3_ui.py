import sys
import re

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Strip everything after self._log in _build_right_panel and add filter buttons BEFORE self._log
pattern = r"        self._log = LogWidget\(\).*?return w"

NEW_RIGHT_BOTTOM = """        # ── Filter Buttons ──
        filter_lay = QHBoxLayout()
        filter_lay.setSpacing(4)
        for f_name in ["All", "System", "Apps", "Voice", "Plugins"]:
            btn = QPushButton(f_name)
            btn.setFixedHeight(24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if f_name == "All":
                btn.setStyleSheet(f"background: {C.PRI}; color: #000; border: none; border-radius: 12px; font-weight: bold; font-size: 10px;")
            else:
                btn.setStyleSheet(f"background: transparent; color: {C.TEXT_MED}; border: 1px solid {C.BORDER}; border-radius: 12px; font-weight: bold; font-size: 10px;")
            filter_lay.addWidget(btn)
        lay.addLayout(filter_lay)
        
        self._log = LogWidget()
        lay.addWidget(self._log, stretch=1)
        
        return w"""
code = re.sub(pattern, NEW_RIGHT_BOTTOM, code, flags=re.DOTALL)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patch 3 done")
