from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any

from app.analysis.music_character import character_payload
from app.analysis.musical_age import apply_musical_age_language, calculate_musical_age
from app.analysis.overview_identity import build_identity_evidence, compose_identity, validate_identity_language
from app.analysis.periods import filter_events, normalised_for_events, resolve_period, serialise_spec, top_payload
from app.analysis.period_profile import build_period_profile
from app.analysis.scoring import build_analysis


OVERVIEW_SCHEMA_VERSION = 3
OVERVIEW_LANGUAGE_CACHE_VERSION = 1
MUSICAL_AGE_SOURCE_PERIOD = "rolling_year"


def build_overview_response(
    normalised: dict[str, Any],
    period: str = "this_month",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
    language: dict[str, Any] | None = None,
    generation_source: str = "fallback",
) -> dict[str, Any]:
    profile = build_period_profile(normalised, period, month, timezone_name, today)
    selected_spec = profile["spec"]
    selected_events = profile["events"]
    selected_analysis = profile["analysis"]
    overview = dict(selected_analysis["overview"])
    overview["coverage"] = _period_coverage(overview.get("coverage") or {}, selected_events, selected_spec)

    musical_age = calculate_musical_age(
        normalised,
        MUSICAL_AGE_SOURCE_PERIOD,
        timezone_name=selected_spec["timezone"],
        today=selected_spec["today"],
    )
    musical_age["sourcePeriod"] = _overview_period_from_payload(musical_age["sourcePeriod"])
    selected_character = character_payload(
        normalised,
        selected_spec["period"],
        selected_spec.get("month"),
        selected_spec["timezone"],
        today=selected_spec["today"],
    )
    identity_evidence = build_identity_evidence(overview, selected_character, musical_age)
    language_identity = language.get("identity") if isinstance(language, dict) else None
    language_age = language.get("musicalAge") if isinstance(language, dict) else None
    identity = compose_identity(identity_evidence, language_identity, generation_source)
    musical_age = apply_musical_age_language(musical_age, language_age, generation_source)

    tracks = {"items": profile["top_tracks"]}
    artists = {"items": profile["top_artists"]}
    period_payload = _overview_period(selected_spec)
    top_five = {
        "period": period_payload,
        "songs": [_top_song(item) for item in tracks.get("items", [])[:5]],
        "artists": [_top_artist(item) for item in artists.get("items", [])[:5]],
    }

    overview["headline_persona"] = identity["characterTitle"]
    overview["selected_period"] = period_payload
    overview["canonical_figures"] = profile["figures"]
    overview["genre_shares"] = profile["genre_shares"]["items"]
    return {
        "schemaVersion": OVERVIEW_SCHEMA_VERSION,
        "source": normalised.get("metadata", {}).get("source") or "youtube",
        "selectedPeriod": period_payload,
        "musicalAgePeriod": musical_age["sourcePeriod"],
        "overview": overview,
        "identity": identity,
        "musicalAge": musical_age,
        "topFive": top_five,
    }


def apply_overview_language(
    response: dict[str, Any],
    language: dict[str, Any] | None,
    generation_source: str,
) -> dict[str, Any]:
    """Apply optional prose to an already-calculated response without recalculating facts."""

    identity = response.get("identity") if isinstance(response.get("identity"), dict) else {}
    language_identity = language.get("identity") if isinstance(language, dict) else None
    top_five = response.get("topFive") if isinstance(response.get("topFive"), dict) else {}
    artist_names = [
        item.get("name")
        for item in top_five.get("artists") or []
        if isinstance(item, dict) and item.get("name")
    ]
    validated_identity = validate_identity_language(language_identity or {}, {"topArtists": artist_names})
    if validated_identity:
        identity.update(validated_identity)
        identity["generationSource"] = generation_source
    else:
        identity["generationSource"] = "fallback"
    response["identity"] = identity

    language_age = language.get("musicalAge") if isinstance(language, dict) else None
    musical_age = response.get("musicalAge") if isinstance(response.get("musicalAge"), dict) else {}
    response["musicalAge"] = apply_musical_age_language(musical_age, language_age, generation_source)
    overview = response.get("overview") if isinstance(response.get("overview"), dict) else {}
    overview["headline_persona"] = identity.get("characterTitle")
    response["overview"] = overview
    return response


