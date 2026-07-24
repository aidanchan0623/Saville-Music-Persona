from __future__ import annotations

from datetime import date

from app.analysis.normalizer import normalise_collection
from app.analysis.period_profile import build_period_profile


def test_golden_reconciliation_and_cross_page_facts() -> None:
    raw = {
        "takeout_import_diagnostics": {"raw_events": 7, "duplicates": 1, "invalid_timestamps": 1},
        "history": [
            {"videoId": "song-a", "title": "Song A", "artists": [{"name": "Artist A"}, {"name": "Artist B"}], "played": "2026-06-30T16:30:00+00:00", "duration_seconds": 180, "genre": "indie"},
            {"videoId": "song-a", "title": "Song A", "artists": [{"name": "Artist A"}, {"name": "Artist B"}], "played": "2026-07-01T01:00:00+00:00", "duration_seconds": 180, "genre": "indie"},
            {"videoId": "song-b", "title": "Song B", "artists": [{"name": "Artist C"}], "played": "2026-07-01T02:00:00+00:00"},
            {"videoId": "podcast", "title": "Interview Podcast", "artists": [{"name": "Host"}], "played": "2026-07-01T03:00:00+00:00", "duration_seconds": 3600},
        ],
        "liked_songs": {"tracks": [{"videoId": "liked", "title": "Liked", "artists": [{"name": "Artist A"}]}]},
    }
    profile = build_period_profile(normalise_collection(raw), "month", "2026-07", "Asia/Kuala_Lumpur", today=date(2026, 7, 2))
    assert profile["reconciliation"]["raw_rows"] == 7
    assert profile["reconciliation"]["exact_duplicates_removed"] == 1
    assert profile["figures"]["accepted_play_count"] == 3
    assert profile["figures"]["detected_minutes"] == 6.0
    assert profile["top_artists"][0]["artist"] == "Artist A"
    assert profile["top_artists"][0]["play_count"] == 1.0
    assert round(sum(item["value"] for item in profile["genre_shares"]["items"]), 1) == 100.0
