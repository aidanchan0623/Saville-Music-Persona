from __future__ import annotations

import json
import re
import zipfile
import csv
from datetime import datetime, timezone
from html.parser import HTMLParser
from io import BytesIO, StringIO
from typing import Any
from urllib.parse import parse_qs, urlparse


class TakeoutParseError(ValueError):
    pass


TAKEOUT_PARSER_SCHEMA_VERSION = 2
TAKEOUT_SOURCE = "google_takeout"
SOURCE_EVENT_ID_KEYS = ("sourceEventId", "eventId", "event_id", "activityId", "activity_id", "id")


class _WatchHistoryHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_block = False
        self._current_href: str | None = None
        self._current_link_text: list[str] = []
        self._current_text: list[str] = []
        self._current_links: list[dict[str, str]] = []
        self.blocks: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag == "div" and attr_map.get("class") == "content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1":
            self._in_block = True
            self._current_text = []
            self._current_links = []
        elif self._in_block and tag == "a":
            self._current_href = attr_map.get("href") or ""
            self._current_link_text = []

    def handle_endtag(self, tag: str) -> None:
        if self._in_block and tag == "a":
            text = " ".join(part.strip() for part in self._current_link_text if part.strip())
            self._current_links.append({"text": text, "href": self._current_href or ""})
            self._current_href = None
            self._current_link_text = []
        if tag == "div" and self._in_block:
            text = " ".join(part.strip() for part in self._current_text if part.strip())
            if text:
                self.blocks.append({"text": text, "links": self._current_links})
            self._in_block = False

    def handle_data(self, data: str) -> None:
        if self._in_block:
            self._current_text.append(data)
            if self._current_href is not None:
                self._current_link_text.append(data)


def parse_takeout_upload(filename: str, content: bytes) -> list[dict[str, Any]]:
    lower = filename.lower()
    if lower.endswith(".zip"):
        return parse_takeout_zip(content)
    if lower.endswith(".json"):
        return normalise_takeout_items(json.loads(content.decode("utf-8-sig")))
    if lower.endswith(".html") or lower.endswith(".htm"):
        return parse_takeout_html(content.decode("utf-8-sig", errors="replace"))
    raise TakeoutParseError("Unsupported file type. Upload a Google Takeout watch-history JSON, HTML, or ZIP file.")


def parse_takeout_zip(content: bytes) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        library_lookup = parse_takeout_music_library(archive)
        history_names = [
            name
            for name in archive.namelist()
            if re.search(r"(watch-history|watch history|historial).*\.(json|html?)$", name, flags=re.I)
            and "youtube" in name.lower()
        ]
        if not history_names:
            raise TakeoutParseError("No YouTube watch-history JSON or HTML file was found inside the ZIP.")
        for name in history_names:
            payload = archive.read(name)
            if name.lower().endswith(".json"):
                entries.extend(normalise_takeout_items(json.loads(payload.decode("utf-8-sig")), library_lookup))
            else:
                entries.extend(parse_takeout_html(payload.decode("utf-8-sig", errors="replace"), library_lookup))
    return dedupe_takeout_entries(entries)


def parse_takeout_music_library(archive: zipfile.ZipFile) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    names = [
        name
        for name in archive.namelist()
        if name.lower().endswith("music library songs.csv") and "youtube" in name.lower()
    ]
    for name in names:
        text = archive.read(name).decode("utf-8-sig", errors="replace")
        for row in csv.DictReader(StringIO(text)):
            video_id = clean_video_id(row.get("Video ID"))
            if not video_id:
                continue
            artists = [
                row.get(f"Artist Name {index}", "").strip()
                for index in range(1, 6)
                if row.get(f"Artist Name {index}", "").strip()
            ]
            lookup[video_id] = {
                "videoId": video_id,
                "title": (row.get("Song Title") or "").strip(),
                "album": (row.get("Album Title") or "").strip() or None,
                "artists": [{"name": artist} for artist in artists],
            }
    return lookup


