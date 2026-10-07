import pathlib
import re

ui_path = pathlib.Path('d:/Jarvis_Project/ui.py')
src = ui_path.read_text('utf-8', errors='replace')

# 1. Update font
src = src.replace('"Courier New"', '"Segoe UI"')

# 2. Update Colors in class C
colors = {
    'BG': '"#0B0F19"',          # Darker modern slate
    'PANEL': '"#111827"',       # Modern gray panel
    'PANEL2': '"#1F2937"',
    'BORDER': '"#374151"',      # Soft borders
    'BORDER_B': '"#3B82F6"',
    'BORDER_A': '"#60A5FA"',
    'PRI': '"#3B82F6"',         # Tailwind Blue 500
    'PRI_DIM': '"#2563EB"',     # Tailwind Blue 600
    'PRI_GHO': '"#1D4ED8"',     # Tailwind Blue 700
    'ACC': '"#8B5CF6"',         # Violet
    'ACC2': '"#A78BFA"',
    'GREEN': '"#10B981"',       # Emerald
    'GREEN_D': '"#059669"',
    'RED': '"#EF4444"',         # Red
    'MUTED_C': '"#EF4444"',
    'TEXT': '"#F9FAFB"',        # Gray 50
    'TEXT_DIM': '"#9CA3AF"',    # Gray 400
    'TEXT_MED': '"#D1D5DB"',    # Gray 300
    'DARK': '"#030712"',        # Deep black/slate
    'BAR_BG': '"#1F2937"'
}

for k, v in colors.items():
    src = re.sub(fr'\b{k}\s*=\s*"[^"]+"', f'{k} = {v}', src)

# 3. Increase border radius globally
src = re.sub(r'border-radius:\s*(\d+)px', lambda m: f'border-radius: {min(int(m.group(1))*2 + 2, 16)}px', src)

# 4. Strip Iron Man orb and draw Modern AI Orb in HudCanvas.paintEvent
# Find start of HudCanvas
start_idx = src.find('class HudCanvas(QWidget):')
if start_idx != -1:
    # Find start of paintEvent
    pe_idx = src.find('    def paintEvent(self, _):', start_idx)
    if pe_idx != -1:
        # Find end of paintEvent (next def or class)
        next_def = src.find('\n    def ', pe_idx + 10)
        next_class = src.find('\nclass ', pe_idx + 10)
        end_idx = min(x for x in (next_def, next_class) if x != -1)
        
        if end_idx != -1:
            new_paint = """    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(C.BG))

        W, H = float(self.width()), float(self.height())
        cx, cy = W / 2.0, H / 2.0 - 15.0  
        fw = min(W, H)
        scale = self._scale

        # AI Glowing Orb (Glassmorphism)
        import math
        orb_r = fw * 0.25 * scale
        if self.speaking:
            orb_r *= 1.1 + 0.05 * math.sin(self._tick * 0.5)

        rad_out = QRadialGradient(cx, cy, orb_r * 1.5)
        if self.muted:
            base_color = QColor(239, 68, 68)  # Red
        elif self.state in ("THINKING", "PROCESSING"):
            base_color = QColor(139, 92, 246) # Violet
        elif self.speaking:
            base_color = QColor(16, 185, 129) # Emerald
        else:
            base_color = QColor(59, 130, 246) # Blue

        c1 = QColor(base_color)
        c1.setAlpha(180)
        c2 = QColor(base_color)
        c2.setAlpha(60)
        c3 = QColor(base_color)
        c3.setAlpha(0)

        rad_out.setColorAt(0.0, c1)
        rad_out.setColorAt(0.6, c2)
        rad_out.setColorAt(1.0, c3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(rad_out))
        p.drawEllipse(QPointF(cx, cy), orb_r * 1.5, orb_r * 1.5)

        # Core
        core_r = orb_r * 0.6
        p.setBrush(QBrush(QColor(255, 255, 255, 220)))
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # Bottom Text
        bot_y = min(H - 24, cy + fw * 0.44)
        banner_text = f"  {self._assistant_name}  "
        if self.muted: banner_text = f"  {self._assistant_name} MUTED  "
        elif self.speaking: banner_text = f"  {self._assistant_name} SPEAKING  "
        elif self.state in ("THINKING", "PROCESSING"): banner_text = f"  PROCESSING  "

        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setPen(QPen(base_color, 1))
        p.drawText(QRectF(cx - 160, bot_y - 10, 320, 22), Qt.AlignmentFlag.AlignCenter, banner_text)
"""
            src = src[:pe_idx] + new_paint + src[end_idx:]

ui_path.write_text(src, 'utf-8')
print("ui.py successfully patched for Modern Glassmorphism!")
