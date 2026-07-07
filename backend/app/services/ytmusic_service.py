from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.analysis.duration import extract_duration_seconds
from app.config import Settings


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
                    "message": f"Browser-header authentication check failed: {exc}",
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
                "message": f"Authentication check failed: {exc}",
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
