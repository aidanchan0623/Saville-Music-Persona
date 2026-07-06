from __future__ import annotations

from datetime import date

from app.analysis.normalizer import normalise_collection, parse_played_date


def test_duplicate_track_normalisation_merges_video_id() -> None:
    raw = {
        "history": [
            {"videoId": "abc", "title": "Song", "artists": [{"name": "Artist"}], "played": "2026-06-01"},
            {"videoId": "abc", "title": "Song", "artists": [{"name": "Artist"}], "played": "2026-06-02"},
        ],
        "liked_songs": {"tracks": [{"videoId": "abc", "title": "Song", "artists": [{"name": "Artist"}]}]},
    }
    result = normalise_collection(raw, today=date(2026, 7, 1))
    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["play_count_in_period"] == 2
    assert result["tracks"][0]["liked"] is True


def test_missing_release_year_and_artist_are_safe() -> None:
    raw = {"history": [{"videoId": "abc", "title": "Ghost Track", "played": "2026-06-01"}]}
    result = normalise_collection(raw, today=date(2026, 7, 1))
    track = result["tracks"][0]
    assert track["primary_artist"] == "Unknown Artist"
    assert track["release_year"] is None


def test_partial_history_coverage_is_not_full_year() -> None:
    raw = {
        "history": [
            {"videoId": "a", "title": "A", "artists": [{"name": "Artist"}], "played": "2026-06-01"},
            {"videoId": "b", "title": "B", "artists": [{"name": "Artist"}], "played": "2026-06-20"},
        ]
    }
    result = normalise_collection(raw, today=date(2026, 7, 1))
    assert result["coverage"]["full_365_day_analysis"] is False
    assert result["coverage"]["days_represented"] == 20


def test_available_history_without_dates_is_labelled() -> None:
    raw = {"history": [{"videoId": "a", "title": "A", "artists": [{"name": "Artist"}]}]}
    result = normalise_collection(raw, today=date(2026, 7, 1))
    assert result["coverage"]["date_data_available"] is False
    assert "available-history analysis" in " ".join(result["coverage"]["notes"])


def test_parse_relative_played_dates() -> None:
    assert parse_played_date("2 weeks ago", today=date(2026, 7, 1)) == date(2026, 6, 17)

