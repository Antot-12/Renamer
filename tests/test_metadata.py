"""Tests for metadata extraction functions."""

import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from renamer.metadata import (
    sanitize,
    bytes_to_human_readable,
    get_audio_tags,
    get_image_dimensions,
    extract_metadata,
    format_audio_info,
    get_album_art,
)


class TestSanitize:
    """Tests for the sanitize function."""

    def test_sanitize_removes_illegal_characters(self):
        """Should remove Windows-illegal filename characters."""
        assert sanitize('file:name') == 'filename'
        assert sanitize('file*name') == 'filename'
        assert sanitize('file?name') == 'filename'
        assert sanitize('file"name') == 'filename'
        assert sanitize('file<name') == 'filename'
        assert sanitize('file>name') == 'filename'
        assert sanitize('file|name') == 'filename'
        assert sanitize('file\\name') == 'filename'
        assert sanitize('file/name') == 'filename'

    def test_sanitize_normalizes_whitespace(self):
        """Should collapse multiple spaces to single space."""
        assert sanitize('file   name') == 'file name'
        assert sanitize('  file  name  ') == 'file name'
        assert sanitize('file\t\nname') == 'file name'

    def test_sanitize_handles_none(self):
        """Should return empty string for None input."""
        assert sanitize(None) == ''

    def test_sanitize_handles_empty_string(self):
        """Should return empty string for empty input."""
        assert sanitize('') == ''

    def test_sanitize_preserves_valid_characters(self):
        """Should keep valid filename characters intact."""
        assert sanitize('Artist - Song (2023)') == 'Artist - Song (2023)'
        assert sanitize('файл_назва') == 'файл_назва'


class TestBytesToHumanReadable:
    """Tests for the bytes_to_human_readable function."""

    def test_converts_bytes_to_mb(self):
        """Should convert bytes to MB with one decimal place."""
        assert bytes_to_human_readable(1048576) == '1.0 MB'
        assert bytes_to_human_readable(1572864) == '1.5 MB'
        assert bytes_to_human_readable(10485760) == '10.0 MB'

    def test_handles_zero(self):
        """Should return empty string for zero."""
        assert bytes_to_human_readable(0) == ''

    def test_handles_none(self):
        """Should return empty string for None."""
        assert bytes_to_human_readable(None) == ''

    def test_handles_small_files(self):
        """Should handle files smaller than 1 MB."""
        assert bytes_to_human_readable(512000) == '0.5 MB'
        assert bytes_to_human_readable(102400) == '0.1 MB'


class TestFormatAudioInfo:
    """Tests for the format_audio_info function."""

    def test_formats_duration_and_bitrate(self):
        """Should format both duration and bitrate."""
        assert format_audio_info(180.5, 320000) == '180s / 320kbps'
        assert format_audio_info(60.0, 128000) == '60s / 128kbps'

    def test_formats_duration_only(self):
        """Should format duration alone when no bitrate."""
        assert format_audio_info(180.5, None) == '180s'
        assert format_audio_info(180.5, 0) == '180s'

    def test_handles_none_duration(self):
        """Should return empty string when no duration."""
        assert format_audio_info(None, 320000) == ''
        assert format_audio_info(None, None) == ''

    def test_handles_zero_duration(self):
        """Should handle zero duration (very short files)."""
        assert format_audio_info(0.5, 320000) == '0s / 320kbps'


class TestGetAudioTags:
    """Tests for the get_audio_tags function."""

    def test_returns_none_tuple_for_missing_file(self):
        """Should return None tuple for non-existent file."""
        result = get_audio_tags('/nonexistent/path/file.mp3')
        assert result == (None, None, None, None)

    @patch('renamer.metadata.MUTAGEN_AVAILABLE', False)
    def test_returns_none_when_mutagen_unavailable(self):
        """Should return None tuple when mutagen not installed."""
        result = get_audio_tags('/some/file.mp3')
        assert result == (None, None, None, None)

    @patch('renamer.metadata.AudioFile')
    @patch('renamer.metadata.MUTAGEN_AVAILABLE', True)
    def test_extracts_tags_successfully(self, mock_audio_file):
        """Should extract artist, title, duration, bitrate."""
        mock_audio = MagicMock()
        mock_audio.get.side_effect = lambda key, default: {
            'artist': ['Test Artist'],
            'title': ['Test Title'],
        }.get(key, default)
        mock_audio.info.length = 180.0
        mock_audio.info.bitrate = 320000
        mock_audio_file.return_value = mock_audio

        artist, title, duration, bitrate = get_audio_tags('/test/file.mp3')

        assert artist == 'Test Artist'
        assert title == 'Test Title'
        assert duration == 180.0
        assert bitrate == 320000


class TestGetImageDimensions:
    """Tests for the get_image_dimensions function."""

    def test_returns_none_for_missing_file(self):
        """Should return None tuple for non-existent file."""
        result = get_image_dimensions('/nonexistent/path/image.png')
        assert result == (None, None)

    def test_extracts_dimensions_from_real_image(self):
        """Should extract width and height from actual image."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            from PIL import Image
            img = Image.new('RGB', (100, 200), color='red')
            img.save(f.name)
            f.flush()

            width, height = get_image_dimensions(f.name)

            assert width == 100
            assert height == 200

            os.unlink(f.name)

    def test_returns_none_for_corrupted_image(self):
        """Should return None tuple for invalid image data."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            f.write(b'not an image')
            f.flush()

            result = get_image_dimensions(f.name)

            assert result == (None, None)

            os.unlink(f.name)


class TestExtractMetadata:
    """Tests for the extract_metadata function."""

    def test_extracts_image_metadata(self):
        """Should extract dimensions for image files."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            from PIL import Image
            img = Image.new('RGB', (640, 480), color='blue')
            img.save(f.name)
            f.flush()

            artist, title, info, size = extract_metadata(f.name, '.png')

            assert artist is None
            assert title is None
            assert info == '640×480'
            assert size > 0

            os.unlink(f.name)

    def test_raises_for_missing_file(self):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            extract_metadata('/nonexistent/file.txt', '.txt')

    def test_returns_empty_info_for_unknown_types(self):
        """Should return empty info for unsupported file types."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'test content')
            f.flush()

            artist, title, info, size = extract_metadata(f.name, '.txt')

            assert artist is None
            assert title is None
            assert info == ''
            assert size > 0

            os.unlink(f.name)


class TestGetAlbumArt:
    """Tests for get_album_art function."""

    def test_returns_none_for_nonexistent_file(self):
        """Should return None for nonexistent file."""
        result = get_album_art('/nonexistent/file.mp3')
        assert result is None

    def test_returns_none_for_non_audio_file(self):
        """Should return None for non-audio file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'test content')
            f.flush()

            result = get_album_art(f.name)

            assert result is None
            os.unlink(f.name)

    def test_returns_none_for_audio_without_art(self):
        """Should return None when audio has no embedded art."""
        result = get_album_art('/nonexistent/file.mp3')
        assert result is None
