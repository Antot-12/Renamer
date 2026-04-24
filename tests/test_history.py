"""Tests for undo/redo history system."""

import os
import tempfile
import shutil
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from renamer.history import RenameOperation, OperationHistory


class TestRenameOperation:
    """Tests for RenameOperation dataclass."""

    def test_create_operation(self):
        op = RenameOperation(
            original_path="/test/old.txt",
            new_path="/test/new.txt",
            was_copy=False,
        )
        assert op.original_path == "/test/old.txt"
        assert op.new_path == "/test/new.txt"
        assert op.was_copy is False
        assert op.backup_path is None
        assert isinstance(op.timestamp, datetime)

    def test_to_dict(self):
        op = RenameOperation(
            original_path="/test/old.txt",
            new_path="/test/new.txt",
            was_copy=True,
            backup_path="/backup/old.txt",
        )
        d = op.to_dict()
        assert d["original_path"] == "/test/old.txt"
        assert d["new_path"] == "/test/new.txt"
        assert d["was_copy"] is True
        assert d["backup_path"] == "/backup/old.txt"
        assert "timestamp" in d

    def test_from_dict(self):
        data = {
            "original_path": "/test/old.txt",
            "new_path": "/test/new.txt",
            "was_copy": False,
            "timestamp": "2024-01-15T10:30:00",
            "backup_path": None,
        }
        op = RenameOperation.from_dict(data)
        assert op.original_path == "/test/old.txt"
        assert op.new_path == "/test/new.txt"
        assert op.was_copy is False


class TestOperationHistory:
    """Tests for OperationHistory class."""

    def test_initial_state(self):
        history = OperationHistory()
        assert history.can_undo() is False
        assert history.can_redo() is False
        assert history.get_undo_count() == 0
        assert history.get_redo_count() == 0

    def test_record_batch(self):
        history = OperationHistory()
        ops = [
            RenameOperation("/old1.txt", "/new1.txt", False),
            RenameOperation("/old2.txt", "/new2.txt", False),
        ]
        history.record_batch(ops)

        assert history.can_undo() is True
        assert history.get_undo_count() == 1

    def test_record_empty_batch_ignored(self):
        history = OperationHistory()
        history.record_batch([])

        assert history.can_undo() is False

    def test_record_clears_redo_stack(self):
        history = OperationHistory()

        # Create initial state with redo available
        history.record_batch([RenameOperation("/a.txt", "/b.txt", False)])

        # Record new batch should clear any redo
        history.record_batch([RenameOperation("/c.txt", "/d.txt", False)])

        assert history.get_undo_count() == 2

    def test_max_size_limit(self):
        history = OperationHistory(max_size=3)

        for i in range(5):
            history.record_batch([RenameOperation(f"/old{i}.txt", f"/new{i}.txt", False)])

        assert history.get_undo_count() == 3

    def test_undo_description(self):
        history = OperationHistory()

        assert history.undo_description() is None

        ops = [RenameOperation("/a.txt", "/b.txt", False)]
        history.record_batch(ops)

        desc = history.undo_description()
        assert desc is not None
        assert "1" in desc  # Should mention file count

    def test_redo_description(self):
        history = OperationHistory()
        assert history.redo_description() is None

    def test_clear(self):
        history = OperationHistory()
        history.record_batch([RenameOperation("/a.txt", "/b.txt", False)])

        history.clear()

        assert history.can_undo() is False
        assert history.can_redo() is False


class TestOperationHistoryWithFiles:
    """Integration tests with actual file operations."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_undo_move_operation(self):
        # Create test file
        old_path = os.path.join(self.tmpdir, "old.txt")
        new_path = os.path.join(self.tmpdir, "new.txt")

        with open(old_path, "w") as f:
            f.write("test content")

        # Simulate move
        shutil.move(old_path, new_path)

        # Record operation
        history = OperationHistory()
        history.record_batch([RenameOperation(old_path, new_path, was_copy=False)])

        # Undo
        result = history.undo()

        assert result is True
        assert os.path.exists(old_path)
        assert not os.path.exists(new_path)

    def test_undo_copy_operation(self):
        # Create test file
        old_path = os.path.join(self.tmpdir, "original.txt")
        new_path = os.path.join(self.tmpdir, "copy.txt")

        with open(old_path, "w") as f:
            f.write("test content")

        # Simulate copy
        shutil.copy2(old_path, new_path)

        # Record operation
        history = OperationHistory()
        history.record_batch([RenameOperation(old_path, new_path, was_copy=True)])

        # Undo - should delete the copy
        result = history.undo()

        assert result is True
        assert os.path.exists(old_path)  # Original still exists
        assert not os.path.exists(new_path)  # Copy removed

    def test_redo_operation(self):
        # Create test file
        old_path = os.path.join(self.tmpdir, "old.txt")
        new_path = os.path.join(self.tmpdir, "new.txt")

        with open(old_path, "w") as f:
            f.write("test content")

        # Simulate move and record
        shutil.move(old_path, new_path)
        history = OperationHistory()
        history.record_batch([RenameOperation(old_path, new_path, was_copy=False)])

        # Undo
        history.undo()
        assert os.path.exists(old_path)

        # Redo
        result = history.redo()

        assert result is True
        assert not os.path.exists(old_path)
        assert os.path.exists(new_path)

    def test_undo_returns_false_when_empty(self):
        history = OperationHistory()
        assert history.undo() is False

    def test_redo_returns_false_when_empty(self):
        history = OperationHistory()
        assert history.redo() is False

    def test_undo_with_progress_callback(self):
        old_path = os.path.join(self.tmpdir, "old.txt")
        new_path = os.path.join(self.tmpdir, "new.txt")

        with open(old_path, "w") as f:
            f.write("test")
        shutil.move(old_path, new_path)

        history = OperationHistory()
        history.record_batch([RenameOperation(old_path, new_path, was_copy=False)])

        progress_calls = []
        history.undo(on_progress=lambda msg: progress_calls.append(msg))

        assert len(progress_calls) > 0
