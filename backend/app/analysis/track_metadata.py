from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from app.analysis.normalizer import parse_release_year


TRACK_METADATA_CACHE_SCHEMA_VERSION = 1

PRESENTATION_SUFFIX = re.compile(
    r"(?:"
    r"\s*[\(\[\u3010]\s*(?:(?:official\s+)?(?:music\s+)?video|official\s+audio|audio|lyrics?|lyric\s+video|visuali[sz]er|mv|m/v)\s*[\)\]\u3011]"
    r"|\s*[-|\uFF5C]\s*(?:(?:official\s+)?(?:music\s+)?video|official\s+audio|audio|lyrics?|lyric\s+video|visuali[sz]er|mv|m/v)"
    r")\s*$",
    re.IGNORECASE,
)
ARTIST_PREFIX_SEPARATOR = re.compile(r"^\s*[-\u2010-\u2015\u2212:：|｜]\s*")
VERSION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("live", r"\blive\b|live at|live from"),
    ("remix", r"\bremix\b|\bmix\)"),
    ("remaster", r"\bremaster(?:ed)?\b"),
    ("slowed", r"\bslowed\b|slowed\s*\+\s*reverb"),
    ("sped_up", r"\bsped[ -]?up\b|\bspeed up\b"),
    ("instrumental", r"\binstrumental\b|\bkaraoke\b"),
    ("acoustic", r"\bacoustic\b|\bunplugged\b"),
    ("radio_edit", r"\bradio edit\b"),
    ("cover", r"\bcover\b"),
)


def normalise_identity_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    return " ".join(text.split())


def display_recording_title(value: Any, artist: Any = None) -> str:
    """Remove presentation-only text and an exact leading artist credit.

    The raw title remains on the source event. Version-defining text such as
    live, remix, remaster, slowed, acoustic, and instrumental is retained.
    """

    title = unicodedata.normalize("NFKC", str(value or "")).strip()
    title = PRESENTATION_SUFFIX.sub("", title).strip(" -|｜") or title
    artist_text = unicodedata.normalize("NFKC", str(artist or "")).strip()
    if artist_text:
        prefix = title[: len(artist_text)]
        remainder = title[len(artist_text) :]
        if normalise_identity_text(prefix) == normalise_identity_text(artist_text) and ARTIST_PREFIX_SEPARATOR.match(remainder):
            stripped = ARTIST_PREFIX_SEPARATOR.sub("", remainder, count=1).strip()
            if stripped:
                title = stripped
    return title


def version_signature(value: Any) -> tuple[str, ...]:
    text = normalise_identity_text(value)
    return tuple(name for name, pattern in VERSION_PATTERNS if re.search(pattern, text, re.I))


def metadata_alias_key(title: Any, artist: Any) -> str:
    cleaned = display_recording_title(title, artist)
    title_key = re.sub(r"[^\w\s']+", " ", normalise_identity_text(cleaned), flags=re.UNICODE)
    title_key = " ".join(title_key.split())
    artist_key = re.sub(r"[^\w\s']+", " ", normalise_identity_text(artist), flags=re.UNICODE)
    artist_key = " ".join(artist_key.split())
    signature = "|".join(version_signature(cleaned))
    return f"{title_key}::{artist_key}::{signature}" if title_key and artist_key else ""


def ensure_track_metadata_cache(value: Any) -> dict[str, Any]:
    if isinstance(value, dict) and value.get("schemaVersion") == TRACK_METADATA_CACHE_SCHEMA_VERSION:
        value.setdefault("items", {})
        value.setdefault("aliases", {})
        value.setdefault("failures", {})
        return value
    if isinstance(value, dict):
        value.clear()
        value.update({"schemaVersion": TRACK_METADATA_CACHE_SCHEMA_VERSION, "items": {}, "aliases": {}, "failures": {}})
        return value
    return {"schemaVersion": TRACK_METADATA_CACHE_SCHEMA_VERSION, "items": {}, "aliases": {}, "failures": {}}


