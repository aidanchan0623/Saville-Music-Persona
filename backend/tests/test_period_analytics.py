from __future__ import annotations

from datetime import date, timedelta

from app.analysis.duration import annotate_normalised_durations, duration_quality
from app.analysis.normalizer import normalise_collection
from app.analysis.periods import (
    album_songs_payload,
    albums_payload,
    artist_songs_payload,
    classification_label,
    listening_minutes_payload,
    movement_payload,
    resolve_period,
    taste_dna_comparison_payload,
    top_payload,
)
from app.analysis.score_interpretations import interpret_score


def _history_item(
    video_id: str,
    title: str,
    artist: str | list[str],
    played: str,
    duration: int | str | None = 180,
    album: str | None = None,
) -> dict:
    artist_names = artist if isinstance(artist, list) else [artist]
    item = {
        "videoId": video_id,
        "title": title,
        "artists": [{"name": name} for name in artist_names],
        "played": played,
        "source": "test",
    }
    if album:
        item["album"] = {"name": album, "id": f"alb-{album.lower().replace(' ', '-')}"}
    if duration is not None:
        if isinstance(duration, int):
            item["duration_seconds"] = duration
        else:
            item["duration"] = duration
    return item


def test_daily_minutes_preserve_zero_days_and_duration_coverage() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("a1", "Song A", "Bring Me The Horizon", "2026-07-01", 180),
                _history_item("b1", "Song B", "My Chemical Romance", "2026-07-01", "4:00"),
                _history_item("a1", "Song A", "Bring Me The Horizon", "2026-07-03", 180),
                _history_item("c1", "Song C", "Wisp", "2026-07-03", None),
            ]
        },
        today=date(2026, 7, 7),
    )
    payload = listening_minutes_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))
    by_date = {item["date"]: item["value"] for item in payload["daily"]}
    assert by_date["2026-07-01"] == 7.0
    assert by_date["2026-07-02"] == 0.0
    assert by_date["2026-07-03"] == 3.0
    assert payload["duration_quality"]["duration_coverage_percent"] == 75.0
    assert payload["metrics"]["active_listening_days"] == 2


def test_timezone_day_boundary_uses_configured_local_day() -> None:
    normalised = annotate_normalised_durations(
        {
            "tracks": [
                {
                    "track_id": "video:late",
                    "video_id": "late",
                    "title": "Late Song",
                    "artists": ["Wisp"],
                    "primary_artist": "Wisp",
                    "duration_seconds": 120,
                }
            ],
            "play_events": [
                {
                    "track_id": "video:late",
                    "video_id": "late",
                    "title": "Late Song",
                    "primary_artist": "Wisp",
                    "artists": ["Wisp"],
                    "played_at": "2026-07-01T16:30:00+00:00",
                }
            ],
            "coverage": {},
            "metadata": {},
        }
    )
    payload = listening_minutes_payload(normalised, "month", "2026-07", timezone_name="Asia/Kuala_Lumpur", today=date(2026, 7, 7))
    by_date = {item["date"]: item["value"] for item in payload["daily"]}
    assert by_date["2026-07-02"] == 2.0
    assert by_date["2026-07-01"] == 0.0


def test_duration_cache_reuse_marks_cached_tracks() -> None:
    normalised = normalise_collection({"history": [_history_item("cache1", "Cached Song", "Oasis", "2026-07-02", None)]}, today=date(2026, 7, 7))
    cached = annotate_normalised_durations(
        normalised,
        {"cache1": {"duration_seconds": 210, "duration_source": "duration_cache", "duration_confidence": "high"}},
    )
    event = cached["play_events"][0]
    assert event["duration_seconds"] == 210
    assert event["duration_source"] == "duration_cache"
    assert duration_quality(cached["play_events"])["duration_coverage_percent"] == 100.0


def test_long_videos_and_podcasts_are_not_counted_as_music_minutes() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("long1", "Two Hour Interview Podcast", "Some Channel", "2026-07-02", 7200),
                _history_item("song1", "Real Song", "Radiohead", "2026-07-02", 300),
            ]
        },
        today=date(2026, 7, 7),
    )
    payload = listening_minutes_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))
    assert payload["metrics"]["selected_period_total_minutes"] == 5.0
    assert payload["duration_quality"]["events_excluded_from_minutes"] == 1
    reasons = {item["reason"] for item in payload["duration_quality"]["main_exclusion_reasons"]}
    assert "non_music_content" in reasons
    ranked = top_payload(normalised, "tracks", "month", "2026-07", today=date(2026, 7, 7))
    assert [item["title"] for item in ranked["items"]] == ["Real Song"]
    assert ranked["items"][0]["thumbnail"] == "https://i.ytimg.com/vi/song1/hqdefault.jpg"


def test_period_resolution_for_current_month_selected_month_and_rolling_year() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("old", "Old", "Oasis", "2025-07-06", 180),
                _history_item("edge", "Edge", "Oasis", "2025-07-08", 180),
                _history_item("month", "Month", "Oasis", "2026-06-12", 180),
                _history_item("now", "Now", "Oasis", "2026-07-02", 180),
            ]
        },
        today=date(2026, 7, 7),
    )
    this_month = resolve_period(normalised, "this_month", today=date(2026, 7, 7))
    selected = resolve_period(normalised, "month", "2026-06", today=date(2026, 7, 7))
    rolling = listening_minutes_payload(normalised, "rolling_year", today=date(2026, 7, 7))
    assert this_month["start_date"] == date(2026, 7, 1)
    assert selected["start_date"] == date(2026, 6, 1)
    assert rolling["duration_quality"]["total_detected_plays"] == 3


