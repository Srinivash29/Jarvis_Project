import sys

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

BUTTON_BAR = """
        # ── System Status & Buttons Below Globe ──
        sys_status_lay = QVBoxLayout()
        sys_status_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sys_status_lbl = QLabel("SYSTEM STATUS\\nONLINE")
        sys_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sys_status_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        sys_status_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 2px;")
        sys_status_lay.addWidget(sys_status_lbl)

        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(10)
        btn_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        for text, icon in [("Voice", "🎙"), ("Apps", "📱"), ("Plugins", "🧩"), ("Settings", "⚙")]:
            btn = QPushButton(f"{icon}  {text}")
            btn.setFixedSize(90, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f\"\"\"
                QPushButton {{
                    background: {C.PANEL2};
                    color: {C.TEXT};
                    border: 1px solid {C.BORDER};
                    border-radius: 8px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    border-color: {C.PRI};
                    color: {C.PRI};
                    background: {C.PANEL};
                }}
            \"\"\")
            btn_lay.addWidget(btn)

        sys_status_lay.addLayout(btn_lay)
        _c_lay.addLayout(sys_status_lay)
        _c_lay.addSpacing(10)
"""

TARGET = "        _c_lay.addWidget(self._hud_cam_stack, stretch=1)"
if "sys_status_lay" not in code:
    code = code.replace(TARGET, TARGET + "\n" + BUTTON_BAR)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Button bar added")
