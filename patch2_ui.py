import sys
import re

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update QUICK STATS in _build_left_panel
OLD_QUICK_STATS = """        self._net_up_lbl   = _net_row("UP", C.GREEN)
        self._net_down_lbl = _net_row("DOWN", C.PRI)
        self._net_ip_lbl   = _net_row("IP", C.PRI)"""
NEW_QUICK_STATS = """        self._qs_uptime = _net_row("Uptime:", C.TEXT_MED)
        self._qs_network = _net_row("Network:", C.TEXT_MED)
        self._qs_temp = _net_row("Temp:", C.TEXT_MED)
        self._qs_battery = _net_row("Battery:", C.TEXT_MED)"""
code = code.replace(OLD_QUICK_STATS, NEW_QUICK_STATS)

# 2. Update QUICK TOOLS to CURRENT APPS
pattern = r"# ── Quick Tools Card ──.*?return w"
NEW_BOTTOM = """        # ── Current Apps ──
        apps_lbl = QLabel("> CURRENT APPS")
        apps_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        apps_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 1px;")
        lay.addWidget(apps_lbl)
        
        apps_cont = QWidget()
        apps_cont.setStyleSheet(f"background: {C.PANEL2}; border-radius: 4px;")
        apps_lay = QVBoxLayout(apps_cont)
        apps_lay.setContentsMargins(8, 8, 8, 8)
        
        for app, val in [("Chrome", 45), ("VS Code", 22), ("Discord", 15), ("Spotify", 8)]:
            r = QHBoxLayout()
            albl = QLabel(app)
            albl.setFont(QFont("Segoe UI", 7))
            albl.setStyleSheet(f"color: {C.TEXT}; background: transparent;")
            r.addWidget(albl)
            
            pbar = QProgressBar()
            pbar.setFixedHeight(4)
            pbar.setTextVisible(False)
            pbar.setValue(val)
            pbar.setStyleSheet(f"QProgressBar {{ background: {C.DARK}; border: none; }} QProgressBar::chunk {{ background: {C.PRI}; }}")
            r.addWidget(pbar)
            apps_lay.addLayout(r)
            
        lay.addWidget(apps_cont)
        
        # ── Recent Commands ──
        cmd_lbl = QLabel("> RECENT COMMANDS")
        cmd_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        cmd_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; letter-spacing: 1px;")
        lay.addWidget(cmd_lbl)
        
        cmd_list = QListWidget()
        cmd_list.setFixedHeight(60)
        cmd_list.setStyleSheet(f"background: {C.PANEL2}; color: {C.TEXT_DIM}; border-radius: 4px; font-size: 10px;")
        cmd_list.addItems(["> Open spotify", "> Show system status", "> Mute volume"])
        lay.addWidget(cmd_list)
        
        lay.addStretch()
        return w"""
code = re.sub(pattern, NEW_BOTTOM, code, flags=re.DOTALL)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patch 2 done")
