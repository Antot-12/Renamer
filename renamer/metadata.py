"""Metadata extraction for various file types."""

from __future__ import annotations

import os
import platform
import re
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

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
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    MUTAGEN_AVAILABLE = True
except ImportError:
    AudioFile = None  # type: ignore
    MutagenError = Exception  # type: ignore
    EasyID3 = None  # type: ignore
    ID3 = None  # type: ignore
    FLAC = None  # type: ignore
    MP4 = None  # type: ignore
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


def get_audio_tags_extended(filepath: str) -> Dict[str, Any]:
    """
    Extract extended metadata from audio file.

    Returns:
        Dict with keys: artist, title, album, year, genre, track, duration, bitrate
    """
    result = {
        "artist": None,
        "title": None,
        "album": None,
        "year": None,
        "genre": None,
        "track": None,
        "duration": None,
        "bitrate": None,
    }

    if not MUTAGEN_AVAILABLE:
        return result

    try:
        audio = AudioFile(filepath, easy=True)
        if not audio:
            return result

        result["duration"] = audio.info.length if audio.info else None
        result["bitrate"] = audio.info.bitrate if audio.info else None
        result["artist"] = audio.get('artist', [None])[0]
        result["title"] = audio.get('title', [None])[0]
        result["album"] = audio.get('album', [None])[0]
        result["genre"] = audio.get('genre', [None])[0]

        # Year handling (can be 'date' or 'year')
        year = audio.get('date', [None])[0] or audio.get('year', [None])[0]
        if year:
            # Extract just the year if it's a full date
            year_match = re.match(r'(\d{4})', str(year))
            result["year"] = year_match.group(1) if year_match else year

        # Track number
        track = audio.get('tracknumber', [None])[0]
        if track:
            # Handle "1/12" format
            track_match = re.match(r'(\d+)', str(track))
            result["track"] = track_match.group(1) if track_match else track

        return result

    except (MutagenError, FileNotFoundError, PermissionError, OSError):
        return result


def write_audio_tags(filepath: str, tags: Dict[str, Any]) -> bool:
    """
    Write metadata tags to audio file.

    Args:
        filepath: Path to audio file
        tags: Dict with keys: artist, title, album, year, genre, track

    Returns:
        True if successful, False otherwise
    """
    if not MUTAGEN_AVAILABLE:
        return False

    try:
        audio = AudioFile(filepath, easy=True)
        if not audio:
            return False

        # Map tag names
        tag_map = {
            'artist': 'artist',
            'title': 'title',
            'album': 'album',
            'year': 'date',
            'genre': 'genre',
            'track': 'tracknumber',
        }

        for key, tag_name in tag_map.items():
            if key in tags and tags[key] is not None:
                value = str(tags[key])
                if value:
                    audio[tag_name] = value
                elif tag_name in audio:
                    del audio[tag_name]

        audio.save()
        return True

    except (MutagenError, FileNotFoundError, PermissionError, OSError):
        return False


def get_file_dates(filepath: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Get file creation and modification dates.

    Args:
        filepath: Path to file

    Returns:
        Tuple of (created_date, modified_date)
    """
    try:
        stat = os.stat(filepath)

        # Modification time is consistent across platforms
        modified = datetime.fromtimestamp(stat.st_mtime)

        # Creation time varies by platform
        if platform.system() == 'Windows':
            created = datetime.fromtimestamp(stat.st_ctime)
        elif platform.system() == 'Darwin':  # macOS
            created = datetime.fromtimestamp(stat.st_birthtime)
        else:  # Linux - use ctime as fallback (not true creation time)
            created = datetime.fromtimestamp(stat.st_ctime)

        return created, modified

    except (OSError, AttributeError):
        return None, None


def format_duration(seconds: Optional[float]) -> str:
    """Format duration in seconds to mm:ss or hh:mm:ss."""
    if seconds is None:
        return ""

    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} MB"
    return f"{size_bytes / 1024 / 1024 / 1024:.2f} GB"


def get_album_art(filepath: str) -> Optional[bytes]:
    """
    Extract album art image data from audio file.

    Args:
        filepath: Path to audio file

    Returns:
        Raw image bytes or None if no art found
    """
    if not MUTAGEN_AVAILABLE:
        return None

    try:
        audio = AudioFile(filepath)
        if not audio:
            return None

        ext = os.path.splitext(filepath)[1].lower()

        if ext == '.mp3':
            if ID3:
                try:
                    tags = ID3(filepath)
                    for key in tags.keys():
                        if key.startswith('APIC'):
                            return tags[key].data
                except Exception:
                    pass

        elif ext == '.flac':
            if FLAC:
                try:
                    flac = FLAC(filepath)
                    if flac.pictures:
                        return flac.pictures[0].data
                except Exception:
                    pass

        elif ext in ('.m4a', '.mp4', '.m4b'):
            if MP4:
                try:
                    mp4 = MP4(filepath)
                    covers = mp4.tags.get('covr', [])
                    if covers:
                        return bytes(covers[0])
                except Exception:
                    pass

        return None

    except (MutagenError, FileNotFoundError, PermissionError, OSError):
        return None
