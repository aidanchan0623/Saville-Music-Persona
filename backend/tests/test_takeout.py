from __future__ import annotations

import json

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.services.takeout_service import normalise_takeout_items, parse_takeout_upload


def test_takeout_json_import_extracts_history_entries() -> None:
    payload = [
        {
            "header": "YouTube Music",
            "title": "Watched Never Meant",
            "titleUrl": "https://www.youtube.com/watch?v=abc123XYZ",
            "subtitles": [{"name": "American Football"}],
            "time": "2025-05-04T12:13:14.000Z",
            "products": ["YouTube"],
        }
    ]
    entries = normalise_takeout_items(payload)
    assert entries[0]["videoId"] == "abc123XYZ"
    assert entries[0]["title"] == "Never Meant"
    assert entries[0]["artists"][0]["name"] == "American Football"
    assert entries[0]["played"] == "2025-05-04"


def test_takeout_history_drives_repeat_counts_when_present() -> None:
    raw = {
        "history": [{"videoId": "recent", "title": "Recent", "artists": [{"name": "Artist"}], "played": "Today"}],
        "takeout_history": [
            {"videoId": "old", "title": "Old Song", "artists": [{"name": "Artist"}], "played": "2025-01-01"},
            {"videoId": "old", "title": "Old Song", "artists": [{"name": "Artist"}], "played": "2025-01-02"},
        ],
    }
    analysis = build_analysis(normalise_collection(raw))
    assert analysis["top_tracks"][0]["title"] == "Old Song"
    assert analysis["top_tracks"][0]["play_count"] == 2


def test_parse_takeout_upload_accepts_json_bytes() -> None:
    payload = json.dumps([{"header": "YouTube", "title": "Watched Song", "time": "2024-01-01T00:00:00Z"}]).encode()
    assert parse_takeout_upload("watch-history.json", payload)[0]["title"] == "Song"

