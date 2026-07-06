from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def _thumb(seed: str) -> list[dict[str, str | int]]:
    return [
        {
            "url": f"https://placehold.co/320x320/171326/ebe7ff?text={seed}",
            "width": 320,
            "height": 320,
        }
    ]


def _track(
    video_id: str,
    title: str,
    artists: list[tuple[str, str]],
    album: str,
    year: int | None,
    duration: int,
    genre: str,
) -> dict[str, Any]:
    return {
        "videoId": video_id,
        "title": title,
        "artists": [{"name": name, "id": artist_id} for name, artist_id in artists],
        "album": {"name": album, "id": f"ALB-{video_id}"},
        "year": str(year) if year else None,
        "duration_seconds": duration,
        "thumbnails": _thumb(title[:2].upper()),
        "genre": genre,
    }


def demo_raw_collection(today: date | None = None) -> dict[str, Any]:
    anchor = today or date.today()
    tracks = [
        _track("demo001", "Midnight Archive", [("Nocturne Vale", "art001")], "Letters After Dark", 2016, 214, "alt pop"),
        _track("demo002", "Soft Static", [("Nocturne Vale", "art001")], "Letters After Dark", 2016, 198, "alt pop"),
        _track("demo003", "Glass Hearts", [("Mira Sol", "art002")], "Neon Weather", 2022, 221, "synth pop"),
        _track("demo004", "Borrowed Summer", [("The Coastline Hours", "art003")], "Weekend Maps", 2011, 205, "indie rock"),
        _track("demo005", "Blue Hour Drive", [("Juno Lane", "art004")], "Late Signals", 2019, 236, "indie pop"),
        _track("demo006", "Retrograde Bloom", [("Mira Sol", "art002"), ("Kaito", "art005")], "Neon Weather", 2022, 247, "synth pop"),
        _track("demo007", "Old Apartment Song", [("The Coastline Hours", "art003")], "Weekend Maps", 2011, 189, "indie rock"),
        _track("demo008", "Signal Fires", [("Low Orbit Club", "art006")], "Signal Fires", 2024, 203, "electronic"),
        _track("demo009", "Cartography", [("Juno Lane", "art004")], "Late Signals", 2019, 210, "indie pop"),
        _track("demo010", "Velvet Echo", [("Arden Vox", "art007")], "Velvet Echo", 1998, 242, "r&b"),
        _track("demo011", "Afterparty Rain", [("Low Orbit Club", "art006")], "Signal Fires", 2024, 218, "electronic"),
        _track("demo012", "Basement Astronomy", [("Paper Satellites", "art008")], "Basement Astronomy", 2006, 229, "emo"),
        _track("demo013", "Lighthouse Phonecall", [("Mira Sol", "art002")], "Neon Weather", 2022, 233, "synth pop"),
        _track("demo014", "Starlit Detour", [("Kaito", "art005")], "Night Market", 2023, 201, "city pop"),
        _track("demo015", "Autumn Receipt", [("Nocturne Vale", "art001")], "Letters After Dark", 2016, 224, "alt pop"),
        _track("demo016", "Static on the Moon", [("Paper Satellites", "art008")], "Basement Astronomy", 2006, 246, "emo"),
        _track("demo017", "Little Rush", [("Low Orbit Club", "art006")], "Signal Fires", 2024, 196, "electronic"),
        _track("demo018", "Magenta Jacket", [("Arden Vox", "art007")], "Velvet Echo", 1998, 215, "r&b"),
        _track("demo019", "Different Windows", [("Juno Lane", "art004")], "Late Signals", 2019, 208, "indie pop"),
        _track("demo020", "Future Polaroid", [("Mira Sol", "art002")], "Neon Weather", 2022, 219, "synth pop"),
    ]
    track_by_id = {track["videoId"]: track for track in tracks}
    history_pattern = [
        ("demo001", 1),
        ("demo003", 2),
        ("demo001", 3),
        ("demo004", 5),
        ("demo006", 7),
        ("demo002", 9),
        ("demo008", 12),
        ("demo001", 14),
        ("demo005", 18),
        ("demo003", 23),
        ("demo007", 29),
        ("demo010", 34),
        ("demo001", 42),
        ("demo004", 52),
        ("demo012", 64),
        ("demo006", 79),
        ("demo009", 94),
        ("demo002", 111),
        ("demo015", 132),
        ("demo010", 150),
        ("demo003", 178),
        ("demo005", 205),
        ("demo016", 244),
        ("demo004", 288),
        ("demo018", 322),
        ("demo012", 368),
        ("demo007", 402),
    ]
    history = []
    for video_id, days_ago in history_pattern:
        item = dict(track_by_id[video_id])
        item["played"] = (anchor - timedelta(days=days_ago)).isoformat()
        history.append(item)

    library_artists = [
        {"browseId": "art001", "artist": "Nocturne Vale", "subscribers": "248K", "thumbnails": _thumb("NV")},
        {"browseId": "art002", "artist": "Mira Sol", "subscribers": "1.3M", "thumbnails": _thumb("MS")},
        {"browseId": "art003", "artist": "The Coastline Hours", "subscribers": "81K", "thumbnails": _thumb("CH")},
        {"browseId": "art004", "artist": "Juno Lane", "subscribers": "530K", "thumbnails": _thumb("JL")},
        {"browseId": "art005", "artist": "Kaito", "subscribers": "2.1M", "thumbnails": _thumb("KA")},
        {"browseId": "art006", "artist": "Low Orbit Club", "subscribers": "38K", "thumbnails": _thumb("LO")},
        {"browseId": "art007", "artist": "Arden Vox", "subscribers": "920K", "thumbnails": _thumb("AV")},
        {"browseId": "art008", "artist": "Paper Satellites", "subscribers": "19K", "thumbnails": _thumb("PS")},
    ]
    library_playlists = [
        {"playlistId": "PL-DEMO-LATE", "title": "Late night repeat therapy", "thumbnails": _thumb("LN"), "count": 8},
        {"playlistId": "PL-DEMO-DRIVE", "title": "Indie drive and golden hour", "thumbnails": _thumb("ID"), "count": 7},
        {"playlistId": "PL-DEMO-ENERGY", "title": "Electronic lift", "thumbnails": _thumb("EL"), "count": 5},
    ]
    playlist_tracks = {
        "PL-DEMO-LATE": [track_by_id[v] for v in ["demo001", "demo002", "demo003", "demo006", "demo012", "demo015", "demo016", "demo018"]],
        "PL-DEMO-DRIVE": [track_by_id[v] for v in ["demo004", "demo005", "demo007", "demo009", "demo014", "demo019", "demo020"]],
        "PL-DEMO-ENERGY": [track_by_id[v] for v in ["demo008", "demo011", "demo017", "demo006", "demo014"]],
    }
    return {
        "source": "demo",
        "history": history,
        "liked_songs": {"tracks": [track_by_id[v] for v in ["demo001", "demo003", "demo004", "demo006", "demo010", "demo012"]]},
        "library_songs": [track_by_id[v] for v in ["demo001", "demo002", "demo003", "demo004", "demo005", "demo006", "demo007", "demo008"]],
        "library_artists": library_artists,
        "library_albums": [
            {"browseId": "alb001", "playlistId": "OLAK-demo001", "title": "Letters After Dark", "year": "2016", "artists": [{"name": "Nocturne Vale", "id": "art001"}], "thumbnails": _thumb("LA")},
            {"browseId": "alb002", "playlistId": "OLAK-demo002", "title": "Neon Weather", "year": "2022", "artists": [{"name": "Mira Sol", "id": "art002"}], "thumbnails": _thumb("NW")},
            {"browseId": "alb003", "playlistId": "OLAK-demo003", "title": "Weekend Maps", "year": "2011", "artists": [{"name": "The Coastline Hours", "id": "art003"}], "thumbnails": _thumb("WM")},
        ],
        "library_playlists": library_playlists,
        "playlist_tracks": playlist_tracks,
        "warnings": [],
    }

