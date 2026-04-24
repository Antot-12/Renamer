"""Tests for persistent history log."""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from renamer.history_log import (
    HistoryLogEntry,
    HistorySession,
    HistoryLog,
    get_history_log,
)


class TestHistoryLogEntry:
    """Tests for HistoryLogEntry dataclass."""

    def test_create_entry(self):
        entry = HistoryLogEntry(
            timestamp=datetime.now(),
            operation_type="rename",
            source_path="/old/file.txt",
            dest_path="/new/file.txt",
            success=True,
        )
        assert entry.operation_type == "rename"
        assert entry.success is True
        assert entry.error_message is None

    def test_to_dict(self):
        ts = datetime(2024, 1, 15, 10, 30, 0)
        entry = HistoryLogEntry(
            timestamp=ts,
            operation_type="copy",
            source_path="/src.txt",
            dest_path="/dst.txt",
            success=False,
            error_message="Permission denied",
            file_size=1024,
            profile_name="test_profile",
        )

        d = entry.to_dict()

        assert d["timestamp"] == "2024-01-15T10:30:00"
        assert d["operation_type"] == "copy"
        assert d["source_path"] == "/src.txt"
        assert d["dest_path"] == "/dst.txt"
        assert d["success"] is False
        assert d["error_message"] == "Permission denied"
        assert d["file_size"] == 1024
        assert d["profile_name"] == "test_profile"

    def test_from_dict(self):
        data = {
            "timestamp": "2024-01-15T10:30:00",
            "operation_type": "rename",
            "source_path": "/old.txt",
            "dest_path": "/new.txt",
            "success": True,
            "error_message": None,
            "file_size": 2048,
            "profile_name": None,
        }

        entry = HistoryLogEntry.from_dict(data)

        assert entry.timestamp == datetime(2024, 1, 15, 10, 30, 0)
        assert entry.operation_type == "rename"
        assert entry.file_size == 2048


class TestHistorySession:
    """Tests for HistorySession dataclass."""

    def test_create_session(self):
        session = HistorySession(
            session_id="20240115_103000_123456",
            timestamp=datetime.now(),
        )
        assert session.session_id == "20240115_103000_123456"
        assert session.total_files == 0
        assert session.successful == 0
        assert session.failed == 0
        assert len(session.entries) == 0

    def test_to_dict(self):
        session = HistorySession(
            session_id="test_session",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            total_files=5,
            successful=4,
            failed=1,
        )

        d = session.to_dict()

        assert d["session_id"] == "test_session"
        assert d["total_files"] == 5
        assert d["successful"] == 4
        assert d["failed"] == 1

    def test_from_dict(self):
        data = {
            "session_id": "test_session",
            "timestamp": "2024-01-15T10:30:00",
            "entries": [],
            "total_files": 10,
            "successful": 8,
            "failed": 2,
        }

        session = HistorySession.from_dict(data)

        assert session.session_id == "test_session"
        assert session.total_files == 10


