"""
Hardware Telemetry and Dynamic ETA Engine for OmniConvert.
Monitors system resources (CPU %, RAM MB), process footprint, and calculates smoothed ETA.
"""

import os
import time
from typing import Optional, Dict, Any
import psutil


class EmaEtaCalculator:
    """Exponential Moving Average (EMA) calculator for stable ETA and throughput estimation."""

    def __init__(self, alpha: float = 0.25):
        self.alpha = alpha
        self.last_time = time.time()
        self.last_bytes = 0
        self.smoothed_speed = 0.0  # Bytes per second
        self.start_time = time.time()

    def update(self, current_bytes: int, total_bytes: int) -> Tuple_ETA:
        now = time.time()
        dt = max(0.001, now - self.last_time)
        d_bytes = max(0, current_bytes - self.last_bytes)

        instant_speed = d_bytes / dt

        if self.smoothed_speed <= 0:
            self.smoothed_speed = instant_speed
        else:
            self.smoothed_speed = (self.alpha * instant_speed) + ((1.0 - self.alpha) * self.smoothed_speed)

        self.last_time = now
        self.last_bytes = current_bytes

        # Calculate remaining
        remaining_bytes = max(0, total_bytes - current_bytes)
        if self.smoothed_speed > 100:  # More than 100 B/s
            eta_seconds = remaining_bytes / self.smoothed_speed
        else:
            elapsed = max(0.001, now - self.start_time)
            avg_speed = current_bytes / elapsed
            eta_seconds = remaining_bytes / max(1.0, avg_speed) if avg_speed > 0 else 0.0

        return eta_seconds, self.smoothed_speed


Tuple_ETA = Any


def format_duration(seconds: float) -> str:
    """Format seconds into readable human string."""
    if seconds <= 0:
        return "0s"
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    mins, s = divmod(secs, 60)
    if mins < 60:
        return f"{mins}m {s:02d}s"
    hrs, m = divmod(mins, 60)
    return f"{hrs}h {m:02d}m"


def format_bytes(num_bytes: float) -> str:
    """Format byte count into human readable units."""
    if num_bytes < 1024:
        return f"{num_bytes:.0f} B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    elif num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


class HardwareMonitor:
    """Monitors live CPU and RAM consumption without causing system overhead."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        # Prime the CPU measurement
        self.process.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None)

    def snapshot(self) -> Dict[str, Any]:
        """Collect current resource usage snapshot."""
        try:
            sys_cpu = psutil.cpu_percent(interval=None)
            proc_cpu = self.process.cpu_percent(interval=None)
            mem_info = self.process.memory_info()
            proc_ram_mb = mem_info.rss / (1024 * 1024)
            sys_ram_pct = psutil.virtual_memory().percent

            return {
                "system_cpu_pct": sys_cpu,
                "process_cpu_pct": proc_cpu,
                "process_ram_mb": proc_ram_mb,
                "system_ram_pct": sys_ram_pct,
            }
        except Exception:
            return {
                "system_cpu_pct": 0.0,
                "process_cpu_pct": 0.0,
                "process_ram_mb": 0.0,
                "system_ram_pct": 0.0,
            }
