"""Windows-specific integration features."""

from __future__ import annotations

import sys
import os
import platform
from typing import Optional


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def get_exe_path() -> str:
    """Get the path to the current executable."""
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return sys.executable
    else:
        # Running as script
        return os.path.abspath(sys.argv[0])


def add_context_menu() -> bool:
    """
    Add 'Rename with Renamer' to Windows Explorer context menu.

    This adds a right-click option for all files (*).
    Requires admin privileges to write to HKEY_CLASSES_ROOT.

    Returns:
        True if successful, False otherwise.
    """
    if not is_windows():
        return False

    try:
        import winreg

        exe_path = get_exe_path()
        key_path = r"*\shell\RenameWithRenamer"

        # Create the context menu entry
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "Rename with Renamer")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path)

        # Create the command subkey
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')

        return True
    except PermissionError:
        # Need admin privileges
        return False
    except Exception:
        return False


def remove_context_menu() -> bool:
    """
    Remove 'Rename with Renamer' from Windows Explorer context menu.

    Returns:
        True if successful, False otherwise.
    """
    if not is_windows():
        return False

    try:
        import winreg

        key_path = r"*\shell\RenameWithRenamer"

        # Delete command subkey first
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command")
        except FileNotFoundError:
            pass

        # Delete main key
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
        except FileNotFoundError:
            pass

        return True
    except PermissionError:
        return False
    except Exception:
        return False


def is_context_menu_installed() -> bool:
    """Check if context menu is already installed."""
    if not is_windows():
        return False

    try:
        import winreg

        key_path = r"*\shell\RenameWithRenamer"
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path):
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def add_folder_context_menu() -> bool:
    """
    Add 'Rename files with Renamer' to folder context menu.

    This allows right-clicking a folder to open it in Renamer.
    Requires admin privileges.

    Returns:
        True if successful, False otherwise.
    """
    if not is_windows():
        return False

    try:
        import winreg

        exe_path = get_exe_path()
        key_path = r"Directory\shell\RenameWithRenamer"

        # Create the context menu entry for folders
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "Rename files with Renamer")
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, exe_path)

        # Create the command subkey
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command") as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')

        return True
    except PermissionError:
        return False
    except Exception:
        return False


def remove_folder_context_menu() -> bool:
    """Remove folder context menu entry."""
    if not is_windows():
        return False

    try:
        import winreg

        key_path = r"Directory\shell\RenameWithRenamer"

        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path + r"\command")
        except FileNotFoundError:
            pass

        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
        except FileNotFoundError:
            pass

        return True
    except PermissionError:
        return False
    except Exception:
        return False


def run_as_admin(command: Optional[str] = None) -> bool:
    """
    Restart the application with admin privileges.

    Args:
        command: Optional command to run (defaults to current script)

    Returns:
        True if elevation was requested, False otherwise.
    """
    if not is_windows():
        return False

    try:
        import ctypes

        if command is None:
            command = get_exe_path()

        # Use ShellExecute to run as admin
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # Operation (run as admin)
            command,        # File
            None,           # Parameters
            None,           # Directory
            1               # Show command (SW_SHOWNORMAL)
        )

        # ShellExecute returns > 32 on success
        return result > 32
    except Exception:
        return False


def is_admin() -> bool:
    """Check if running with admin privileges."""
    if not is_windows():
        return False

    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False