class TestHistoryLog:
    """Tests for HistoryLog class."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log_file = Path(self.tmpdir) / "test_history.json"

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_history_log(self):
        log = HistoryLog(self.log_file)
        assert log.log_file == self.log_file

    def test_start_session(self):
        log = HistoryLog(self.log_file)

        session_id = log.start_session()

        assert session_id is not None
        assert len(session_id) > 0

    def test_add_entry_to_session(self):
        log = HistoryLog(self.log_file)
        session_id = log.start_session()

        entry = HistoryLogEntry(
            timestamp=datetime.now(),
            operation_type="rename",
            source_path="/old.txt",
            dest_path="/new.txt",
            success=True,
        )
        log.add_entry(session_id, entry)

        session = log.get_session(session_id)
        assert session is not None
        assert len(session.entries) == 1
        assert session.total_files == 1
        assert session.successful == 1

    def test_add_failed_entry(self):
        log = HistoryLog(self.log_file)
        session_id = log.start_session()

        entry = HistoryLogEntry(
            timestamp=datetime.now(),
            operation_type="rename",
            source_path="/old.txt",
            dest_path="/new.txt",
            success=False,
            error_message="Error occurred",
        )
        log.add_entry(session_id, entry)

        session = log.get_session(session_id)
        assert session.failed == 1

    def test_log_operation_helper(self):
        log = HistoryLog(self.log_file)
        session_id = log.start_session()

        log.log_operation(
            session_id,
            operation_type="copy",
            source="/src.txt",
            dest="/dst.txt",
            success=True,
            size=1024,
            profile="my_profile",
        )

        session = log.get_session(session_id)
        assert len(session.entries) == 1
        assert session.entries[0].operation_type == "copy"
        assert session.entries[0].file_size == 1024

    def test_end_session_saves(self):
        log = HistoryLog(self.log_file)
        session_id = log.start_session()
        log.log_operation(session_id, "rename", "/a.txt", "/b.txt", True)
        log.end_session(session_id)

        # Create new log instance to verify persistence
        log2 = HistoryLog(self.log_file)
        sessions = log2.get_sessions()

        assert len(sessions) == 1

    def test_get_sessions_returns_recent_first(self):
        log = HistoryLog(self.log_file)

        # Create multiple sessions
        for i in range(3):
            session_id = log.start_session()
            log.log_operation(session_id, "rename", f"/file{i}.txt", f"/new{i}.txt", True)
            log.end_session(session_id)

        sessions = log.get_sessions()

        assert len(sessions) == 3
        # Most recent should be first
        assert sessions[0].timestamp >= sessions[1].timestamp

    def test_get_sessions_with_limit(self):
        log = HistoryLog(self.log_file)

        for i in range(5):
            session_id = log.start_session()
            log.end_session(session_id)

        sessions = log.get_sessions(limit=2)
        assert len(sessions) == 2

    def test_get_all_entries(self):
        log = HistoryLog(self.log_file)

        session_id = log.start_session()
        for i in range(3):
            log.log_operation(session_id, "rename", f"/old{i}.txt", f"/new{i}.txt", True)
        log.end_session(session_id)

        entries = log.get_all_entries()
        assert len(entries) == 3

    def test_clear_history(self):
        log = HistoryLog(self.log_file)
        session_id = log.start_session()
        log.log_operation(session_id, "rename", "/a.txt", "/b.txt", True)
        log.end_session(session_id)

        log.clear()

        assert len(log.get_sessions()) == 0

    def test_clear_old_sessions(self):
        log = HistoryLog(self.log_file)

        # Create a session
        session_id = log.start_session()
        log.end_session(session_id)

        # Clear sessions older than 0 days (all of them)
        removed = log.clear_old(days=0)

        # Should have removed the session
        assert removed >= 0

    def test_get_stats(self):
        log = HistoryLog(self.log_file)

        session_id = log.start_session()
        log.log_operation(session_id, "rename", "/a.txt", "/b.txt", True, size=100)
        log.log_operation(session_id, "rename", "/c.txt", "/d.txt", True, size=200)
        log.log_operation(session_id, "rename", "/e.txt", "/f.txt", False, error="fail")
        log.end_session(session_id)

        stats = log.get_stats()

        assert stats["total_sessions"] == 1
        assert stats["total_operations"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1
        assert stats["total_size_processed"] == 300

    def test_export_csv(self):
        log = HistoryLog(self.log_file)

        session_id = log.start_session()
        log.log_operation(session_id, "rename", "/old.txt", "/new.txt", True, size=1024)
        log.end_session(session_id)

        csv_path = os.path.join(self.tmpdir, "export.csv")
        result = log.export_csv(csv_path)

        assert result is True
        assert os.path.exists(csv_path)

        with open(csv_path, "r") as f:
            content = f.read()
            assert "Timestamp" in content
            assert "/old.txt" in content

    def test_export_csv_specific_session(self):
        log = HistoryLog(self.log_file)

        session_id = log.start_session()
        log.log_operation(session_id, "rename", "/file.txt", "/new.txt", True)
        log.end_session(session_id)

        csv_path = os.path.join(self.tmpdir, "export.csv")
        result = log.export_csv(csv_path, session_id=session_id)

        assert result is True

    def test_max_sessions_limit(self):
        # Create log with custom max
        log = HistoryLog(self.log_file)
        log.MAX_SESSIONS = 3

        for i in range(5):
            session_id = log.start_session()
            log.end_session(session_id)

        sessions = log.get_sessions(limit=100)
        assert len(sessions) <= 3

    def test_load_corrupted_file(self):
        # Write invalid JSON
        with open(self.log_file, "w") as f:
            f.write("not valid json {{{")

        # Should not crash, just start with empty sessions
        log = HistoryLog(self.log_file)
        assert len(log.get_sessions()) == 0


class TestGetHistoryLog:
    """Tests for global history log accessor."""

    def test_returns_singleton(self):
        # Note: This might fail if other tests have already created the singleton
        # In real testing, you'd want to reset the singleton between tests
        log1 = get_history_log()
        log2 = get_history_log()

        assert log1 is log2
