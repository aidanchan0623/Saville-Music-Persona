from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from app.analysis.duration import annotate_normalised_durations


UNKNOWN_ARTIST = "Unknown Artist"


GENRE_KEYWORDS: dict[str, set[str]] = {
    "indie / alternative": {"indie", "alternative", "alt ", "bedroom", "lo-fi", "lofi", "emo"},
    "pop": {"pop", "dance pop", "synth pop", "city pop"},
    "electronic": {"electronic", "edm", "house", "techno", "ambient", "synth", "club"},
    "r&b / soul": {"r&b", "rnb", "soul", "funk"},
    "rock": {"rock", "punk", "guitar", "garage"},
    "hip-hop": {"hip hop", "hip-hop", "rap", "trap"},
    "jazz / classical": {"jazz", "classical", "piano", "orchestra"},
    "folk / acoustic": {"folk", "acoustic", "country", "singer-songwriter"},
}


MOOD_KEYWORDS: dict[str, set[str]] = {
    "introspective": {"night", "midnight", "late", "alone", "letter", "archive", "static", "receipt"},
    "high-energy": {"rush", "lift", "party", "club", "drive", "fire", "afterparty"},
    "romantic": {"heart", "velvet", "love", "phonecall", "summer"},
    "nostalgic": {"old", "retro", "polaroid", "apartment", "archive", "basement"},
    "late-night": {"night", "midnight", "moon", "dark", "late"},
    "comfort-listening": {"repeat", "comfort", "therapy", "soft", "blue"},
    "indie-leaning": {"indie", "bedroom", "basement", "coastline"},
    "melancholic": {"rain", "blue", "static", "echo", "borrowed"},
    "party-oriented": {"party", "club", "afterparty", "rush"},
}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    if math.isnan(value) or math.isinf(value):
        return low
    return max(low, min(high, value))


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def stable_key(title: str, primary_artist: str) -> str:
    base = f"{title.lower().strip()}::{primary_artist.lower().strip()}"
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]
    return f"text:{digest}"


def parse_release_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if 1800 <= value <= 2100 else None
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return None
    year = int(match.group(0))
    return year if 1800 <= year <= 2100 else None


def parse_duration_seconds(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    parts = value.split(":")
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def parse_played_date(value: Any, today: date | None = None) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    anchor = today or date.today()
    low = text.lower()
    if low in {"today", "just now"}:
        return anchor
    if low == "yesterday":
        return anchor - timedelta(days=1)
    if low == "this week":
        return anchor - timedelta(days=anchor.weekday())
    last_periods = {
        "last week": timedelta(days=7),
        "last month": timedelta(days=30),
        "last year": timedelta(days=365),
    }
    if low in last_periods:
        return anchor - last_periods[low]
    rel = re.search(r"(\d+)\s+(day|week|month|year)s?\s+ago", low)
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2)
        if unit == "day":
            return anchor - timedelta(days=amount)
        if unit == "week":
            return anchor - timedelta(weeks=amount)
        if unit == "month":
            return anchor - timedelta(days=amount * 30)
        if unit == "year":
            return anchor - timedelta(days=amount * 365)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def extract_artist_names(item: dict[str, Any]) -> list[str]:
    artists = item.get("artists") or item.get("artist")
    names: list[str] = []
    if isinstance(artists, list):
        for artist in artists:
            if isinstance(artist, dict):
                name = artist.get("name") or artist.get("artist")
            else:
                name = str(artist)
            if name:
                names.append(str(name).strip())
    elif isinstance(artists, dict):
        name = artists.get("name") or artists.get("artist")
        if name:
            names.append(str(name).strip())
    elif isinstance(artists, str):
        names.extend([part.strip() for part in re.split(r",|&| feat\. | ft\. ", artists) if part.strip()])
    return names or [UNKNOWN_ARTIST]


