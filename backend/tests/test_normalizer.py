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
    assert parse_played_date("Last week", today=date(2026, 7, 1)) == date(2026, 6, 24)
    assert parse_played_date("This week", today=date(2026, 7, 7)) == date(2026, 7, 6)


def test_preference_evidence_and_non_music_do_not_create_analytics_plays() -> None:
    raw = {
        "history": [
            {"videoId": "song001", "title": "Real Song", "artists": [{"name": "Artist"}], "played": "2026-07-01T10:00:00Z"},
            {"videoId": "pod001", "title": "Long Interview Podcast", "artists": [{"name": "Channel"}], "played": "2026-07-01T11:00:00Z", "duration_seconds": 7200},
        ],
        "liked_songs": {"tracks": [{"videoId": "like001", "title": "Liked", "artists": [{"name": "Artist"}]}]},
        "library_songs": [{"videoId": "lib0001", "title": "Library", "artists": [{"name": "Artist"}]}],
        "platform_top_tracks": [{"source": "spotify", "source_track_id": "spotify:track:top", "title": "Top", "artists": [{"name": "Artist"}]}],
    }
    result = normalise_collection(raw, today=date(2026, 7, 2))
    assert result["metadata"]["play_count"] == 1
    assert {event["evidence_type"] for event in result["listening_events"]} == {
        "play_event", "liked_item", "library_item", "platform_top_item"
    }
    assert any(event["music_classification"] == "non_music" for event in result["excluded_play_events"])
    assert result["import_diagnostics"]["accepted_music_plays"] == 1


def test_canonical_events_are_idempotent_for_a_repeated_takeout_import() -> None:
    raw = {
        "takeout_import_batch_id": "first-import",
        "takeout_history": [
            {"videoId": "repeat01", "title": "Repeat", "artists": [{"name": "Artist"}], "played": "2026-07-01T10:00:00+00:00", "source": "google_takeout"}
        ],
    }
    first = normalise_collection(raw, today=date(2026, 7, 2))
    second = normalise_collection({**raw, "takeout_import_batch_id": "second-import"}, today=date(2026, 7, 2))
    assert first["play_events"][0]["event_id"] == second["play_events"][0]["event_id"]
    assert first["play_events"][0]["timestamp_utc"] == "2026-07-01T10:00:00+00:00"
