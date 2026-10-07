import re

with open("ui.py", "r", encoding="utf-8") as f:
    code = f.read()

pattern = r"    def _update_metrics\(self\):.*?        self._net_ip_lbl\.setText\(str\(ip\)\)"

NEW_UPDATE_METRICS = """    def _update_metrics(self):
        snap = _metrics.snapshot()

        # CPU
        cpu = snap["cpu"]
        self._gauge_cpu.set_value(cpu, f"{cpu:.0f}%")

        # RAM
        mem = snap["mem"]
        self._gauge_ram.set_value(mem, f"{mem:.0f}%")

        # DISK (C:)
        disk = snap.get("disk", 0.0)
        self._gauge_disk.set_value(disk, f"{disk:.0f}%")

        # GPU
        gpu = snap["gpu"]
        if gpu >= 0:
            self._gauge_gpu.set_value(gpu, f"{gpu:.0f}%")
        else:
            self._gauge_gpu.set_value(0, "N/A")

        # TMP
        tmp = snap["tmp"]
        if tmp >= 0:
            self._qs_temp.setText(f"{tmp:.0f}°C")
        else:
            self._qs_temp.setText("N/A")

        # Network labels
        net_up = snap.get("net_up", 0.0)
        net_down = snap.get("net_down", 0.0)
        
        up_str = f"{net_up:.1f} KB/s" if net_up < 1024 else f"{net_up/1024:.1f} MB/s"
        down_str = f"{net_down:.1f} KB/s" if net_down < 1024 else f"{net_down/1024:.1f} MB/s"
        
        self._qs_network.setText(f"↑ {up_str}  ↓ {down_str}")
        
        # Uptime
        import psutil, time
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        self._qs_uptime.setText(f"{hours}h {minutes}m")
        
        # Battery
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                self._qs_battery.setText(f"{battery.percent}% {'(Plugged In)' if battery.power_plugged else ''}")
            else:
                self._qs_battery.setText("N/A")"""

code = re.sub(pattern, NEW_UPDATE_METRICS, code, flags=re.DOTALL)

with open("ui.py", "w", encoding="utf-8") as f:
    f.write(code)
print("Patch 8 done")
