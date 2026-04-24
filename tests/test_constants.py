"""Tests for constants module."""

import pytest

from renamer.constants import (
    AUDIO,
    IMG,
    DOC,
    VID,
    ARC,
    PRESENTATION,
    CODE,
    TEXT,
    GAME,
    SUPPORTED,
    MAX_FILES,
    MAX_PREVIEW_SIZE,
    MAX_PREVIEW_MEMORY,
    TYPE_EMOJI,
)


class TestFileTypeConstants:
    """Tests for file type extension constants."""

    def test_audio_extensions(self):
        """Should contain common audio formats."""
        assert '.mp3' in AUDIO
        assert '.flac' in AUDIO
        assert '.wav' in AUDIO
        assert '.ogg' in AUDIO
        assert '.m4a' in AUDIO
        assert '.aac' in AUDIO
        assert '.opus' in AUDIO

    def test_image_extensions(self):
        """Should contain common image formats."""
        assert '.jpg' in IMG
        assert '.jpeg' in IMG
        assert '.png' in IMG
        assert '.gif' in IMG
        assert '.webp' in IMG
        assert '.svg' in IMG
        assert '.psd' in IMG

    def test_document_extensions(self):
        """Should contain common document formats."""
        assert '.pdf' in DOC
        assert '.docx' in DOC
        assert '.txt' in DOC
        assert '.xlsx' in DOC
        assert '.csv' in DOC

    def test_video_extensions(self):
        """Should contain common video formats."""
        assert '.mp4' in VID
        assert '.mov' in VID
        assert '.avi' in VID
        assert '.mkv' in VID
        assert '.webm' in VID

    def test_archive_extensions(self):
        """Should contain common archive formats."""
        assert '.zip' in ARC
        assert '.rar' in ARC
        assert '.7z' in ARC
        assert '.tar' in ARC
        assert '.gz' in ARC

    def test_presentation_extensions(self):
        """Should contain common presentation formats."""
        assert '.ppt' in PRESENTATION
        assert '.pptx' in PRESENTATION
        assert '.odp' in PRESENTATION
        assert '.key' in PRESENTATION

    def test_code_extensions(self):
        """Should contain common programming file formats."""
        assert '.py' in CODE
        assert '.js' in CODE
        assert '.ts' in CODE
        assert '.java' in CODE
        assert '.cpp' in CODE
        assert '.go' in CODE
        assert '.rs' in CODE
        assert '.html' in CODE
        assert '.css' in CODE
        assert '.json' in CODE
        assert '.yaml' in CODE

    def test_text_extensions(self):
        """Should contain common text file formats."""
        assert '.txt' in TEXT
        assert '.log' in TEXT
        assert '.srt' in TEXT
        assert '.env' in TEXT

    def test_game_extensions(self):
        """Should contain common game file formats."""
        assert '.sav' in GAME
        assert '.pak' in GAME
        assert '.unity' in GAME
        assert '.rom' in GAME

    def test_supported_includes_all_types(self):
        """Should include all file types."""
        for ext in AUDIO:
            assert ext in SUPPORTED
        for ext in IMG:
            assert ext in SUPPORTED
        for ext in DOC:
            assert ext in SUPPORTED
        for ext in VID:
            assert ext in SUPPORTED
        for ext in ARC:
            assert ext in SUPPORTED
        for ext in PRESENTATION:
            assert ext in SUPPORTED
        for ext in CODE:
            assert ext in SUPPORTED
        for ext in TEXT:
            assert ext in SUPPORTED
        for ext in GAME:
            assert ext in SUPPORTED


class TestResourceLimits:
    """Tests for resource limit constants."""

    def test_max_files_is_reasonable(self):
        """MAX_FILES should be a reasonable limit."""
        assert MAX_FILES > 0
        assert MAX_FILES <= 100000

    def test_max_preview_size_is_reasonable(self):
        """MAX_PREVIEW_SIZE should be a reasonable pixel limit."""
        assert MAX_PREVIEW_SIZE > 0
        assert MAX_PREVIEW_SIZE <= 8192

    def test_max_preview_memory_is_reasonable(self):
        """MAX_PREVIEW_MEMORY should be a reasonable byte limit."""
        assert MAX_PREVIEW_MEMORY > 0
        assert MAX_PREVIEW_MEMORY <= 200 * 1024 * 1024  # 200 MB


class TestTypeEmoji:
    """Tests for type emoji mapping."""

    def test_has_all_types(self):
        """Should have emoji for all file types."""
        assert 'audio' in TYPE_EMOJI
        assert 'image' in TYPE_EMOJI
        assert 'document' in TYPE_EMOJI
        assert 'video' in TYPE_EMOJI
        assert 'archive' in TYPE_EMOJI
        assert 'presentation' in TYPE_EMOJI
        assert 'code' in TYPE_EMOJI
        assert 'text' in TYPE_EMOJI
        assert 'game' in TYPE_EMOJI

    def test_emoji_are_non_empty(self):
        """All emoji values should be non-empty."""
        for key, emoji in TYPE_EMOJI.items():
            assert emoji, f"Empty emoji for {key}"
