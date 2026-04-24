"""Tests for file operations."""

import os
import tempfile
import shutil
from unittest.mock import MagicMock, patch
import tkinter as tk

import pytest

from renamer.file_ops import (
    FileEntry,
    AppState,
    collect_files,
    is_duplicate_name,
    check_for_duplicate_destinations,
)


class TestFileEntry:
    """Tests for the FileEntry dataclass."""

    def test_creates_entry_with_defaults(self):
        """Should create entry with default values."""
        root = tk.Tk()
        root.withdraw()

        entry = FileEntry(
            path='/test/file.mp3',
            original='file.mp3',
            directory='/test',
            new_name='new_file.mp3',
            ext='.mp3',
            file_type='🎵',
        )

        assert entry.path == '/test/file.mp3'
        assert entry.original == 'file.mp3'
        assert entry.size == 0
        assert entry.info == ''

        root.destroy()

    def test_to_dict_conversion(self):
        """Should convert to dictionary correctly."""
        root = tk.Tk()
        root.withdraw()

        entry = FileEntry(
            path='/test/file.mp3',
            original='file.mp3',
            directory='/test',
            new_name='new_file.mp3',
            ext='.mp3',
            file_type='🎵',
            size=1024,
            info='180s',
        )

        d = entry.to_dict()

        assert d['path'] == '/test/file.mp3'
        assert d['original'] == 'file.mp3'
        assert d['size'] == 1024
        assert d['info'] == '180s'

        root.destroy()


class TestAppState:
    """Tests for the AppState class."""

    def test_add_entry_success(self):
        """Should add entry successfully."""
        root = tk.Tk()
        root.withdraw()

        state = AppState()
        entry = FileEntry(
            path='/test/file.mp3',
            original='file.mp3',
            directory='/test',
            new_name='new_file.mp3',
            ext='.mp3',
            file_type='🎵',
        )

        result = state.add_entry(entry)

        assert result is True
        assert len(state.entries) == 1
        assert '/test/file.mp3' in state.path_set

        root.destroy()

    def test_add_entry_prevents_duplicates(self):
        """Should not add duplicate paths."""
        root = tk.Tk()
        root.withdraw()

        state = AppState()
        entry = FileEntry(
            path='/test/file.mp3',
            original='file.mp3',
            directory='/test',
            new_name='new_file.mp3',
            ext='.mp3',
            file_type='🎵',
        )

        state.add_entry(entry)
        result = state.add_entry(entry)

        assert result is False
        assert len(state.entries) == 1

        root.destroy()

    def test_remove_entry(self):
        """Should remove entry by index."""
        root = tk.Tk()
        root.withdraw()

        state = AppState()
        entry = FileEntry(
            path='/test/file.mp3',
            original='file.mp3',
            directory='/test',
            new_name='new_file.mp3',
            ext='.mp3',
            file_type='🎵',
        )
        state.add_entry(entry)

        removed = state.remove_entry(0)

        assert removed is entry
        assert len(state.entries) == 0
        assert '/test/file.mp3' not in state.path_set

        root.destroy()

    def test_clear(self):
        """Should clear all entries."""
        root = tk.Tk()
        root.withdraw()

        state = AppState()
        for i in range(3):
            entry = FileEntry(
                path=f'/test/file{i}.mp3',
                original=f'file{i}.mp3',
                directory='/test',
                new_name=f'new_file{i}.mp3',
                ext='.mp3',
                file_type='🎵',
            )
            state.add_entry(entry)

        state.clear()

        assert len(state.entries) == 0
        assert len(state.path_set) == 0

        root.destroy()

    def test_get_selected(self):
        """Should return only selected entries."""
        root = tk.Tk()
        root.withdraw()

        state = AppState()

        entry1 = FileEntry(
            path='/test/file1.mp3',
            original='file1.mp3',
            directory='/test',
            new_name='new_file1.mp3',
            ext='.mp3',
            file_type='🎵',
            selected=tk.BooleanVar(value=True),
        )
        entry2 = FileEntry(
            path='/test/file2.mp3',
            original='file2.mp3',
            directory='/test',
            new_name='new_file2.mp3',
            ext='.mp3',
            file_type='🎵',
            selected=tk.BooleanVar(value=False),
        )

        state.add_entry(entry1)
        state.add_entry(entry2)

        selected = state.get_selected()

        assert len(selected) == 1
        assert selected[0].original == 'file1.mp3'

        root.destroy()


