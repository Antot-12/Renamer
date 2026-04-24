"""File operations with threading support."""

from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass, field
from typing import Callable, Generator, List, Optional, Set
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
        """
        self.entries = entries
        self.target_dir = target_dir
        self.copy_mode = copy_mode
        self.on_success = on_success
        self.on_error = on_error
        self.on_complete = on_complete
        self._thread: Optional[threading.Thread] = None
        self._cancelled = False

    def start(self) -> None:
        """Start the file operation in a background thread."""
        self._cancelled = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Cancel the operation (best effort)."""
        self._cancelled = True

    def _run(self) -> None:
        """Execute file operations."""
        operation = shutil.copy2 if self.copy_mode else shutil.move

        for entry in self.entries:
            if self._cancelled:
                break

            if not entry.selected.get():
                continue

            dest = self.target_dir or entry.directory
            try:
                os.makedirs(dest, exist_ok=True)
                full_dest = os.path.join(dest, entry.new_name)

                if os.path.exists(full_dest):
                    self.on_error(entry, f"File already exists: {entry.new_name}")
                    continue

                operation(entry.path, full_dest)
                self.on_success(entry)

            except PermissionError:
                self.on_error(entry, "Permission denied")
            except FileNotFoundError:
                self.on_error(entry, "Source file not found")
            except OSError as e:
                self.on_error(entry, str(e))

        self.on_complete()
