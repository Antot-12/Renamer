"""
Renamer - A cross-platform desktop GUI application for batch file renaming.

Features:
- Smart metadata extraction from audio files
- Flexible templating system for renaming patterns
- Support for multiple file types (audio, images, documents, video, archives)
- Drag-and-drop functionality
- Live logging of operations
"""

__version__ = "1.0.0"
__author__ = "Anton Shyrko"

from renamer.constants import (
    AUDIO,
    IMG,
    DOC,
    VID,
    ARC,
    PRESENTATION,
    CODE,
    TEXT,
    GAME,
    SUPPORTED,
    MAX_FILES,
    MAX_PREVIEW_SIZE,
)

__all__ = [
    "AUDIO",
    "IMG",
    "DOC",
    "VID",
    "ARC",
    "PRESENTATION",
    "CODE",
    "TEXT",
    "GAME",
    "SUPPORTED",
    "MAX_FILES",
    "MAX_PREVIEW_SIZE",
    "__version__",
]


def get_app():
    """Lazy import of RenamerApp to avoid GUI dependencies during testing."""
    from renamer.app import RenamerApp
    return RenamerApp
