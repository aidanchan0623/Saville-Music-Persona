from __future__ import annotations

import re
from collections import Counter
from datetime import date
from typing import Any

from app.analysis.normalizer import parse_release_year
from app.analysis.periods import filter_events, resolve_period, serialise_spec, tracks_by_id


MUSICAL_AGE_CALCULATION_VERSION = 2
AGE_MIN = 0
AGE_MAX = 100
AGE_CATEGORIES = (
    (2, "The Release-Day Resident", "Mostly brand-new releases and current music."),
    (5, "The Recent Rotation", "Recent music dominates, supported by a smaller established catalogue."),
    (9, "The Late-2010s Native", "Late-2010s and early-2020s releases form the centre."),
    (14, "The 2010s Time Capsule", "Music from the 2010s forms the core of the listening history."),
    (24, "The Y2K Archive", "Mostly 2000s and early-2010s music."),
    (39, "The CD-Era Resident", "Strong 1980s, 1990s and early-2000s presence."),
    (AGE_MAX, "The Vinyl Time Traveller", "Older classics form the core of the library."),
)


def age_category_catalogue() -> list[dict[str, Any]]:
    lower = 0
    result = []
    for upper, title, summary in AGE_CATEGORIES:
        result.append({"minAge": lower, "maxAge": upper, "title": title, "summary": summary})
        lower = upper + 1
    return result


def category_for_age(age: int) -> str:
    for upper, title, _ in AGE_CATEGORIES:
        if age <= upper:
            return title
    return AGE_CATEGORIES[-1][1]


def confidence_label(value: float) -> str:
    if value >= .8: return "High confidence"
    if value >= .6: return "Good confidence"
    if value >= .4: return "Medium confidence"
    return "Limited confidence"


def _weighted_percentile(values: list[int], percentile: float) -> int:
    if not values: return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile)))]


def calculate_musical_age(normalised: dict[str, Any], period: str = "rolling_year", month: str | None = None, timezone_name: str | None = None, today: date | None = None) -> dict[str, Any]:
    """Use release years only: every valid listening event is one weight."""
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = [event for event in filter_events(normalised, spec) if event.get("is_music_candidate") is not False]
    tracks = tracks_by_id(normalised)
    current_year = spec["end_date"].year
    years = []
    for event in events:
        year = parse_release_year((tracks.get(event.get("track_id")) or {}).get("release_year"))
        if year is not None and 1880 <= year <= current_year:
            years.append(year)
    coverage = len(years) / max(len(events), 1)
    if years:
        median_year = _weighted_percentile(years, .5)
        ages = [max(0, current_year - year) for year in years]
        age = max(0, current_year - median_year)
        likely_min, likely_max = _weighted_percentile(ages, .25), _weighted_percentile(ages, .75)
        decade = Counter(f"{year // 10 * 10}s" for year in years).most_common(1)[0][0]
    else:
        median_year, age, likely_min, likely_max, decade = current_year, 0, 0, 0, "Unknown"
    sample = min(len(years) / 100, 1)
    confidence = round(min(1.0, coverage * .75 + sample * .25), 2)
    title = category_for_age(age)
    summary = next(summary for upper, name, summary in AGE_CATEGORIES if name == title)
    explanation = (f"Your play-weighted release years centre on {median_year}, with {decade} as the dominant decade. "
                   "Musical Age measures how old your music is and which eras dominate. It is not your real age.")
    return {"age": age, "likelyMin": likely_min, "likelyMax": likely_max, "title": title, "summary": summary,
            "explanation": explanation, "confidence": confidence, "confidenceLabel": confidence_label(confidence),
            "weightedMedianReleaseYear": median_year, "dominantDecade": decade, "releaseYearCoverage": round(coverage * 100, 1),
            "factors": {"repeatAttachment": 0, "discovery": 0, "tasteStability": 0, "catalogMaturity": 0, "albumDepth": 0, "crossEraBreadth": 0, "emotionalIntensity": 0, "reflectiveListening": 0},
            "calculationVersion": MUSICAL_AGE_CALCULATION_VERSION, "generationSource": "fallback", "sourcePeriod": serialise_spec(spec), "strongestFactors": [],
            "metadataCoverage": {"releaseYearPercent": round(coverage * 100, 1)}}


def age_from_factor_scores(_factors: dict[str, float]) -> int:
    """Compatibility shim: Musical Age no longer uses behavioural factor scores."""
    return 0


def apply_musical_age_language(result: dict[str, Any], language: dict[str, Any] | None, generation_source: str) -> dict[str, Any]:
    if not isinstance(language, dict): return dict(result)
    summary, explanation = str(language.get("summary") or "").strip(), str(language.get("explanation") or "").strip()
    if not summary or not explanation or re.search(r"\d", f"{summary} {explanation}"):
        return dict(result)
    value = dict(result); value.update({"summary": summary, "explanation": explanation, "generationSource": generation_source}); return value
