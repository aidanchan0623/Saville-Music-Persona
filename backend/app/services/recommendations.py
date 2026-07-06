from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from app.analysis.demo_data import demo_raw_collection
from app.analysis.normalizer import extract_artist_names, normalise_collection, normalise_track_item, slug
from app.analysis.scoring import build_analysis


def duplicate_key(title: str, artist: str) -> str:
    clean_title = re.sub(r"\s+\((official|audio|video|lyrics?|visualizer|remaster(ed)?|live).*?\)", "", title, flags=re.I)
    clean_title = re.sub(r"\s+-\s+(official|audio|video|lyrics?|visualizer).*", "", clean_title, flags=re.I)
    return f"{slug(clean_title)}::{slug(artist)}"


def dedupe_candidates(candidates: list[dict[str, Any]], existing_keys: set[str], existing_video_ids: set[str]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for candidate in candidates:
        title = str(candidate.get("title") or candidate.get("track_title") or "").strip()
        artists = extract_artist_names(candidate)
        artist = artists[0]
        video_id = candidate.get("videoId") or candidate.get("video_id")
        key = duplicate_key(title, artist)
        if not title or key in seen or key in existing_keys:
            continue
        if video_id and str(video_id) in existing_video_ids:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def demo_recommendation_pool() -> list[dict[str, Any]]:
    raw = demo_raw_collection()
    seeds = [
        ("demo101", "Night Bus Souvenir", "Nocturne Vale", "B-Sides After Dark", 2018, "safe", "same artist deep cut"),
        ("demo102", "Clouded Metro", "Mira Sol", "Neon Weather Deluxe", 2023, "safe", "same artist release"),
        ("demo103", "Another Golden Hour", "Juno Lane", "Late Signals Deluxe", 2020, "safe", "same artist release"),
        ("demo104", "Coastal Static", "The Coastline Hours", "Weekend Maps B-Sides", 2012, "safe", "same artist deep cut"),
        ("demo105", "Orbiting Small Rooms", "Low Orbit Club", "Signal Fires", 2024, "safe", "same artist release"),
        ("demo106", "Old Film Light", "Arden Vox", "Velvet Echo Sessions", 1999, "safe", "same artist catalog"),
        ("demo107", "Satellites at Home", "Paper Satellites", "Basement Astronomy", 2007, "safe", "same artist catalog"),
        ("demo108", "Market Lights", "Kaito", "Night Market", 2023, "safe", "same artist release"),
        ("demo109", "Apartment Weather", "The Sunday Static", "Apartment Weather", 2015, "adjacent", "related indie artist"),
        ("demo110", "Velvet Monorail", "Hana Circuit", "City Bloom", 2021, "adjacent", "synth pop cluster"),
        ("demo111", "Blue Neon Errand", "Luma Park", "Blue Neon Errand", 2022, "adjacent", "synth pop cluster"),
        ("demo112", "Rain on Cassette", "North Arcade", "Rain on Cassette", 2014, "adjacent", "nostalgic indie cluster"),
        ("demo113", "Comfort Frequencies", "Signal Apartment", "Soft Machines", 2020, "adjacent", "late-night playlist pattern"),
        ("demo114", "Rush Hour Moon", "Orbit Bloom", "Rush Hour Moon", 2024, "adjacent", "electronic lift pattern"),
        ("demo115", "After Dark Postcard", "Milo Vale", "After Dark Postcard", 2017, "adjacent", "alt pop cluster"),
        ("demo116", "Lighthouse FM", "June Atlas", "Lighthouse FM", 2019, "adjacent", "indie pop cluster"),
        ("demo117", "Desert Software", "Palace Queue", "Desert Software", 2025, "discovery", "outside usual electronic edge"),
        ("demo118", "Small Cinema Jazz", "Arc Lamp Trio", "Small Cinema Jazz", 2021, "discovery", "mood-adjacent jazz step"),
        ("demo119", "Glossolalia Driver", "Monsoon Console", "Glossolalia Driver", 2024, "discovery", "higher-energy discovery"),
        ("demo120", "Folk Song for Robots", "Elder Circuit", "Folk Song for Robots", 2020, "discovery", "acoustic-electronic bridge"),
    ]
    result = []
    for video_id, title, artist, album, year, rec_type, source in seeds:
        result.append(
            {
                "videoId": video_id,
                "title": title,
                "artists": [{"name": artist, "id": f"art-{slug(artist)}"}],
                "album": {"name": album, "id": f"alb-{video_id}"},
                "year": str(year),
                "thumbnails": [{"url": f"https://placehold.co/320x320/1b152b/f0eaff?text={title[:2].upper()}", "width": 320, "height": 320}],
                "recommendation_source": source,
                "target_type": rec_type,
            }
        )
    return result


def score_candidate(candidate: dict[str, Any], analysis: dict[str, Any], normalised: dict[str, Any]) -> tuple[float, str]:
    top_artists = {artist["artist"]: artist["rank"] for artist in analysis.get("top_artists", [])}
    top_genres = {item["name"] for item in analysis.get("charts", {}).get("top_genre_clusters", [])[:4]}
    track = normalise_track_item(candidate, "recommendation")
    artist = track["primary_artist"]
    score = 40.0
    source = str(candidate.get("recommendation_source") or "search result")
    if artist in top_artists:
        score += max(12, 32 - top_artists[artist] * 2)
    if set(track.get("genre_clusters", [])) & top_genres:
        score += 14
    if candidate.get("target_type") == "discovery":
        score += 4
    if track.get("release_year") and track["release_year"] >= 2020:
        score += 5
    if "similar" in source or "watch playlist" in source:
        score += 8
    if "related" in source:
        score += 6
    return min(score, 100), source


def build_existing_sets(normalised: dict[str, Any]) -> tuple[set[str], set[str]]:
    keys: set[str] = set()
    videos: set[str] = set()
    for track in normalised.get("tracks", []):
        keys.add(duplicate_key(track.get("title", ""), track.get("primary_artist", "")))
        if track.get("video_id"):
            videos.add(str(track["video_id"]))
    return keys, videos


def recommendation_type(index: int, candidate: dict[str, Any]) -> str:
    target = candidate.get("target_type")
    if target in {"safe", "adjacent", "discovery"}:
        return str(target).capitalize()
    if index < 8:
        return "Safe"
    if index < 16:
        return "Adjacent"
    return "Discovery"


def generate_recommendations(
    normalised: dict[str, Any],
    analysis: dict[str, Any],
    ytmusic_candidates: list[dict[str, Any]] | None = None,
    explanation_map: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    candidates = list(ytmusic_candidates or [])
    if len(candidates) < 20:
        candidates.extend(demo_recommendation_pool())
    existing_keys, existing_videos = build_existing_sets(normalised)
    candidates = dedupe_candidates(candidates, existing_keys, existing_videos)
    scored = []
    for candidate in candidates:
        score, source = score_candidate(candidate, analysis, normalised)
        scored.append((score, source, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    per_artist: Counter[str] = Counter()
    selected: list[tuple[float, str, dict[str, Any]]] = []
    for item in scored:
        artist = extract_artist_names(item[2])[0]
        if per_artist[artist] >= 2 and len(selected) < 16:
            continue
        per_artist[artist] += 1
        selected.append(item)
        if len(selected) == 20:
            break
    explanations = explanation_map or {}
    output = []
    for index, (score, source, candidate) in enumerate(selected):
        track = normalise_track_item(candidate, "recommendation")
        rec_type = recommendation_type(index, candidate)
        key = f"{track['title']}::{track['primary_artist']}"
        why = explanations.get(key) or (
            f"{rec_type} match based on {source}; it connects to your top artists, genre clusters, or listening patterns without repeating a heavily played track."
        )
        output.append(
            {
                "rank": index + 1,
                "track_title": track["title"],
                "artist": track["primary_artist"],
                "artists": track["artists"],
                "album": track.get("album"),
                "album_art": (track.get("thumbnails") or [{}])[-1].get("url") if track.get("thumbnails") else None,
                "release_year": track.get("release_year"),
                "video_id": track.get("video_id"),
                "recommendation_type": rec_type,
                "why_this_fits": why,
                "source_reason": source,
                "score": round(score, 1),
            }
        )
    return output

