"""
Command Line Interface for OmniConvert.
Supports launching GUI or executing rapid head-less conversions directly from terminal.
"""

import os
import sys
import argparse
import time
from converter.core.registry import registry
from converter.engines.base import ConversionProgress, CancellationToken
from converter.core.telemetry import format_bytes, format_duration


def print_progress(prog: ConversionProgress):
    speed_str = f"[{format_bytes(prog.speed_bytes_sec)}/s]" if prog.speed_bytes_sec > 0 else ""
    eta_str = f"ETA: {format_duration(prog.eta_seconds)}" if prog.eta_seconds > 0 else ""
    fps_str = f"({prog.fps:.0f} fps)" if prog.fps > 0 else ""
    bar_len = 25
    filled = int(bar_len * (prog.progress / 100.0))
    bar = "=" * filled + "-" * (bar_len - filled)
    
    status_snippet = prog.status_text[:25] if prog.status_text else ""
    sys.stdout.write(f"\r  [{bar}] {prog.progress:5.1f}% {speed_str} {eta_str} {fps_str} {status_snippet}")
    sys.stdout.flush()
    if prog.progress >= 100.0:
        sys.stdout.write("\n")


def run_cli_conversion(input_path: str, output_path: str, target_format: str, power_mode: str = "balanced", lossless: bool = True) -> int:
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    src_ext = registry.get_extension(input_path)
    dst_ext = target_format.lower().lstrip(".")

    if not output_path:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(os.path.dirname(input_path) or ".", f"{base_name}.{dst_ext}")
    elif os.path.isdir(output_path):
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(output_path, f"{base_name}.{dst_ext}")

    engine = registry.resolve_engine(src_ext, dst_ext)
    if not engine:
        print(f"Error: No conversion engine available for {src_ext} -> {dst_ext}", file=sys.stderr)
        return 1

    print(f"OmniConvert v1.0.0")
    print(f"Input:   {input_path} ({format_bytes(os.path.getsize(input_path))})")
    print(f"Output:  {output_path}")
    print(f"Engine:  {engine.name}")
    print(f"Profile: {power_mode.upper()} | Lossless: {lossless}")
    print("-" * 60)

    try:
        success = engine.convert(
            source_path=input_path,
            target_path=output_path,
            options={"lossless": lossless, "power_mode": power_mode},
            progress_callback=print_progress,
            cancel_token=CancellationToken()
        )
        if success:
            out_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            print(f"Conversion finished successfully! Output size: {format_bytes(out_size)}")
            return 0
        else:
            print("Conversion returned failure.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"\nConversion failed: {e}", file=sys.stderr)
        return 1


def launch_gui(initial_files=None):
    from PyQt6.QtWidgets import QApplication
    from converter.ui.main_window import MainWindow

    # Enable High DPI scaling
    app = QApplication(sys.argv)
    app.setApplicationName("OmniConvert")
    app.setApplicationDisplayName("OmniConvert")

    window = MainWindow(initial_files=initial_files)
    window.show()
    sys.exit(app.exec())
