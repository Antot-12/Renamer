"""File operations with threading support."""

from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Generator, List, Optional, Set, Any
import tkinter as tk

from renamer.constants import MAX_FILES


@dataclass
class FileEntry:
    """Represents a file entry in the rename queue."""

    path: str
    original: str
    directory: str
    new_name: str
    ext: str
    file_type: str
    selected: tk.BooleanVar = field(default_factory=lambda: tk.BooleanVar(value=True))
    size: int = 0
    info: str = ""
    # New fields for enhanced features
    relative_path: str = ""  # Path relative to base folder (for subfolder support)
    file_hash: Optional[str] = None  # MD5 hash for duplicate detection
    created_date: Optional[datetime] = None  # File creation date
    modified_date: Optional[datetime] = None  # File modification date
    metadata: Dict[str, Any] = field(default_factory=dict)  # Extended metadata (audio tags, etc.)

    def to_dict(self) -> dict:
        """Convert entry to dictionary for compatibility."""
        return {
            "path": self.path,
            "original": self.original,
            "directory": self.directory,
            "new_name": self.new_name,
            "ext": self.ext,
            "type": self.file_type,
            "selected": self.selected,
            "size": self.size,
            "info": self.info,
            "relative_path": self.relative_path,
            "file_hash": self.file_hash,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "modified_date": self.modified_date.isoformat() if self.modified_date else None,
            "metadata": self.metadata,
        }


class AppState:
    """
    Central state management for the application.
    Replaces global variables with encapsulated state.
    """

    def __init__(self) -> None:
        self.entries: List[FileEntry] = []
        self.path_set: Set[str] = set()
        self.target_dir: Optional[str] = None
        self._lock = threading.Lock()

    def add_entry(self, entry: FileEntry) -> bool:
        """
        Add an entry to the state if not already present.

        Args:
            entry: FileEntry to add

        Returns:
            True if added, False if already exists or at limit
        """
        with self._lock:
            if entry.path in self.path_set:
                return False
            if len(self.entries) >= MAX_FILES:
                return False
            self.entries.append(entry)
            self.path_set.add(entry.path)
            return True

    def remove_entry(self, index: int) -> Optional[FileEntry]:
        """
        Remove an entry by index.

        Args:
            index: Index of entry to remove

        Returns:
            Removed entry or None if index invalid
        """
        with self._lock:
            if 0 <= index < len(self.entries):
                entry = self.entries.pop(index)
                self.path_set.discard(entry.path)
                return entry
            return None

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self.entries.clear()
            self.path_set.clear()

    def get_selected(self) -> List[FileEntry]:
        """Get all selected entries."""
        with self._lock:
            return [e for e in self.entries if e.selected.get()]

    def count_selected(self) -> int:
        """Count selected entries."""
        with self._lock:
            return sum(1 for e in self.entries if e.selected.get())

    def is_at_limit(self) -> bool:
        """Check if at file limit."""
        return len(self.entries) >= MAX_FILES

    def get_remaining_capacity(self) -> int:
        """Get remaining file capacity."""
        return MAX_FILES - len(self.entries)

    def sort_entries(self, key: str, reverse: bool = False) -> None:
        """
        Sort entries by specified key.

        Args:
            key: Sort key - 'name', 'size', 'date', 'type', 'modified', 'created'
            reverse: Reverse sort order
        """
        with self._lock:
            if key == "name":
                self.entries.sort(key=lambda e: e.original.lower(), reverse=reverse)
            elif key == "size":
                self.entries.sort(key=lambda e: e.size, reverse=reverse)
            elif key == "type":
                self.entries.sort(key=lambda e: e.ext.lower(), reverse=reverse)
            elif key == "modified":
                self.entries.sort(
                    key=lambda e: e.modified_date or datetime.min,
                    reverse=reverse
                )
            elif key == "created":
                self.entries.sort(
                    key=lambda e: e.created_date or datetime.min,
                    reverse=reverse
                )
            elif key == "date":
                # Default to modified date
                self.entries.sort(
                    key=lambda e: e.modified_date or datetime.min,
                    reverse=reverse
                )

    def filter_entries(self, file_type: Optional[str] = None) -> List[FileEntry]:
        """
        Get entries filtered by type.

        Args:
            file_type: Filter by type (None or 'all' = no filter)

        Returns:
            Filtered list of entries
        """
        with self._lock:
            if not file_type or file_type.lower() == "all":
                return list(self.entries)
            return [e for e in self.entries if e.file_type.lower() == file_type.lower()]

    def get_by_extension(self, ext: str) -> List[FileEntry]:
        """Get entries with specific extension."""
        ext_lower = ext.lower().lstrip('.')
        with self._lock:
            return [e for e in self.entries if e.ext.lower().lstrip('.') == ext_lower]

    def get_unique_extensions(self) -> List[str]:
        """Get list of unique file extensions."""
        with self._lock:
            exts = set(e.ext.lower() for e in self.entries if e.ext)
            return sorted(exts)

    def get_unique_types(self) -> List[str]:
        """Get list of unique file types."""
        with self._lock:
            types = set(e.file_type for e in self.entries if e.file_type)
            return sorted(types)