def overview_language_evidence(response: dict[str, Any]) -> dict[str, Any]:
    identity = response.get("identity") if isinstance(response.get("identity"), dict) else {}
    musical_age = response.get("musicalAge") if isinstance(response.get("musicalAge"), dict) else {}
    overview = response.get("overview") if isinstance(response.get("overview"), dict) else {}
    return {
        "selectedPeriod": response.get("selectedPeriod"),
        "identityFacts": {
            "fallbackCharacterTitle": identity.get("characterTitle"),
            "topGenre": overview.get("top_genre_cluster"),
            "topGenres": [
                item.get("name")
                for item in ((overview.get("taste_interpretation") or {}).get("cluster_shares") or [])[:5]
                if isinstance(item, dict)
            ],
            "sonicTraits": list((overview.get("taste_interpretation") or {}).get("sonic_traits") or [])[:6],
            "repeatAttachment": (musical_age.get("factors") or {}).get("repeatAttachment"),
            "artistLoyalty": _score_value(overview, "artist_loyalty"),
            "discovery": (musical_age.get("factors") or {}).get("discovery"),
            "albumDepth": (musical_age.get("factors") or {}).get("albumDepth"),
            "tasteStability": (musical_age.get("factors") or {}).get("tasteStability"),
            "emotionalIntensity": (musical_age.get("factors") or {}).get("emotionalIntensity"),
            "reflectiveListening": (musical_age.get("factors") or {}).get("reflectiveListening"),
        },
        "musicalAgeFacts": {
            "age": musical_age.get("age"),
            "category": musical_age.get("title"),
            "sourcePeriod": response.get("musicalAgePeriod"),
            "strongestFactors": musical_age.get("strongestFactors"),
            "confidenceLabel": musical_age.get("confidenceLabel"),
        },
    }


def overview_language_fingerprint(evidence: dict[str, Any], source: str, model: str) -> str:
    payload = {
        "schemaVersion": OVERVIEW_SCHEMA_VERSION,
        "languageVersion": OVERVIEW_LANGUAGE_CACHE_VERSION,
        "source": source,
        "model": model,
        "evidence": evidence,
    }
    compact = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()[:20]


def _period_coverage(base: dict[str, Any], events: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    dates = sorted(
        {
            str(event.get("played_at") or event.get("played_date_raw") or "")[:10]
            for event in events
            if event.get("played_at") or event.get("played_date_raw")
        }
    )
    return {
        **base,
        "days_represented": len(dates),
        "earliest_detected_play": dates[0] if dates else None,
        "latest_detected_play": dates[-1] if dates else None,
        "period_label": _display_period_label(spec),
        "period_start": spec["start_date"].isoformat(),
        "period_end": spec["end_date"].isoformat(),
    }


def _overview_period(spec: dict[str, Any]) -> dict[str, Any]:
    payload = serialise_spec(spec)
    return {
        "key": payload["period"],
        "month": payload.get("month"),
        "timezone": payload["timezone"],
        "startDate": payload["start_date"],
        "endDate": payload["end_date"],
        "availableMonths": payload["available_months"],
        "label": _display_period_label(spec),
    }


def _overview_period_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": payload.get("period"),
        "month": payload.get("month"),
        "timezone": payload.get("timezone"),
        "startDate": payload.get("start_date"),
        "endDate": payload.get("end_date"),
        "availableMonths": payload.get("available_months") or [],
        "label": _display_period_label_from_payload(payload),
    }


def _display_period_label(spec: dict[str, Any]) -> str:
    period = spec["period"]
    start = spec["start_date"]
    end = spec["end_date"]
    if period in {"this_month", "month"}:
        return str(spec["label"])
    if period == "rolling_year":
        return f"Rolling year \u00b7 {_range_label(start, end)}"
    if period == "last_30":
        return f"Last 30 days \u00b7 {_range_label(start, end)}"
    if period == "last_7":
        return f"Last 7 days \u00b7 {_range_label(start, end)}"
    if period == "all":
        return "All available history"
    return str(spec["label"])


def _display_period_label_from_payload(payload: dict[str, Any]) -> str:
    try:
        start = date.fromisoformat(str(payload["start_date"]))
        end = date.fromisoformat(str(payload["end_date"]))
    except (KeyError, ValueError):
        return str(payload.get("label") or "Rolling year")
    period = payload.get("period")
    if period == "rolling_year":
        return f"Rolling year \u00b7 {_range_label(start, end)}"
    return str(payload.get("label") or _range_label(start, end))


def _range_label(start: date, end: date) -> str:
    if start.year == end.year:
        return f"{start.strftime('%b')} {start.day}-{end.strftime('%b')} {end.day}, {end.year}"
    return f"{start.strftime('%b')} {start.day}, {start.year}-{end.strftime('%b')} {end.day}, {end.year}"


def _top_song(item: dict[str, Any]) -> dict[str, Any]:
    minutes = item.get("detected_minutes")
    return {
        "rank": item.get("rank"),
        "title": item.get("title"),
        "artist": item.get("artist"),
        "album": item.get("album"),
        "imageUrl": item.get("track_image_url") or item.get("thumbnail") or item.get("album_art_url"),
        "detectedPlays": item.get("play_count", 0),
        "detectedMinutes": minutes if minutes and minutes > 0 else None,
    }


def _top_artist(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": item.get("rank"),
        "name": item.get("artist"),
        "imageUrl": item.get("artist_image_url") or item.get("thumbnail"),
        "detectedPlays": item.get("play_count", 0),
        "uniqueSongs": item.get("unique_songs", 0),
    }


def _score_value(overview: dict[str, Any], key: str) -> float:
    if key == "artist_loyalty":
        return float(((overview.get("taste_dna") or {}).get("artist_concentration") or {}).get("value") or 0)
    return 0.0
