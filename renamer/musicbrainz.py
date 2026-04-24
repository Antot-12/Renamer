"""MusicBrainz API integration for fetching audio metadata."""

from __future__ import annotations

import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, List, Optional, Any
import time

# MusicBrainz API base URL
MB_API_BASE = "https://musicbrainz.org/ws/2"

# User agent required by MusicBrainz API
USER_AGENT = "Renamer/1.0 (https://github.com/Antot-12/Renamer)"

# Rate limiting (1 request per second per MusicBrainz policy)
_last_request_time = 0.0


def _rate_limit() -> None:
    """Ensure we don't exceed MusicBrainz rate limit."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_time = time.time()


def _make_request(url: str) -> Optional[Dict[str, Any]]:
    """Make a request to MusicBrainz API."""
    _rate_limit()

    request = urllib.request.Request(url)
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError):
        return None


def search_recording(
    artist: Optional[str] = None,
    title: Optional[str] = None,
    album: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Search MusicBrainz for recordings.

    Args:
        artist: Artist name to search for
        title: Track title to search for
        album: Album name to search for
        limit: Maximum number of results

    Returns:
        List of recording results with metadata
    """
    if not artist and not title:
        return []

    query_parts = []
    if artist:
        query_parts.append(f'artist:"{artist}"')
    if title:
        query_parts.append(f'recording:"{title}"')
    if album:
        query_parts.append(f'release:"{album}"')

    query = " AND ".join(query_parts)
    encoded_query = urllib.parse.quote(query)

    url = f"{MB_API_BASE}/recording?query={encoded_query}&limit={limit}&fmt=json"

    data = _make_request(url)
    if not data or "recordings" not in data:
        return []

    results = []
    for recording in data["recordings"][:limit]:
        result = {
            "id": recording.get("id"),
            "title": recording.get("title"),
            "artist": None,
            "album": None,
            "year": None,
            "duration": recording.get("length"),  # in milliseconds
            "score": recording.get("score", 0),
        }

        # Get artist
        artist_credits = recording.get("artist-credit", [])
        if artist_credits:
            artists = [ac.get("name", "") for ac in artist_credits if "name" in ac]
            result["artist"] = " & ".join(artists) if artists else None

        # Get album (first release)
        releases = recording.get("releases", [])
        if releases:
            first_release = releases[0]
            result["album"] = first_release.get("title")
            date = first_release.get("date", "")
            if date:
                result["year"] = date[:4] if len(date) >= 4 else date

        results.append(result)

    return results


def get_recording_details(recording_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information for a specific recording.

    Args:
        recording_id: MusicBrainz recording ID

    Returns:
        Dict with recording details or None if not found
    """
    url = f"{MB_API_BASE}/recording/{recording_id}?inc=artists+releases+genres&fmt=json"

    data = _make_request(url)
    if not data:
        return None

    result = {
        "id": data.get("id"),
        "title": data.get("title"),
        "artist": None,
        "album": None,
        "year": None,
        "genre": None,
        "duration": data.get("length"),
    }

    # Get artist
    artist_credits = data.get("artist-credit", [])
    if artist_credits:
        artists = [ac.get("name", "") for ac in artist_credits if "name" in ac]
        result["artist"] = " & ".join(artists) if artists else None

    # Get album and year from releases
    releases = data.get("releases", [])
    if releases:
        first_release = releases[0]
        result["album"] = first_release.get("title")
        date = first_release.get("date", "")
        if date:
            result["year"] = date[:4] if len(date) >= 4 else date

    # Get genre
    genres = data.get("genres", [])
    if genres:
        result["genre"] = genres[0].get("name")

    return result


def search_by_filename(filename: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search MusicBrainz using a filename to extract artist and title.

    Tries common filename patterns like:
    - "Artist - Title.mp3"
    - "Title - Artist.mp3"
    - "01 - Artist - Title.mp3"

    Args:
        filename: Filename without extension
        limit: Maximum number of results

    Returns:
        List of recording results
    """
    import re

    # Remove common prefix patterns (track numbers)
    name = re.sub(r'^[\d\s\-_.]+', '', filename).strip()

    # Try "Artist - Title" pattern
    if " - " in name:
        parts = name.split(" - ", 1)
        if len(parts) == 2:
            artist, title = parts[0].strip(), parts[1].strip()
            results = search_recording(artist=artist, title=title, limit=limit)
            if results:
                return results

            # Try reversed (Title - Artist)
            results = search_recording(artist=title, title=artist, limit=limit)
            if results:
                return results

    # Search by the whole name as title
    return search_recording(title=name, limit=limit)