def collect_files(paths: List[str]) -> Generator[str, None, None]:
    """
    Recursively collect files from paths (files and directories).

    Args:
        paths: List of file/directory paths

    Yields:
        Individual file paths
    """
    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for filename in files:
                    yield os.path.join(root, filename)
        elif os.path.isfile(path):
            yield path


def is_duplicate_name(
    name: str,
    directory: str,
    entries: List[FileEntry],
    skip_index: int,
    target_dir: Optional[str] = None
) -> bool:
    """
    Check if a filename would be a duplicate (case-insensitive).

    Args:
        name: Proposed filename
        directory: Original file directory
        entries: List of all entries
        skip_index: Index to skip in comparison
        target_dir: Override target directory

    Returns:
        True if duplicate would exist
    """
    effective_dir = target_dir or directory
    name_lower = name.lower()

    for i, entry in enumerate(entries):
        if i == skip_index:
            continue
        entry_dir = target_dir or entry.directory
        if entry_dir == effective_dir and entry.new_name.lower() == name_lower:
            return True
    return False


def check_for_duplicate_destinations(
    entries: List[FileEntry],
    target_dir: Optional[str] = None
) -> bool:
    """
    Check if any selected entries would create duplicates.

    Uses case-insensitive comparison for Windows compatibility.

    Args:
        entries: List of file entries
        target_dir: Optional override target directory

    Returns:
        True if duplicates exist
    """
    dest_names: Set[str] = set()

    for entry in entries:
        if not entry.selected.get():
            continue
        dest = target_dir or entry.directory
        full_dest = os.path.join(dest, entry.new_name.lower())
        if full_dest in dest_names:
            return True
        dest_names.add(full_dest)

    return False


class FileOperationWorker:
    """Threaded worker for file operations to prevent UI freezing."""

    def __init__(
        self,
        entries: List[FileEntry],
        target_dir: Optional[str],
        copy_mode: bool,
        on_success: Callable[[FileEntry], None],
        on_error: Callable[[FileEntry, str], None],
        on_complete: Callable[[], None],
        backup_dir: Optional[str] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        """
        Initialize the worker.

        Args:
            entries: List of entries to process
            target_dir: Target directory (None = original directory)
            copy_mode: True to copy, False to move
            on_success: Callback for successful operations
            on_error: Callback for failed operations
            on_complete: Callback when all operations complete
            backup_dir: Optional backup directory (creates copies before rename)
            on_progress: Optional callback(current, total, filename) for progress
        """
        self.entries = entries
        self.target_dir = target_dir
        self.copy_mode = copy_mode
        self.on_success = on_success
        self.on_error = on_error
        self.on_complete = on_complete
        self.backup_dir = backup_dir
        self.on_progress = on_progress
        self._thread: Optional[threading.Thread] = None
        self._cancelled = False
        self.operations: List[Dict[str, Any]] = []  # Track operations for undo

    def start(self) -> None:
        """Start the file operation in a background thread."""
        self._cancelled = False
        self.operations = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Cancel the operation (best effort)."""
        self._cancelled = True

    def _create_backup(self, entry: FileEntry) -> Optional[str]:
        """Create backup of file before operation."""
        if not self.backup_dir:
            return None

        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            backup_path = os.path.join(self.backup_dir, entry.original)

            # Handle duplicate backup names
            if os.path.exists(backup_path):
                base, ext = os.path.splitext(entry.original)
                counter = 1
                while os.path.exists(backup_path):
                    backup_path = os.path.join(
                        self.backup_dir, f"{base}_backup{counter}{ext}"
                    )
                    counter += 1

            shutil.copy2(entry.path, backup_path)
            return backup_path
        except (OSError, PermissionError):
            return None

    def _run(self) -> None:
        """Execute file operations."""
        operation = shutil.copy2 if self.copy_mode else shutil.move
        total = sum(1 for e in self.entries if e.selected.get())
        current = 0

        for entry in self.entries:
            if self._cancelled:
                break

            if not entry.selected.get():
                continue

            current += 1
            if self.on_progress:
                self.on_progress(current, total, entry.original)

            dest = self.target_dir or entry.directory
            backup_path = None

            try:
                # Create backup if enabled
                if self.backup_dir:
                    backup_path = self._create_backup(entry)

                os.makedirs(dest, exist_ok=True)
                full_dest = os.path.join(dest, entry.new_name)

                if os.path.exists(full_dest):
                    self.on_error(entry, f"File already exists: {entry.new_name}")
                    continue

                operation(entry.path, full_dest)

                # Track operation for undo
                self.operations.append({
                    "original_path": entry.path,
                    "new_path": full_dest,
                    "was_copy": self.copy_mode,
                    "backup_path": backup_path,
                })

                self.on_success(entry)

            except PermissionError:
                self.on_error(entry, "Permission denied")
            except FileNotFoundError:
                self.on_error(entry, "Source file not found")
            except OSError as e:
                self.on_error(entry, str(e))

        self.on_complete()
