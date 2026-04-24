"""Tests for duplicate file detection."""

import os
import tempfile
import shutil
import tkinter as tk

import pytest

from renamer.duplicates import (
    calculate_file_hash,
    calculate_partial_hash,
    find_duplicates,
    find_duplicates_quick,
    get_duplicate_groups,
    get_duplicate_stats,
)
from renamer.file_ops import FileEntry


class TestCalculateFileHash:
    """Tests for file hash calculation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_hash_same_content(self):
        # Create two files with same content
        file1 = os.path.join(self.tmpdir, "file1.txt")
        file2 = os.path.join(self.tmpdir, "file2.txt")

        content = b"test content for hashing"
        with open(file1, "wb") as f:
            f.write(content)
        with open(file2, "wb") as f:
            f.write(content)

        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)

        assert hash1 == hash2
        assert hash1 is not None

    def test_hash_different_content(self):
        file1 = os.path.join(self.tmpdir, "file1.txt")
        file2 = os.path.join(self.tmpdir, "file2.txt")

        with open(file1, "wb") as f:
            f.write(b"content one")
        with open(file2, "wb") as f:
            f.write(b"content two")

        hash1 = calculate_file_hash(file1)
        hash2 = calculate_file_hash(file2)

        assert hash1 != hash2

    def test_hash_nonexistent_file(self):
        result = calculate_file_hash("/nonexistent/file.txt")
        assert result is None

    def test_hash_md5_algorithm(self):
        file_path = os.path.join(self.tmpdir, "test.txt")
        with open(file_path, "wb") as f:
            f.write(b"test")

        result = calculate_file_hash(file_path, algorithm="md5")
        assert result is not None
        assert len(result) == 32  # MD5 hex digest length

    def test_hash_sha256_algorithm(self):
        file_path = os.path.join(self.tmpdir, "test.txt")
        with open(file_path, "wb") as f:
            f.write(b"test")

        result = calculate_file_hash(file_path, algorithm="sha256")
        assert result is not None
        assert len(result) == 64  # SHA256 hex digest length


class TestCalculatePartialHash:
    """Tests for partial file hash calculation."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_partial_hash_small_file(self):
        file_path = os.path.join(self.tmpdir, "small.txt")
        with open(file_path, "wb") as f:
            f.write(b"small content")

        result = calculate_partial_hash(file_path)
        assert result is not None

    def test_partial_hash_large_file(self):
        file_path = os.path.join(self.tmpdir, "large.txt")
        # Create file larger than default partial size
        with open(file_path, "wb") as f:
            f.write(b"x" * 100000)

        result = calculate_partial_hash(file_path, size=1000)
        assert result is not None

    def test_partial_hash_nonexistent(self):
        result = calculate_partial_hash("/nonexistent/file.txt")
        assert result is None


class TestFindDuplicates:
    """Tests for duplicate detection."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = tk.Tk()
        self.root.withdraw()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        self.root.destroy()

    def _create_file(self, name: str, content: bytes) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def _create_entry(self, path: str) -> FileEntry:
        return FileEntry(
            path=path,
            original=os.path.basename(path),
            directory=os.path.dirname(path),
            new_name=os.path.basename(path),
            ext=os.path.splitext(path)[1],
            file_type="📁",
            size=os.path.getsize(path),
        )

    def test_find_duplicates_same_content(self):
        content = b"duplicate content here"
        path1 = self._create_file("file1.txt", content)
        path2 = self._create_file("file2.txt", content)
        path3 = self._create_file("unique.txt", b"different content")

        entries = [
            self._create_entry(path1),
            self._create_entry(path2),
            self._create_entry(path3),
        ]

        duplicates = find_duplicates(entries)

        assert len(duplicates) == 1  # One group of duplicates
        group = list(duplicates.values())[0]
        assert len(group) == 2  # Two files in the group

    def test_find_duplicates_no_duplicates(self):
        path1 = self._create_file("file1.txt", b"content one")
        path2 = self._create_file("file2.txt", b"content two")
        path3 = self._create_file("file3.txt", b"content three")

        entries = [
            self._create_entry(path1),
            self._create_entry(path2),
            self._create_entry(path3),
        ]

        duplicates = find_duplicates(entries)

        assert len(duplicates) == 0

    def test_find_duplicates_different_sizes_not_duplicates(self):
        # Files with different sizes can't be duplicates
        path1 = self._create_file("file1.txt", b"short")
        path2 = self._create_file("file2.txt", b"much longer content")

        entries = [
            self._create_entry(path1),
            self._create_entry(path2),
        ]

        duplicates = find_duplicates(entries)

        assert len(duplicates) == 0

    def test_find_duplicates_with_progress(self):
        content = b"test content"
        path1 = self._create_file("file1.txt", content)
        path2 = self._create_file("file2.txt", content)

        entries = [self._create_entry(path1), self._create_entry(path2)]

        progress_calls = []
        find_duplicates(entries, on_progress=lambda c, t: progress_calls.append((c, t)))

        assert len(progress_calls) > 0

    def test_find_duplicates_empty_list(self):
        duplicates = find_duplicates([])
        assert len(duplicates) == 0

    def test_find_duplicates_skips_zero_size(self):
        # Create empty file
        path = self._create_file("empty.txt", b"")

        entries = [self._create_entry(path)]

        duplicates = find_duplicates(entries)
        assert len(duplicates) == 0


class TestFindDuplicatesQuick:
    """Tests for quick duplicate detection."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = tk.Tk()
        self.root.withdraw()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        self.root.destroy()

    def _create_file(self, name: str, content: bytes) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def _create_entry(self, path: str) -> FileEntry:
        return FileEntry(
            path=path,
            original=os.path.basename(path),
            directory=os.path.dirname(path),
            new_name=os.path.basename(path),
            ext=os.path.splitext(path)[1],
            file_type="📁",
            size=os.path.getsize(path),
        )

    def test_quick_find_duplicates(self):
        content = b"duplicate content"
        path1 = self._create_file("file1.txt", content)
        path2 = self._create_file("file2.txt", content)

        entries = [self._create_entry(path1), self._create_entry(path2)]

        duplicates = find_duplicates_quick(entries)

        assert len(duplicates) == 1


