from __future__ import annotations

from datetime import date, timedelta
from typing import Any


SPOTIFY_LIMITATION_NOTE = (
    "Spotify profile is based on top items, saved music, playlists and recent sync data. "
    "Full historical play counts are not available immediately, so monthly history improves after repeated syncs."
)


def spotify_raw_to_collection(raw: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    anchor = today or date.today()
    artist_details = raw.get("artist_details") if isinstance(raw.get("artist_details"), dict) else {}
    top_tracks = raw.get("top_tracks") if isinstance(raw.get("top_tracks"), dict) else {}
    top_artists = raw.get("top_artists") if isinstance(raw.get("top_artists"), dict) else {}
    recent_plays = raw.get("recent_plays") if isinstance(raw.get("recent_plays"), list) else []
    saved_tracks = raw.get("saved_tracks") if isinstance(raw.get("saved_tracks"), list) else []
    playlists = raw.get("playlists") if isinstance(raw.get("playlists"), list) else []
    raw_playlist_tracks = raw.get("playlist_tracks") if isinstance(raw.get("playlist_tracks"), dict) else {}

    history: list[dict[str, Any]] = []
    library_songs: dict[str, dict[str, Any]] = {}
    liked_songs: list[dict[str, Any]] = []
    playlist_tracks: dict[str, list[dict[str, Any]]] = {}
    library_artists: dict[str, dict[str, Any]] = {}
    platform_top_tracks: list[dict[str, Any]] = []

    for period, tracks in top_tracks.items():
        if not isinstance(tracks, list):
            continue
        for rank, track in enumerate(tracks, 1):
            adapted = adapt_track(track, artist_details, source_type="spotify_top_track", time_range=str(period), rank=rank)
            if not adapted:
                continue
            library_songs.setdefault(adapted["source_track_id"], adapted)
            platform_top_tracks.append({**adapted, "event_source": "spotify_top_track_signal"})

    for play in recent_plays:
        track = play.get("track") if isinstance(play, dict) else None
        adapted = adapt_track(track, artist_details, source_type="spotify_recent_play")
        if not adapted:
            continue
        played_at = play.get("played_at")
        library_songs.setdefault(adapted["source_track_id"], adapted)
        history.append({**adapted, "played": played_at, "event_source": "spotify_recent_play", "spotify_signal_label": "Spotify recent play"})

    for saved in saved_tracks:
        track = saved.get("track") if isinstance(saved, dict) else saved
        adapted = adapt_track(track, artist_details, source_type="spotify_saved_track")
        if adapted:
            library_songs.setdefault(adapted["source_track_id"], adapted)
            liked_songs.append(adapted)

    for playlist in playlists:
        if not isinstance(playlist, dict) or not playlist.get("id"):
            continue
        playlist_id = str(playlist["id"])
        adapted_tracks: list[dict[str, Any]] = []
        for entry in raw_playlist_tracks.get(playlist_id) or []:
            track = entry.get("track") if isinstance(entry, dict) else None
            adapted = adapt_track(track, artist_details, source_type="spotify_playlist_track")
            if not adapted:
                continue
            library_songs.setdefault(adapted["source_track_id"], adapted)
            adapted_tracks.append(adapted)
        playlist_tracks[playlist_id] = adapted_tracks

    for period, artists in top_artists.items():
        if not isinstance(artists, list):
            continue
        for rank, artist in enumerate(artists, 1):
            if isinstance(artist, dict) and artist.get("id"):
                merged = {**artist, **(artist_details.get(str(artist["id"])) or {})}
                library_artists[str(artist["id"])] = adapt_artist(merged, time_range=str(period), rank=rank)
    for artist in artist_details.values():
        if isinstance(artist, dict) and artist.get("id"):
            library_artists.setdefault(str(artist["id"]), adapt_artist(artist))

    return {
        "source": "spotify",
        "profile": raw.get("profile") or {},
        "history": history,
        "liked_songs": {"tracks": liked_songs},
        "library_songs": list(library_songs.values()),
        "library_artists": list(library_artists.values()),
        "library_playlists": [
            {
                "playlistId": playlist.get("id"),
                "title": playlist.get("name"),
                "description": playlist.get("description"),
                "trackCount": (playlist.get("tracks") or {}).get("total") if isinstance(playlist.get("tracks"), dict) else None,
                "thumbnails": playlist.get("images") or [],
                "source": "spotify",
            }
            for playlist in playlists
            if isinstance(playlist, dict)
        ],
        "playlist_tracks": playlist_tracks,
        "platform_top_tracks": platform_top_tracks,
        "spotify_top_items": {"tracks": top_tracks, "artists": top_artists},
        "warnings": [SPOTIFY_LIMITATION_NOTE],
    }


def adapt_track(
    track: Any,
    artist_details: dict[str, Any],
    source_type: str,
    time_range: str | None = None,
    rank: int | None = None,
) -> dict[str, Any] | None:
    if not isinstance(track, dict) or track.get("type") not in (None, "track") or not track.get("id"):
        return None
    album = track.get("album") if isinstance(track.get("album"), dict) else {}
    artists = []
    for artist in track.get("artists") or []:
        if not isinstance(artist, dict):
            continue
        detail = artist_details.get(str(artist.get("id"))) if artist.get("id") else {}
        artists.append(
            {
                "name": artist.get("name"),
                "id": spotify_id("artist", artist.get("id")),
                "genres": detail.get("genres") if isinstance(detail, dict) else [],
            }
        )
    spotify_track_id = str(track["id"])
    return {
        "source": "spotify",
        "source_track_id": spotify_id("track", spotify_track_id),
        "id": spotify_track_id,
        "title": track.get("name") or "Unavailable track",
        "artists": artists,
        "album": {
            "name": album.get("name"),
            "id": spotify_id("album", album.get("id")) if album.get("id") else None,
            "year": album.get("release_date"),
        },
        "releaseDate": album.get("release_date"),
        "duration_seconds": round(int(track.get("duration_ms") or 0) / 1000) if track.get("duration_ms") else None,
        "thumbnails": album.get("images") or [],
        "popularity": track.get("popularity"),
        "external_url": ((track.get("external_urls") or {}).get("spotify") if isinstance(track.get("external_urls"), dict) else None),
        "source_types": [source_type],
        "spotify_time_range": time_range,
        "spotify_rank": rank,
        "spotify_signal_label": spotify_signal_label(source_type, time_range),
    }


def adapt_artist(artist: dict[str, Any], time_range: str | None = None, rank: int | None = None) -> dict[str, Any]:
    followers = artist.get("followers") if isinstance(artist.get("followers"), dict) else {}
    return {
        "source": "spotify",
        "name": artist.get("name"),
        "artist": artist.get("name"),
        "id": spotify_id("artist", artist.get("id")) if artist.get("id") else None,
        "browseId": spotify_id("artist", artist.get("id")) if artist.get("id") else None,
        "subscribers": followers.get("total"),
        "followers": followers.get("total"),
        "genres": artist.get("genres") or [],
        "popularity": artist.get("popularity"),
        "thumbnails": artist.get("images") or [],
        "spotify_time_range": time_range,
        "spotify_rank": rank,
    }


def spotify_id(kind: str, value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("spotify:"):
        return text
    return f"spotify:{kind}:{text}"


def spotify_signal_label(source_type: str, time_range: str | None = None) -> str:
    if source_type == "spotify_recent_play":
        return "Spotify recent play"
    if source_type == "spotify_saved_track":
        return "Spotify saved track"
    if source_type == "spotify_playlist_track":
        return "Spotify playlist track"
    if time_range == "short_term":
        return "Spotify short-term top track"
    if time_range == "medium_term":
        return "Spotify medium-term top track"
    if time_range == "long_term":
        return "Spotify long-term top track"
    return "Spotify top track"


def signal_date(time_range: str, rank: int, anchor: date) -> str:
    if time_range == "short_term":
        day_count = max(anchor.day, 1)
        return (anchor - timedelta(days=(rank - 1) % day_count)).isoformat()
    if time_range == "medium_term":
        return (anchor - timedelta(days=30 + rank)).isoformat()
    return (anchor - timedelta(days=120 + rank)).isoformat()
