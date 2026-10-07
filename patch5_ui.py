import re

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

# Instead of exact string replace, we'll use regex to rewrite _build_input_row
pattern = r"    def _build_input_row\(self\) -> QHBoxLayout:.*?return row"

NEW_INPUT = """    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(6)
        
        self._mute_btn = QPushButton("🎙")
        self._mute_btn.setFixedSize(34, 34)
        self._mute_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        
        # Style like a sleek mic button
        self._mute_btn.setStyleSheet(f\"\"\"
            QPushButton {{
                background: rgba(0, 210, 255, 0.08);
                color: {C.PRI};
                border: 1px solid {C.BORDER};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: rgba(0, 210, 255, 0.22);
                border-color: {C.PRI};
            }}
        \"\"\")
        row.addWidget(self._mute_btn)

        self._input = QLineEdit()
        self._input.setPlaceholderText("LISTENING... SAY 'HEY JARVIS' OR TYPE A COMMAND")
        self._input.setFont(QFont("Segoe UI", 9))
        self._input.setFixedHeight(34)
        self._input.setStyleSheet(f\"\"\"
            QLineEdit {{
                background: #020814;
                color: {C.WHITE};
                border: 1px solid {C.BORDER};
                border-radius: 10px;
                padding: 4px 10px;
            }}
            QLineEdit:focus {{
                border: 1px solid {C.PRI};
                background: #040e22;
            }}
        \"\"\")
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton(">")
        send.setFixedSize(34, 34)
        send.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f\"\"\"
            QPushButton {{
                background: {C.ACC};
                color: #000000;
                border: 1px solid {C.ACC};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: #ffc033;
                border-color: #ffc033;
            }}
            QPushButton:pressed {{
                background: #e69900;
            }}
        \"\"\")
        send.clicked.connect(self._send)
        row.addWidget(send)
        
        # Dummy _interrupt_btn
        self._interrupt_btn = QPushButton("")
        self._interrupt_btn.hide()
        
        return row"""

code = re.sub(pattern, NEW_INPUT, code, flags=re.DOTALL)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patch 5 done")
