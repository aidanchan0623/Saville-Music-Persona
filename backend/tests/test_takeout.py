from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.services.takeout_service import (
    dedupe_takeout_entries,
    normalise_takeout_items,
    parse_takeout_file,
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


def test_generic_youtube_history_is_not_counted_as_confirmed_music() -> None:
    entries = normalise_takeout_items(
        [{
            "header": "YouTube",
            "title": "Watched a general video",
            "titleUrl": "https://www.youtube.com/watch?v=general123",
            "subtitles": [{"name": "A channel rather than a music artist"}],
            "time": "2026-07-10T08:01:02Z",
            "products": ["YouTube"],
        }]
    )
    normalised = normalise_collection({"takeout_history": entries})
    assert entries[0]["takeoutMusicEvidence"] == "unverified_youtube_history"
    assert normalised["metadata"]["play_count"] == 0
    assert normalised["excluded_play_events"][0]["music_classification"] == "unknown"


def test_youtube_music_product_counts_song_even_when_artist_metadata_is_missing() -> None:
    entries = normalise_takeout_items(
        [{
            "header": "YouTube Music",
            "title": "Watched เพลงที่ไม่มีข้อมูลศิลปิน",
            "titleUrl": "https://music.youtube.com/watch?v=thai123456",
            "time": "2026-07-10T08:01:02Z",
            "products": ["YouTube"],
        }]
    )
    normalised = normalise_collection({"takeout_history": entries})
    assert normalised["metadata"]["play_count"] == 1
    assert normalised["play_events"][0]["artist"] == "Unknown Artist"


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


@pytest.mark.parametrize(
    ("title", "channel", "expected_artist", "expected_title"),
    [
        ("周杰倫 Jay Chou【晴天 Sunny Day】Official Music Video", "周杰倫 Jay Chou", "周杰倫 Jay Chou", "晴天 Sunny Day"),
        ("아이유『밤편지』공식 뮤직비디오", "이지금 [IU Official]", "아이유", "밤편지"),
        ("米津玄師「Lemon」公式ミュージックビデオ", "Kenshi Yonezu", "米津玄師", "Lemon"),
    ],
)
def test_takeout_html_parses_multilingual_official_music_titles(
    title: str,
    channel: str,
    expected_artist: str,
    expected_title: str,
) -> None:
    html = f"""
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched <a href="https://www.youtube.com/watch?v=multi12345">{title}</a><br>
      <a href="https://www.youtube.com/channel/example">{channel}</a><br>
      Jul 10, 2026, 10:32:18 PM GMT+08:00
    </div>
    """
    entry = parse_takeout_html(html)[0]
    assert entry["artists"][0]["name"] == expected_artist
    assert entry["title"] == expected_title
    assert entry["takeoutMusicEvidence"] == "explicit_music_metadata"


def test_music_youtube_source_is_language_neutral_positive_evidence() -> None:
    html = """
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched <a href="https://music.youtube.com/watch?v=arabic1234">نسم علينا الهوى</a><br>
      <a href="https://www.youtube.com/channel/example">Fairuz</a><br>
      Jul 10, 2026, 10:32:18 PM GMT+08:00
    </div>
    """
    entry = parse_takeout_html(html)[0]
    assert entry["artists"][0]["name"] == "Fairuz"
    assert entry["takeoutMusicEvidence"] == "youtube_music_product"
    assert normalise_collection({"takeout_history": [entry]})["metadata"]["play_count"] == 1


def test_unverified_html_row_is_retained_but_not_ranked() -> None:
    html = """
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched <a href="https://www.youtube.com/watch?v=generic1234">A general documentary</a><br>
      <a href="https://www.youtube.com/channel/example">General Channel</a><br>
      Jul 10, 2026, 10:32:18 PM GMT+08:00
    </div>
    """
    entries = parse_takeout_html(html)
    assert len(entries) == 1
    assert entries[0]["artists"] == []
    normalised = normalise_collection({"takeout_history": entries})
    assert len(normalised["listening_events"]) == 1
    assert normalised["metadata"]["play_count"] == 0


def test_strongest_video_metadata_is_applied_to_every_play_regardless_of_order() -> None:
    weak = {
        "videoId": "samevideo1",
        "title": "晴天 Sunny Day",
        "artists": [],
        "played": "2026-07-11T10:00:00+00:00",
        "source": "google_takeout",
        "sourceFormat": "html",
        "takeoutMusicEvidence": "unverified_youtube_history",
    }
    strong = {
        **weak,
        "title": "晴天 Sunny Day",
        "artists": [{"name": "周杰倫 Jay Chou"}],
        "played": "2026-07-10T10:00:00+00:00",
        "takeoutMusicEvidence": "youtube_music_product",
    }
    normalised = normalise_collection({"takeout_history": [weak, strong]})
    assert normalised["metadata"]["play_count"] == 2
    assert len(normalised["excluded_play_events"]) == 0
    assert {event["artist"] for event in normalised["play_events"]} == {"周杰倫 Jay Chou"}


def test_takeout_html_explicit_ad_row_is_discarded() -> None:
    html = """
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched <a href="https://www.youtube.com/watch?v=advert12345">Brand - Summer Song</a><br>
      Watched at 10:32 PM<br>
      Jul 10, 2026, 10:32:18 PM GMT+08:00
    </div>
    """
    assert parse_takeout_html(html) == []


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
    assert entries[0]["parserSchemaVersion"] == 5


def test_html_parser_accepts_narrow_nonbreaking_timestamp_whitespace() -> None:
    entries = parse_takeout_html(
        """<div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
        Watched <a href="https://www.youtube.com/watch?v=whitespace1">Whitespace Song</a><br>
        <a href="https://www.youtube.com/channel/example">Whitespace Artist - Topic</a><br>
        Jul 10, 2026, 10:32:18 PM GMT+08:00</div>"""
    )
    assert entries[0]["videoId"] == "whitespace1"
    assert entries[0]["played"] == "2026-07-10T14:32:18+00:00"


def test_html_file_audit_reconciles_duplicates_exclusions_and_repeated_plays(tmp_path: Path) -> None:
    song = """
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched <a href="https://music.youtube.com/watch?v=audit1234">Audit Song</a><br>
      <a href="https://www.youtube.com/channel/example">Audit Artist - Topic</a><br>
      {timestamp}<br>
    </div>
    """
    ad = """
    <div class="content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1">
      Watched at Jul 11, 2026, 10:32:18 PM GMT+08:00<br>From Google Ads
    </div>
    """
    path = tmp_path / "watch-history.html"
    first = song.format(timestamp="Jul 10, 2026, 10:32:18 PM GMT+08:00")
    later = song.format(timestamp="Jul 11, 2026, 10:32:18 PM GMT+08:00")
    path.write_text(first + first + later + ad, encoding="utf-8")

    result = parse_takeout_file(path)

    assert result.raw_event_count == 4
    assert len(result.entries) == 2
    assert result.diagnostics["parsed_records"] == 3
    assert result.diagnostics["duplicates"] == 1
    assert result.diagnostics["intentionally_excluded_records"] == 1
    assert result.diagnostics["silent_loss"] == 0
    assert result.entries[0]["rawTitle"] == "Audit Song"
    assert result.entries[0]["rawChannel"] == "Audit Artist - Topic"


def test_zip_reconciles_the_same_json_event_across_multiple_history_files(tmp_path: Path) -> None:
    item = {
        "header": "YouTube Music",
        "title": "Watched Repeated Export Song",
        "titleUrl": "https://www.youtube.com/watch?v=repeat1234",
        "subtitles": [{"name": "Export Artist"}],
        "time": "2026-07-10T08:01:02Z",
        "products": ["YouTube"],
    }
    archive_path = tmp_path / "takeout.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("Takeout/YouTube and YouTube Music/history/watch-history.json", json.dumps([item]))
        archive.writestr("Takeout/YouTube and YouTube Music/history/watch history backup.json", json.dumps([item]))

    result = parse_takeout_file(archive_path)

    assert result.raw_event_count == 2
    assert result.diagnostics["parsed_records"] == 2
    assert len(result.entries) == 1
    assert result.diagnostics["duplicates"] == 1
    assert result.diagnostics["silent_loss"] == 0
