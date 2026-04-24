#!/usr/bin/env python3
"""Entry point for the Renamer application."""

import sys
import os

# Add renamer folder to path
app_path = os.path.dirname(os.path.abspath(__file__))
if app_path not in sys.path:
    sys.path.insert(0, app_path)


def check_dependencies():
    """Check if all required dependencies are installed."""
    missing = []
    optional_missing = []

    try:
        import tkinter
    except ImportError:
        missing.append("tkinter (встановіть: sudo apt install python3-tk або brew install python-tk)")

    try:
        import tkinterdnd2
    except ImportError:
        optional_missing.append("tkinterdnd2 (drag & drop не працюватиме)")

    try:
        import ttkbootstrap
    except ImportError:
        missing.append("ttkbootstrap")

    try:
        import mutagen
    except ImportError:
        missing.append("mutagen")

    try:
        import PIL
    except ImportError:
        missing.append("Pillow")

    if missing:
        print("=" * 50)
        print("❌ Відсутні залежності / Missing dependencies:")
        print("=" * 50)
        for dep in missing:
            print(f"  • {dep}")
        print()
        print("Встановіть їх командою / Install them with:")
        print("  pip install -r requirements.txt")
        print()
        print("Або окремо / Or individually:")
        print("  pip install ttkbootstrap mutagen Pillow tkinterdnd2")
        print("=" * 50)
        sys.exit(1)

    if optional_missing:
        print("⚠️  Опціональні залежності / Optional dependencies:")
        for dep in optional_missing:
            print(f"   • {dep}")
        print()


def main():
    """Launch the Renamer GUI application."""
    check_dependencies()
    from renamer.app import main as app_main
    app_main()


if __name__ == "__main__":
    main()
