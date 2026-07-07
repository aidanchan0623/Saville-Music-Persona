from __future__ import annotations

import json

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.services.takeout_service import normalise_takeout_items, parse_takeout_html, parse_takeout_upload


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


def test_takeout_html_uses_topic_channel_as_artist() -> None:
    html = """
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched&nbsp;<a href="https://www.youtube.com/watch?v=v_uncMEJkBc">Welcome to the Black Parade</a><br>
      <a href="https://www.youtube.com/channel/abc">My Chemical Romance - Topic</a><br>
      Jul 6, 2026, 9:20:14 PM GMT+08:00<br>
    </div>
    """
    entries = parse_takeout_html(html)
    assert entries[0]["title"] == "Welcome to the Black Parade"
    assert entries[0]["artists"][0]["name"] == "My Chemical Romance"
    assert entries[0]["videoId"] == "v_uncMEJkBc"
    assert entries[0]["played"] == "2026-07-06"


def test_takeout_html_splits_artist_dash_title_music_video() -> None:
    html = """
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched&nbsp;<a href="https://www.youtube.com/watch?v=abc123XYZ99">Avoure - Aura</a><br>
      <a href="https://www.youtube.com/channel/abc">This Never Happened</a><br>
      Jul 6, 2026, 10:09:50 PM GMT+08:00<br>
    </div>
    """
    entries = parse_takeout_html(html)
    assert entries[0]["title"] == "Aura"
    assert entries[0]["artists"][0]["name"] == "Avoure"
