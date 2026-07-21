from __future__ import annotations

import json
import logging
import re
import shutil
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
import unicodedata

from app.analysis.duration import extract_duration_seconds
from app.analysis.normalizer import UNKNOWN_ARTIST, extract_artist_ids, extract_artist_names, extract_tracks
from app.analysis.thumbnails import best_thumbnail
from app.config import Settings


logger = logging.getLogger(__name__)


class YTMusicService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def auth_status(self) -> dict[str, Any]:
        auth_file_exists = self.settings.ytmusic_auth_file.exists()
        browser_file_exists = self.settings.ytmusic_browser_auth_file.exists()
        oauth_configured = bool(self.settings.ytmusic_client_id and self.settings.ytmusic_client_secret)
        if browser_file_exists:
            try:
                yt = self.client(prefer_browser=True)
                info = yt.get_account_info()
                name = None
                if isinstance(info, dict):
                    name = info.get("name") or info.get("accountName")
                return {
                    "connected": True,
                    "auth_file_exists": True,
                    "auth_file_path": str(self.settings.ytmusic_browser_auth_file),
                    "oauth_client_configured": oauth_configured,
                    "account_name": name,
                    "message": "Authenticated YouTube Music access is working through manual browser-header auth.",
                }
            except Exception as exc:  # noqa: BLE001
                return {
                    "connected": False,
                    "auth_file_exists": True,
                    "auth_file_path": str(self.settings.ytmusic_browser_auth_file),
                    "oauth_client_configured": oauth_configured,
                    "account_name": None,
                    "message": f"Browser-header authentication check failed: {friendly_auth_error(exc, is_browser=True)}",
                }
        if not auth_file_exists:
            return {
                "connected": False,
                "auth_file_exists": False,
                "auth_file_path": str(self.settings.ytmusic_auth_file),
                "oauth_client_configured": oauth_configured,
                "account_name": None,
                "message": "No oauth.json file found. Use the Connect YouTube Music guide to create it locally.",
            }
        if not oauth_configured:
            return {
                "connected": False,
                "auth_file_exists": True,
                "auth_file_path": str(self.settings.ytmusic_auth_file),
                "oauth_client_configured": False,
                "account_name": None,
                "message": "oauth.json exists, but YTMUSIC_OAUTH_CLIENT_ID and YTMUSIC_OAUTH_CLIENT_SECRET are not configured.",
            }
        try:
            yt = self.client()
            info = yt.get_account_info()
            name = None
            if isinstance(info, dict):
                name = info.get("name") or info.get("accountName")
            return {
                "connected": True,
                "auth_file_exists": True,
                "auth_file_path": str(self.settings.ytmusic_auth_file),
                "oauth_client_configured": True,
                "account_name": name,
                "message": "Authenticated YouTube Music access is working.",
            }
        except Exception as exc:  # noqa: BLE001 - expose friendly failure only
            return {
                "connected": False,
                "auth_file_exists": True,
                "auth_file_path": str(self.settings.ytmusic_auth_file),
                "oauth_client_configured": True,
                "account_name": None,
                "message": f"Authentication check failed: {friendly_auth_error(exc)}",
            }

    def setup_instructions(self) -> dict[str, Any]:
        return {
            "preferred_method": "ytmusicapi OAuth",
            "auth_file_path": str(self.settings.ytmusic_auth_file),
            "private_directory": str(self.settings.private_dir),
            "steps": [
                "Install backend requirements.",
                "Create a Google Cloud OAuth client ID for TVs and Limited Input devices.",
                "Set YTMUSIC_OAUTH_CLIENT_ID and YTMUSIC_OAUTH_CLIENT_SECRET locally.",
                "Run ytmusicapi oauth from backend/private and complete the device login.",
                "Keep oauth.json in backend/private only.",
            ],
            "warning": "Do not commit oauth.json, browser headers, cookies, .env files, or raw listening exports.",
        }

    def client(self, prefer_browser: bool = True) -> Any:
        try:
            from ytmusicapi import OAuthCredentials, YTMusic
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("ytmusicapi is not installed. Run scripts/setup_windows.ps1 first.") from exc
        if prefer_browser and self.settings.ytmusic_browser_auth_file.exists():
            return YTMusic(str(self.settings.ytmusic_browser_auth_file))
        if not self.settings.ytmusic_auth_file.exists():
            raise RuntimeError(f"Missing auth file: {self.settings.ytmusic_auth_file}")
        if not self.settings.ytmusic_client_id or not self.settings.ytmusic_client_secret:
            raise RuntimeError("Missing YTMUSIC_OAUTH_CLIENT_ID or YTMUSIC_OAUTH_CLIENT_SECRET.")
        credentials = OAuthCredentials(
            client_id=self.settings.ytmusic_client_id,
            client_secret=self.settings.ytmusic_client_secret,
        )
        return YTMusic(str(self.settings.ytmusic_auth_file), oauth_credentials=credentials)

    def public_client(self) -> Any:
        try:
            from ytmusicapi import YTMusic
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("ytmusicapi is not installed. Run scripts/setup_windows.ps1 first.") from exc
        return YTMusic()

    def fetch_library(self) -> dict[str, Any]:
        yt = self.client()
        warnings: list[str] = []

        def safe_call(label: str, fn: Callable[[], Any], default: Any) -> Any:
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{label} failed: {exc}")
                return default

        history = safe_call("history", lambda: yt.get_history(), [])
        liked_songs = safe_call("liked songs", lambda: yt.get_liked_songs(limit=1000), {"tracks": []})
        library_songs = safe_call("library songs", lambda: yt.get_library_songs(limit=1000, order="recently_added"), [])
        library_artists = safe_call("library artists", lambda: yt.get_library_artists(limit=1000), [])
        library_albums = safe_call("library albums", lambda: yt.get_library_albums(limit=1000, order="recently_added"), [])
        library_playlists = safe_call("library playlists", lambda: yt.get_library_playlists(limit=None), [])
        playlist_tracks: dict[str, Any] = {}
        for playlist in library_playlists or []:
            playlist_id = playlist.get("playlistId") if isinstance(playlist, dict) else None
            if not playlist_id:
                continue
            result = safe_call(f"playlist {playlist_id}", lambda playlist_id=playlist_id: yt.get_playlist(playlist_id, limit=None), {"tracks": []})
            playlist_tracks[playlist_id] = result.get("tracks", []) if isinstance(result, dict) else []
        return {
            "source": "ytmusicapi",
            "history": history,
            "liked_songs": liked_songs,
            "library_songs": library_songs,
            "library_artists": library_artists,
            "library_albums": library_albums,
            "library_playlists": library_playlists,
            "playlist_tracks": playlist_tracks,
            "warnings": warnings,
        }

    def save_raw_snapshot(self, raw_dir: Path, raw: dict[str, Any]) -> None:
        raw_dir.mkdir(parents=True, exist_ok=True)
        path = raw_dir / "latest_raw_collection.json"
        path.write_text(json.dumps(raw, ensure_ascii=True, indent=2, default=str), encoding="utf-8")

    def enrich_artist_image_cache(self, raw: dict[str, Any], artist_cache: dict[str, Any], limit: int = 25, preferred_artists: list[str] | None = None) -> dict[str, int]:
        if limit <= 0:
            return {"seeded": 0, "attempted": 0, "added": 0, "failed": 0}
        seeded = seed_artist_cache_from_library(raw, artist_cache)
        artist_targets = top_artist_targets(raw, preferred_artists=preferred_artists)
        if not artist_targets:
            raw["artist_image_cache"] = artist_cache
            return {"seeded": seeded, "attempted": 0, "added": 0, "failed": 0}

        try:
            yt = self.client()
        except Exception:
            yt = self.public_client()
        attempted = 0
        added = 0
        failed = 0
        for artist, artist_id in artist_targets:
            cached = artist_cache.get(artist)
            if artist_cache_has_result(cached):
                continue
            if attempted >= limit:
                break
            attempted += 1
            try:
                payload = None
                matched_browse_id = artist_id
                if artist_id:
                    try:
                        payload = yt.get_artist(str(artist_id))
                    except Exception:
                        payload = None
                if not artist_payload_has_thumbnail(payload):
                    search_match = first_artist_search_result(yt, artist)
                    matched_browse_id = browse_id_from_payload(search_match) or matched_browse_id
                    if matched_browse_id:
                        try:
                            payload = yt.get_artist(str(matched_browse_id))
                        except Exception:
                            artist_cache[artist] = artist_cache_failure_entry(artist, matched_browse_id, "artist_page_failed")
                            failed += 1
                            continue
                    else:
                        payload = None
                entry = artist_cache_entry(artist, payload, artist_id=matched_browse_id)
                if entry.get("thumbnails"):
                    added += 1
                    logger.info('[artist-image] Resolved "%s" using browseId %s', artist, entry.get("browse_id") or "unknown")
                else:
                    failed += 1
                    logger.info('[artist-image] No official thumbnail found for "%s"', artist)
                artist_cache[artist] = entry
            except Exception:
                artist_cache[artist] = artist_cache_failure_entry(artist, artist_id, "upstream_exception")
                failed += 1
                logger.info('[artist-image] No official thumbnail found for "%s"', artist)
        raw["artist_image_cache"] = artist_cache
        return {"seeded": seeded, "attempted": attempted, "added": added, "failed": failed}

    def enrich_duration_cache(self, normalised: dict[str, Any], duration_cache: dict[str, Any], limit: int = 150) -> dict[str, Any]:
        if limit <= 0:
            return {"attempted": 0, "added": 0, "failed": 0}
        yt = self.client()
        attempted = 0
        added = 0
        failed = 0
        for track in normalised.get("tracks") or []:
            if attempted >= limit:
                break
            if track.get("duration_seconds"):
                continue
            video_id = track.get("video_id")
            if not video_id or video_id in duration_cache:
                continue
            attempted += 1
            try:
                payload = yt.get_song(str(video_id))
                seconds = duration_from_ytmusic_payload(payload)
            except Exception:
                seconds = None
            if seconds:
                duration_cache[str(video_id)] = {
                    "duration_seconds": seconds,
                    "duration_source": "ytmusicapi.get_song",
                    "duration_confidence": "high",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                added += 1
            else:
                duration_cache[str(video_id)] = {
                    "duration_seconds": None,
                    "duration_source": "ytmusicapi.get_song",
                    "duration_confidence": "missing",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                failed += 1
        return {"attempted": attempted, "added": added, "failed": failed}

    def search_candidates(self, analysis: dict[str, Any], limit_per_seed: int = 8) -> list[dict[str, Any]]:
        yt = self.client()
        candidates: list[dict[str, Any]] = []
        top_artists = analysis.get("top_artists", [])[:8]
        top_tracks = analysis.get("top_tracks", [])[:5]
        for artist in top_artists:
            name = artist.get("artist")
            if not name:
                continue
            try:
                results = yt.search(str(name), filter="songs", limit=limit_per_seed)
                for item in results:
                    if isinstance(item, dict):
                        item["recommendation_source"] = "same or related artist search"
                        item["seed_artist"] = name
                        candidates.append(item)
            except Exception:
                continue
        for track in top_tracks:
            video_id = track.get("video_id")
            if not video_id:
                continue
            try:
                watch = yt.get_watch_playlist(videoId=video_id, limit=limit_per_seed)
                for item in watch.get("tracks", []) if isinstance(watch, dict) else []:
                    if isinstance(item, dict):
                        item["recommendation_source"] = "watch playlist / similar track"
                        item["seed_track"] = track.get("title")
                        candidates.append(item)
            except Exception:
                continue
        return candidates

    def create_private_playlist(self, title: str, video_ids: list[str]) -> str:
        yt = self.client()
        result = yt.create_playlist(
            title=title,
            description="Created locally by Saville Music Persona from evidence-based recommendations.",
            privacy_status="PRIVATE",
            video_ids=video_ids,
        )
        if isinstance(result, str):
            return result
        raise RuntimeError(f"YouTube Music returned an error while creating the playlist: {result}")


def executable_available(name: str) -> bool:
    return shutil.which(name) is not None


def friendly_auth_error(exc: Exception, is_browser: bool = False) -> str:
    text = str(exc)
    if "Unable to find 'header'" in text and "multiPageMenuRenderer" in text:
        return (
            "YouTube responded, but the account menu did not expose account details. "
            "Saved browser headers may be stale; imported Google Takeout data can still be used."
        )
    if "invalid argument" in text.lower():
        return "Google rejected the OAuth token or client configuration as invalid."
    if is_browser:
        return "YouTube Music rejected the saved browser headers. Copy fresh request headers from a logged-in music.youtube.com tab."
    cleaned = " ".join(text.split())
    if not cleaned:
        return exc.__class__.__name__
    return cleaned[:240]


def duration_from_ytmusic_payload(payload: Any) -> int | None:
    if not isinstance(payload, (dict, list)):
        return None
    stack: list[Any] = [payload]
    seen = 0
    while stack and seen < 1000:
        seen += 1
        item = stack.pop()
        if isinstance(item, dict):
            for key in ("duration_seconds", "durationSeconds", "lengthSeconds", "length_seconds", "duration"):
                seconds = extract_duration_seconds(item.get(key))
                if seconds:
                    return seconds
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return None


def seed_artist_cache_from_library(raw: dict[str, Any], artist_cache: dict[str, Any]) -> int:
    seeded = 0
    for artist in raw.get("library_artists") or []:
        if not isinstance(artist, dict):
            continue
        name = artist.get("artist") or artist.get("name")
        thumbnails = artist.get("thumbnails") or []
        if not name or not best_thumbnail(thumbnails):
            continue
        key = str(name).strip()
        cached = artist_cache.get(key)
        if artist_cache_has_thumbnail(cached):
            continue
        artist_cache[key] = artist_cache_entry(key, artist, artist_id=artist.get("browseId") or artist.get("id"), source="ytmusicapi.library_artists")
        seeded += 1
    return seeded


def top_artist_targets(raw: dict[str, Any], limit: int = 40, preferred_artists: list[str] | None = None) -> list[tuple[str, str | None]]:
    history = extract_tracks(raw.get("takeout_history")) or extract_tracks(raw.get("history"))
    counts: Counter[str] = Counter()
    ids: dict[str, str] = {}
    for item in history:
        names = [name for name in extract_artist_names(item) if name and name != UNKNOWN_ARTIST]
        artist_ids = extract_artist_ids(item)
        for name in names:
            counts[name] += 1
            if name in artist_ids and name not in ids:
                ids[name] = artist_ids[name]
    ordered: list[str] = []
    seen: set[str] = set()
    for artist in preferred_artists or []:
        name = str(artist or "").strip()
        key = normalise_artist_name(name)
        if key and key not in seen:
            seen.add(key)
            ordered.append(name)
    for artist, _ in counts.most_common(limit):
        key = normalise_artist_name(artist)
        if key and key not in seen:
            seen.add(key)
            ordered.append(artist)
    return [(artist, ids.get(artist)) for artist in ordered[:limit]]


def artist_cache_has_thumbnail(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return bool(value.get("thumbnail_url") or best_thumbnail(value.get("thumbnails")))


def artist_cache_has_result(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if artist_cache_has_thumbnail(value):
        return True
    retry_after = value.get("retry_after")
    if not retry_after:
        return False
    try:
        retry_at = datetime.fromisoformat(str(retry_after).replace("Z", "+00:00"))
    except ValueError:
        return True
    return retry_at > datetime.now(timezone.utc)


def artist_payload_has_thumbnail(payload: Any) -> bool:
    return isinstance(payload, dict) and bool(best_thumbnail(payload))


def first_artist_search_result(yt: Any, artist: str) -> dict[str, Any] | None:
    results = yt.search(str(artist), filter="artists", limit=5)
    if not isinstance(results, list):
        return None
    normalised = normalise_artist_name(artist)
    for item in results:
        if not isinstance(item, dict):
            continue
        candidate_names = artist_candidate_names(item)
        if any(normalise_artist_name(candidate) == normalised for candidate in candidate_names):
            return item
    return None


def artist_cache_entry(artist: str, payload: Any, artist_id: Any = None, source: str = "ytmusicapi.artist_lookup") -> dict[str, Any]:
    if not isinstance(payload, dict):
        return artist_cache_failure_entry(artist, artist_id, "no_exact_artist_match")
    selected = best_thumbnail(payload)
    canonical_name = str(payload.get("artist") or payload.get("name") or artist).strip() or artist
    browse_id = browse_id_from_payload(payload) or artist_id
    entry = {
        "artist": canonical_name,
        "canonical_artist": canonical_name,
        "normalised_name": normalise_artist_name(canonical_name),
        "artist_id": browse_id,
        "browse_id": browse_id,
        "channel_id": payload.get("channelId") or payload.get("channel_id"),
        "subscribers": payload.get("subscribers"),
        "aliases": artist_candidate_names(payload),
        "thumbnails": [selected] if selected else [],
        "thumbnail_url": selected.get("url") if selected else None,
        "thumbnail_width": selected.get("width") if selected else None,
        "thumbnail_height": selected.get("height") if selected else None,
        "source": source,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    if selected:
        entry["last_successful_update_at"] = entry["fetched_at"]
    else:
        entry["failure_reason"] = "missing_thumbnails"
        entry["retry_after"] = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    return entry


def normalise_artist_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().strip()
    text = re.sub(r"\s*-\s*topic$", "", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[/_.·•]+", " ", text)
    text = re.sub(r"[^\w\s'-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def artist_candidate_names(payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for key in ("artist", "name", "title"):
        if payload.get(key):
            names.append(str(payload[key]).strip())
    aliases = payload.get("aliases") or payload.get("alternateNames") or []
    if isinstance(aliases, str):
        names.append(aliases.strip())
    elif isinstance(aliases, list):
        for alias in aliases:
            if alias:
                names.append(str(alias).strip())
    result: list[str] = []
    seen: set[str] = set()
    for name in names:
        normalised = normalise_artist_name(name)
        if normalised and normalised not in seen:
            seen.add(normalised)
            result.append(name)
    return result


def browse_id_from_payload(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("browseId") or payload.get("artist_id") or payload.get("id")
    return str(value) if value else None


def artist_cache_failure_entry(artist: str, artist_id: Any, reason: str) -> dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    return {
        "artist": artist,
        "canonical_artist": artist,
        "normalised_name": normalise_artist_name(artist),
        "artist_id": artist_id,
        "browse_id": artist_id,
        "thumbnails": [],
        "thumbnail_url": None,
        "thumbnail_width": None,
        "thumbnail_height": None,
        "source": "ytmusicapi.artist_lookup",
        "fetched_at": fetched_at,
        "failure_reason": reason,
        "retry_after": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }
