from __future__ import annotations

from datetime import date, timedelta

from app.analysis import periods
from app.analysis.duration import annotate_normalised_durations, duration_quality
from app.analysis.insights import insights_payload
from app.analysis.media import album_id_key, album_name_artist_key
from app.analysis.normalizer import normalise_collection
from app.analysis.periods import (
    album_songs_payload,
    albums_payload,
    artist_songs_payload,
    classification_label,
    listening_minutes_payload,
    movement_payload,
    rank_items,
    resolve_period,
    seconds_for_events,
    taste_dna_comparison_payload,
    top_payload,
    tracks_by_id,
)
from app.analysis.score_interpretations import interpret_score


def _history_item(
    video_id: str,
    title: str,
    artist: str | list[str],
    played: str,
    duration: int | str | None = 180,
    album: str | None = None,
    album_thumbnail: str | None = None,
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
        if album_thumbnail:
            item["album"]["thumbnails"] = [{"url": album_thumbnail, "width": 600, "height": 600}]
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


def test_insights_reuses_period_rankings_and_preserves_unclassified_plays() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("bmth", "Heavy One", "Bring Me The Horizon", "2026-07-01", 180),
                _history_item("bmth", "Heavy One", "Bring Me The Horizon", "2026-07-02", 180),
                _history_item("wisp", "Haze", "Wisp", "2026-07-03", None),
                _history_item("unknown", "Unknown Lane", "Unmapped Artist", "2026-07-04", 240),
            ]
        },
        today=date(2026, 7, 7),
    )
    payload = insights_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))
    artists = top_payload(normalised, "artists", "month", "2026-07", today=date(2026, 7, 7))
    tracks = top_payload(normalised, "tracks", "month", "2026-07", today=date(2026, 7, 7))

    assert payload["schemaVersion"] == 1
    assert payload["summary"]["detectedMinutes"] == 10.0
    assert sum(point["detectedMinutes"] for point in payload["rhythm"]["weekly"]) == 10.0
    assert sum(point["detectedMinutes"] for point in payload["rhythm"]["monthly"]) == 10.0
    assert payload["topArtists"][0]["artist"] == artists["items"][0]["artist"]
    assert payload["repeatedSongs"][0]["title"] == tracks["items"][0]["title"]
    assert payload["musicProfile"]["classifiedPlays"] == 3
    assert payload["musicProfile"]["unclassifiedPlays"] == 1
    assert payload["musicProfile"]["coverage"] == 0.75
    assert round(sum(axis["value"] for axis in payload["musicProfile"]["axes"]), 1) == 75.0
    assert payload["rhythm"]["weekly"][0]["playCount"] == 4


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


def test_exact_video_music_proof_promotes_quarantined_takeout_without_guessing() -> None:
    normalised = normalise_collection(
        {
            "source": "google_takeout",
            "history": [
                {
                    "videoId": "verified-music",
                    "title": "Artist - Verified Song (Official Video)",
                    "played": "2026-07-02",
                    "source": "google_takeout",
                    "takeoutMusicEvidence": "unverified_youtube_history",
                    "sourceFormat": "html",
                    "duration_seconds": 210,
                }
            ],
        },
        today=date(2026, 7, 7),
    )
    assert normalised["play_events"] == []

    rebuilt = annotate_normalised_durations(
        normalised,
        {
            "verified-music": {
                "duration_seconds": 210,
                "duration_source": "ytmusicapi.public.get_song",
                "duration_confidence": "high",
                "music_classification": "confirmed_music",
                "music_classification_source": "ytmusicapi.public.get_song",
                "media_title": "Verified Song",
                "media_author": "Artist - Topic",
                "identity_confidence": "high",
            }
        },
    )

    assert len(rebuilt["play_events"]) == 1
    assert rebuilt["play_events"][0]["title"] == "Verified Song"
    assert rebuilt["play_events"][0]["artist"] == "Artist"
    assert rebuilt["excluded_play_events"] == []


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


