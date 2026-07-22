from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any

from app.analysis.duration import duration_quality
from app.analysis.normalizer import UNKNOWN_ARTIST, parse_release_year
from app.analysis.periods import event_local_date, filter_events, resolve_period, serialise_spec, tracks_by_id
from app.analysis.taste_model import profile_for_artist


MUSICAL_AGE_CALCULATION_VERSION = 1
AGE_MIN = 12
AGE_MAX = 65

# Kept together so the calculation is inspectable, reproducible, and easy to version.
MATURITY_WEIGHTS = {
    "tasteStability": 0.22,
    "catalogMaturity": 0.20,
    "albumDepth": 0.16,
    "selectiveDiscovery": 0.14,
    "crossEraBreadth": 0.12,
    "reflectiveListening": 0.10,
    "longTermArtistLoyalty": 0.06,
}

AGE_CATEGORIES = (
    (14, "The Mood Mirror"),
    (17, "The Catharsis Engine"),
    (21, "The Identity Explorer"),
    (26, "The Self-Aware Regulator"),
    (34, "The Curated Balancer"),
    (49, "The Reflective Curator"),
    (64, "The Meaning Keeper"),
    (AGE_MAX, "The Timeless Integrator"),
)

CATEGORY_SUMMARIES = {
    "The Mood Mirror": "Immediate feeling and fast-changing favourites lead the listening style.",
    "The Catharsis Engine": "High emotional charge and trusted releases keep the listening direct.",
    "The Identity Explorer": "Discovery and emotional commitment are still actively reshaping the map.",
    "The Self-Aware Regulator": "Emotionally expressive, with growing intention behind what earns a return.",
    "The Curated Balancer": "Familiar anchors and selective discovery share the same well-kept rotation.",
    "The Reflective Curator": "Long-running favourites, album depth, and broader context shape the profile.",
    "The Meaning Keeper": "Continuity and cross-era listening matter more than novelty for its own sake.",
    "The Timeless Integrator": "The listening map connects eras and established favourites without treating age as a hierarchy.",
}

INTENSITY_TERMS = {
    "aggressive",
    "anthemic",
    "cathartic",
    "dramatic",
    "emo",
    "emotionally charged",
    "high-energy",
    "metalcore",
    "post-hardcore",
}

REFLECTIVE_TERMS = {
    "ambient",
    "atmospheric",
    "cinematic",
    "classical",
    "contemplative",
    "instrumental",
    "reflective",
    "soundtrack",
}


