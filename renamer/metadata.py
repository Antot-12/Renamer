"""Metadata extraction for various file types."""

from __future__ import annotations

import os
import re
from typing import Optional, Tuple

from PIL import Image, UnidentifiedImageError

from renamer.constants import (
    AUDIO,
    IMG,
    ILLEGAL_CHARS_PATTERN,
    MAX_PREVIEW_MEMORY,
)

try:
    from mutagen import File as AudioFile
    from mutagen import MutagenError
    MUTAGEN_AVAILABLE = True
except ImportError:
    AudioFile = None  # type: ignore
    MutagenError = Exception  # type: ignore
    MUTAGEN_AVAILABLE = False


def sanitize(text: Optional[str]) -> str:
    """
    Remove illegal filename characters and normalize whitespace.

    Args:
        text: Input string to sanitize (can be None)

    Returns:
        Sanitized string with illegal characters removed and whitespace normalized
    """
    if not text:
        return ""
    cleaned = re.sub(ILLEGAL_CHARS_PATTERN, '', text)
    normalized = re.sub(r'\s+', ' ', cleaned)
    return normalized.strip()


def bytes_to_human_readable(size_bytes: Optional[int]) -> str:
    """
    Convert bytes to human-readable format (MB).

    Args:
        size_bytes: File size in bytes

    Returns:
        Human-readable string (e.g., "1.5 MB") or empty string if None
    """
    if not size_bytes:
        return ""
    return f"{size_bytes / 1024 / 1024:.1f} MB"


def get_audio_tags(filepath: str) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[int]]:
    """
    Extract metadata tags from an audio file.

    Args:
        filepath: Path to the audio file

    Returns:
        Tuple of (artist, title, duration_seconds, bitrate_bps)
        Returns (None, None, None, None) if extraction fails
    """
    if not MUTAGEN_AVAILABLE:
        return None, None, None, None

    try:
        audio = AudioFile(filepath, easy=True)
        if not audio:
            return None, None, None, None

        duration = audio.info.length if audio.info else None
        bitrate = audio.info.bitrate if audio.info else None
        artist = audio.get('artist', [None])[0]
        title = audio.get('title', [None])[0]

        return artist, title, duration, bitrate

    except MutagenError:
        return None, None, None, None
    except FileNotFoundError:
        return None, None, None, None
    except PermissionError:
        return None, None, None, None
    except OSError:
        return None, None, None, None


def get_image_dimensions(filepath: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Get dimensions of an image file.

    Args:
        filepath: Path to the image file

    Returns:
        Tuple of (width, height) or (None, None) if extraction fails
    """
    try:
        file_size = os.path.getsize(filepath)
        if file_size > MAX_PREVIEW_MEMORY:
            return None, None

        with Image.open(filepath) as img:
            return img.size
    except (FileNotFoundError, PermissionError, OSError, UnidentifiedImageError):
        return None, None


def extract_metadata(filepath: str, extension: str) -> Tuple[Optional[str], Optional[str], str, int]:
    """
    Extract metadata from a file based on its type.

    Args:
        filepath: Path to the file
        extension: File extension (lowercase, with dot)

    Returns:
        Tuple of (artist, title, info_string, file_size_bytes)

    Raises:
        FileNotFoundError: If the file doesn't exist
        PermissionError: If the file can't be read
    """
    size = os.path.getsize(filepath)

    if extension in AUDIO:
        artist, title, duration, bitrate = get_audio_tags(filepath)
        if duration is not None:
            bitrate_str = f"{bitrate // 1000}kbps" if bitrate else ""
            info = f"{int(duration)}s / {bitrate_str}" if bitrate_str else f"{int(duration)}s"
        else:
            info = ""
        return artist, title, info, size

    if extension in IMG:
        width, height = get_image_dimensions(filepath)
        info = f"{width}×{height}" if width and height else ""
        return None, None, info, size

    return None, None, "", size


def format_audio_info(duration: Optional[float], bitrate: Optional[int]) -> str:
    """
    Format audio duration and bitrate into a display string.

    Args:
        duration: Duration in seconds
        bitrate: Bitrate in bits per second

    Returns:
        Formatted string like "180s / 320kbps"
    """
    if duration is None:
        return ""

    parts = [f"{int(duration)}s"]
    if bitrate:
        parts.append(f"{bitrate // 1000}kbps")

    return " / ".join(parts)
