"""Duplicate file detection using file hashing."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Dict, List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from renamer.file_ops import FileEntry


def calculate_file_hash(filepath: str, chunk_size: int = 8192, algorithm: str = "md5") -> Optional[str]:
    """
    Calculate hash of a file.

    Args:
        filepath: Path to file
        chunk_size: Size of chunks to read (default 8KB)
        algorithm: Hash algorithm ('md5', 'sha1', 'sha256')

    Returns:
        Hex digest of file hash, or None on error
    """
    try:
        if algorithm == "md5":
            hasher = hashlib.md5()
        elif algorithm == "sha1":
            hasher = hashlib.sha1()
        elif algorithm == "sha256":
            hasher = hashlib.sha256()
        else:
            hasher = hashlib.md5()

        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)

        return hasher.hexdigest()

    except (OSError, PermissionError, FileNotFoundError):
        return None


def calculate_partial_hash(filepath: str, size: int = 65536) -> Optional[str]:
    """
    Calculate hash of first N bytes of file (faster for large files).
    Good for quick duplicate detection before full hash.
    """
    try:
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            data = f.read(size)
            hasher.update(data)
        return hasher.hexdigest()
    except (OSError, PermissionError, FileNotFoundError):
        return None


def find_duplicates(
    entries: List["FileEntry"],
    on_progress: Optional[Callable[[int, int], None]] = None
) -> Dict[str, List["FileEntry"]]:
    """
    Find duplicate files among entries.

    Uses two-phase detection:
    1. Group by file size (quick filter)
    2. Hash files with same size

    Args:
        entries: List of FileEntry objects
        on_progress: Optional callback(current, total) for progress updates

    Returns:
        Dictionary mapping hash -> list of duplicate FileEntry objects
        Only includes groups with 2+ files
    """
    # Phase 1: Group by size
    size_groups: Dict[int, List["FileEntry"]] = defaultdict(list)

    for entry in entries:
        if entry.size > 0:
            size_groups[entry.size].append(entry)

    # Phase 2: Hash files with matching sizes
    duplicates: Dict[str, List["FileEntry"]] = defaultdict(list)
    files_to_hash = []

    for size, group in size_groups.items():
        if len(group) > 1:
            files_to_hash.extend(group)

    total = len(files_to_hash)
    for i, entry in enumerate(files_to_hash):
        if on_progress:
            on_progress(i + 1, total)

        file_hash = calculate_file_hash(entry.path)
        if file_hash:
            entry.file_hash = file_hash
            duplicates[file_hash].append(entry)

    # Filter to only groups with duplicates
    return {h: group for h, group in duplicates.items() if len(group) > 1}


def find_duplicates_quick(
    entries: List["FileEntry"],
    on_progress: Optional[Callable[[int, int], None]] = None
) -> Dict[str, List["FileEntry"]]:
    """
    Quick duplicate detection using partial hash.
    Faster but may have false positives for large files.
    """
    # Group by size first
    size_groups: Dict[int, List["FileEntry"]] = defaultdict(list)

    for entry in entries:
        if entry.size > 0:
            size_groups[entry.size].append(entry)

    # Partial hash for same-size files
    duplicates: Dict[str, List["FileEntry"]] = defaultdict(list)
    files_to_hash = []

    for size, group in size_groups.items():
        if len(group) > 1:
            files_to_hash.extend(group)

    total = len(files_to_hash)
    for i, entry in enumerate(files_to_hash):
        if on_progress:
            on_progress(i + 1, total)

        # Use size + partial hash as key
        partial = calculate_partial_hash(entry.path)
        if partial:
            key = f"{entry.size}_{partial}"
            duplicates[key].append(entry)

    return {h: group for h, group in duplicates.items() if len(group) > 1}


def get_duplicate_groups(
    entries: List["FileEntry"],
    quick: bool = True,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> List[List["FileEntry"]]:
    """
    Get list of duplicate groups.

    Args:
        entries: List of FileEntry objects
        quick: Use quick (partial) hash detection
        on_progress: Progress callback

    Returns:
        List of lists, where each inner list contains duplicate entries
    """
    if quick:
        duplicates = find_duplicates_quick(entries, on_progress)
    else:
        duplicates = find_duplicates(entries, on_progress)

    return list(duplicates.values())


def mark_duplicates(
    entries: List["FileEntry"],
    quick: bool = True,
    on_progress: Optional[Callable[[int, int], None]] = None
) -> int:
    """
    Mark entries that are duplicates by setting file_hash.

    Returns:
        Number of duplicate groups found
    """
    groups = get_duplicate_groups(entries, quick, on_progress)
    return len(groups)


def get_duplicate_stats(entries: List["FileEntry"]) -> Dict[str, int]:
    """
    Get statistics about duplicates.

    Returns:
        Dict with keys: total_files, unique_files, duplicate_groups, wasted_space
    """
    groups = find_duplicates(entries)

    total_files = len(entries)
    duplicate_files = sum(len(g) for g in groups.values())
    unique_in_groups = len(groups)  # One unique per group

    # Space wasted = (files in group - 1) * size for each group
    wasted_space = 0
    for group in groups.values():
        if group:
            wasted_space += (len(group) - 1) * group[0].size

    return {
        "total_files": total_files,
        "unique_files": total_files - duplicate_files + unique_in_groups,
        "duplicate_groups": len(groups),
        "duplicate_files": duplicate_files - unique_in_groups,
        "wasted_space": wasted_space,
    }