class TestGetDuplicateStats:
    """Tests for duplicate statistics."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = tk.Tk()
        self.root.withdraw()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        self.root.destroy()

    def _create_file(self, name: str, content: bytes) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def _create_entry(self, path: str) -> FileEntry:
        return FileEntry(
            path=path,
            original=os.path.basename(path),
            directory=os.path.dirname(path),
            new_name=os.path.basename(path),
            ext=os.path.splitext(path)[1],
            file_type="📁",
            size=os.path.getsize(path),
        )

    def test_stats_with_duplicates(self):
        content = b"duplicate content here!"  # 23 bytes
        path1 = self._create_file("file1.txt", content)
        path2 = self._create_file("file2.txt", content)
        path3 = self._create_file("file3.txt", content)
        path4 = self._create_file("unique.txt", b"different")

        entries = [
            self._create_entry(path1),
            self._create_entry(path2),
            self._create_entry(path3),
            self._create_entry(path4),
        ]

        stats = get_duplicate_stats(entries)

        assert stats["total_files"] == 4
        assert stats["duplicate_groups"] == 1
        assert stats["duplicate_files"] == 2  # 3 files - 1 unique = 2 duplicates
        assert stats["wasted_space"] == 2 * 23  # 2 duplicate files * size

    def test_stats_no_duplicates(self):
        path1 = self._create_file("file1.txt", b"one")
        path2 = self._create_file("file2.txt", b"two")

        entries = [self._create_entry(path1), self._create_entry(path2)]

        stats = get_duplicate_stats(entries)

        assert stats["total_files"] == 2
        assert stats["duplicate_groups"] == 0
        assert stats["duplicate_files"] == 0
        assert stats["wasted_space"] == 0


class TestGetDuplicateGroups:
    """Tests for get_duplicate_groups function."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = tk.Tk()
        self.root.withdraw()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        self.root.destroy()

    def _create_file(self, name: str, content: bytes) -> str:
        path = os.path.join(self.tmpdir, name)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def _create_entry(self, path: str) -> FileEntry:
        return FileEntry(
            path=path,
            original=os.path.basename(path),
            directory=os.path.dirname(path),
            new_name=os.path.basename(path),
            ext=os.path.splitext(path)[1],
            file_type="📁",
            size=os.path.getsize(path),
        )

    def test_returns_list_of_groups(self):
        content = b"duplicate"
        path1 = self._create_file("file1.txt", content)
        path2 = self._create_file("file2.txt", content)

        entries = [self._create_entry(path1), self._create_entry(path2)]

        groups = get_duplicate_groups(entries, quick=False)

        assert isinstance(groups, list)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_quick_mode(self):
        content = b"duplicate"
        path1 = self._create_file("file1.txt", content)
        path2 = self._create_file("file2.txt", content)

        entries = [self._create_entry(path1), self._create_entry(path2)]

        groups = get_duplicate_groups(entries, quick=True)

        assert len(groups) == 1
