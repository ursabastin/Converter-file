"""
OmniConvert - Universal High-Fidelity File Converter
Entry point for GUI and CLI operations.
"""

import sys
import os

# Ensure the project root is in sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from converter.cli import launch_gui, run_cli_conversion
from setup_terminal import install_wrappers


def main():
    args = sys.argv[1:]

    # Check for terminal setup command
    if "--setup-terminal" in args or "--install" in args:
        install_wrappers()
        return

    # Check for CLI flags: -i / --input
    if "-i" in args or "--input" in args:
        import argparse
        parser = argparse.ArgumentParser(
            description="OmniConvert - Universal High-Fidelity File Converter",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument("-converter", "--gui", action="store_true", help="Launch the modern graphical user interface")
        parser.add_argument("-i", "--input", required=True, help="Path to input source file")
        parser.add_argument("-o", "--output", default="", help="Path to target output file or directory")
        parser.add_argument("-f", "--format", required=True, help="Target format extension (e.g. webp, mp3, pdf, xlsx, zip)")
        parser.add_argument("--power", choices=["eco", "balanced", "turbo"], default="balanced", help="Power profile for low hardware stress")
        parser.add_argument("--lossless", action="store_true", default=True, help="Preserve highest fidelity/lossless encoding")
        
        parsed = parser.parse_args()
        sys.exit(run_cli_conversion(
            input_path=parsed.input,
            output_path=parsed.output,
            target_format=parsed.format,
            power_mode=parsed.power,
            lossless=parsed.lossless
        ))

    # Strip -converter or --gui flag if present
    clean_files = [a for a in args if a not in ("-converter", "--converter", "-gui", "--gui")]

    # If file paths were passed as positional arguments, pass them into GUI
    existing_files = [os.path.abspath(f) for f in clean_files if os.path.exists(f)]

    # Launch GUI
    launch_gui(initial_files=existing_files)


if __name__ == "__main__":
    main()
