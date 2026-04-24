#!/usr/bin/env python3
"""Build script for creating lightweight Windows executable."""

import subprocess
import sys
import shutil
from pathlib import Path

def build():
    """Build the executable."""
    print("🔨 Building Renamer.exe...")

    # PyInstaller command for lightweight, fast executable
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",           # Single file executable
        "--windowed",          # No console window
        "--name=Renamer",      # Output name
        "--icon=rename.ico",   # App icon
        "--noconfirm",         # Overwrite without asking
        "--clean",             # Clean cache

        # Optimize for size
        "--strip",             # Strip debug symbols (Linux/Mac)

        # Exclude unnecessary modules
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "--exclude-module=pytest",
        "--exclude-module=setuptools",
        "--exclude-module=wheel",
        "--exclude-module=pip",
        "--exclude-module=tkinterdnd2",  # Optional, may not work

        # Hidden imports that might be needed
        "--hidden-import=PIL._tkinter_finder",

        # Entry point
        "run.py"
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n✅ Build successful!")
        print("📁 Executable: dist/Renamer.exe")

        # Show file size
        exe_path = Path("dist/Renamer.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📊 Size: {size_mb:.1f} MB")
    else:
        print("\n❌ Build failed!")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(build())