class TestCollectFiles:
    """Tests for the collect_files function."""

    def test_collects_single_file(self):
        """Should yield single file path."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b'test')

            files = list(collect_files([f.name]))

            assert len(files) == 1
            assert files[0] == f.name

            os.unlink(f.name)

    def test_collects_files_from_directory(self):
        """Should recursively collect files from directory."""
        tmpdir = tempfile.mkdtemp()
        try:
            open(os.path.join(tmpdir, 'file1.txt'), 'w').close()
            open(os.path.join(tmpdir, 'file2.txt'), 'w').close()

            subdir = os.path.join(tmpdir, 'subdir')
            os.makedirs(subdir)
            open(os.path.join(subdir, 'file3.txt'), 'w').close()

            files = list(collect_files([tmpdir]))

            assert len(files) == 3
        finally:
            shutil.rmtree(tmpdir)

    def test_handles_nonexistent_path(self):
        """Should skip non-existent paths."""
        files = list(collect_files(['/nonexistent/path']))
        assert len(files) == 0


class TestIsDuplicateName:
    """Tests for the is_duplicate_name function."""

    def test_detects_duplicate_same_directory(self):
        """Should detect duplicate in same directory."""
        root = tk.Tk()
        root.withdraw()

        entries = [
            FileEntry(
                path='/test/file1.mp3',
                original='file1.mp3',
                directory='/test',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
            ),
        ]

        result = is_duplicate_name('song.mp3', '/test', entries, skip_index=1)

        assert result is True

        root.destroy()

    def test_no_duplicate_different_directory(self):
        """Should not detect duplicate in different directory."""
        root = tk.Tk()
        root.withdraw()

        entries = [
            FileEntry(
                path='/test/file1.mp3',
                original='file1.mp3',
                directory='/test',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
            ),
        ]

        result = is_duplicate_name('song.mp3', '/other', entries, skip_index=1)

        assert result is False

        root.destroy()

    def test_case_insensitive_comparison(self):
        """Should detect duplicates case-insensitively."""
        root = tk.Tk()
        root.withdraw()

        entries = [
            FileEntry(
                path='/test/file1.mp3',
                original='file1.mp3',
                directory='/test',
                new_name='Song.MP3',
                ext='.mp3',
                file_type='🎵',
            ),
        ]

        result = is_duplicate_name('SONG.mp3', '/test', entries, skip_index=1)

        assert result is True

        root.destroy()

    def test_skips_specified_index(self):
        """Should skip the specified index."""
        root = tk.Tk()
        root.withdraw()

        entries = [
            FileEntry(
                path='/test/file1.mp3',
                original='file1.mp3',
                directory='/test',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
            ),
        ]

        result = is_duplicate_name('song.mp3', '/test', entries, skip_index=0)

        assert result is False

        root.destroy()


class TestCheckForDuplicateDestinations:
    """Tests for the check_for_duplicate_destinations function."""

    def test_detects_duplicates_among_selected(self):
        """Should detect duplicates among selected entries."""
        root = tk.Tk()
        root.withdraw()

        entries = [
            FileEntry(
                path='/test/file1.mp3',
                original='file1.mp3',
                directory='/test',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
                selected=tk.BooleanVar(value=True),
            ),
            FileEntry(
                path='/test/file2.mp3',
                original='file2.mp3',
                directory='/test',
                new_name='Song.mp3',
                ext='.mp3',
                file_type='🎵',
                selected=tk.BooleanVar(value=True),
            ),
        ]

        result = check_for_duplicate_destinations(entries)

        assert result is True

        root.destroy()

    def test_no_duplicates_when_unselected(self):
        """Should not detect duplicates among unselected entries."""
        root = tk.Tk()
        root.withdraw()

        entries = [
            FileEntry(
                path='/test/file1.mp3',
                original='file1.mp3',
                directory='/test',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
                selected=tk.BooleanVar(value=True),
            ),
            FileEntry(
                path='/test/file2.mp3',
                original='file2.mp3',
                directory='/test',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
                selected=tk.BooleanVar(value=False),
            ),
        ]

        result = check_for_duplicate_destinations(entries)

        assert result is False

        root.destroy()

    def test_uses_target_dir_override(self):
        """Should use target_dir when specified."""
        root = tk.Tk()
        root.withdraw()

        entries = [
            FileEntry(
                path='/test/file1.mp3',
                original='file1.mp3',
                directory='/test1',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
                selected=tk.BooleanVar(value=True),
            ),
            FileEntry(
                path='/test/file2.mp3',
                original='file2.mp3',
                directory='/test2',
                new_name='song.mp3',
                ext='.mp3',
                file_type='🎵',
                selected=tk.BooleanVar(value=True),
            ),
        ]

        result = check_for_duplicate_destinations(entries, target_dir='/output')

        assert result is True

        root.destroy()
