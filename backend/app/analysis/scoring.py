from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from app.analysis.normalizer import UNKNOWN_ARTIST, clamp, parse_release_year
from app.analysis.score_interpretations import attach_score_interpretations
from app.analysis.taste_model import build_taste_model, enrich_artist


def score_label(score: float, bands: list[tuple[int, int, str]]) -> str:
    for low, high, label in bands:
        if low <= score <= high:
            return label
    return bands[-1][2]


def thumbnail_url(thumbnails: Any, video_id: Any = None) -> str | None:
    if isinstance(thumbnails, str) and thumbnails:
        return thumbnails
    if isinstance(thumbnails, list):
        candidates = [item for item in thumbnails if isinstance(item, dict) and item.get("url")]
        if candidates:
            return str(candidates[-1]["url"])
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return None


def repeat_score(total_track_plays: int, unique_tracks: int) -> dict[str, Any]:
    score = clamp(100 * (1 - unique_tracks / total_track_plays)) if total_track_plays else 0
    return {
        "key": "repeat",
        "name": "Repeat score",
        "value": round(score, 1),
        "label": score_label(score, [(0, 25, "explorer"), (26, 50, "balanced"), (51, 75, "comfort listener"), (76, 100, "emotional loop specialist")]),
        "explanation": "Measures how much the same tracks repeat inside the analysed period.",
        "formula": "100 * (1 - unique_tracks / total_track_plays)",
        "inputs": {"total_track_plays": total_track_plays, "unique_tracks": unique_tracks},
    }


