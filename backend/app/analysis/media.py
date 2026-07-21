from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from app.analysis.thumbnails import best_thumbnail_url


ARTIST_IMAGE_CACHE_SCHEMA_VERSION = 2
ALBUM_IMAGE_CACHE_SCHEMA_VERSION = 1


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


def normalise_album_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().strip()
    text = text.replace("&", " and ")
    text = re.sub(r"[/_.\u00b7\u2022]+", " ", text)
    text = re.sub(r"[^\w\s'-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def album_id_key(album_id: Any) -> str | None:
    text = str(album_id or "").strip()
    return f"album:{text}" if text else None


def album_name_artist_key(album: Any, artist: Any) -> str | None:
    normalised_album = normalise_album_name(album)
    normalised_artist = normalise_artist_name(artist)
    if not normalised_album or not normalised_artist:
        return None
    return f"album-name:{normalised_artist}::{normalised_album}"


def empty_artist_image_cache() -> dict[str, Any]:
    return {"schemaVersion": ARTIST_IMAGE_CACHE_SCHEMA_VERSION, "items": {}}


def empty_album_image_cache() -> dict[str, Any]:
    return {"schemaVersion": ALBUM_IMAGE_CACHE_SCHEMA_VERSION, "items": {}, "index": {}}


def ensure_artist_image_cache_schema(cache: Any) -> dict[str, Any]:
    if not isinstance(cache, dict):
        return empty_artist_image_cache()
    if cache.get("schemaVersion") == ARTIST_IMAGE_CACHE_SCHEMA_VERSION and isinstance(cache.get("items"), dict):
        return cache
    cache.clear()
    cache.update(empty_artist_image_cache())
    return cache


def ensure_album_image_cache_schema(cache: Any) -> dict[str, Any]:
    if not isinstance(cache, dict):
        return empty_album_image_cache()
    if cache.get("schemaVersion") == ALBUM_IMAGE_CACHE_SCHEMA_VERSION and isinstance(cache.get("items"), dict):
        cache.setdefault("index", {})
        if not isinstance(cache["index"], dict):
            cache["index"] = {}
        return cache
    cache.clear()
    cache.update(empty_album_image_cache())
    return cache


def artist_cache_items(cache: dict[str, Any]) -> dict[str, Any]:
    ensured = ensure_artist_image_cache_schema(cache)
    return ensured.setdefault("items", {})


def album_cache_items(cache: dict[str, Any]) -> dict[str, Any]:
    ensured = ensure_album_image_cache_schema(cache)
    return ensured.setdefault("items", {})


def album_cache_index(cache: dict[str, Any]) -> dict[str, str]:
    ensured = ensure_album_image_cache_schema(cache)
    return ensured.setdefault("index", {})


def artist_cache_lookup(cache: dict[str, Any], artist: Any, artist_id: Any = None) -> dict[str, Any] | None:
    items = artist_cache_items(cache)
    for key in (artist_id_key(artist_id), artist_name_key(artist)):
        if key and isinstance(items.get(key), dict):
            value = items[key]
            if value.get("schemaVersion") == ARTIST_IMAGE_CACHE_SCHEMA_VERSION and value.get("mediaType") == "artist":
                return value
    return None


def album_cache_lookup(cache: dict[str, Any], album_id: Any = None, album: Any = None, artist: Any = None) -> dict[str, Any] | None:
    items = album_cache_items(cache)
    direct_key = album_id_key(album_id)
    if direct_key and isinstance(items.get(direct_key), dict):
        value = items[direct_key]
        if value.get("schemaVersion") == ALBUM_IMAGE_CACHE_SCHEMA_VERSION and value.get("mediaType") == "album":
            return value
    alias_key = album_name_artist_key(album, artist)
    mapped_key = album_cache_index(cache).get(alias_key) if alias_key else None
    if mapped_key and isinstance(items.get(mapped_key), dict):
        value = items[mapped_key]
        if value.get("schemaVersion") == ALBUM_IMAGE_CACHE_SCHEMA_VERSION and value.get("mediaType") == "album":
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


def album_cache_set(cache: dict[str, Any], entry: dict[str, Any], album_id: Any = None, album: Any = None, artist: Any = None) -> None:
    key = album_id_key(album_id or entry.get("entityId") or entry.get("album_id") or entry.get("browse_id"))
    if not key:
        return
    items = album_cache_items(cache)
    items[key] = entry
    alias_key = album_name_artist_key(album or entry.get("album") or entry.get("entityName"), artist or entry.get("artist"))
    if alias_key:
        album_cache_index(cache)[alias_key] = key


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
    explicit = str(item.get("album_art_url") or item.get("albumImageUrl") or item.get("album_image_url") or "").strip()
    if explicit:
        return explicit
    if item.get("mediaType") == "album":
        cached = str(item.get("thumbnail_url") or "").strip()
        if cached:
            return cached
    return best_thumbnail_url(album_thumbnail_candidates(item))


def album_image_source(item: dict[str, Any]) -> str | None:
    if item.get("album_art_source"):
        return str(item["album_art_source"])
    if item.get("album_image_source"):
        return str(item["album_image_source"])
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


def album_cache_success_entry(album: str, artist: str, payload: dict[str, Any], selected_url: str | None, album_id: Any = None, source: str = "ytmusicapi.album_lookup") -> dict[str, Any]:
    canonical_album = str(payload.get("title") or payload.get("album") or payload.get("name") or album).strip() or album
    browse_id = payload.get("browseId") or payload.get("album_id") or payload.get("id") or album_id
    resolved_at = datetime.now(timezone.utc).isoformat()
    thumbnail = best_thumbnail_url(payload.get("thumbnails") or payload.get("thumbnail") or payload.get("images") or payload.get("image")) or selected_url
    return {
        "schemaVersion": ALBUM_IMAGE_CACHE_SCHEMA_VERSION,
        "mediaType": "album",
        "entityId": browse_id,
        "entityName": canonical_album,
        "album": canonical_album,
        "artist": artist,
        "normalisedAlbum": normalise_album_name(canonical_album),
        "normalisedArtist": normalise_artist_name(artist),
        "album_id": browse_id,
        "browse_id": browse_id,
        "thumbnails": [{"url": thumbnail}] if thumbnail else [],
        "thumbnail_url": thumbnail,
        "url": thumbnail,
        "album_image_url": thumbnail,
        "album_art_url": thumbnail,
        "source": source,
        "album_image_source": "youtube_album_cover",
        "album_art_source": "youtube_album_cover",
        "resolvedAt": resolved_at,
        "fetched_at": resolved_at,
        "last_successful_update_at": resolved_at if thumbnail else None,
        "failureReason": None if thumbnail else "missing_thumbnails",
        "failure_reason": None if thumbnail else "missing_thumbnails",
        "retry_after": None if thumbnail else (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
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


def album_cache_failure(album: str, artist: str, album_id: Any, reason: str) -> dict[str, Any]:
    resolved_at = datetime.now(timezone.utc).isoformat()
    return {
        "schemaVersion": ALBUM_IMAGE_CACHE_SCHEMA_VERSION,
        "mediaType": "album",
        "entityId": album_id,
        "entityName": album,
        "album": album,
        "artist": artist,
        "normalisedAlbum": normalise_album_name(album),
        "normalisedArtist": normalise_artist_name(artist),
        "album_id": album_id,
        "browse_id": album_id,
        "thumbnails": [],
        "thumbnail_url": None,
        "url": None,
        "album_image_url": None,
        "album_art_url": None,
        "source": "ytmusicapi.album_lookup",
        "album_image_source": "youtube_album_cover",
        "album_art_source": "youtube_album_cover",
        "resolvedAt": resolved_at,
        "fetched_at": resolved_at,
        "failureReason": reason,
        "failure_reason": reason,
        "retry_after": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }
