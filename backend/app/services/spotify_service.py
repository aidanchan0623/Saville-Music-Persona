from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import Settings
from app.database.repository import JsonRepository


SPOTIFY_SCOPES = [
    "user-top-read",
    "user-read-recently-played",
    "user-library-read",
    "playlist-read-private",
    "playlist-read-collaborative",
]

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"


class SpotifyService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def configured(self) -> bool:
        return bool(self.settings.spotify_client_id and self.settings.spotify_client_secret and self.settings.spotify_redirect_uri)

    def new_state(self) -> str:
        return secrets.token_urlsafe(24)

    def login_url(self, state: str) -> str:
        if not self.configured():
            raise RuntimeError("Spotify client ID, client secret, and redirect URI are not configured.")
        params = {
            "client_id": self.settings.spotify_client_id,
            "response_type": "code",
            "redirect_uri": self.settings.spotify_redirect_uri,
            "scope": " ".join(SPOTIFY_SCOPES),
            "state": state,
        }
        return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> dict[str, Any]:
        return self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.settings.spotify_redirect_uri,
            }
        )

    def refresh_token(self, tokens: dict[str, Any]) -> dict[str, Any]:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("Spotify refresh token is missing. Reconnect Spotify.")
        refreshed = self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})
        if not refreshed.get("refresh_token"):
            refreshed["refresh_token"] = refresh_token
        return refreshed

    def access_token(self, repo: JsonRepository) -> str:
        tokens = repo.load_json("spotify_tokens")
        if not isinstance(tokens, dict) or not tokens.get("access_token"):
            raise RuntimeError("Spotify is not connected.")
        expires_at = parse_timestamp(tokens.get("expires_at"))
        if expires_at and expires_at > datetime.now(timezone.utc) + timedelta(seconds=60):
            return str(tokens["access_token"])
        refreshed = self.refresh_token(tokens)
        repo.save_json("spotify_tokens", refreshed)
        return str(refreshed["access_token"])

    def status(self, repo: JsonRepository) -> dict[str, Any]:
        tokens = repo.load_json("spotify_tokens")
        profile = repo.load_json("spotify_profile") if isinstance(tokens, dict) else None
        meta = repo.load_json("spotify_last_refresh_meta") or {}
        images = profile.get("images") if isinstance(profile, dict) else []
        image = first_image_url(images)
        return {
            "configured": self.configured(),
            "connected": isinstance(tokens, dict) and bool(tokens.get("refresh_token") or tokens.get("access_token")),
            "display_name": profile.get("display_name") if isinstance(profile, dict) else None,
            "profile_image": image,
            "spotify_user_id": profile.get("id") if isinstance(profile, dict) else None,
            "last_synced_at": meta.get("refreshed_at"),
            "message": self.status_message(tokens, profile),
        }

    def fetch_all(self, repo: JsonRepository) -> dict[str, Any]:
        token = self.access_token(repo)
        headers = {"Authorization": f"Bearer {token}"}
        with httpx.Client(timeout=30.0, headers=headers) as client:
            profile = self._get(client, "/me")
            top_artists = {
                period: self._get_paged(client, "/me/top/artists", {"time_range": period, "limit": 50}, max_items=50)
                for period in ("short_term", "medium_term", "long_term")
            }
            top_tracks = {
                period: self._get_paged(client, "/me/top/tracks", {"time_range": period, "limit": 50}, max_items=50)
                for period in ("short_term", "medium_term", "long_term")
            }
            recent_plays = self._get(client, "/me/player/recently-played", {"limit": 50}).get("items", [])
            saved_tracks = self._get_paged(client, "/me/tracks", {"limit": 50}, max_items=500)
            playlists = self._get_paged(client, "/me/playlists", {"limit": 50}, max_items=100)
            playlist_tracks: dict[str, list[dict[str, Any]]] = {}
            for playlist in playlists:
                playlist_id = playlist.get("id") if isinstance(playlist, dict) else None
                if not playlist_id:
                    continue
                try:
                    playlist_tracks[str(playlist_id)] = self._get_paged(
                        client,
                        f"/playlists/{playlist_id}/tracks",
                        {"limit": 100, "fields": "items(track(id,name,artists,album,duration_ms,popularity,external_urls,type)),next,total"},
                        max_items=200,
                    )
                except Exception:
                    playlist_tracks[str(playlist_id)] = []
            artist_details = self.artist_details(client, top_artists, top_tracks, recent_plays, saved_tracks, playlist_tracks)
        return {
            "source": "spotify",
            "profile": profile,
            "top_artists": top_artists,
            "top_tracks": top_tracks,
            "recent_plays": recent_plays,
            "saved_tracks": saved_tracks,
            "playlists": playlists,
            "playlist_tracks": playlist_tracks,
            "artist_details": artist_details,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "scopes": SPOTIFY_SCOPES,
        }

    def artist_details(
        self,
        client: httpx.Client,
        top_artists: dict[str, list[dict[str, Any]]],
        top_tracks: dict[str, list[dict[str, Any]]],
        recent_plays: list[dict[str, Any]],
        saved_tracks: list[dict[str, Any]],
        playlist_tracks: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        artists: dict[str, dict[str, Any]] = {}
        for items in top_artists.values():
            for artist in items:
                if isinstance(artist, dict) and artist.get("id"):
                    artists[str(artist["id"])] = artist
        for track in iter_spotify_tracks(top_tracks, recent_plays, saved_tracks, playlist_tracks):
            for artist in track.get("artists") or []:
                if isinstance(artist, dict) and artist.get("id") and artist["id"] not in artists:
                    artists[str(artist["id"])] = {"id": artist["id"], "name": artist.get("name")}
        missing = [artist_id for artist_id, value in artists.items() if not value.get("genres") and not value.get("images")]
        for chunk in chunks(missing, 50):
            payload = self._get(client, "/artists", {"ids": ",".join(chunk)})
            for artist in payload.get("artists") or []:
                if isinstance(artist, dict) and artist.get("id"):
                    artists[str(artist["id"])] = artist
        return artists

    def _token_request(self, data: dict[str, str]) -> dict[str, Any]:
        if not self.configured():
            raise RuntimeError("Spotify client ID, client secret, and redirect URI are not configured.")
        response = httpx.post(
            SPOTIFY_TOKEN_URL,
            data=data,
            auth=(self.settings.spotify_client_id, self.settings.spotify_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20.0,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Spotify token request failed: {response.status_code} {response.text[:180]}")
        payload = response.json()
        payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in") or 3600))).isoformat()
        return payload

    def _get(self, client: httpx.Client, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = client.get(f"{SPOTIFY_API_URL}{path}", params=params)
        if response.status_code >= 400:
            raise RuntimeError(f"Spotify API request failed for {path}: {response.status_code} {response.text[:180]}")
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _get_paged(self, client: httpx.Client, path: str, params: dict[str, Any] | None = None, max_items: int = 500) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = None
        current_params = dict(params or {})
        while len(items) < max_items:
            if next_url:
                response = client.get(next_url)
                if response.status_code >= 400:
                    raise RuntimeError(f"Spotify API request failed for {path}: {response.status_code} {response.text[:180]}")
                payload = response.json()
            else:
                payload = self._get(client, path, current_params)
            page_items = payload.get("items") or []
            items.extend(item for item in page_items if isinstance(item, dict))
            next_url = payload.get("next")
            if not next_url:
                break
        return items[:max_items]

    def status_message(self, tokens: Any, profile: Any) -> str:
        if not self.configured():
            return "Spotify credentials are not configured in backend/private/.env."
        if not isinstance(tokens, dict):
            return "Spotify is optional and not connected."
        if isinstance(profile, dict) and profile.get("display_name"):
            return f"Connected as {profile['display_name']}."
        return "Spotify token is stored locally. Refresh Spotify data to load profile details."


def first_image_url(images: Any) -> str | None:
    if not isinstance(images, list):
        return None
    candidates = [item for item in images if isinstance(item, dict) and item.get("url")]
    return str(candidates[0]["url"]) if candidates else None


def parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def iter_spotify_tracks(
    top_tracks: dict[str, list[dict[str, Any]]],
    recent_plays: list[dict[str, Any]],
    saved_tracks: list[dict[str, Any]],
    playlist_tracks: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    for items in top_tracks.values():
        tracks.extend(item for item in items if isinstance(item, dict))
    for item in recent_plays:
        track = item.get("track") if isinstance(item, dict) else None
        if isinstance(track, dict):
            tracks.append(track)
    for item in saved_tracks:
        track = item.get("track") if isinstance(item, dict) else None
        if isinstance(track, dict):
            tracks.append(track)
    for items in playlist_tracks.values():
        for item in items:
            track = item.get("track") if isinstance(item, dict) else None
            if isinstance(track, dict):
                tracks.append(track)
    return tracks