def normalise_takeout_items(items: Any, library_lookup: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise TakeoutParseError("Takeout JSON was not a list of history entries.")
    library_lookup = library_lookup or {}
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        header = str(item.get("header") or "")
        products = " ".join(str(product) for product in item.get("products", []) if product)
        if "youtube" not in f"{header} {products}".lower():
            continue
        raw_title = str(item.get("title") or "").strip()
        if not raw_title or raw_title.lower().startswith("visited "):
            continue
        subtitles = item.get("subtitles")
        artists: list[str] = []
        if isinstance(subtitles, list):
            for subtitle in subtitles:
                if isinstance(subtitle, dict) and subtitle.get("name"):
                    artists.append(str(subtitle["name"]).strip())
        video_id = extract_video_id(str(item.get("titleUrl") or ""))
        library_item = library_lookup.get(video_id or "")
        played, timestamp_invalid, raw_timestamp = normalise_takeout_timestamp(item.get("time"))
        source_event_id = extract_source_event_id(item)
        result.append(
            {
                "videoId": video_id,
                "title": library_item.get("title") or clean_takeout_title(raw_title) if library_item else clean_takeout_title(raw_title),
                "artists": library_item.get("artists") or [{"name": artist} for artist in artists] if library_item else [{"name": artist} for artist in artists],
                "album": library_item.get("album") if library_item else None,
                "played": played,
                "titleUrl": item.get("titleUrl"),
                "source": TAKEOUT_SOURCE,
                "sourceFormat": "json",
                "sourceEventId": source_event_id,
                "timestampInvalid": timestamp_invalid,
                **({"rawTimestamp": raw_timestamp} if timestamp_invalid else {}),
            }
        )
    return dedupe_takeout_entries(result)


def parse_takeout_html(html: str, library_lookup: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    library_lookup = library_lookup or {}
    parser = _WatchHistoryHtmlParser()
    parser.feed(html)
    entries: list[dict[str, Any]] = []
    for block in parser.blocks:
        entry = normalise_takeout_html_block(block, library_lookup)
        if entry:
            entries.append(entry)
    return dedupe_takeout_entries(entries)


def clean_takeout_title(title: str) -> str:
    cleaned = re.sub(r"^(Watched|Listened to|Played)\s+", "", title, flags=re.I).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or title.strip()


def clean_channel_artist(channel: str) -> str:
    artist = re.sub(r"\s+-\s+Topic$", "", channel.strip(), flags=re.I)
    artist = re.sub(r"(Official)?VEVO$", "", artist, flags=re.I).strip()
    return artist or channel.strip()


def normalise_takeout_html_block(block: dict[str, Any], library_lookup: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    text = str(block.get("text") or "")
    links = [link for link in block.get("links", []) if isinstance(link, dict)]
    if "Viewed Ads" in text or "YouTube Homepage" in text:
        return None
    if not links:
        return normalise_legacy_html_text(text)
    title_link = links[0]
    title = clean_takeout_title(str(title_link.get("text") or ""))
    href = str(title_link.get("href") or "")
    video_id = extract_video_id(href)
    channel = str(links[1].get("text") or "").strip() if len(links) > 1 else ""
    library_item = library_lookup.get(video_id or "")
    raw_played = extract_takeout_html_date_raw(text)
    played, timestamp_invalid, raw_timestamp = normalise_takeout_timestamp(raw_played)
    artist_names: list[str] = []
    album = None
    if library_item:
        title = library_item.get("title") or title
        artist_names = [artist["name"] for artist in library_item.get("artists", []) if artist.get("name")]
        album = library_item.get("album")
    if not artist_names and channel.lower().endswith(" - topic"):
        artist_names = [clean_channel_artist(channel)]
    if not artist_names and " - " in title:
        possible_artist, possible_title = title.split(" - ", 1)
        if possible_artist.strip() and possible_title.strip():
            artist_names = [possible_artist.strip()]
            title = clean_official_video_title(possible_title)
    if not artist_names and "vevo" in channel.lower():
        artist_names = [clean_channel_artist(channel)]
    if not artist_names:
        return None
    return {
        "videoId": video_id,
        "title": title[:240],
        "artists": [{"name": artist} for artist in artist_names],
        "album": album,
        "played": played,
        "titleUrl": href,
        "source": TAKEOUT_SOURCE,
        "sourceFormat": "html",
        "sourceEventId": None,
        "timestampInvalid": timestamp_invalid,
        **({"rawTimestamp": raw_timestamp} if timestamp_invalid else {}),
    }


def normalise_legacy_html_text(text: str) -> dict[str, Any] | None:
    cleaned = strip_takeout_html_date(text)
    if not cleaned or "Watched at " in cleaned or "Viewed Ads" in cleaned:
        return None
    video_id = extract_video_id(cleaned)
    if cleaned.startswith("http"):
        return None
    title = cleaned
    artists: list[str] = []
    if cleaned.lower().endswith(" - topic"):
        before_topic = cleaned[:-8].strip()
        parts = before_topic.rsplit(" ", 1)
        if len(parts) == 2:
            title, artist = parts
            artists = [artist]
    elif " - " in cleaned:
        artist, title = cleaned.split(" - ", 1)
        artists = [artist.strip()]
        title = clean_official_video_title(title)
    if not artists or not title.strip():
        return None
    raw_played = extract_takeout_html_date_raw(text)
    played, timestamp_invalid, raw_timestamp = normalise_takeout_timestamp(raw_played)
    return {
        "videoId": video_id,
        "title": title.strip()[:240],
        "artists": [{"name": artist} for artist in artists],
        "played": played,
        "source": TAKEOUT_SOURCE,
        "sourceFormat": "html_legacy",
        "sourceEventId": None,
        "timestampInvalid": timestamp_invalid,
        **({"rawTimestamp": raw_timestamp} if timestamp_invalid else {}),
    }


def clean_official_video_title(title: str) -> str:
    cleaned = re.sub(r"\s*\((?:Official|Music|Lyric|Audio|Visualizer)[^)]+\)\s*", " ", title, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    return cleaned or title.strip()


def extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    query_id = parse_qs(parsed.query).get("v")
    if query_id:
        return clean_video_id(query_id[0])
    match = re.search(r"(?:youtu\.be/|[?&]v=|/watch/|videoId=)([A-Za-z0-9_-]{6,20})", url)
    return clean_video_id(match.group(1)) if match else None


def clean_video_id(value: Any) -> str | None:
    if not value:
        return None
    match = re.match(r"([A-Za-z0-9_-]{6,20})", str(value).strip())
    return match.group(1) if match else None


def normalise_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u202f", " ").replace("\xa0", " ")).strip()


def extract_takeout_html_date(value: str) -> str | None:
    raw = extract_takeout_html_date_raw(value)
    return parse_takeout_time(raw)


def extract_takeout_html_date_raw(value: str) -> str | None:
    text = normalise_spaces(value)
    match = re.search(r"([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2} [AP]M GMT[+-]\d{2}:\d{2})", text)
    if match:
        return match.group(1)
    return None


def strip_takeout_html_date(value: str) -> str:
    text = normalise_spaces(value)
    return re.sub(r"\s+[A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2} [AP]M GMT[+-]\d{2}:\d{2}.*$", "", text).strip()


def parse_takeout_time(value: Any) -> str | None:
    played, _, _ = normalise_takeout_timestamp(value)
    return played


def normalise_takeout_timestamp(value: Any) -> tuple[str | None, bool, str | None]:
    if value is None:
        return None, True, None
    text = normalise_spaces(str(value))
    if not text:
        return None, True, text
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(re.sub(r"Z$", "+00:00", text, flags=re.I))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%b %d, %Y, %I:%M:%S %p GMT%z")
        except ValueError:
            return text, True, text
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return text, True, text
    return parsed.astimezone(timezone.utc).isoformat(), False, None


def extract_source_event_id(item: dict[str, Any]) -> str | None:
    for key in SOURCE_EVENT_ID_KEYS:
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def dedupe_takeout_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, ...]] = set()
    result: list[dict[str, Any]] = []
    for entry in entries:
        source = str(entry.get("source") or TAKEOUT_SOURCE)
        source_event_id = entry.get("sourceEventId")
        if source_event_id:
            key = ("source_event_id", source, str(source_event_id))
        elif entry.get("timestampInvalid") or not entry.get("played"):
            # A malformed timestamp has no safe occurrence identity. Keep it instead of
            # silently merging potentially unrelated plays.
            result.append(entry)
            continue
        elif entry.get("videoId"):
            key = ("video_timestamp", source, str(entry["videoId"]), str(entry["played"]))
        else:
            title = normalise_spaces(str(entry.get("title") or "")).casefold()
            key = ("title_timestamp", source, title, str(entry["played"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result
