import sys

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace widths securely
code = code.replace("w.setFixedWidth(_LEFT_W)", "w.setFixedWidth(345)")
code = code.replace("w.setFixedWidth(_RIGHT_W)", "w.setFixedWidth(260)") # Activity log narrower

# Define CircularGauge
CIRCULAR_GAUGE = """
class CircularGauge(QWidget):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0
        self._text = "--"
        self.setFixedSize(70, 70)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct)) if pct >= 0 else -1.0
        self._text = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setPen(QPen(QColor(C.PANEL2), 4))
        rect = QRectF(5, 5, W-10, H-10)
        p.drawArc(rect, 0, 360 * 16)

        if self._value >= 0:
            c = QColor(self._color)
            p.setPen(QPen(c, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            span = int(-(self._value / 100.0) * 360 * 16)
            p.drawArc(rect, 90 * 16, span)

        p.setPen(QColor(C.TEXT))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(QRectF(0, 20, W, 20), Qt.AlignmentFlag.AlignCenter, self._text)

        p.setPen(QColor(C.TEXT_DIM))
        font2 = QFont("Segoe UI", 7)
        p.setFont(font2)
        p.drawText(QRectF(0, H-22, W, 15), Qt.AlignmentFlag.AlignCenter, self._label)

"""

if "class CircularGauge" not in code:
    code = code.replace("class MetricBar(QWidget):", CIRCULAR_GAUGE + "\nclass MetricBar(QWidget):")

# Replace the 5 MetricBar instantiation with CircularGauges in a grid
OLD_METRICS = """        # ── 5 MetricBar Cards ──
        self._bar_cpu  = MetricBar("🖳", "CPU", C.PRI)
        self._bar_mem  = MetricBar("💾", "RAM", C.ACC)
        self._bar_disk = MetricBar("💽", "DISK (C:)", C.GREEN)
        self._bar_gpu  = MetricBar("📷", "GPU", C.PRI)
        self._bar_tmp  = MetricBar("🌡", "TEMP", "#ff6688")

        for bar in [self._bar_cpu, self._bar_mem, self._bar_disk, self._bar_gpu, self._bar_tmp]:
            lay.addWidget(bar)"""

NEW_METRICS = """        # ── 4 Circular Gauges ──
        self._bar_cpu  = CircularGauge("CPU", C.PRI)
        self._bar_mem  = CircularGauge("RAM", C.ACC)
        self._bar_gpu  = CircularGauge("GPU", C.PRI)
        self._bar_disk = CircularGauge("DISK", C.GREEN)
        self._bar_tmp  = MetricBar("🌡", "TEMP", C.RED) # keep tmp as fallback or hidden
        self._bar_tmp.hide() # We hide temp to match image

        grid = QHBoxLayout()
        grid.setSpacing(5)
        for bar in [self._bar_cpu, self._bar_mem, self._bar_gpu, self._bar_disk]:
            grid.addWidget(bar)
        lay.addLayout(grid)
        
        # ── Performance Graph Placeholder ──
        graph_lbl = QLabel("PERFORMANCE GRAPH")
        graph_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        graph_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        lay.addWidget(graph_lbl)
        
        graph_box = QWidget()
        graph_box.setFixedHeight(60)
        graph_box.setStyleSheet(f"background: {C.PANEL2}; border-radius: 4px;")
        lay.addWidget(graph_box)
        """

code = code.replace(OLD_METRICS, NEW_METRICS)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)

print("UI Patched successfully")