def cache_track_metadata(cache: dict[str, Any], entry: dict[str, Any], *, video_id: Any = None) -> None:
    prepared = ensure_track_metadata_cache(cache)
    item = dict(entry)
    item.setdefault("fetchedAt", datetime.now(timezone.utc).isoformat())
    stable_video_id = str(video_id or item.get("video_id") or "").strip()
    if stable_video_id:
        prepared["items"][stable_video_id] = item
        prepared["failures"].pop(stable_video_id, None)
    alias = metadata_alias_key(item.get("title"), item.get("primary_artist"))
    if alias:
        existing = prepared["aliases"].get(alias)
        if not isinstance(existing, dict) or float(item.get("match_confidence") or 0) >= float(existing.get("match_confidence") or 0):
            prepared["aliases"][alias] = item


def track_metadata_lookup(cache: dict[str, Any], track: dict[str, Any]) -> dict[str, Any] | None:
    prepared = ensure_track_metadata_cache(cache)
    video_id = str(track.get("video_id") or "").strip()
    exact = prepared["items"].get(video_id) if video_id else None
    if isinstance(exact, dict):
        return exact
    alias = metadata_alias_key(track.get("title"), track.get("primary_artist"))
    candidate = prepared["aliases"].get(alias) if alias else None
    if not isinstance(candidate, dict):
        return None
    if tuple(candidate.get("version_signature") or ()) != version_signature(display_recording_title(track.get("title"), track.get("primary_artist"))):
        return None
    return candidate


def apply_track_metadata_cache(normalised: dict[str, Any], cache: dict[str, Any] | None) -> int:
    prepared = ensure_track_metadata_cache(cache)
    applied = 0
    by_track: dict[str, dict[str, Any]] = {}
    for track in normalised.get("tracks") or []:
        if not isinstance(track, dict):
            continue
        by_track[str(track.get("track_id") or "")] = track
        metadata = track_metadata_lookup(prepared, track)
        if not metadata:
            continue
        changed = False
        for field in ("album", "album_id", "album_art_url", "album_art_source", "original_release_year", "edition_release_year", "album_release_year"):
            value = metadata.get(field)
            if value not in (None, "", []) and track.get(field) in (None, "", []):
                track[field] = value
                changed = True
        canonical_title = str(metadata.get("title") or "").strip()
        if canonical_title and float(metadata.get("identity_confidence") or metadata.get("match_confidence") or 0) >= 0.85:
            current = str(track.get("title") or "")
            if display_recording_title(current, track.get("primary_artist")) != canonical_title:
                track.setdefault("source_title", current)
            if current != canonical_title:
                track["title"] = canonical_title
                changed = True
        artists = [str(value).strip() for value in metadata.get("artists") or [] if str(value).strip()]
        if artists and (track.get("primary_artist") in (None, "", "Unknown Artist") or float(metadata.get("identity_confidence") or 0) >= 0.95):
            track["artists"] = artists
            track["primary_artist"] = artists[0]
            changed = True
        year = (
            parse_release_year(metadata.get("original_release_year"))
            or parse_release_year(metadata.get("album_release_year"))
            or parse_release_year(metadata.get("edition_release_year"))
        )
        if year and not track.get("release_year"):
            track["release_year"] = year
            changed = True
        if year:
            track["release_year_source"] = metadata.get("source")
            track["release_year_confidence"] = metadata.get("release_year_confidence") or "medium"
            track["release_year_match_method"] = metadata.get("match_method")
        if changed:
            applied += 1

    for event in [*(normalised.get("play_events") or []), *(normalised.get("excluded_play_events") or []), *(normalised.get("listening_events") or [])]:
        if not isinstance(event, dict):
            continue
        track = by_track.get(str(event.get("track_id") or ""))
        if not track:
            continue
        event["title"] = track.get("title")
        event["artist"] = track.get("primary_artist")
        event["primary_artist"] = track.get("primary_artist")
        event["artists"] = list(track.get("artists") or [])
        event["album"] = track.get("album")
        event["release_year"] = track.get("release_year")
    return applied
