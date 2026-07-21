from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from app.analysis.thumbnails import best_thumbnail_url


ARTIST_IMAGE_CACHE_SCHEMA_VERSION = 2


def normalise_artist_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().strip()
    text = re.sub(r"\s*-\s*topic$", "", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[/_.\u00b7\u2022]+", " ", text)
    text = re.sub(r"[^\w\s'-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def artist_id_key(artist_id: Any) -> str | None:
    text = str(artist_id or "").strip()
    return f"artist:{text}" if text else None


def artist_name_key(name: Any) -> str | None:
    normalised = normalise_artist_name(name)
    return f"artist-name:{normalised}" if normalised else None


def empty_artist_image_cache() -> dict[str, Any]:
    return {"schemaVersion": ARTIST_IMAGE_CACHE_SCHEMA_VERSION, "items": {}}


def ensure_artist_image_cache_schema(cache: Any) -> dict[str, Any]:
    if not isinstance(cache, dict):
        return empty_artist_image_cache()
    if cache.get("schemaVersion") == ARTIST_IMAGE_CACHE_SCHEMA_VERSION and isinstance(cache.get("items"), dict):
        return cache
    cache.clear()
    cache.update(empty_artist_image_cache())
    return cache


def artist_cache_items(cache: dict[str, Any]) -> dict[str, Any]:
    ensured = ensure_artist_image_cache_schema(cache)
    return ensured.setdefault("items", {})


def artist_cache_lookup(cache: dict[str, Any], artist: Any, artist_id: Any = None) -> dict[str, Any] | None:
    items = artist_cache_items(cache)
    for key in (artist_id_key(artist_id), artist_name_key(artist)):
        if key and isinstance(items.get(key), dict):
            value = items[key]
            if value.get("schemaVersion") == ARTIST_IMAGE_CACHE_SCHEMA_VERSION and value.get("mediaType") == "artist":
                return value
    return None


def artist_cache_set(cache: dict[str, Any], artist: Any, entry: dict[str, Any], artist_id: Any = None) -> None:
    items = artist_cache_items(cache)
    keys = [
        artist_id_key(artist_id or entry.get("entityId") or entry.get("artist_id") or entry.get("browse_id")),
        artist_name_key(artist or entry.get("entityName") or entry.get("artist") or entry.get("canonical_artist")),
    ]
    for key in keys:
        if key:
            items[key] = entry


def youtube_video_thumbnail(video_id: Any) -> str | None:
    if not video_id:
        return None
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def album_thumbnail_candidates(item: dict[str, Any]) -> Any:
    album = item.get("album")
    if isinstance(album, dict):
        return album.get("thumbnails") or album.get("thumbnail") or album.get("images") or album.get("image")
    return item.get("album_thumbnails") or item.get("albumImages") or item.get("album_images")


def album_image_url(item: dict[str, Any]) -> str | None:
    return (
        str(item.get("album_art_url") or item.get("albumImageUrl") or "").strip()
        or best_thumbnail_url(album_thumbnail_candidates(item))
    )


def album_image_source(item: dict[str, Any]) -> str | None:
    if item.get("album_art_source"):
        return str(item["album_art_source"])
    if album_image_url(item):
        source = str(item.get("source") or "").lower()
        return "spotify_album_image" if source == "spotify" else "youtube_album_cover"
    return None


def track_image_url(item: dict[str, Any]) -> str | None:
    explicit = str(item.get("track_image_url") or item.get("trackImageUrl") or "").strip()
    if explicit:
        return explicit
    url = best_thumbnail_url(item.get("track_thumbnails") or item.get("thumbnails"))
    if url:
        return url
    return youtube_video_thumbnail(item.get("video_id") or item.get("videoId"))


def track_image_source(item: dict[str, Any]) -> str | None:
    if item.get("track_image_source"):
        return str(item["track_image_source"])
    if track_image_url(item):
        source = str(item.get("source") or "").lower()
        return "spotify_album_image" if source == "spotify" else "youtube_track_thumbnail"
    return None


def artist_image_url(meta: dict[str, Any]) -> str | None:
    return (
        str(meta.get("artist_image_url") or meta.get("artistImageUrl") or meta.get("url") or meta.get("thumbnail_url") or "").strip()
        or best_thumbnail_url(meta.get("artist_thumbnails") or meta.get("thumbnails"))
    )


def artist_image_source(meta: dict[str, Any]) -> str | None:
    if meta.get("artist_image_source"):
        return str(meta["artist_image_source"])
    if meta.get("source"):
        source = str(meta["source"])
        if "spotify" in source:
            return "spotify_artist_profile"
        if "artist" in source or "ytmusic" in source or "youtube" in source:
            return "youtube_artist_profile"
    return "youtube_artist_profile" if artist_image_url(meta) else None


def artist_cache_success_entry(artist: str, payload: dict[str, Any], selected_url: str | None, artist_id: Any = None, source: str = "ytmusicapi.artist_lookup") -> dict[str, Any]:
    canonical_name = str(payload.get("artist") or payload.get("name") or artist).strip() or artist
    browse_id = payload.get("browseId") or payload.get("artist_id") or payload.get("id") or artist_id
    resolved_at = datetime.now(timezone.utc).isoformat()
    return {
        "schemaVersion": ARTIST_IMAGE_CACHE_SCHEMA_VERSION,
        "mediaType": "artist",
        "entityId": browse_id,
        "entityName": canonical_name,
        "artist": canonical_name,
        "canonical_artist": canonical_name,
        "normalisedName": normalise_artist_name(canonical_name),
        "normalised_name": normalise_artist_name(canonical_name),
        "artist_id": browse_id,
        "browse_id": browse_id,
        "channel_id": payload.get("channelId") or payload.get("channel_id"),
        "subscribers": payload.get("subscribers"),
        "aliases": [],
        "thumbnails": [{"url": selected_url}] if selected_url else [],
        "thumbnail_url": selected_url,
        "url": selected_url,
        "source": source,
        "artist_image_source": "spotify_artist_profile" if "spotify" in source else "youtube_artist_profile",
        "resolvedAt": resolved_at,
        "fetched_at": resolved_at,
        "last_successful_update_at": resolved_at if selected_url else None,
        "failureReason": None if selected_url else "missing_thumbnails",
        "failure_reason": None if selected_url else "missing_thumbnails",
        "retry_after": None if selected_url else (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }


def artist_cache_failure(artist: str, artist_id: Any, reason: str) -> dict[str, Any]:
    resolved_at = datetime.now(timezone.utc).isoformat()
    return {
        "schemaVersion": ARTIST_IMAGE_CACHE_SCHEMA_VERSION,
        "mediaType": "artist",
        "entityId": artist_id,
        "entityName": artist,
        "artist": artist,
        "canonical_artist": artist,
        "normalisedName": normalise_artist_name(artist),
        "normalised_name": normalise_artist_name(artist),
        "artist_id": artist_id,
        "browse_id": artist_id,
        "thumbnails": [],
        "thumbnail_url": None,
        "url": None,
        "source": "ytmusicapi.artist_lookup",
        "artist_image_source": "youtube_artist_profile",
        "resolvedAt": resolved_at,
        "fetched_at": resolved_at,
        "failureReason": reason,
        "failure_reason": reason,
        "retry_after": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }
