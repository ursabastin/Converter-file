"""
Automated Terminal Integration Installer for OmniConvert.
Installs executable batch/cmd launchers into WindowsApps (on Windows PATH) so that
typing `anyotherterminal -converter` or `converter` works from any terminal anywhere.
"""

import os
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = os.path.join(PROJECT_DIR, "main.py")
PYTHON_EXE = sys.executable

# Standard Windows user path directories already in PATH
USER_APPS_DIR = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")
LOCAL_BIN_DIR = os.path.join(PROJECT_DIR, "bin")


def install_wrappers():
    os.makedirs(LOCAL_BIN_DIR, exist_ok=True)
    target_dirs = [LOCAL_BIN_DIR]

    if os.path.exists(USER_APPS_DIR) and os.access(USER_APPS_DIR, os.W_OK):
        target_dirs.append(USER_APPS_DIR)

    # 1. anyotherterminal.cmd:
    # Supports `anyotherterminal -converter` or `anyotherterminal ...`
    anyother_cmd_content = f"""@echo off
"{PYTHON_EXE}" "{MAIN_SCRIPT}" %*
"""

    # Clean up any legacy .ps1 files that trigger PowerShell execution policy errors
    for tdir in target_dirs:
        for fname in ["anyotherterminal.ps1", "converter.ps1", "file-converter.ps1"]:
            old_ps1 = os.path.join(tdir, fname)
            if os.path.exists(old_ps1):
                try:
                    os.remove(old_ps1)
                except OSError:
                    pass

    # Batch and CMD wrappers (native Windows executables that bypass PowerShell script execution policies)
    cmd_content = f"""@echo off
"{PYTHON_EXE}" "{MAIN_SCRIPT}" %*
"""

    installed_locations = []

    for tdir in target_dirs:
        try:
            for name in ["anyotherterminal", "converter", "file-converter"]:
                for ext in [".cmd", ".bat"]:
                    wrapper_path = os.path.join(tdir, f"{name}{ext}")
                    with open(wrapper_path, "w", encoding="utf-8") as f:
                        f.write(cmd_content)

            installed_locations.append(tdir)
        except Exception as e:
            print(f"Warning: Could not write to {tdir}: {e}")

    print("\n" + "=" * 60)
    print("OmniConvert Terminal Integration Installed Successfully!")
    print("=" * 60)
    for loc in installed_locations:
        print(f"  [OK] Installed command wrappers to: {loc}")
    print("\nYou can now launch the converter from ANY terminal anywhere using:")
    print("  -> anyotherterminal -converter")
    print("  -> converter")
    print("  -> file-converter")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    install_wrappers()
