"""Persistent history log for rename operations."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import threading


@dataclass
class HistoryLogEntry:
    """Single log entry for a rename operation."""
    timestamp: datetime
    operation_type: str  # "rename" | "copy" | "undo" | "redo"
    source_path: str
    dest_path: str
    success: bool
    error_message: Optional[str] = None
    file_size: int = 0
    profile_name: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "operation_type": self.operation_type,
            "source_path": self.source_path,
            "dest_path": self.dest_path,
            "success": self.success,
            "error_message": self.error_message,
            "file_size": self.file_size,
            "profile_name": self.profile_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryLogEntry":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            operation_type=data["operation_type"],
            source_path=data["source_path"],
            dest_path=data["dest_path"],
            success=data["success"],
            error_message=data.get("error_message"),
            file_size=data.get("file_size", 0),
            profile_name=data.get("profile_name"),
        )


@dataclass
class HistorySession:
    """A group of operations performed in one batch."""
    session_id: str
    timestamp: datetime
    entries: List[HistoryLogEntry] = field(default_factory=list)
    total_files: int = 0
    successful: int = 0
    failed: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "entries": [e.to_dict() for e in self.entries],
            "total_files": self.total_files,
            "successful": self.successful,
            "failed": self.failed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistorySession":
        return cls(
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            entries=[HistoryLogEntry.from_dict(e) for e in data.get("entries", [])],
            total_files=data.get("total_files", 0),
            successful=data.get("successful", 0),
            failed=data.get("failed", 0),
        )


class HistoryLog:
    """Persistent history log saved to disk."""

    DEFAULT_LOG_FILE = Path.home() / ".renamer_history.json"
    MAX_SESSIONS = 100
    MAX_ENTRIES_PER_SESSION = 1000

    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file or self.DEFAULT_LOG_FILE
        self._sessions: List[HistorySession] = []
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Load history from file."""
        try:
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._sessions = [HistorySession.from_dict(s) for s in data.get("sessions", [])]
        except (json.JSONDecodeError, IOError, KeyError):
            self._sessions = []

    def _save(self) -> None:
        """Save history to file."""
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                data = {"sessions": [s.to_dict() for s in self._sessions]}
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError:
            pass

    def start_session(self) -> str:
        """Start a new logging session. Returns session ID."""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        session = HistorySession(
            session_id=session_id,
            timestamp=datetime.now(),
        )

        with self._lock:
            self._sessions.append(session)

            # Limit sessions
            while len(self._sessions) > self.MAX_SESSIONS:
                self._sessions.pop(0)

        return session_id

    def add_entry(self, session_id: str, entry: HistoryLogEntry) -> None:
        """Add entry to a session."""
        with self._lock:
            for session in self._sessions:
                if session.session_id == session_id:
                    if len(session.entries) < self.MAX_ENTRIES_PER_SESSION:
                        session.entries.append(entry)
                        session.total_files += 1
                        if entry.success:
                            session.successful += 1
                        else:
                            session.failed += 1
                    break

    def end_session(self, session_id: str) -> None:
        """End session and save to disk."""
        with self._lock:
            self._save()

    def log_operation(
        self,
        session_id: str,
        operation_type: str,
        source: str,
        dest: str,
        success: bool,
        error: Optional[str] = None,
        size: int = 0,
        profile: Optional[str] = None
    ) -> None:
        """Log a single operation."""
        entry = HistoryLogEntry(
            timestamp=datetime.now(),
            operation_type=operation_type,
            source_path=source,
            dest_path=dest,
            success=success,
            error_message=error,
            file_size=size,
            profile_name=profile,
        )
        self.add_entry(session_id, entry)

    def get_sessions(self, limit: int = 50) -> List[HistorySession]:
        """Get recent sessions."""
        with self._lock:
            return list(reversed(self._sessions[-limit:]))

    def get_session(self, session_id: str) -> Optional[HistorySession]:
        """Get specific session by ID."""
        with self._lock:
            for session in self._sessions:
                if session.session_id == session_id:
                    return session
        return None

    def get_all_entries(self, limit: int = 500) -> List[HistoryLogEntry]:
        """Get all entries across sessions, most recent first."""
        all_entries = []
        with self._lock:
            for session in reversed(self._sessions):
                all_entries.extend(reversed(session.entries))
                if len(all_entries) >= limit:
                    break
        return all_entries[:limit]

    def clear(self) -> None:
        """Clear all history."""
        with self._lock:
            self._sessions.clear()
            self._save()

    def clear_old(self, days: int = 30) -> int:
        """Clear sessions older than N days. Returns count removed."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        removed = 0

        with self._lock:
            original_count = len(self._sessions)
            self._sessions = [
                s for s in self._sessions
                if s.timestamp.timestamp() > cutoff
            ]
            removed = original_count - len(self._sessions)
            if removed > 0:
                self._save()

        return removed

    def export_csv(self, filepath: str, session_id: Optional[str] = None) -> bool:
        """Export history to CSV file."""
        try:
            entries = []
            if session_id:
                session = self.get_session(session_id)
                if session:
                    entries = session.entries
            else:
                entries = self.get_all_entries(limit=10000)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Operation", "Source", "Destination",
                    "Success", "Error", "Size (bytes)", "Profile"
                ])
                for entry in entries:
                    writer.writerow([
                        entry.timestamp.isoformat(),
                        entry.operation_type,
                        entry.source_path,
                        entry.dest_path,
                        "Yes" if entry.success else "No",
                        entry.error_message or "",
                        entry.file_size,
                        entry.profile_name or "",
                    ])
            return True
        except IOError:
            return False

    def get_stats(self) -> dict:
        """Get overall statistics."""
        total_ops = 0
        successful = 0
        failed = 0
        total_size = 0

        with self._lock:
            for session in self._sessions:
                total_ops += session.total_files
                successful += session.successful
                failed += session.failed
                for entry in session.entries:
                    if entry.success:
                        total_size += entry.file_size

        return {
            "total_sessions": len(self._sessions),
            "total_operations": total_ops,
            "successful": successful,
            "failed": failed,
            "total_size_processed": total_size,
        }


# Global instance
_history_log: Optional[HistoryLog] = None


def get_history_log() -> HistoryLog:
    """Get global history log instance."""
    global _history_log
    if _history_log is None:
        _history_log = HistoryLog()
    return _history_log
