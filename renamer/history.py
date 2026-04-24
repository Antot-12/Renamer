"""Undo/Redo system for rename operations."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable
import threading


@dataclass
class RenameOperation:
    """Records a single rename operation for undo/redo."""
    original_path: str
    new_path: str
    was_copy: bool
    timestamp: datetime = field(default_factory=datetime.now)
    backup_path: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "original_path": self.original_path,
            "new_path": self.new_path,
            "was_copy": self.was_copy,
            "timestamp": self.timestamp.isoformat(),
            "backup_path": self.backup_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RenameOperation":
        """Create from dictionary."""
        return cls(
            original_path=data["original_path"],
            new_path=data["new_path"],
            was_copy=data["was_copy"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            backup_path=data.get("backup_path"),
        )


class OperationHistory:
    """Manages undo/redo stack for rename operations."""

    def __init__(self, max_size: int = 50):
        self._undo_stack: List[List[RenameOperation]] = []
        self._redo_stack: List[List[RenameOperation]] = []
        self._max_size = max_size
        self._lock = threading.Lock()

    def record_batch(self, operations: List[RenameOperation]) -> None:
        """Record a batch of operations (one rename action may affect multiple files)."""
        if not operations:
            return

        with self._lock:
            self._undo_stack.append(operations)
            self._redo_stack.clear()  # Clear redo stack on new action

            # Limit stack size
            while len(self._undo_stack) > self._max_size:
                self._undo_stack.pop(0)

    def undo(self, on_progress: Optional[Callable[[str], None]] = None) -> bool:
        """
        Undo the last batch of operations.
        Returns True if successful, False if nothing to undo.
        """
        with self._lock:
            if not self._undo_stack:
                return False

            batch = self._undo_stack.pop()

        errors = []
        successful_ops = []

        # Reverse operations
        for op in reversed(batch):
            try:
                if on_progress:
                    on_progress(f"Скасування: {os.path.basename(op.new_path)}")

                if op.was_copy:
                    # For copy operations, just delete the copy
                    if os.path.exists(op.new_path):
                        os.remove(op.new_path)
                else:
                    # For move operations, move back
                    if os.path.exists(op.new_path):
                        # Ensure original directory exists
                        os.makedirs(os.path.dirname(op.original_path), exist_ok=True)
                        shutil.move(op.new_path, op.original_path)

                successful_ops.append(op)
            except (OSError, PermissionError, FileNotFoundError) as e:
                errors.append(f"{op.new_path}: {e}")

        # Add to redo stack
        with self._lock:
            if successful_ops:
                self._redo_stack.append(successful_ops)

        return len(errors) == 0

    def redo(self, on_progress: Optional[Callable[[str], None]] = None) -> bool:
        """
        Redo the last undone batch of operations.
        Returns True if successful, False if nothing to redo.
        """
        with self._lock:
            if not self._redo_stack:
                return False

            batch = self._redo_stack.pop()

        errors = []
        successful_ops = []

        # Re-apply operations
        for op in batch:
            try:
                if on_progress:
                    on_progress(f"Повторення: {os.path.basename(op.original_path)}")

                # Ensure target directory exists
                os.makedirs(os.path.dirname(op.new_path), exist_ok=True)

                if op.was_copy:
                    if os.path.exists(op.original_path):
                        shutil.copy2(op.original_path, op.new_path)
                else:
                    if os.path.exists(op.original_path):
                        shutil.move(op.original_path, op.new_path)

                successful_ops.append(op)
            except (OSError, PermissionError, FileNotFoundError) as e:
                errors.append(f"{op.original_path}: {e}")

        # Add back to undo stack
        with self._lock:
            if successful_ops:
                self._undo_stack.append(successful_ops)

        return len(errors) == 0

    def can_undo(self) -> bool:
        """Check if undo is available."""
        with self._lock:
            return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        with self._lock:
            return len(self._redo_stack) > 0

    def undo_description(self) -> Optional[str]:
        """Get description of what will be undone."""
        with self._lock:
            if not self._undo_stack:
                return None
            batch = self._undo_stack[-1]
            count = len(batch)
            return f"Скасувати ({count} файлів)"

    def redo_description(self) -> Optional[str]:
        """Get description of what will be redone."""
        with self._lock:
            if not self._redo_stack:
                return None
            batch = self._redo_stack[-1]
            count = len(batch)
            return f"Повторити ({count} файлів)"

    def clear(self) -> None:
        """Clear all history."""
        with self._lock:
            self._undo_stack.clear()
            self._redo_stack.clear()

    def get_undo_count(self) -> int:
        """Get number of undo operations available."""
        with self._lock:
            return len(self._undo_stack)

    def get_redo_count(self) -> int:
        """Get number of redo operations available."""
        with self._lock:
            return len(self._redo_stack)
