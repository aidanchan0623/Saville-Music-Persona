from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app.analysis.normalizer import normalise_collection
from app.analysis.spotify_adapter import spotify_raw_to_collection
from app.config import Settings
from app.database.repository import JsonRepository
from app.main import app
from app.services.spotify_service import SpotifyService


def _settings(tmp_path: Path) -> Settings:
    settings = Settings()
    settings.data_dir = tmp_path
    settings.db_path = tmp_path / "test.db"
    settings.spotify_client_id = "client"
    settings.spotify_client_secret = "secret"
    settings.spotify_redirect_uri = "http://localhost:8000/api/spotify/callback"
    return settings


def test_spotify_disconnected_status_never_exposes_tokens(tmp_path: Path) -> None:
    repo = JsonRepository(tmp_path / "spotify.db")
    service = SpotifyService(_settings(tmp_path))
    status = service.status(repo)
    assert status["configured"] is True
    assert status["connected"] is False
    assert "access_token" not in status
    assert "refresh_token" not in status


def test_spotify_connected_status_returns_profile_without_tokens(tmp_path: Path) -> None:
    repo = JsonRepository(tmp_path / "spotify.db")
    repo.save_json("spotify_tokens", {"access_token": "private-access", "refresh_token": "private-refresh"})
    repo.save_json("spotify_profile", {"id": "user-1", "display_name": "Aidan", "images": [{"url": "https://img.example/me.jpg"}]})
    service = SpotifyService(_settings(tmp_path))
    status = service.status(repo)
    assert status["connected"] is True
    assert status["display_name"] == "Aidan"
    assert status["profile_image"] == "https://img.example/me.jpg"
    assert "private-access" not in str(status)
    assert "private-refresh" not in str(status)


def test_spotify_cache_keys_do_not_overwrite_youtube_data(tmp_path: Path) -> None:
    repo = JsonRepository(tmp_path / "storage.db")
    repo.save_json("normalised", {"metadata": {"source": "ytmusicapi"}, "tracks": [{"title": "YouTube"}]})
    repo.save_json("spotify_normalised", {"metadata": {"source": "spotify"}, "tracks": [{"title": "Spotify"}]})
    repo.delete_json_many(["spotify_normalised"])
    assert repo.load_json("normalised")["tracks"][0]["title"] == "YouTube"
    assert repo.load_json("spotify_normalised") is None


def test_spotify_routes_are_registered() -> None:
    client = TestClient(app)
    health = client.get("/api/spotify/health")
    assert health.status_code == 200
    assert health.json() == {"ok": True, "spotify_router": "registered"}

    login = client.get("/api/spotify/login", follow_redirects=False)
    assert login.status_code != 404


def test_spotify_track_and_artist_normalisation() -> None:
    raw = {
        "profile": {"id": "user"},
        "top_tracks": {
            "short_term": [
                {
                    "id": "track-1",
                    "name": "Signal Song",
                    "type": "track",
                    "duration_ms": 201000,
                    "popularity": 77,
                    "artists": [{"id": "artist-1", "name": "Signal Artist"}],
                    "album": {
                        "id": "album-1",
                        "name": "Signal Album",
                        "release_date": "2024-02-01",
                        "images": [{"url": "https://img.example/album.jpg"}],
                    },
                }
            ],
            "medium_term": [],
            "long_term": [],
        },
        "top_artists": {
            "short_term": [
                {
                    "id": "artist-1",
                    "name": "Signal Artist",
                    "genres": ["indie rock"],
                    "popularity": 70,
                    "followers": {"total": 12345},
                    "images": [{"url": "https://img.example/artist.jpg"}],
                }
            ],
            "medium_term": [],
            "long_term": [],
        },
        "recent_plays": [],
        "saved_tracks": [],
        "playlists": [],
        "playlist_tracks": {},
        "artist_details": {
            "artist-1": {
                "id": "artist-1",
                "name": "Signal Artist",
                "genres": ["indie rock"],
                "popularity": 70,
                "followers": {"total": 12345},
                "images": [{"url": "https://img.example/artist.jpg"}],
            }
        },
    }
    collection = spotify_raw_to_collection(raw, today=date(2026, 7, 8))
    normalised = normalise_collection(collection, today=date(2026, 7, 8))
    track = normalised["tracks"][0]
    artist = normalised["artist_metadata"]["Signal Artist"]
    assert normalised["metadata"]["source"] == "spotify"
    assert track["track_id"] == "spotify:track:track-1"
    assert track["source_track_id"] == "spotify:track:track-1"
    assert track["thumbnails"][0]["url"] == "https://img.example/album.jpg"
    assert track["spotify_signal_label"] == "Spotify short-term top track"
    assert artist["artist_id"] == "spotify:artist:artist-1"
    assert artist["thumbnails"][0]["url"] == "https://img.example/artist.jpg"
    assert artist["genres"] == ["indie rock"]
