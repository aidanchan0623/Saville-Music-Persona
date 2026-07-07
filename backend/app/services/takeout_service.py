from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from io import BytesIO
from typing import Any
from urllib.parse import parse_qs, urlparse


class TakeoutParseError(ValueError):
    pass


class _WatchHistoryHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_block = False
        self._current_text: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and dict(attrs).get("class") == "content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1":
            self._in_block = True
            self._current_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._in_block:
            text = " ".join(part.strip() for part in self._current_text if part.strip())
            if text:
                self.blocks.append(text)
            self._in_block = False

    def handle_data(self, data: str) -> None:
        if self._in_block:
            self._current_text.append(data)


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
                entries.extend(normalise_takeout_items(json.loads(payload.decode("utf-8-sig"))))
            else:
                entries.extend(parse_takeout_html(payload.decode("utf-8-sig", errors="replace")))
    return dedupe_takeout_entries(entries)


def normalise_takeout_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        raise TakeoutParseError("Takeout JSON was not a list of history entries.")
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
        result.append(
            {
                "videoId": extract_video_id(str(item.get("titleUrl") or "")),
                "title": clean_takeout_title(raw_title),
                "artists": [{"name": artist} for artist in artists],
                "played": parse_takeout_time(item.get("time")),
                "titleUrl": item.get("titleUrl"),
                "source": "google_takeout",
            }
        )
    return dedupe_takeout_entries(result)


def parse_takeout_html(html: str) -> list[dict[str, Any]]:
    parser = _WatchHistoryHtmlParser()
    parser.feed(html)
    entries: list[dict[str, Any]] = []
    for block in parser.blocks:
        video_id = extract_video_id(block)
        title = clean_takeout_title(block)
        time_match = re.search(r"([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2} [AP]M [A-Z]+)", block)
        entries.append(
            {
                "videoId": video_id,
                "title": title[:240],
                "artists": [],
                "played": time_match.group(1) if time_match else None,
                "source": "google_takeout_html",
            }
        )
    return dedupe_takeout_entries(entries)


def clean_takeout_title(title: str) -> str:
    cleaned = re.sub(r"^(Watched|Listened to|Played)\s+", "", title, flags=re.I).strip()
    return cleaned or title.strip()


def extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    query_id = parse_qs(parsed.query).get("v")
    if query_id:
        return query_id[0]
    match = re.search(r"(?:youtu\.be/|/watch/|videoId=)([A-Za-z0-9_-]{6,})", url)
    return match.group(1) if match else None


def parse_takeout_time(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text


def dedupe_takeout_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str | None, str, str | None]] = set()
    result: list[dict[str, Any]] = []
    for entry in entries:
        key = (entry.get("videoId"), entry.get("title", ""), entry.get("played"))
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result