def extract_artist_ids(item: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    artists = item.get("artists")
    if isinstance(artists, list):
        for artist in artists:
            if isinstance(artist, dict):
                name = artist.get("name") or artist.get("artist")
                artist_id = artist.get("id") or artist.get("browseId")
                if name and artist_id:
                    result[str(name).strip()] = str(artist_id)
    return result


def extract_album(item: dict[str, Any]) -> tuple[str | None, str | None]:
    album = item.get("album")
    if isinstance(album, dict):
        return album.get("name") or album.get("title"), album.get("id") or album.get("browseId")
    if isinstance(album, str):
        return album, None
    return item.get("albumName"), item.get("albumId")


def extract_tracks(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, dict):
        tracks = value.get("tracks") or value.get("items") or value.get("contents")
        if isinstance(tracks, list):
            return [track for track in tracks if isinstance(track, dict)]
        return []
    if isinstance(value, list):
        return [track for track in value if isinstance(track, dict)]
    return []


def infer_keywords(item: dict[str, Any], extra_text: str = "") -> tuple[list[str], list[str]]:
    text_parts: list[str] = [extra_text]
    for field in ("title", "category", "genre", "description", "playlistTitle"):
        if item.get(field):
            text_parts.append(str(item[field]))
    album, _ = extract_album(item)
    if album:
        text_parts.append(album)
    for artist in extract_artist_names(item):
        text_parts.append(artist)
    text = " ".join(text_parts).lower()
    genres: list[str] = []
    moods: list[str] = []
    for cluster, words in GENRE_KEYWORDS.items():
        if any(word in text for word in words):
            genres.append(cluster)
    for mood, words in MOOD_KEYWORDS.items():
        if any(word in text for word in words):
            moods.append(mood)
    return genres, moods


def normalise_track_item(item: dict[str, Any], source_type: str, playlist_id: str | None = None, playlist_title: str = "") -> dict[str, Any]:
    title = str(item.get("title") or item.get("name") or "Unavailable track").strip()
    artists = extract_artist_names(item)
    primary_artist = artists[0]
    source = str(item.get("source") or "").strip().lower()
    source_track_id = item.get("source_track_id")
    if source == "spotify":
        spotify_id = str(source_track_id or item.get("id") or "").strip()
        source_track_id = spotify_id if spotify_id.startswith("spotify:") else f"spotify:track:{spotify_id}" if spotify_id else None
        video_id = None
        track_id = source_track_id or stable_key(title, primary_artist)
    else:
        video_id = item.get("videoId") or item.get("video_id") or item.get("id")
        track_id = f"video:{video_id}" if video_id else stable_key(title, primary_artist)
    album, album_id = extract_album(item)
    year = (
        parse_release_year(item.get("release_year"))
        or parse_release_year(item.get("year"))
        or parse_release_year(item.get("releaseDate"))
        or parse_release_year((item.get("album") or {}).get("year") if isinstance(item.get("album"), dict) else None)
    )
    duration = item.get("duration_seconds") or parse_duration_seconds(item.get("duration"))
    genres, moods = infer_keywords(item, playlist_title)
    incoming_source_types = [str(value) for value in item.get("source_types") or [] if value]
    source_types = [source_type]
    for incoming in incoming_source_types:
        if incoming not in source_types:
            source_types.append(incoming)
    return {
        "track_id": track_id,
        "video_id": str(video_id) if video_id else None,
        "source": source or "youtube",
        "source_track_id": source_track_id,
        "title": title,
        "artists": artists,
        "artist_ids": extract_artist_ids(item),
        "primary_artist": primary_artist,
        "album": album,
        "album_id": album_id,
        "release_year": year,
        "duration_seconds": duration,
        "thumbnails": item.get("thumbnails") or [],
        "source_types": source_types,
        "playlist_ids": [playlist_id] if playlist_id else [],
        "playlist_titles": [playlist_title] if playlist_title else [],
        "liked": source_type == "liked",
        "library_saved": source_type == "library",
        "play_count_in_period": 0,
        "last_played": None,
        "first_played_in_period": None,
        "history_coverage_status": "not_in_history",
        "genre_clusters": genres,
        "mood_signals": moods,
        "genre_confidence": 0.65 if genres else 0.0,
        "popularity": item.get("popularity"),
        "spotify_time_range": item.get("spotify_time_range"),
        "spotify_rank": item.get("spotify_rank"),
        "spotify_signal_label": item.get("spotify_signal_label"),
    }


def merge_track(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    for source in incoming["source_types"]:
        if source not in existing["source_types"]:
            existing["source_types"].append(source)
    for playlist_id in incoming["playlist_ids"]:
        if playlist_id and playlist_id not in existing["playlist_ids"]:
            existing["playlist_ids"].append(playlist_id)
    for playlist_title in incoming.get("playlist_titles", []):
        if playlist_title and playlist_title not in existing["playlist_titles"]:
            existing["playlist_titles"].append(playlist_title)
    existing["liked"] = existing["liked"] or incoming["liked"]
    existing["library_saved"] = existing["library_saved"] or incoming["library_saved"]
    for field in ("album", "album_id", "release_year", "duration_seconds", "video_id", "source_track_id", "popularity", "spotify_time_range", "spotify_rank", "spotify_signal_label"):
        if existing.get(field) in (None, "", []):
            existing[field] = incoming.get(field)
    if not existing.get("thumbnails") and incoming.get("thumbnails"):
        existing["thumbnails"] = incoming["thumbnails"]
    for genre in incoming.get("genre_clusters", []):
        if genre not in existing["genre_clusters"]:
            existing["genre_clusters"].append(genre)
    for mood in incoming.get("mood_signals", []):
        if mood not in existing["mood_signals"]:
            existing["mood_signals"].append(mood)
    existing["genre_confidence"] = max(existing.get("genre_confidence", 0), incoming.get("genre_confidence", 0))
    existing["artist_ids"].update(incoming.get("artist_ids", {}))
    return existing


def build_artist_metadata(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}

    def store_artist(
        name: Any,
        artist_id: Any = None,
        subscribers: Any = None,
        thumbnails: Any = None,
        genres: Any = None,
        popularity: Any = None,
        followers: Any = None,
        source: Any = None,
    ) -> None:
        if not name:
            return
        key = str(name).strip()
        if not key:
            return
        existing = metadata.setdefault(key, {"artist_id": None, "subscribers": None, "thumbnails": [], "genres": [], "popularity": None, "followers": None, "source": None})
        if not existing.get("artist_id") and artist_id:
            existing["artist_id"] = artist_id
        if not existing.get("subscribers") and subscribers:
            existing["subscribers"] = subscribers
        if not existing.get("thumbnails") and thumbnails:
            existing["thumbnails"] = thumbnails
        if not existing.get("genres") and genres:
            existing["genres"] = genres
        if existing.get("popularity") is None and popularity is not None:
            existing["popularity"] = popularity
        if existing.get("followers") is None and followers is not None:
            existing["followers"] = followers
        if not existing.get("source") and source:
            existing["source"] = source

    for artist in raw.get("library_artists") or []:
        if not isinstance(artist, dict):
            continue
        name = artist.get("artist") or artist.get("name")
        store_artist(
            name,
            artist.get("browseId") or artist.get("id"),
            artist.get("subscribers") or artist.get("followers"),
            artist.get("thumbnails") or [],
            artist.get("genres") or [],
            artist.get("popularity"),
            artist.get("followers"),
            artist.get("source"),
        )

    image_cache = raw.get("artist_image_cache")
    if isinstance(image_cache, dict):
        for name, artist in image_cache.items():
            if not isinstance(artist, dict):
                continue
            store_artist(
                artist.get("artist") or artist.get("name") or name,
                artist.get("browseId") or artist.get("artist_id") or artist.get("id"),
                artist.get("subscribers"),
                artist.get("thumbnails") or [],
                artist.get("genres") or [],
                artist.get("popularity"),
                artist.get("followers"),
                artist.get("source"),
            )
    return metadata


def normalise_collection(raw: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    anchor = today or date.today()
    tracks: dict[str, dict[str, Any]] = {}
    play_events: list[dict[str, Any]] = []
    ytmusic_history = extract_tracks(raw.get("history"))
    takeout_history = extract_tracks(raw.get("takeout_history"))
    history = takeout_history if takeout_history else ytmusic_history
    parsed_history_dates = [parse_played_date(item.get("played"), anchor) for item in history]
    dated_dates = [item for item in parsed_history_dates if item is not None]
    latest = max(dated_dates) if dated_dates else None
    earliest_available = min(dated_dates) if dated_dates else None
    cutoff = latest - timedelta(days=365) if latest else None
    use_dated_window = latest is not None
    undated_history_count = sum(1 for item in parsed_history_dates if item is None)

    def upsert(item: dict[str, Any], source_type: str, playlist_id: str | None = None, playlist_title: str = "") -> dict[str, Any]:
        normalised = normalise_track_item(item, source_type, playlist_id, playlist_title)
        if normalised["track_id"] in tracks:
            return merge_track(tracks[normalised["track_id"]], normalised)
        tracks[normalised["track_id"]] = normalised
        return normalised

    if takeout_history:
        for item in ytmusic_history:
            upsert(item, "history_metadata")

    included_dated_dates: list[date] = []
    for item, played_at in zip(history, parsed_history_dates):
        include = False
        coverage_status = "available_history_no_dates"
        if use_dated_window and played_at:
            include = cutoff is None or played_at >= cutoff
            coverage_status = "dated_365_window" if include else "outside_365_window"
        elif not use_dated_window:
            include = True
        if not include:
            continue
        track = upsert(item, "history")
        track["play_count_in_period"] += 1
        track["history_coverage_status"] = coverage_status
        played_iso = played_at.isoformat() if played_at else None
        if played_at:
            included_dated_dates.append(played_at)
            if track["last_played"] is None or played_iso > track["last_played"]:
                track["last_played"] = played_iso
            if track["first_played_in_period"] is None or played_iso < track["first_played_in_period"]:
                track["first_played_in_period"] = played_iso
        play_events.append(
            {
                "track_id": track["track_id"],
                "video_id": track.get("video_id"),
                "source_track_id": track.get("source_track_id"),
                "title": track["title"],
                "primary_artist": track["primary_artist"],
                "artists": track["artists"],
                "played_at": played_iso,
                "played_date_raw": item.get("played"),
                "source": item.get("event_source") or item.get("source") or "history",
                "spotify_time_range": item.get("spotify_time_range"),
                "spotify_rank": item.get("spotify_rank"),
                "spotify_signal_label": item.get("spotify_signal_label"),
            }
        )

    for item in extract_tracks(raw.get("liked_songs")):
        upsert(item, "liked")
    for item in extract_tracks(raw.get("library_songs")):
        upsert(item, "library")

    playlists = raw.get("library_playlists") or []
    playlist_titles = {
        str(playlist.get("playlistId")): str(playlist.get("title") or "")
        for playlist in playlists
        if isinstance(playlist, dict) and playlist.get("playlistId")
    }
    playlist_tracks = raw.get("playlist_tracks") or {}
    if isinstance(playlist_tracks, dict):
        for playlist_id, items in playlist_tracks.items():
            for item in extract_tracks(items):
                upsert(item, "playlist", str(playlist_id), playlist_titles.get(str(playlist_id), ""))

    earliest_included = min(included_dated_dates) if included_dated_dates else None
    latest_included = max(included_dated_dates) if included_dated_dates else None
    days_represented = (latest_included - earliest_included).days + 1 if earliest_included and latest_included else 0
    dated_ratio = (len(dated_dates) / len(history)) if history else 0
    full_365 = bool(days_represented >= 350 and dated_ratio >= 0.8)
    notes: list[str] = []
    if not history:
        notes.append("No listening history was returned by ytmusicapi.")
    elif not dated_dates:
        notes.append("History items did not include parseable play dates; using available-history analysis.")
    elif undated_history_count:
        notes.append(f"{undated_history_count} history items had missing or unparseable play dates and were excluded from dated coverage metrics.")
    if dated_dates and not full_365:
        notes.append("Available dated history does not cover approximately 365 days, so the report is labelled as partial coverage.")

    artist_metadata = build_artist_metadata(raw)
    by_artist: dict[str, list[str]] = defaultdict(list)
    for track in tracks.values():
        by_artist[track["primary_artist"]].append(track["track_id"])
        if track["primary_artist"] in artist_metadata and not track["thumbnails"]:
            track["thumbnails"] = artist_metadata[track["primary_artist"]].get("thumbnails", [])

    for track in tracks.values():
        if not track["genre_clusters"]:
            track["genre_clusters"] = ["unknown"]
        track["genre_confidence"] = clamp(track.get("genre_confidence", 0))

    coverage = {
        "earliest_detected_play": earliest_included.isoformat() if earliest_included else None,
        "latest_detected_play": latest_included.isoformat() if latest_included else None,
        "earliest_available_play": earliest_available.isoformat() if earliest_available else None,
        "days_represented": days_represented,
        "full_365_day_analysis": full_365,
        "dated_history_items": len(dated_dates),
        "undated_history_items": undated_history_count,
        "history_items_returned": len(history),
        "date_data_available": bool(dated_dates),
        "history_coverage_status": "dated_365_window" if dated_dates else "available_history_no_dates",
        "notes": notes,
    }
    payload = {
        "tracks": list(tracks.values()),
        "play_events": play_events,
        "coverage": coverage,
        "artist_metadata": artist_metadata,
        "library_playlists": playlists,
        "metadata": {
            "track_count": len(tracks),
            "play_count": len(play_events),
            "source": raw.get("source", "ytmusicapi"),
        },
    }
    return annotate_normalised_durations(payload)