def test_top_ranking_tiebreaks_use_minutes_and_movement_is_deterministic() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("short", "Short", "Oasis", "2026-07-02", 120),
                _history_item("long", "Long", "Oasis", "2026-07-02", 240),
                _history_item("prev", "Previous", "Oasis", "2026-06-02", 180),
            ]
        },
        today=date(2026, 7, 7),
    )
    payload = top_payload(normalised, "tracks", "month", "2026-07", today=date(2026, 7, 7))
    assert payload["items"][0]["title"] == "Long"
    assert payload["sample_warning"]
    assert movement_payload(2, 5, True)["direction"] == "up"
    assert movement_payload(5, 2, True)["direction"] == "down"
    assert movement_payload(1, None, True)["direction"] == "new"


def test_top_label_classification_rules() -> None:
    assert classification_label(1, 12, "month", None, None, 1) == "One-month spike"
    assert classification_label(4, 5, "month", None, 4, 5) == "Long-term anchor"
    assert classification_label(1, 3, "month", None, None, 0) == "Current obsession"
    assert classification_label(7, 2, "month", {"direction": "new"}, None, 0) == "New arrival"


def test_artist_songs_drilldown_matches_featured_artists() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("duet", "Shared Chorus", ["Lead Artist", "Guest Artist"], "2026-07-02", 180, "Shared Album"),
                _history_item("solo", "Solo Track", "Lead Artist", "2026-07-03", 180, "Shared Album"),
            ]
        },
        today=date(2026, 7, 7),
    )
    payload = artist_songs_payload(normalised, "Guest Artist", "month", "2026-07", today=date(2026, 7, 7))
    assert payload["total_plays"] == 1
    assert payload["unique_songs"] == 1
    assert payload["songs"][0]["title"] == "Shared Chorus"
    assert payload["songs"][0]["share_of_artist_plays"] == 100.0


def test_favourite_albums_rank_by_plays_minutes_and_unique_songs() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("a1", "Album Song One", "Album Artist", "2026-07-01", 180, "Real Album"),
                _history_item("a1", "Album Song One", "Album Artist", "2026-07-02", 180, "Real Album"),
                _history_item("a2", "Album Song Two", "Album Artist", "2026-07-03", 180, "Real Album"),
                _history_item("a2", "Album Song Two", "Album Artist", "2026-07-04", 180, "Real Album"),
                _history_item("b1", "Single Driver", "Single Artist", "2026-07-01", 180, "Single Album"),
                _history_item("b1", "Single Driver", "Single Artist", "2026-07-02", 180, "Single Album"),
                _history_item("b1", "Single Driver", "Single Artist", "2026-07-03", 180, "Single Album"),
                _history_item("unknown", "Unknown Album Track", "Mystery", "2026-07-04", 180),
            ]
        },
        today=date(2026, 7, 7),
    )
    albums = albums_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))["albums"]
    assert albums[0]["album"] == "Real Album"
    assert albums[0]["thumbnail"] == "https://i.ytimg.com/vi/a1/hqdefault.jpg"
    assert albums[0]["unique_songs"] == 2
    assert albums[0]["album_signal_note"] == "Real album-level signal."
    assert albums[1]["label"] == "Single-led album signal"
    assert all(item["album"] != "Unknown Album" for item in albums)

    drilldown = album_songs_payload(normalised, "Real Album", "Album Artist", "month", "2026-07", today=date(2026, 7, 7))
    assert drilldown["total_plays"] == 4
    assert [song["title"] for song in drilldown["songs"]] == ["Album Song One", "Album Song Two"]
    assert drilldown["songs"][0]["share_of_album_plays"] == 50.0


def test_score_interpretation_thresholds_are_plain_english() -> None:
    repeat = interpret_score({"key": "repeat", "value": 78, "inputs": {"total_track_plays": 1000, "unique_tracks": 220}})
    nostalgia = interpret_score({"key": "nostalgia", "value": 0, "inputs": {"tracks_with_release_year": 0}})
    niche = interpret_score({"key": "mainstream_niche", "value": 90, "inputs": {"artist_subscriber_metadata_coverage": 64.9}})
    assert repeat["status_title"] == "Emotional loop specialist"
    assert "personal soundtrack" in repeat["plain_english"]
    assert nostalgia["status_title"] == "Era preference unavailable"
    assert niche["status_title"] == "Niche-leaning listener"


def test_taste_dna_comparison_suppresses_small_samples() -> None:
    normalised = normalise_collection({"history": [_history_item("a", "A", "Bring Me The Horizon", "2026-07-02", 180)]}, today=date(2026, 7, 7))
    comparison = taste_dna_comparison_payload(normalised, today=date(2026, 7, 7))
    assert comparison["sample_warning"]
    assert comparison["claims"]["growing_cluster"] is None


def test_taste_dna_comparison_detects_growing_cluster_with_enough_data() -> None:
    history = []
    start = date(2026, 7, 1)
    for index in range(60):
        history.append(_history_item(f"w{index}", f"Wisp {index}", "Wisp", (start + timedelta(days=index % 6)).isoformat(), 180))
    for index in range(80):
        history.append(_history_item(f"b{index}", f"BMTH {index}", "Bring Me The Horizon", (date(2026, 2, 1) + timedelta(days=index % 20)).isoformat(), 180))
    normalised = normalise_collection({"history": history}, today=date(2026, 7, 7))
    comparison = taste_dna_comparison_payload(normalised, today=date(2026, 7, 7))
    assert comparison["sample_warning"] is None
    assert comparison["claims"]["growing_cluster"] is not None