def test_top_artists_use_official_metadata_not_track_art() -> None:
    raw = {
        "history": [
            _history_item("official-song", "Official Song", "Official Artist", "2026-07-02", 180),
            _history_item("official-song", "Official Song", "Official Artist", "2026-07-03", 180),
            _history_item("plain-song", "Plain Song", "Plain Artist", "2026-07-02", 180),
        ],
        "artist_image_cache_v2": artist_cache_v2("Official Artist", "UC-official", "https://yt.example/official.jpg"),
    }
    normalised = normalise_collection(raw, today=date(2026, 7, 7))
    artists = top_payload(normalised, "artists", "month", "2026-07", today=date(2026, 7, 7))["items"]
    by_artist = {item["artist"]: item for item in artists}
    assert by_artist["Official Artist"]["thumbnail"] == "https://yt.example/official.jpg"
    assert by_artist["Official Artist"]["artist_image_url"] == "https://yt.example/official.jpg"
    assert by_artist["Plain Artist"]["thumbnail"] is None


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
    assert albums[0]["thumbnail"] is None
    assert albums[0]["album_image_url"] is None
    assert albums[0]["unique_songs"] == 2
    assert albums[0]["album_signal_note"] == "Real album-level signal."
    assert albums[1]["label"] == "Single-led album signal"
    assert albums[1]["album_image_url"] is None
    assert albums[1]["thumbnail"] == "https://i.ytimg.com/vi/b1/hqdefault.jpg"
    assert all(item["album"] != "Unknown Album" for item in albums)

    drilldown = album_songs_payload(normalised, "Real Album", "Album Artist", "month", "2026-07", today=date(2026, 7, 7))
    assert drilldown["total_plays"] == 4
    assert [song["title"] for song in drilldown["songs"]] == ["Album Song One", "Album Song Two"]
    assert drilldown["songs"][0]["share_of_album_plays"] == 50.0


def test_album_cover_uses_album_metadata_not_artist_or_video_art() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item(
                    "mcr-song",
                    "MCR Song",
                    "My Chemical Romance",
                    "2026-07-01",
                    180,
                    "The Black Parade",
                    album_thumbnail="https://yt.example/black-parade-cover.jpg",
                )
            ],
            "artist_image_cache_v2": artist_cache_v2("My Chemical Romance", "UC-mcr", "https://yt.example/mcr-artist.jpg"),
        },
        today=date(2026, 7, 7),
    )
    albums = albums_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))["albums"]
    assert albums[0]["album_image_url"] == "https://yt.example/black-parade-cover.jpg"
    assert albums[0]["thumbnail"] == "https://yt.example/black-parade-cover.jpg"
    assert albums[0]["thumbnail"] != "https://yt.example/mcr-artist.jpg"


def test_album_cover_uses_typed_album_cache() -> None:
    normalised = normalise_collection(
        {
            "history": [_history_item("bmth-song", "Can You Feel My Heart", "Bring Me The Horizon", "2026-07-01", 180, "Sempiternal")],
            "album_image_cache_v1": album_cache_v1("Sempiternal", "Bring Me The Horizon", "alb-sempiternal", "https://yt.example/sempiternal-cover.jpg"),
            "artist_image_cache_v2": artist_cache_v2("Bring Me The Horizon", "UC-bmth", "https://yt.example/bmth-artist.jpg"),
        },
        today=date(2026, 7, 7),
    )
    albums = albums_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))["albums"]
    assert albums[0]["album_image_url"] == "https://yt.example/sempiternal-cover.jpg"
    assert albums[0]["album_image_source"] == "youtube_album_cover"
    assert albums[0]["thumbnail"] != "https://yt.example/bmth-artist.jpg"


def test_tracks_never_inherit_artist_profile_art() -> None:
    normalised = normalise_collection(
        {
            "history": [_history_item("mcr-video", "Famous Last Words", "My Chemical Romance", "2026-07-01", 180)],
            "artist_image_cache_v2": artist_cache_v2("My Chemical Romance", "UC-mcr", "https://yt.example/mcr-artist.jpg"),
        },
        today=date(2026, 7, 7),
    )
    tracks = top_payload(normalised, "tracks", "month", "2026-07", today=date(2026, 7, 7))["items"]
    assert tracks[0]["track_image_url"] == "https://i.ytimg.com/vi/mcr-video/hqdefault.jpg"
    assert tracks[0]["thumbnail"] != "https://yt.example/mcr-artist.jpg"


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
        history.append(_history_item(f"k{index}", f"K-pop {index}", "FIFTY FIFTY", (start + timedelta(days=index % 6)).isoformat(), 180))
    for index in range(80):
        history.append(_history_item(f"b{index}", f"BMTH {index}", "Bring Me The Horizon", (date(2026, 2, 1) + timedelta(days=index % 20)).isoformat(), 180))
    normalised = normalise_collection({"history": history}, today=date(2026, 7, 7))
    comparison = taste_dna_comparison_payload(normalised, today=date(2026, 7, 7))
    assert comparison["sample_warning"] is None
    assert comparison["claims"]["growing_cluster"] is not None


def test_artist_ranking_uses_primary_attribution_without_collaborator_rescans(monkeypatch) -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item(f"duet-{index}", f"Duet {index}", ["Lead Artist", "Guest Artist"], "2026-07-02", 180)
                for index in range(20)
            ]
        },
        today=date(2026, 7, 7),
    )
    events = normalised["play_events"]
    original = periods.artist_names_for
    calls = 0

    def counted_artist_names(track: dict, event: dict | None = None) -> list[str]:
        nonlocal calls
        calls += 1
        return original(track, event)

    monkeypatch.setattr(periods, "artist_names_for", counted_artist_names)
    ranked = periods.rank_items(events, periods.tracks_by_id(normalised), "artists")

    assert calls == 0
    assert ranked[0]["raw_appearance_count"] == len(events)


def test_repeated_track_uses_every_event_duration_for_minutes() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("repeat", "Repeat Song", "Repeat Artist", f"2026-07-02T10:{index:02d}:00+00:00", 240)
                for index in range(10)
            ]
        },
        today=date(2026, 7, 7),
    )
    minutes = listening_minutes_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))
    track = top_payload(normalised, "tracks", "month", "2026-07", today=date(2026, 7, 7))["items"][0]

    assert track["play_count"] == 10
    assert track["detected_seconds"] == 2400
    assert track["detected_minutes"] == 40.0
    assert minutes["metrics"]["selected_period_total_minutes"] == 40.0


def test_same_day_repeats_and_missing_duration_coverage_reconcile() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item("same", "Same Day", "Artist A", "2026-07-02T10:00:00+00:00", 180),
                _history_item("same", "Same Day", "Artist A", "2026-07-02T11:00:00+00:00", 180),
                _history_item("missing", "Missing Duration", "Artist B", "2026-07-02T12:00:00+00:00", None),
            ]
        },
        today=date(2026, 7, 7),
    )
    events = normalised["play_events"]
    tracks = rank_items(events, tracks_by_id(normalised), "tracks")
    minutes = listening_minutes_payload(normalised, "month", "2026-07", today=date(2026, 7, 7))

    assert tracks[0]["play_count"] == 2
    assert tracks[0]["detected_seconds"] == 360
    assert tracks[0]["duration_coverage_percent"] == 100.0
    missing = next(item for item in tracks if item["track_id"] == "video:missing")
    assert missing["play_count"] == 1
    assert missing["detected_seconds"] == 0
    assert missing["duration_coverage_percent"] == 0.0
    assert seconds_for_events(events) == sum(item["detected_seconds"] for item in tracks)
    assert minutes["metrics"]["selected_period_total_minutes"] == 6.0
    assert minutes["duration_quality"]["duration_coverage_percent"] == 66.7


def test_artist_metrics_use_primary_artist_events_without_fractional_plays() -> None:
    normalised = normalise_collection(
        {
            "history": [
                _history_item(f"duet-{index}", f"Duet {index}", ["Lead Artist", "Guest Artist"], f"2026-07-02T10:{index:02d}:00+00:00", 180)
                for index in range(3)
            ]
            + [_history_item("guest-solo", "Guest Solo", "Guest Artist", "2026-07-03T10:00:00+00:00", 240)]
        },
        today=date(2026, 7, 7),
    )
    artists = rank_items(normalised["play_events"], tracks_by_id(normalised), "artists")
    by_name = {item["artist"]: item for item in artists}

    assert by_name["Lead Artist"]["play_count"] == 3
    assert by_name["Lead Artist"]["detected_seconds"] == 540
    assert by_name["Guest Artist"]["play_count"] == 1
    assert by_name["Guest Artist"]["detected_seconds"] == 240
    assert all(isinstance(item["play_count"], int) for item in artists)
    assert all("weighted_play_score" not in item for item in artists)


def test_top_songs_merge_exact_title_artist_across_video_ids() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": "official-video", "title": "Same Song", "artists": [{"name": "Artist"}], "played": "2026-07-01"},
                {"videoId": "official-audio", "title": "Same Song", "artists": [{"name": "Artist"}], "played": "2026-07-02"},
                {"videoId": "live-version", "title": "Same Song (Live)", "artists": [{"name": "Artist"}], "played": "2026-07-03"},
            ]
        },
        today=date(2026, 7, 7),
    )

    ranked = rank_items(normalised["play_events"], tracks_by_id(normalised), "tracks")

    assert [(item["title"], item["play_count"]) for item in ranked] == [("Same Song", 2), ("Same Song (Live)", 1)]
    assert ranked[0]["track_id"] in {"video:official-video", "video:official-audio"}


def test_top_songs_strip_presentation_labels_but_keep_real_versions_separate() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": "video", "title": "Same Song (Official Music Video)", "artists": [{"name": "Artist"}], "played": "2026-07-01"},
                {"videoId": "lyrics", "title": "Same Song - Lyrics", "artists": [{"name": "Artist"}], "played": "2026-07-02"},
                {"videoId": "live", "title": "Same Song (Live)", "artists": [{"name": "Artist"}], "played": "2026-07-03"},
            ]
        },
        today=date(2026, 7, 7),
    )

    ranked = rank_items(normalised["play_events"], tracks_by_id(normalised), "tracks")

    assert [(item["title"], item["play_count"]) for item in ranked] == [("Same Song", 2), ("Same Song (Live)", 1)]


def test_top_artists_merge_safe_aliases_and_count_canonical_unique_songs() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": "one-video", "title": "One (Official Video)", "artists": [{"name": "Bring Me The Horizon"}], "played": "2026-07-01"},
                {"videoId": "one-audio", "title": "One", "artists": [{"name": "BMTH"}], "played": "2026-07-02"},
                {"videoId": "two", "title": "Two", "artists": [{"name": "Bring Me The Horizon"}], "played": "2026-07-03"},
            ]
        },
        today=date(2026, 7, 7),
    )

    ranked = rank_items(normalised["play_events"], tracks_by_id(normalised), "artists")

    assert len(ranked) == 1
    assert ranked[0]["artist"] == "Bring Me The Horizon"
    assert ranked[0]["play_count"] == 3
    assert ranked[0]["unique_songs"] == 2


def test_top_artists_merge_known_bilingual_display_names() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": "one", "title": "Song One", "artists": [{"name": "Jay Chou"}], "played": "2026-07-01"},
                {"videoId": "two", "title": "Song Two", "artists": [{"name": "周杰倫 Jay Chou"}], "played": "2026-07-02"},
            ]
        },
        today=date(2026, 7, 7),
    )

    ranked = rank_items(normalised["play_events"], tracks_by_id(normalised), "artists")

    assert len(ranked) == 1
    assert ranked[0]["play_count"] == 2


def test_duration_milliseconds_are_normalised_once() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {
                    "videoId": "milliseconds",
                    "title": "Milliseconds Song",
                    "artists": [{"name": "Artist A"}],
                    "played": "2026-07-02T10:00:00+00:00",
                    "duration_ms": 240000,
                },
                {
                    "videoId": "seconds",
                    "title": "Seconds Song",
                    "artists": [{"name": "Artist B"}],
                    "played": "2026-07-02T11:00:00+00:00",
                    "duration_seconds": 240,
                },
            ]
        },
        today=date(2026, 7, 7),
    )
    durations = {track["video_id"]: track["duration_seconds"] for track in normalised["tracks"]}

    assert durations == {"milliseconds": 240, "seconds": 240}


def artist_cache_v2(artist: str, artist_id: str, url: str) -> dict[str, object]:
    normalised = " ".join(artist.lower().split())
    entry = {
        "schemaVersion": 2,
        "mediaType": "artist",
        "entityId": artist_id,
        "entityName": artist,
        "artist": artist,
        "artist_id": artist_id,
        "url": url,
        "thumbnail_url": url,
        "artist_image_source": "youtube_artist_profile",
        "thumbnails": [{"url": url, "width": 512, "height": 512}],
        "resolvedAt": "2026-07-07T00:00:00+00:00",
    }
    return {"schemaVersion": 2, "items": {f"artist:{artist_id}": entry, f"artist-name:{normalised}": entry}}


def album_cache_v1(album: str, artist: str, album_id: str, url: str) -> dict[str, object]:
    entry = {
        "schemaVersion": 1,
        "mediaType": "album",
        "entityId": album_id,
        "entityName": album,
        "album": album,
        "artist": artist,
        "album_id": album_id,
        "browse_id": album_id,
        "album_image_url": url,
        "album_art_url": url,
        "thumbnail_url": url,
        "album_image_source": "youtube_album_cover",
        "thumbnails": [{"url": url, "width": 512, "height": 512}],
        "resolvedAt": "2026-07-07T00:00:00+00:00",
    }
    alias = album_name_artist_key(album, artist)
    typed = album_id_key(album_id)
    return {"schemaVersion": 1, "items": {typed: entry}, "index": {alias: typed}}
