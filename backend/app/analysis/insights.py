from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from app.analysis.duration import usable_duration_seconds
from app.analysis.normalizer import UNKNOWN_ARTIST
from app.analysis.periods import (
    event_local_date,
    filter_events,
    listening_minutes_payload,
    normalised_for_events,
    resolve_period,
    serialise_spec,
    top_payload,
    tracks_by_id,
)
from app.analysis.scoring import build_analysis
from app.analysis.period_profile import build_period_profile
from app.analysis.taste_model import profile_for_artist


INSIGHTS_SCHEMA_VERSION = 1

FAMILY_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("alternative_rock", "Alternative / Rock"),
    ("pop", "Pop"),
    ("heavy", "Heavy"),
    ("electronic_atmospheric", "Electronic / Atmospheric"),
    ("hip_hop_rnb", "Hip-Hop / R&B"),
    ("classical_cinematic", "Classical / Cinematic"),
)

CLUSTER_TO_FAMILY = {
    "Alternative / Indie Rock": "alternative_rock",
    "Emo / Pop Punk / Post-Hardcore": "alternative_rock",
    "Pop / Pop Rock Crossover": "pop",
    "Heavy Alternative / Metalcore": "heavy",
    "Electronic / Atmospheric": "electronic_atmospheric",
    "Hip-Hop / Rap": "hip_hop_rnb",
    "Cinematic / Soundtrack": "classical_cinematic",
}

USEFUL_SCORE_KEYS = (
    "repeat",
    "discovery",
    "artist_loyalty",
    "broad_cluster_diversity",
    "mainstream_niche",
)


def insights_payload(
    normalised: dict[str, Any],
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    profile = build_period_profile(normalised, period, month, timezone_name, today)
    spec = profile["spec"]
    events = profile["events"]
    analysis = profile["analysis"]
    minutes = profile["minutes"]
    artist_top = {"items": profile["top_artists"]}
    track_top = {"items": profile["top_tracks"]}
    music_events = [event for event in events if event.get("is_music_candidate") is not False]
    scores = compact_scores(analysis.get("scores") or [], spec, len(music_events))

    return {
        "schemaVersion": INSIGHTS_SCHEMA_VERSION,
        "period": {
            **serialise_spec(spec),
            "display_label": display_period_label(spec),
        },
        "summary": {
            "detectedMinutes": minutes["metrics"]["selected_period_total_minutes"],
            "detectedMinutesFormatted": minutes["metrics"]["selected_period_total_formatted"],
            "activeDays": minutes["metrics"]["active_listening_days"],
            "averageActiveDayMinutes": minutes["metrics"]["average_active_day_minutes"],
            "longestDayMinutes": (minutes["metrics"]["longest_detected_listening_day"] or {}).get("minutes", 0),
            "longestDayDate": (minutes["metrics"]["longest_detected_listening_day"] or {}).get("date"),
            "currentStreakDays": minutes["metrics"]["current_listening_streak_days"],
            "detectedPlays": len(music_events),
        },
        "durationQuality": minutes["duration_quality"],
        "canonicalFigures": profile["figures"],
        "genreShares": profile["genre_shares"]["items"],
        "musicProfile": music_profile(music_events, tracks_by_id(normalised)),
        "scores": scores,
        "rhythm": rhythm_payload(minutes, music_events, spec),
        "topArtists": [compact_artist(item) for item in (artist_top.get("items") or [])[:5]],
        "repeatedSongs": [compact_track(item) for item in (track_top.get("items") or [])[:5]],
        "dailyIntensity": minutes.get("heatmap") or [],
        "sampleWarning": artist_top.get("sample_warning"),
        "methodology": "All Insights values are deterministic. Detected minutes estimate full-track duration for events with usable duration metadata; play rankings retain events without duration metadata.",
    }


def music_profile(events: list[dict[str, Any]], track_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    family_weights: Counter[str] = Counter()
    classified_plays = 0
    for event in events:
        track = track_lookup.get(event.get("track_id"), {})
        artist = str(track.get("primary_artist") or event.get("primary_artist") or UNKNOWN_ARTIST)
        profile = profile_for_artist(artist)
        families = {
            CLUSTER_TO_FAMILY[cluster]
            for cluster in profile.get("broad_clusters") or []
            if cluster in CLUSTER_TO_FAMILY
        }
        if not families:
            continue
        classified_plays += 1
        weight = 1 / len(families)
        for family in families:
            family_weights[family] += weight

    total = len(events)
    axes = [
        {
            "key": key,
            "label": label,
            "value": round(family_weights[key] / total * 100, 1) if total else 0.0,
            "detectedPlays": round(family_weights[key], 1),
        }
        for key, label in FAMILY_DEFINITIONS
    ]
    target_share = round(classified_plays / total * 100, 1) if total else 0.0
    displayed_share = round(sum(axis["value"] for axis in axes), 1)
    if axes and displayed_share != target_share:
        strongest = max(range(len(axes)), key=lambda index: axes[index]["value"])
        axes[strongest]["value"] = round(axes[strongest]["value"] + target_share - displayed_share, 1)
    return {
        "coverage": round(classified_plays / total, 4) if total else 0.0,
        "classifiedPlays": classified_plays,
        "unclassifiedPlays": max(total - classified_plays, 0),
        "totalPlays": total,
        "axes": axes,
        "methodology": "Each classified play is split evenly across that artist's canonical mapped families, so displayed shares remain portions of all detected plays and sum to classification coverage.",
    }


def compact_scores(scores: list[dict[str, Any]], spec: dict[str, Any], detected_plays: int) -> list[dict[str, Any]]:
    by_key = {str(score.get("key")): score for score in scores}
    result = []
    for key in USEFUL_SCORE_KEYS:
        score = by_key.get(key)
        if not score:
            continue
        inputs = dict(score.get("inputs") or {})
        inputs["period_label"] = spec["label"]
        inputs["period_detected_plays"] = detected_plays
        if spec["period"] in {"this_month", "month"} and detected_plays < 50:
            inputs["confidence_note"] = "Limited sample for this month"
        result.append({**score, "inputs": inputs})
    return result


def rhythm_payload(minutes: dict[str, Any], events: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    weekly_counts: Counter[str] = Counter()
    monthly_counts: Counter[str] = Counter()
    weekly_usable: Counter[str] = Counter()
    monthly_usable: Counter[str] = Counter()
    for event in events:
        day = event_local_date(event, spec["timezone"])
        if day is None:
            continue
        week = (day - timedelta(days=day.weekday())).isoformat()
        month = day.strftime("%Y-%m")
        weekly_counts[week] += 1
        monthly_counts[month] += 1
        if usable_duration_seconds(event) is not None:
            weekly_usable[week] += 1
            monthly_usable[month] += 1
    return {
        "weekly": enrich_rhythm_points(minutes.get("weekly") or [], weekly_counts, weekly_usable),
        "monthly": enrich_rhythm_points(minutes.get("monthly") or [], monthly_counts, monthly_usable),
    }


def enrich_rhythm_points(points: list[dict[str, Any]], counts: Counter[str], usable: Counter[str]) -> list[dict[str, Any]]:
    return [
        {
            "label": point.get("name") or point.get("date"),
            "startDate": point.get("date"),
            "detectedMinutes": point.get("value", 0),
            "playCount": counts[str(point.get("date"))],
            "durationCoveragePercent": round(usable[str(point.get("date"))] / counts[str(point.get("date"))] * 100, 1)
            if counts[str(point.get("date"))]
            else 0.0,
        }
        for point in points
    ]


def compact_artist(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": item.get("rank"),
        "artist": item.get("artist") or UNKNOWN_ARTIST,
        "imageUrl": item.get("artist_image_url") or item.get("thumbnail"),
        "detectedPlays": item.get("play_count", 0),
        "share": item.get("share_of_period", 0),
    }


def compact_track(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": item.get("rank"),
        "title": item.get("title") or "Unknown track",
        "artist": item.get("artist") or UNKNOWN_ARTIST,
        "imageUrl": item.get("track_image_url") or item.get("album_art_url") or item.get("thumbnail"),
        "detectedPlays": item.get("play_count", 0),
        "share": item.get("share_of_period", 0),
    }


def display_period_label(spec: dict[str, Any]) -> str:
    if spec["period"] == "rolling_year":
        return f"Rolling year | {short_date(spec['start_date'])}-{short_date(spec['end_date'])}"
    return str(spec["label"])


def short_date(value: date) -> str:
    return f"{value.strftime('%b')} {value.day}, {value.year}"