def calculate_musical_age(
    normalised: dict[str, Any],
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    """Calculate a playful listening-style age from bounded behavioural signals.

    Missing metadata lowers confidence instead of being converted into a zero-year release.
    The result describes music behaviour only and is not a physical or psychological age.
    """

    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = [event for event in filter_events(normalised, spec) if event.get("is_music_candidate") is not False]
    lookup = tracks_by_id(normalised)
    factors, diagnostics = _factor_scores(events, lookup, spec)

    age = age_from_factor_scores(factors)
    confidence = _confidence(events, lookup, spec, diagnostics)
    likely_min, likely_max = _likely_range(age, confidence)
    title = category_for_age(age)
    strongest = _strongest_factor_labels(factors)

    return {
        "age": age,
        "likelyMin": likely_min,
        "likelyMax": likely_max,
        "title": title,
        "summary": CATEGORY_SUMMARIES[title],
        "explanation": fallback_explanation(strongest),
        "confidence": round(confidence, 2),
        "confidenceLabel": confidence_label(confidence),
        "factors": {
            "repeatAttachment": factors["repeatAttachment"],
            "discovery": factors["discovery"],
            "tasteStability": factors["tasteStability"],
            "catalogMaturity": factors["catalogMaturity"],
            "albumDepth": factors["albumDepth"],
            "crossEraBreadth": factors["crossEraBreadth"],
            "emotionalIntensity": factors["emotionalIntensity"],
            "reflectiveListening": factors["reflectiveListening"],
        },
        "calculationVersion": MUSICAL_AGE_CALCULATION_VERSION,
        "generationSource": "fallback",
        "sourcePeriod": serialise_spec(spec),
        "strongestFactors": strongest,
        "metadataCoverage": {
            "releaseYearPercent": diagnostics["release_year_coverage"],
            "traitPercent": diagnostics["trait_coverage"],
            "durationPercent": diagnostics["duration_coverage"],
        },
    }


def category_for_age(age: int) -> str:
    bounded = int(_clamp(age, AGE_MIN, AGE_MAX))
    for upper, label in AGE_CATEGORIES:
        if bounded <= upper:
            return label
    return AGE_CATEGORIES[-1][1]


def age_from_factor_scores(factors: dict[str, float]) -> int:
    bounded = {key: _clamp(value) for key, value in factors.items()}
    maturity_index = sum(
        bounded.get(key, 0) * weight
        for key, weight in MATURITY_WEIGHTS.items()
        if key != "selectiveDiscovery"
    )
    maturity_index += (100 - bounded.get("discovery", 100)) * MATURITY_WEIGHTS["selectiveDiscovery"]

    # Intensity is a restrained adjustment only. Reflective intensity is never penalised.
    intensity_excess = max(0.0, bounded.get("emotionalIntensity", 0) - max(62.0, bounded.get("reflectiveListening", 0)))
    maturity_index = _clamp(maturity_index - min(5.0, intensity_excess * 0.10))

    # A gentle curve keeps ordinary mixed profiles in the central categories while
    # preserving the full 12-65 range for true minimum and maximum profiles.
    age = round(AGE_MIN + (AGE_MAX - AGE_MIN) * math.pow(maturity_index / 100, 1.45))
    return int(_clamp(age, AGE_MIN, AGE_MAX))


def confidence_label(confidence: float) -> str:
    if confidence >= 0.80:
        return "High confidence"
    if confidence >= 0.60:
        return "Good confidence"
    if confidence >= 0.40:
        return "Medium confidence"
    return "Limited confidence"


def fallback_explanation(strongest_factors: list[str]) -> str:
    labels = strongest_factors[:3]
    if not labels:
        return "The available listening sample is still forming, so this estimate stays deliberately cautious."
    if len(labels) == 1:
        evidence = labels[0]
    elif len(labels) == 2:
        evidence = f"{labels[0]} and {labels[1]}"
    else:
        evidence = f"{labels[0]}, {labels[1]}, and {labels[2]}"
    return f"The estimate is led by {evidence}. It is a playful read of listening behaviour, not a claim about physical age or emotional maturity."


def apply_musical_age_language(
    result: dict[str, Any],
    language: dict[str, Any] | None,
    generation_source: str,
) -> dict[str, Any]:
    value = dict(result)
    if not isinstance(language, dict):
        return value
    summary = _clean_language(language.get("summary"))
    explanation = _clean_language(language.get("explanation"))
    combined = f"{summary} {explanation}".casefold()
    unsafe = (
        "mental health",
        "depression",
        "anxiety",
        "trauma",
        "relationship",
        "emotionally mature",
        "emotional maturity",
        "psychological",
        "diagnosis",
        "physical age",
    )
    if not summary or not explanation or len(summary) > 180 or len(explanation) > 400:
        return value
    if re.search(r"\d", combined) or any(term in combined for term in unsafe):
        return value
    sentence_count = len([part for part in re.split(r"[.!?]+", explanation) if part.strip()])
    if sentence_count < 2 or sentence_count > 3:
        return value
    value["summary"] = summary
    value["explanation"] = explanation
    value["generationSource"] = generation_source if generation_source in {"gemma", "cache-gemma"} else "gemma"
    return value


def _factor_scores(
    events: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
    spec: dict[str, Any],
) -> tuple[dict[str, float], dict[str, float]]:
    total = len(events)
    track_counts = Counter(str(event.get("track_id") or "") for event in events if event.get("track_id"))
    artist_counts = Counter(_event_artist(event, lookup) for event in events)

    repeat_attachment = _repeat_attachment(track_counts, total)
    discovery = _discovery(events, lookup, spec)
    taste_stability = _taste_stability(events, lookup, spec)
    catalog_maturity, release_coverage, decade_counts = _catalog_maturity(events, lookup, spec)
    album_depth = _album_depth(events, lookup)
    cross_era_breadth = _normalised_entropy(decade_counts)
    emotional_intensity, reflective_listening, trait_coverage = _trait_factors(events, lookup)
    long_term_loyalty = sum(count for _, count in artist_counts.most_common(5)) / total * 100 if total else 0
    quality = duration_quality(events)

    factors = {
        "repeatAttachment": _round_score(repeat_attachment),
        "discovery": _round_score(discovery),
        "tasteStability": _round_score(taste_stability),
        "catalogMaturity": _round_score(catalog_maturity),
        "albumDepth": _round_score(album_depth),
        "crossEraBreadth": _round_score(cross_era_breadth),
        "emotionalIntensity": _round_score(emotional_intensity),
        "reflectiveListening": _round_score(reflective_listening),
        "longTermArtistLoyalty": _round_score(long_term_loyalty),
    }
    diagnostics = {
        "release_year_coverage": round(release_coverage, 1),
        "trait_coverage": round(trait_coverage, 1),
        "duration_coverage": float(quality.get("duration_coverage_percent") or 0),
    }
    return factors, diagnostics


def _repeat_attachment(track_counts: Counter[str], total: int) -> float:
    if not total or not track_counts:
        return 0
    counts = sorted(track_counts.values(), reverse=True)
    unique = len(counts)
    top_track_share = counts[0] / total * 100
    top_ten_share = sum(counts[:10]) / total * 100
    repeats_per_unique = total / unique
    repeat_ratio = (total - unique) / total * 100
    hhi = sum((count / total) ** 2 for count in counts)
    hhi_floor = 1 / unique
    concentration = ((hhi - hhi_floor) / max(1 - hhi_floor, 1e-9)) * 100 if unique > 1 else 100
    repeat_depth = _clamp((repeats_per_unique - 1) / 5 * 100)
    return top_track_share * 0.20 + top_ten_share * 0.20 + repeat_ratio * 0.35 + concentration * 0.10 + repeat_depth * 0.15


def _discovery(events: list[dict[str, Any]], lookup: dict[str, dict[str, Any]], spec: dict[str, Any]) -> float:
    total = len(events)
    if total < 6:
        return 50 if total else 0
    dated = sorted(
        ((event_local_date(event, spec.get("timezone")), event) for event in events),
        key=lambda item: item[0] or spec["start_date"],
    )
    midpoint = max(1, len(dated) // 2)
    earlier = dated[:midpoint]
    recent = dated[midpoint:]
    earlier_tracks = {str(event.get("track_id") or "") for _, event in earlier}
    earlier_artists = {_event_artist(event, lookup) for _, event in earlier}
    new_track_share = sum(str(event.get("track_id") or "") not in earlier_tracks for _, event in recent) / max(len(recent), 1) * 100
    new_artist_share = sum(_event_artist(event, lookup) not in earlier_artists for _, event in recent) / max(len(recent), 1) * 100
    unique_track_rate = len({event.get("track_id") for event in events if event.get("track_id")}) / total * 100
    unique_artist_rate = len({_event_artist(event, lookup) for event in events}) / total * 100
    return new_track_share * 0.38 + new_artist_share * 0.27 + unique_track_rate * 0.22 + unique_artist_rate * 0.13


def _taste_stability(events: list[dict[str, Any]], lookup: dict[str, dict[str, Any]], spec: dict[str, Any]) -> float:
    if len(events) < 12:
        return 50
    dated = sorted(events, key=lambda event: event_local_date(event, spec.get("timezone")) or spec["start_date"])
    midpoint = len(dated) // 2
    first_counts = Counter(_event_artist(event, lookup) for event in dated[:midpoint])
    second_counts = Counter(_event_artist(event, lookup) for event in dated[midpoint:])
    first_top = [name for name, _ in first_counts.most_common(10)]
    second_top = [name for name, _ in second_counts.most_common(10)]
    overlap = len(set(first_top) & set(second_top)) / max(len(set(first_top) | set(second_top)), 1) * 100
    rank_points = 0.0
    for artist in set(first_top) & set(second_top):
        distance = abs(first_top.index(artist) - second_top.index(artist))
        rank_points += max(0.0, 1 - distance / 10)
    rank_stability = rank_points / max(len(set(first_top) | set(second_top)), 1) * 100
    return overlap * 0.72 + rank_stability * 0.28


def _catalog_maturity(
    events: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
    spec: dict[str, Any],
) -> tuple[float, float, Counter[str]]:
    years: list[int] = []
    decades: Counter[str] = Counter()
    current_year = spec["end_date"].year
    for event in events:
        year = parse_release_year(lookup.get(event.get("track_id"), {}).get("release_year"))
        if year is None or year > current_year:
            continue
        years.append(year)
        decades[f"{year // 10 * 10}s"] += 1
    coverage = len(years) / len(events) * 100 if events else 0
    if not years:
        return 50.0, coverage, decades
    ages = [max(0, current_year - year) for year in years]
    average_age = sum(ages) / len(ages)
    older_ten = sum(age > 10 for age in ages) / len(ages) * 100
    older_twenty = sum(age > 20 for age in ages) / len(ages) * 100
    recent_three = sum(age <= 3 for age in ages) / len(ages) * 100
    score = _clamp(average_age / 25 * 100) * 0.50 + older_ten * 0.24 + older_twenty * 0.18 + (100 - recent_three) * 0.08
    return score, coverage, decades


def _album_depth(events: list[dict[str, Any]], lookup: dict[str, dict[str, Any]]) -> float:
    album_tracks: dict[str, set[str]] = defaultdict(set)
    album_plays: Counter[str] = Counter()
    for event in events:
        track = lookup.get(event.get("track_id"), {})
        album = str(track.get("album") or "").strip()
        artist = str(track.get("primary_artist") or event.get("primary_artist") or "").strip()
        track_id = str(event.get("track_id") or "").strip()
        if not album or not artist or not track_id:
            continue
        key = f"{album.casefold()}::{artist.casefold()}"
        album_tracks[key].add(track_id)
        album_plays[key] += 1
    if not album_tracks:
        return 0
    deep = {key for key, tracks in album_tracks.items() if len(tracks) >= 3}
    deep_play_share = sum(album_plays[key] for key in deep) / max(sum(album_plays.values()), 1) * 100
    average_tracks = sum(len(tracks) for tracks in album_tracks.values()) / len(album_tracks)
    breadth = _clamp((average_tracks - 1) / 4 * 100)
    return deep_play_share * 0.68 + breadth * 0.32


def _trait_factors(events: list[dict[str, Any]], lookup: dict[str, dict[str, Any]]) -> tuple[float, float, float]:
    intensity = 0.0
    reflective = 0.0
    covered = 0
    for event in events:
        track = lookup.get(event.get("track_id"), {})
        artist_profile = profile_for_artist(_event_artist(event, lookup))
        values = [
            *[str(value).casefold() for value in track.get("sonic_traits") or []],
            *[str(value).casefold() for value in track.get("genre_clusters") or []],
            *[str(value).casefold() for value in track.get("canonical_genres") or []],
            *[str(value).casefold() for value in artist_profile.get("sonic_traits") or []],
            *[str(value).casefold() for value in artist_profile.get("broad_clusters") or []],
            *[str(value).casefold() for value in artist_profile.get("canonical_genres") or []],
        ]
        if values:
            covered += 1
        joined = " / ".join(values)
        intensity += min(1.0, sum(term in joined for term in INTENSITY_TERMS) / 2)
        reflective += min(1.0, sum(term in joined for term in REFLECTIVE_TERMS) / 2)
    total = len(events)
    coverage = covered / total * 100 if total else 0
    if not total:
        return 0, 0, coverage
    # The neutral floor prevents sparse taxonomies from being mistaken for absence.
    return 25 + intensity / total * 75, 25 + reflective / total * 75, coverage


def _normalised_entropy(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 50
    if len(counts) <= 1:
        return 0
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values() if count > 0)
    return _clamp(entropy / math.log(len(counts)) * 100)


def _confidence(
    events: list[dict[str, Any]],
    lookup: dict[str, dict[str, Any]],
    spec: dict[str, Any],
    diagnostics: dict[str, float],
) -> float:
    unique_tracks = len({event.get("track_id") for event in events if event.get("track_id")})
    days = {
        day
        for event in events
        for day in [event_local_date(event, spec.get("timezone"))]
        if day is not None
    }
    expected_days = max((spec["end_date"] - spec["start_date"]).days + 1, 1)
    span_days = (max(days) - min(days)).days + 1 if days else 0
    period_completeness = min(span_days / expected_days, 1)
    score = (
        min(len(events) / 500, 1) * 0.24
        + min(len(days) / 120, 1) * 0.17
        + min(unique_tracks / 150, 1) * 0.13
        + diagnostics["release_year_coverage"] / 100 * 0.16
        + diagnostics["trait_coverage"] / 100 * 0.14
        + diagnostics["duration_coverage"] / 100 * 0.08
        + period_completeness * 0.08
    )
    if len(events) < 20:
        score = min(score, 0.35)
    elif len(events) < 50:
        score = min(score, 0.48)
    return round(_clamp(score, 0, 1), 2)


def _likely_range(age: int, confidence: float) -> tuple[int, int]:
    spread = 2 if confidence >= 0.80 else 4 if confidence >= 0.60 else 6 if confidence >= 0.40 else 8
    return max(AGE_MIN, age - spread), min(AGE_MAX, age + spread)


def _strongest_factor_labels(factors: dict[str, float]) -> list[str]:
    labels = {
        "repeatAttachment": "strong repeat attachment",
        "discovery": "active discovery",
        "tasteStability": "stable long-term taste",
        "catalogMaturity": "older-catalog pull",
        "albumDepth": "album-depth listening",
        "crossEraBreadth": "cross-era breadth",
        "emotionalIntensity": "high emotional intensity",
        "reflectiveListening": "reflective listening",
    }
    ranked = sorted(
        ((key, value) for key, value in factors.items() if key in labels),
        key=lambda item: (abs(item[1] - 50), item[1], item[0]),
        reverse=True,
    )
    return [labels[key] for key, _ in ranked[:3]]


def _event_artist(event: dict[str, Any], lookup: dict[str, dict[str, Any]]) -> str:
    track = lookup.get(event.get("track_id"), {})
    return str(track.get("primary_artist") or event.get("primary_artist") or UNKNOWN_ARTIST)


def _clean_language(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _round_score(value: float) -> float:
    return round(_clamp(value), 1)


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return min(high, max(low, float(value)))
