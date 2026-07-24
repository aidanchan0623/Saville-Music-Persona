from __future__ import annotations

import json
from pathlib import Path

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.services.takeout_service import (
    dedupe_takeout_entries,
    normalise_takeout_items,
    parse_takeout_html,
    parse_takeout_upload,
)


FIXTURES = Path(__file__).parent / "fixtures"


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
    assert entries[0]["played"] == "2025-05-04T12:13:14+00:00"
    assert entries[0]["timestampInvalid"] is False


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
    assert entries[0]["played"] == "2026-07-06T13:20:14+00:00"


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


def test_three_same_day_plays_remain_three_plays() -> None:
    payload = json.loads((FIXTURES / "takeout_three_same_day.json").read_text(encoding="utf-8"))
    entries = normalise_takeout_items(payload)

    assert len(entries) == 3
    assert len({entry["played"] for entry in entries}) == 3
    normalised = normalise_collection({"takeout_history": entries})
    assert normalised["metadata"]["play_count"] == 3
    assert [event["played_at"] for event in normalised["play_events"]] == [
        "2026-07-10T08:01:02+00:00",
        "2026-07-10T14:32:18+00:00",
        "2026-07-10T23:59:58+00:00",
    ]


def test_exact_duplicate_event_is_deduplicated() -> None:
    item = {
        "header": "YouTube Music",
        "title": "Watched Duplicate",
        "titleUrl": "https://www.youtube.com/watch?v=duplicate1",
        "time": "2026-07-10T14:32:18Z",
        "products": ["YouTube"],
    }
    assert len(normalise_takeout_items([item, dict(item)])) == 1


def test_source_event_id_is_the_strongest_identity() -> None:
    first = {
        "header": "YouTube Music",
        "id": "event-42",
        "title": "Watched First Metadata",
        "titleUrl": "https://www.youtube.com/watch?v=sourceid01",
        "time": "2026-07-10T14:32:18Z",
        "products": ["YouTube"],
    }
    second = {**first, "title": "Watched Updated Metadata", "time": "2026-07-11T14:32:18Z"}
    assert len(normalise_takeout_items([first, second])) == 1


def test_same_title_with_different_video_ids_is_not_deduplicated() -> None:
    items = [
        {
            "header": "YouTube Music",
            "title": "Watched Shared Title",
            "titleUrl": f"https://www.youtube.com/watch?v={video_id}",
            "time": "2026-07-10T14:32:18Z",
            "products": ["YouTube"],
        }
        for video_id in ("videoAAA1", "videoBBB2")
    ]
    assert len(normalise_takeout_items(items)) == 2


def test_missing_video_id_uses_title_and_exact_timestamp() -> None:
    base = {
        "header": "YouTube Music",
        "title": "Watched Missing Video ID",
        "time": "2026-07-10T14:32:18Z",
        "products": ["YouTube"],
    }
    later = {**base, "time": "2026-07-10T14:35:18Z"}
    assert len(normalise_takeout_items([base, dict(base), later])) == 2


def test_timezone_is_converted_to_utc() -> None:
    payload = [
        {
            "header": "YouTube Music",
            "title": "Watched Timezone Song",
            "time": "2026-07-10T22:32:18+08:00",
            "products": ["YouTube"],
        }
    ]
    assert normalise_takeout_items(payload)[0]["played"] == "2026-07-10T14:32:18+00:00"


def test_html_and_json_equivalents_use_one_canonical_timestamp() -> None:
    json_entries = normalise_takeout_items(
        [
            {
                "header": "YouTube Music",
                "title": "Watched Equivalent Song",
                "titleUrl": "https://www.youtube.com/watch?v=equiv1234",
                "subtitles": [{"name": "Equivalent Artist"}],
                "time": "2026-07-10T22:32:18+08:00",
                "products": ["YouTube"],
            }
        ]
    )
    html_entries = parse_takeout_html(
        """
        <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
          Watched <a href="https://www.youtube.com/watch?v=equiv1234">Equivalent Song</a><br>
          <a href="https://www.youtube.com/channel/example">Equivalent Artist - Topic</a><br>
          Jul 10, 2026, 10:32:18 PM GMT+08:00<br>
        </div>
        """
    )
    assert json_entries[0]["played"] == html_entries[0]["played"] == "2026-07-10T14:32:18+00:00"
    assert len(dedupe_takeout_entries([*json_entries, *html_entries])) == 1


def test_malformed_timestamp_is_preserved_and_not_unsafely_deduplicated() -> None:
    item = {
        "header": "YouTube Music",
        "title": "Watched Unknown Time",
        "titleUrl": "https://www.youtube.com/watch?v=badtime123",
        "time": "not-a-real-timestamp",
        "products": ["YouTube"],
    }
    entries = normalise_takeout_items([item, dict(item)])
    assert len(entries) == 2
    assert entries[0]["played"] == "not-a-real-timestamp"
    assert entries[0]["rawTimestamp"] == "not-a-real-timestamp"
    assert entries[0]["timestampInvalid"] is True


def test_html_parser_tolerates_class_order_and_keeps_timestamp_out_of_link_text() -> None:
    entries = parse_takeout_html(
        """
        <div class="mdl-typography--body-1 content-cell extra mdl-cell--6-col mdl-cell">
          Watched <a href="https://www.youtube.com/watch?v=struct123">Structured Song</a>
          <a href="https://www.youtube.com/channel/example">Structured Artist - Topic</a>
          Jul 10, 2026, 10:32:18 PM GMT+08:00
        </div>
        """
    )
    assert entries[0]["title"] == "Structured Song"
    assert entries[0]["artists"][0]["name"] == "Structured Artist"
    assert entries[0]["played"] == "2026-07-10T14:32:18+00:00"
    assert entries[0]["parserSchemaVersion"] == 3
