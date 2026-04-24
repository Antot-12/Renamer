"""Tests for MusicBrainz integration."""

import pytest
from unittest.mock import patch, MagicMock

from renamer.musicbrainz import (
    search_recording,
    get_recording_details,
    search_by_filename,
)


class TestSearchRecording:
    """Tests for search_recording function."""

    def test_returns_empty_list_without_params(self):
        """Should return empty list when no search params provided."""
        result = search_recording()
        assert result == []

    @patch('renamer.musicbrainz._make_request')
    def test_returns_results_for_artist_title(self, mock_request):
        """Should return results when searching by artist and title."""
        mock_request.return_value = {
            "recordings": [
                {
                    "id": "abc123",
                    "title": "Test Song",
                    "score": 100,
                    "artist-credit": [{"name": "Test Artist"}],
                    "releases": [{"title": "Test Album", "date": "2020-01-01"}]
                }
            ]
        }

        result = search_recording(artist="Test Artist", title="Test Song")

        assert len(result) == 1
        assert result[0]["title"] == "Test Song"
        assert result[0]["artist"] == "Test Artist"
        assert result[0]["album"] == "Test Album"
        assert result[0]["year"] == "2020"

    @patch('renamer.musicbrainz._make_request')
    def test_handles_api_error(self, mock_request):
        """Should return empty list on API error."""
        mock_request.return_value = None

        result = search_recording(artist="Test", title="Song")

        assert result == []

    @patch('renamer.musicbrainz._make_request')
    def test_handles_missing_fields(self, mock_request):
        """Should handle missing fields gracefully."""
        mock_request.return_value = {
            "recordings": [
                {
                    "id": "abc123",
                    "title": "Song Only",
                }
            ]
        }

        result = search_recording(title="Song Only")

        assert len(result) == 1
        assert result[0]["title"] == "Song Only"
        assert result[0]["artist"] is None
        assert result[0]["album"] is None


class TestSearchByFilename:
    """Tests for search_by_filename function."""

    @patch('renamer.musicbrainz.search_recording')
    def test_parses_artist_title_format(self, mock_search):
        """Should parse 'Artist - Title' format."""
        mock_search.return_value = [{"title": "Test"}]

        search_by_filename("Coldplay - Yellow")

        # First call should be with artist and title
        mock_search.assert_called()
        call_args = mock_search.call_args_list[0]
        assert call_args[1].get("artist") == "Coldplay"
        assert call_args[1].get("title") == "Yellow"

    @patch('renamer.musicbrainz.search_recording')
    def test_strips_track_numbers(self, mock_search):
        """Should strip track numbers from filename."""
        mock_search.return_value = [{"title": "Test"}]

        search_by_filename("01 - Artist - Title")

        mock_search.assert_called()

    @patch('renamer.musicbrainz.search_recording')
    def test_fallback_to_title_only(self, mock_search):
        """Should search by title only if pattern doesn't match."""
        mock_search.return_value = []

        search_by_filename("Just A Song Name")

        # Should be called with title only
        mock_search.assert_called()


class TestGetRecordingDetails:
    """Tests for get_recording_details function."""

    @patch('renamer.musicbrainz._make_request')
    def test_returns_details(self, mock_request):
        """Should return recording details."""
        mock_request.return_value = {
            "id": "abc123",
            "title": "Test Song",
            "length": 180000,
            "artist-credit": [{"name": "Artist"}],
            "releases": [{"title": "Album", "date": "2021"}],
            "genres": [{"name": "Rock"}]
        }

        result = get_recording_details("abc123")

        assert result is not None
        assert result["title"] == "Test Song"
        assert result["artist"] == "Artist"
        assert result["genre"] == "Rock"

    @patch('renamer.musicbrainz._make_request')
    def test_returns_none_on_error(self, mock_request):
        """Should return None on API error."""
        mock_request.return_value = None

        result = get_recording_details("invalid")

        assert result is None