def parse_subscriber_count(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    match = math.nan
    import re

    found = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([kKmMbB]?)", text)
    if not found:
        return None
    amount = float(found.group(1))
    suffix = found.group(2).lower()
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    elif suffix == "b":
        amount *= 1_000_000_000
    return int(amount)


def artist_loyalty_score(artist_counts: Counter[str], total_plays: int) -> dict[str, Any]:
    top = artist_counts.most_common()
    top_artist_share = (top[0][1] / total_plays * 100) if total_plays and top else 0
    top5_share = (sum(count for _, count in top[:5]) / total_plays * 100) if total_plays else 0
    return {
        "key": "artist_loyalty",
        "name": "Artist loyalty",
        "value": round(clamp(top5_share), 1),
        "label": score_label(top5_share, [(0, 30, "wide roaming"), (31, 55, "lightly loyal"), (56, 75, "core cast"), (76, 100, "inner circle listener")]),
        "explanation": "Shows how concentrated your plays are around your top five artists.",
        "formula": "top_5_artist_plays / total_track_plays * 100",
        "inputs": {
            "top_artist_share": round(top_artist_share, 1),
            "top_5_artist_share": round(top5_share, 1),
            "unique_artists_listened": len(artist_counts),
        },
    }


def discovery_score(events: list[dict[str, Any]], tracks_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    dated = []
    for event in events:
        if event.get("played_at"):
            try:
                dated.append((datetime.fromisoformat(event["played_at"]).date(), event))
            except ValueError:
                pass
    if len(dated) < 6:
        return {
            "key": "discovery",
            "name": "Discovery score",
            "value": 0,
            "label": "insufficient dated history",
            "explanation": "Not enough dated plays were available to separate earlier listening from the recent window.",
            "formula": "recent new-track share and new-artist share over the last 30 dated days",
            "inputs": {"dated_plays": len(dated)},
        }
    latest = max(day for day, _ in dated)
    recent_cutoff = latest - timedelta(days=30)
    earlier_track_ids = {event["track_id"] for day, event in dated if day < recent_cutoff}
    earlier_artists = {
        tracks_by_id.get(event["track_id"], {}).get("primary_artist", event.get("primary_artist", UNKNOWN_ARTIST))
        for day, event in dated
        if day < recent_cutoff
    }
    recent = [(day, event) for day, event in dated if day >= recent_cutoff]
    if not recent or not earlier_track_ids:
        return {
            "key": "discovery",
            "name": "Discovery score",
            "value": 0,
            "label": "not enough comparison data",
            "explanation": "The dated listening window is too short to compare recent plays against an earlier baseline.",
            "formula": "recent new-track share and new-artist share over the last 30 dated days",
            "inputs": {"recent_plays": len(recent), "earlier_tracks": len(earlier_track_ids)},
        }
    new_track_plays = 0
    new_artist_plays = 0
    for _, event in recent:
        track = tracks_by_id.get(event["track_id"], {})
        artist = track.get("primary_artist", event.get("primary_artist", UNKNOWN_ARTIST))
        if event["track_id"] not in earlier_track_ids:
            new_track_plays += 1
        if artist not in earlier_artists:
            new_artist_plays += 1
    track_share = new_track_plays / len(recent)
    artist_share = new_artist_plays / len(recent)
    score = clamp((track_share * 0.6 + artist_share * 0.4) * 100)
    return {
        "key": "discovery",
        "name": "Discovery score",
        "value": round(score, 1),
        "label": score_label(score, [(0, 25, "settled"), (26, 50, "selectively curious"), (51, 75, "active discoverer"), (76, 100, "new-music hunter")]),
        "explanation": "Compares your most recent 30 dated days against artists and tracks that appeared earlier.",
        "formula": "(new_recent_track_share * 0.6 + new_recent_artist_share * 0.4) * 100",
        "inputs": {
            "recent_plays": len(recent),
            "new_recent_track_share": round(track_share * 100, 1),
            "new_recent_artist_share": round(artist_share * 100, 1),
        },
    }


def nostalgia_score(tracks: list[dict[str, Any]], events: list[dict[str, Any]], current_year: int | None = None) -> dict[str, Any]:
    current = current_year or date.today().year
    tracks_by_id = {track["track_id"]: track for track in tracks}
    weighted_years: list[int] = []
    for event in events:
        year = tracks_by_id.get(event["track_id"], {}).get("release_year")
        if isinstance(year, int):
            weighted_years.append(year)
    decade_counts: Counter[str] = Counter()
    for year in weighted_years:
        decade_counts[f"{year // 10 * 10}s"] += 1
    total = sum(decade_counts.values())
    percentages = {decade: round(count / total * 100, 1) for decade, count in sorted(decade_counts.items())} if total else {}
    favourite_decade = decade_counts.most_common(1)[0][0] if decade_counts else "unknown"
    frequent_tracks = [track for track in tracks if track.get("play_count_in_period", 0) >= 2 and track.get("release_year")]
    oldest = min(frequent_tracks, key=lambda track: track["release_year"], default=None)
    newest = max(frequent_tracks, key=lambda track: track["release_year"], default=None)
    if not weighted_years:
        score = 0
    else:
        score = sum(clamp((current - year) / 30 * 100) for year in weighted_years) / len(weighted_years)
    return {
        "key": "nostalgia",
        "name": "Nostalgia score",
        "value": round(clamp(score), 1),
        "label": score_label(score, [(0, 25, "mostly current"), (26, 50, "era-balanced"), (51, 75, "retro pull"), (76, 100, "catalog time traveller")]),
        "explanation": "Estimates how strongly older release years shape the dated listening period.",
        "formula": "average min((current_year - release_year) / 30 * 100, 100), weighted by plays with known years",
        "inputs": {
            "favourite_release_decade": favourite_decade,
            "decade_percentages": percentages,
            "oldest_frequently_played_song": oldest["title"] if oldest else None,
            "newest_frequently_played_song": newest["title"] if newest else None,
            "tracks_with_release_year": len(weighted_years),
        },
    }


def mainstream_niche_score(artist_counts: Counter[str], artist_metadata: dict[str, dict[str, Any]]) -> dict[str, Any]:
    weighted: list[float] = []
    missing = 0
    for artist, count in artist_counts.items():
        subscribers = parse_subscriber_count(artist_metadata.get(artist, {}).get("subscribers"))
        if subscribers is None:
            missing += count
            continue
        if subscribers >= 10_000_000:
            artist_score = 10
        elif subscribers >= 1_000_000:
            artist_score = 30
        elif subscribers >= 100_000:
            artist_score = 55
        elif subscribers >= 10_000:
            artist_score = 75
        else:
            artist_score = 90
        weighted.extend([artist_score] * count)
    total = sum(artist_counts.values())
    metadata_coverage = (len(weighted) / total * 100) if total else 0
    score = sum(weighted) / len(weighted) if weighted else 50
    confidence_note = "Subscriber metadata covered enough artists for a cautious estimate." if metadata_coverage >= 60 else "Low subscriber metadata coverage; treat this as a rough proxy, not a judgement."
    label = score_label(score, [(0, 25, "mainstream-facing"), (26, 50, "recognisable"), (51, 75, "niche-leaning"), (76, 100, "deep-cut territory")])
    if metadata_coverage < 60 and label == "deep-cut territory":
        label = "niche-leaning estimate"
    return {
        "key": "mainstream_niche",
        "name": "Mainstream-Niche Estimate",
        "value": round(clamp(score), 1),
        "label": label,
        "explanation": "Uses available artist subscriber counts as a cautious popularity proxy.",
        "formula": "play-weighted artist subscriber bucket score, where higher means more niche",
        "inputs": {"artist_subscriber_metadata_coverage": round(metadata_coverage, 1), "missing_play_count": missing, "confidence_note": confidence_note},
    }


def genre_diversity_score(tracks: list[dict[str, Any]], events: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tracks_by_id = {track["track_id"]: track for track in tracks}
    counts: Counter[str] = Counter()
    known = 0
    for event in events:
        clusters = tracks_by_id.get(event["track_id"], {}).get("genre_clusters") or ["unknown"]
        usable = [cluster for cluster in clusters if cluster != "unknown"]
        if usable:
            known += 1
        for cluster in usable or ["unknown"]:
            counts[cluster] += 1 / len(clusters)
    total = sum(counts.values())
    known_share = (known / len(events) * 100) if events else 0
    if total <= 0 or len([key for key in counts if key != "unknown"]) < 2:
        diversity = 0
    else:
        entropy = -sum((count / total) * math.log(count / total) for count in counts.values() if count > 0)
        diversity = entropy / math.log(len(counts)) * 100
    chart = [
        {"name": cluster, "value": round(count / total * 100, 1) if total else 0}
        for cluster, count in counts.most_common()
    ]
    metric = {
        "key": "genre_diversity",
        "name": "Genre diversity",
        "value": round(clamp(diversity), 1),
        "label": score_label(diversity, [(0, 25, "single-lane"), (26, 50, "clustered"), (51, 75, "varied"), (76, 100, "genre omnivore")]),
        "explanation": "Uses Shannon entropy over available or inferred genre clusters.",
        "formula": "normalised Shannon entropy of play-weighted genre cluster counts",
        "inputs": {"genre_data_coverage": round(known_share, 1), "top_genre_clusters": chart[:5]},
    }
    return metric, chart


def mood_profile(tracks: list[dict[str, Any]], events: list[dict[str, Any]], repeat_metric: dict[str, Any]) -> list[dict[str, str]]:
    tracks_by_id = {track["track_id"]: track for track in tracks}
    counts: Counter[str] = Counter()
    examples: dict[str, set[str]] = defaultdict(set)
    for event in events:
        track = tracks_by_id.get(event["track_id"], {})
        for mood in track.get("mood_signals", []):
            counts[mood] += 1
            if len(examples[mood]) < 3:
                examples[mood].add(track.get("title", "a track"))
    if repeat_metric["value"] >= 45:
        counts["comfort-listening"] += max(2, int(repeat_metric["value"] // 20))
        examples["comfort-listening"].add("repeat-heavy listening pattern")
    tags = []
    for mood, count in counts.most_common(6):
        sample = ", ".join(sorted(examples[mood])) if examples[mood] else "playlist and title signals"
        tags.append({"tag": mood, "score": count, "reason": f"Evidence from {sample}."})
    return tags


def taste_confidence_score(
    coverage: dict[str, Any],
    total_plays: int,
    unique_artists: int,
    tracks: list[dict[str, Any]],
    genre_metric: dict[str, Any],
) -> dict[str, Any]:
    with_year = sum(1 for track in tracks if track.get("release_year"))
    metadata_share = (with_year / len(tracks) * 100) if tracks else 0
    genre_share = genre_metric["inputs"].get("genre_data_coverage", 0)
    date_share = 100 if coverage.get("date_data_available") else 20
    coverage_component = min(coverage.get("days_represented", 0) / 365, 1) * 20
    play_component = min(total_plays / 500, 1) * 20
    artist_component = min(unique_artists / 75, 1) * 15
    metadata_component = metadata_share / 100 * 15
    genre_component = genre_share / 100 * 15
    date_component = date_share / 100 * 15
    score = coverage_component + play_component + artist_component + metadata_component + genre_component + date_component
    return {
        "key": "taste_confidence",
        "name": "Taste confidence",
        "value": round(clamp(score), 1),
        "label": score_label(score, [(0, 35, "low confidence"), (36, 60, "useful but partial"), (61, 80, "solid signal"), (81, 100, "high confidence")]),
        "explanation": "Rates how complete and reliable the report inputs are.",
        "formula": "weighted blend of date coverage, play volume, unique artists, release-year metadata, genre data, and date availability",
        "inputs": {
            "days_represented": coverage.get("days_represented", 0),
            "track_plays": total_plays,
            "unique_artists": unique_artists,
            "release_year_metadata_coverage": round(metadata_share, 1),
            "genre_data_coverage": genre_share,
            "date_data_available": coverage.get("date_data_available", False),
        },
    }


def build_top_tracks(tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        tracks,
        key=lambda track: (
            track.get("play_count_in_period", 0),
            track.get("last_played") or "",
            track.get("liked", False),
        ),
        reverse=True,
    )
    result = []
    max_play_count = max((track.get("play_count_in_period", 0) for track in tracks), default=0)
    no_repeat_signal = max_play_count <= 1
    for index, track in enumerate([track for track in ranked if track.get("play_count_in_period", 0) > 0][:10], 1):
        reason = f"{track.get('play_count_in_period', 0)} detected plays in the analysed period; recency only broke ties."
        if no_repeat_signal:
            reason = (
                "The available YouTube Music web history has no repeated tracks, so this row is a recent detected song "
                "rather than a meaningful top-song ranking. Import Google Takeout history for stronger counts."
            )
        result.append(
            {
                "rank": index,
                "track_id": track["track_id"],
                "video_id": track.get("video_id"),
                "title": track["title"],
                "artist": track["primary_artist"],
                "artists": track["artists"],
                "album": track.get("album"),
                "release_year": track.get("release_year"),
                "thumbnail": thumbnail_url(track.get("thumbnails"), track.get("video_id")),
                "play_count": track.get("play_count_in_period", 0),
                "last_played": track.get("last_played"),
                "why_it_ranked": reason,
                "genre_clusters": track.get("genre_clusters", []),
                "ranking_confidence": "low_no_repeat_signal" if no_repeat_signal else "play_count",
            }
        )
    return result


def build_top_artists(events: list[dict[str, Any]], tracks: list[dict[str, Any]], artist_metadata: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    tracks_by_id = {track["track_id"]: track for track in tracks}
    artist_counts: Counter[str] = Counter()
    artist_tracks: dict[str, Counter[str]] = defaultdict(Counter)
    artist_genres: dict[str, Counter[str]] = defaultdict(Counter)
    for event in events:
        track = tracks_by_id.get(event["track_id"], {})
        artist = track.get("primary_artist", event.get("primary_artist", UNKNOWN_ARTIST))
        artist_counts[artist] += 1
        artist_tracks[artist][track.get("title", event.get("title", "Unknown track"))] += 1
        for genre in track.get("genre_clusters", []):
            if genre != "unknown":
                artist_genres[artist][genre] += 1
    total = sum(artist_counts.values())
    result = []
    for index, (artist, count) in enumerate(artist_counts.most_common(10), 1):
        meta = artist_metadata.get(artist, {})
        share = count / total * 100 if total else 0
        unique_songs = len(artist_tracks[artist])
        most_played = artist_tracks[artist].most_common(1)[0][0] if artist_tracks[artist] else None
        if share >= 15:
            label = "Dominant core influence"
        elif share >= 6:
            label = "Core influence"
        elif share >= 2:
            label = "Secondary influence"
        else:
            label = "Distinctive side interest"
        top_genres = [name for name, _ in artist_genres[artist].most_common(3)]
        result.append(
            {
                "rank": index,
                "artist": artist,
                "artist_id": meta.get("artist_id"),
                "image": thumbnail_url(meta.get("thumbnails")),
                "play_count": count,
                "share_of_listens": round(share, 1),
                "unique_songs_played": unique_songs,
                "most_played_song": most_played,
                "artist_loyalty_label": label,
                "related_genres": top_genres or ["inferred genre unavailable"],
                "observation": f"{artist} accounts for {round(share, 1)}% of detected plays across {unique_songs} song(s).",
            }
        )
    total_plays = len(events)
    return [enrich_artist(item, total_plays) for item in result]


def broad_cluster_diversity_metric(taste_model: dict[str, Any]) -> dict[str, Any]:
    diversity = taste_model.get("diversity", {})
    coverage = taste_model.get("coverage", {})
    return {
        "key": "broad_cluster_diversity",
        "name": "Broad-cluster diversity",
        "value": diversity.get("broad_cluster_score", 0),
        "label": diversity.get("label", "confidence-aware taste profile"),
        "explanation": "How varied are the major musical worlds you listen to, using curated and confidence-aware artist mappings.",
        "formula": "normalised Shannon entropy over broad curated taste clusters, weighted by plays",
        "inputs": {
            "top_clusters": taste_model.get("cluster_shares", [])[:5],
            "genre_data_coverage": coverage.get("genre_coverage_percent", 0),
            "curated_artist_coverage_percent": coverage.get("curated_artist_coverage_percent", 0),
        },
    }


def within_cluster_diversity_metric(taste_model: dict[str, Any]) -> dict[str, Any]:
    diversity = taste_model.get("diversity", {})
    return {
        "key": "within_cluster_diversity",
        "name": "Within-cluster diversity",
        "value": diversity.get("within_cluster_score", 0),
        "label": "internally varied" if diversity.get("within_cluster_score", 0) >= 45 else "focused within core worlds",
        "explanation": "How much you explore within your dominant rock/alternative/soundtrack worlds.",
        "formula": "normalised Shannon entropy over canonical genres, weighted by plays",
        "inputs": {
            "top_canonical_genres": taste_model.get("canonical_genre_shares", [])[:8],
        },
    }


def build_charts(
    tracks: list[dict[str, Any]],
    events: list[dict[str, Any]],
    artist_counts: Counter[str],
    genre_chart: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    tracks_by_id = {track["track_id"]: track for track in tracks}
    decade_counts: Counter[str] = Counter()
    playlist_counts: Counter[str] = Counter()
    timeline_counts: Counter[str] = Counter()
    for event in events:
        track = tracks_by_id.get(event["track_id"], {})
        year = parse_release_year(track.get("release_year"))
        if year:
            decade_counts[f"{year // 10 * 10}s"] += 1
        for playlist_title in track.get("playlist_titles", []):
            playlist_counts[playlist_title] += 1
        if event.get("played_at"):
            timeline_counts[event["played_at"][:7]] += 1
    most_repeated = [
        {"name": track["title"], "value": track.get("play_count_in_period", 0)}
        for track in sorted(tracks, key=lambda item: item.get("play_count_in_period", 0), reverse=True)[:10]
        if track.get("play_count_in_period", 0) > 0
    ]
    artist_total = sum(artist_counts.values())
    artist_concentration = [
        {"name": artist, "value": round(count / artist_total * 100, 1) if artist_total else 0}
        for artist, count in artist_counts.most_common(10)
    ]
    return {
        "release_decades": [{"name": name, "value": value} for name, value in sorted(decade_counts.items())],
        "top_genre_clusters": genre_chart,
        "top_artists": [{"name": artist, "value": count} for artist, count in artist_counts.most_common(10)],
        "most_repeated_songs": most_repeated,
        "artist_concentration": artist_concentration,
        "playlist_influence": [{"name": name, "value": value} for name, value in playlist_counts.most_common(10)],
        "coverage_timeline": [{"name": month, "value": count} for month, count in sorted(timeline_counts.items())] if coverage.get("date_data_available") else [],
    }


def build_analysis(normalised: dict[str, Any]) -> dict[str, Any]:
    tracks = normalised.get("tracks", [])
    events = normalised.get("play_events", [])
    coverage = normalised.get("coverage", {})
    tracks_by_id = {track["track_id"]: track for track in tracks}
    artist_counts: Counter[str] = Counter()
    for event in events:
        track = tracks_by_id.get(event["track_id"], {})
        artist_counts[track.get("primary_artist", event.get("primary_artist", UNKNOWN_ARTIST))] += 1

    total_plays = len(events)
    unique_tracks = len({event["track_id"] for event in events})
    taste = build_taste_model(normalised, artist_counts, total_plays)
    repeat = repeat_score(total_plays, unique_tracks)
    loyalty = artist_loyalty_score(artist_counts, total_plays)
    discovery = discovery_score(events, tracks_by_id)
    nostalgia = nostalgia_score(tracks, events)
    mainstream = mainstream_niche_score(artist_counts, normalised.get("artist_metadata", {}))
    genre_metric = broad_cluster_diversity_metric(taste)
    within_genre_metric = within_cluster_diversity_metric(taste)
    confidence = taste_confidence_score(coverage, total_plays, len(artist_counts), tracks, genre_metric)
    scores = attach_score_interpretations([repeat, loyalty, discovery, nostalgia, mainstream, genre_metric, within_genre_metric, confidence])
    top_tracks = build_top_tracks(tracks)
    top_artists = build_top_artists(events, tracks, normalised.get("artist_metadata", {}))
    moods = mood_profile(tracks, events, repeat)
    genre_chart = [{"name": item["name"], "value": item["value"]} for item in taste.get("cluster_shares", [])]
    charts = build_charts(tracks, events, artist_counts, genre_chart, coverage)
    charts["canonical_genres"] = [{"name": item["name"], "value": item["value"]} for item in taste.get("canonical_genre_shares", [])[:12]]

    top_artist = top_artists[0]["artist"] if top_artists else "Unknown Artist"
    favourite_decade = nostalgia["inputs"].get("favourite_release_decade", "unknown")
    top_genre = genre_chart[0]["name"] if genre_chart else "unknown"
    persona_tag = "The Private Listening Cartographer"
    if repeat["value"] >= 50 and nostalgia["value"] >= 45:
        persona_tag = f"The {favourite_decade} Comfort Archivist"
    elif discovery["value"] >= 55:
        persona_tag = "The Restless New-Sound Scout"
    elif loyalty["value"] >= 65:
        persona_tag = f"The {top_artist} Inner-Circle Listener"
    elif top_genre != "unknown":
        persona_tag = f"The {top_genre.title()} Signal Curator"

    overview = {
        "headline_persona": persona_tag,
        "top_3_artists": top_artists[:3],
        "top_3_tracks": top_tracks[:3],
        "top_genre_cluster": top_genre,
        "favourite_decade": favourite_decade,
        "repeat_score": repeat,
        "discovery_score": discovery,
        "taste_confidence": confidence,
        "last_refreshed_at": normalised.get("refreshed_at"),
        "coverage": coverage,
        "total_detected_plays": total_plays,
        "unique_tracks": unique_tracks,
        "unique_artists": len(artist_counts),
        "taste_interpretation": taste,
        "taste_dna": taste.get("taste_dna", {}),
        "genre_coverage_percent": taste.get("coverage", {}).get("genre_coverage_percent", 0),
        "curated_artist_coverage_percent": taste.get("coverage", {}).get("curated_artist_coverage_percent", 0),
        "inferred_artist_coverage_percent": taste.get("coverage", {}).get("inferred_artist_coverage_percent", 0),
        "unknown_artist_coverage_percent": taste.get("coverage", {}).get("unknown_artist_coverage_percent", 0),
        "top_tracks_ranking_note": (
            "Available history has no repeated tracks; songs are shown as recent detected plays until longer history is imported."
            if top_tracks and max((track.get("play_count", 0) for track in top_tracks), default=0) <= 1
            else "Top songs are ranked by detected play count, with recency only breaking ties."
        ),
    }
    return {
        "overview": overview,
        "coverage": coverage,
        "top_tracks": top_tracks,
        "top_artists": top_artists,
        "scores": scores,
        "charts": charts,
        "mood_profile": moods,
        "report_profile": build_report_profile(overview, top_tracks, top_artists, scores, moods, charts),
    }


def build_report_profile(
    overview: dict[str, Any],
    top_tracks: list[dict[str, Any]],
    top_artists: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    moods: list[dict[str, Any]],
    charts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "headline_persona": overview["headline_persona"],
        "coverage": overview["coverage"],
        "total_detected_plays": overview.get("total_detected_plays", 0),
        "unique_tracks": overview.get("unique_tracks", 0),
        "unique_artists": overview.get("unique_artists", 0),
        "taste_interpretation": overview.get("taste_interpretation", {}),
        "taste_dna": overview.get("taste_dna", {}),
        "genre_confidence": {
            "genre_coverage_percent": overview.get("genre_coverage_percent", 0),
            "curated_artist_coverage_percent": overview.get("curated_artist_coverage_percent", 0),
            "inferred_artist_coverage_percent": overview.get("inferred_artist_coverage_percent", 0),
            "unknown_artist_coverage_percent": overview.get("unknown_artist_coverage_percent", 0),
        },
        "top_tracks": top_tracks[:10],
        "top_artists": top_artists[:10],
        "scores": [
            {
                "key": score["key"],
                "name": score["name"],
                "value": score["value"],
                "label": score["label"],
                "inputs": score["inputs"],
                "interpretation": score.get("interpretation"),
            }
            for score in scores
        ],
        "mood_profile": moods[:6],
        "genre_clusters": charts.get("top_genre_clusters", [])[:8],
        "release_decades": charts.get("release_decades", []),
        "important_instruction": "Use only this JSON as evidence. Do not invent artists, tracks, dates, genres, play counts, or personal details.",
    }
