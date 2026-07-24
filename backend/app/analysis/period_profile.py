from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from typing import Any

from app.analysis.duration import duration_quality, usable_duration_seconds
from app.analysis.periods import (
    event_local_date,
    filter_events,
    listening_minutes_payload,
    normalised_for_events,
    rank_items,
    resolve_period,
    serialise_spec,
    tracks_by_id,
)
from app.analysis.scoring import build_analysis


ANALYTICS_VERSION = 2
GENRE_MAP_VERSION = 1


def build_period_profile(
    normalised: dict[str, Any],
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """The sole deterministic source for a source/period's dashboard facts."""
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = filter_events(normalised, spec)
    period_normalised = normalised_for_events(normalised, events, spec)
    analysis = build_analysis(period_normalised)
    lookup = tracks_by_id(normalised)
    minutes = listening_minutes_payload(normalised, period, month, timezone_name, today)
    tracks = rank_items(events, lookup, "tracks")
    artists = rank_items(events, lookup, "artists", normalised.get("artist_metadata") or {})
    genres = genre_shares(events, lookup)
    raw_diagnostics = normalised.get("import_diagnostics") or {}
    duration = duration_quality(events)
    active_days = {
        event_local_date(event, spec["timezone"])
        for event in events
        if event_local_date(event, spec["timezone"]) is not None
    }
    fingerprint = data_fingerprint(normalised, events, spec)
    reconciliation = {
        "raw_rows": int(raw_diagnostics.get("raw_events") or len(normalised.get("listening_events") or events)),
        "canonical_events": len(normalised.get("listening_events") or events),
        "accepted_music_play_events": int(raw_diagnostics.get("accepted_music_plays") or len(normalised.get("play_events") or [])),
        "exact_duplicates_removed": int(raw_diagnostics.get("duplicates") or 0),
        "non_music_excluded": sum(1 for event in normalised.get("excluded_play_events") or [] if event.get("music_classification") == "non_music"),
        "unknown_music_excluded": sum(1 for event in normalised.get("excluded_play_events") or [] if event.get("music_classification") == "unknown"),
        "invalid_timestamps": int(raw_diagnostics.get("invalid_timestamps") or 0),
        "events_in_period": len(events),
    }
    return {
        "analyticsVersion": ANALYTICS_VERSION,
        "genreMapVersion": GENRE_MAP_VERSION,
        "dataFingerprint": fingerprint,
        "spec": spec,
        "period": serialise_spec(spec),
        "events": events,
        "normalised": period_normalised,
        "analysis": analysis,
        "top_tracks": tracks,
        "top_artists": artists,
        "minutes": minutes,
        "genre_shares": genres,
        "figures": {
            "raw_event_count": reconciliation["raw_rows"],
            "accepted_play_count": len(events),
            "active_days": len(active_days),
            "unique_track_count": len({event.get("track_id") for event in events if event.get("track_id")}),
            "unique_artist_count": len({artist for event in events for artist in event_artists(event, lookup)}),
            "detected_minutes": minutes["metrics"]["selected_period_total_minutes"],
            "duration_coverage": duration["duration_coverage_percent"],
            "timestamp_coverage": timestamp_coverage(events),
            "genre_coverage": genres["coveragePercent"],
            "release_year_coverage": release_year_coverage(events, lookup),
        },
        "reconciliation": reconciliation,
    }


def event_artists(event: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> list[str]:
    artists = lookup.get(event.get("track_id"), {}).get("artists") or event.get("artists") or []
    return [str(artist).strip() for artist in artists if str(artist).strip() and str(artist).strip() != "Unknown Artist"]


def genre_shares(events: list[dict[str, Any]], lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    weights: Counter[str] = Counter()
    classified = 0
    for event in events:
        genres = [str(value).strip() for value in lookup.get(event.get("track_id"), {}).get("genre_clusters") or [] if value and value != "unknown"]
        if not genres:
            weights["Other / Unclassified"] += 1
            continue
        classified += 1
        for genre in genres:
            weights[genre] += 1 / len(genres)
    total = sum(weights.values())
    items = [{"name": name, "value": round(value / total * 100, 1)} for name, value in sorted(weights.items(), key=lambda item: (-item[1], item[0]))] if total else []
    if items:
        items[0]["value"] = round(items[0]["value"] + 100 - sum(item["value"] for item in items), 1)
    return {"items": items, "coveragePercent": round(classified / len(events) * 100, 1) if events else 0.0}


def timestamp_coverage(events: list[dict[str, Any]]) -> float:
    return round(sum(event.get("timestamp_status") in (None, "valid") for event in events) / len(events) * 100, 1) if events else 0.0


def release_year_coverage(events: list[dict[str, Any]], lookup: dict[str, dict[str, Any]]) -> float:
    return round(sum(bool(lookup.get(event.get("track_id"), {}).get("release_year")) for event in events) / len(events) * 100, 1) if events else 0.0


def data_fingerprint(normalised: dict[str, Any], events: list[dict[str, Any]], spec: dict[str, Any]) -> str:
    payload = {
        "parser": normalised.get("metadata", {}).get("parser_schema_version"),
        "event": normalised.get("metadata", {}).get("listening_event_schema_version"),
        "analytics": ANALYTICS_VERSION,
        "genre": GENRE_MAP_VERSION,
        "period": serialise_spec(spec),
        "events": [(event.get("event_id") or event.get("id"), event.get("timestamp_utc") or event.get("played_at")) for event in events],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:20]
