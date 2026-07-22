from __future__ import annotations

import re
from typing import Any


IDENTITY_PROMPT_VERSION = 1
FORBIDDEN_TITLE_STARTS = ("alternative", "indie", "rock", "pop", "electronic", "classical", "hip-hop")
UNSAFE_LANGUAGE = (
    "mental health",
    "depression",
    "depressed",
    "anxiety",
    "trauma",
    "relationship",
    "emotionally mature",
    "emotional maturity",
    "psychological",
    "diagnosis",
)


def build_identity_evidence(
    overview: dict[str, Any],
    character: dict[str, Any],
    musical_age: dict[str, Any],
) -> dict[str, Any]:
    taste = overview.get("taste_interpretation") if isinstance(overview.get("taste_interpretation"), dict) else {}
    factors = musical_age.get("factors") if isinstance(musical_age.get("factors"), dict) else {}
    top_artists = overview.get("top_3_artists") if isinstance(overview.get("top_3_artists"), list) else []
    return {
        "topGenre": overview.get("top_genre_cluster"),
        "topGenres": [
            item.get("name")
            for item in (taste.get("cluster_shares") or [])[:5]
            if isinstance(item, dict) and item.get("name")
        ],
        "sonicTraits": list(taste.get("sonic_traits") or [])[:8],
        "listeningCharacter": list(taste.get("listening_character") or [])[:6],
        "repeatAttachment": factors.get("repeatAttachment", 0),
        "artistLoyalty": _score_from_character(character, "artist_loyalty"),
        "discovery": factors.get("discovery", 0),
        "albumDepth": factors.get("albumDepth", 0),
        "tasteStability": factors.get("tasteStability", 0),
        "emotionalIntensity": factors.get("emotionalIntensity", 0),
        "reflectiveListening": factors.get("reflectiveListening", 0),
        "topArtists": [item.get("artist") for item in top_artists if isinstance(item, dict) and item.get("artist")],
    }


def compose_identity(
    evidence: dict[str, Any],
    gemma_language: dict[str, Any] | None = None,
    generation_source: str = "fallback",
) -> dict[str, Any]:
    fallback = deterministic_identity(evidence)
    validated = validate_identity_language(gemma_language or {}, evidence)
    if not validated:
        return {**fallback, "generationSource": "fallback"}
    return {
        **fallback,
        **validated,
        "generationSource": generation_source if generation_source in {"gemma", "cache-gemma"} else "gemma",
    }


def deterministic_identity(evidence: dict[str, Any]) -> dict[str, Any]:
    repeat = _number(evidence.get("repeatAttachment"))
    discovery = _number(evidence.get("discovery"))
    stability = _number(evidence.get("tasteStability"))
    album_depth = _number(evidence.get("albumDepth"))
    intensity = _number(evidence.get("emotionalIntensity"))
    reflective = _number(evidence.get("reflectiveListening"))

    if intensity >= 62:
        emotional = "Cathartic"
    elif reflective >= 58:
        emotional = "Reflective"
    elif discovery >= 58:
        emotional = "Adventurous"
    elif repeat >= 62:
        emotional = "Comfort-Driven"
    elif stability >= 62:
        emotional = "Nostalgic"
    else:
        emotional = "Atmospheric"

    if discovery >= 62:
        behaviour = "Explorer"
    elif repeat >= 65:
        behaviour = "Repeater"
    elif album_depth >= 58:
        behaviour = "Collector"
    elif stability >= 60:
        behaviour = "Loyalist"
    else:
        behaviour = "Curator"

    if reflective >= 58:
        context = "Cinematic"
    elif album_depth >= 58:
        context = "Album"
    elif intensity >= 65 and repeat >= 60:
        context = "Controlled-Chaos"
    elif repeat >= 65:
        context = "Night-Drive"
    else:
        context = "Soundtrack"

    title = f"The {emotional} {context} {behaviour}"
    top_sound = str(evidence.get("topGenre") or "Still mapping")
    traits = [str(item) for item in evidence.get("sonicTraits") or [] if str(item).strip()]
    description = traits[0].capitalize() if traits else "The strongest mapped sound in this period"
    tagline = _fallback_tagline(behaviour, repeat, discovery)
    explanation = _fallback_explanation(top_sound, traits, repeat, discovery, stability)
    return {
        "characterTitle": title,
        "tagline": tagline,
        "explanation": explanation,
        "mostActiveSound": {"label": top_sound, "description": description},
        "generationSource": "fallback",
    }


def validate_identity_language(value: dict[str, Any], evidence: dict[str, Any]) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    title = _clean(value.get("characterTitle"))
    tagline = _clean(value.get("tagline"))
    explanation = _clean(value.get("explanation"))
    if not title or not tagline or not explanation:
        return None
    words = title.split()
    if len(words) < 3 or len(words) > 7 or len(title) > 60:
        return None
    title_without_article = title[4:] if title.casefold().startswith("the ") else title
    if title_without_article.casefold().startswith(FORBIDDEN_TITLE_STARTS):
        return None
    if len(tagline) > 140 or len(explanation) > 400:
        return None
    combined = f"{title} {tagline} {explanation}".casefold()
    if any(term in combined for term in UNSAFE_LANGUAGE):
        return None
    if re.search(r"\d", combined):
        return None

    # Identity copy does not need artist names. Reject proper-name-shaped phrases so
    # an unrecognised artist cannot slip into an otherwise valid response.
    prose = f"{tagline} {explanation}"
    if re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", prose):
        return None
    for artist in evidence.get("topArtists") or []:
        if str(artist).casefold() in combined:
            return None
    return {"characterTitle": title, "tagline": tagline, "explanation": explanation}


def _fallback_tagline(behaviour: str, repeat: float, discovery: float) -> str:
    if behaviour == "Repeater":
        return "You return to emotional favourites until they feel like places."
    if behaviour == "Explorer":
        return "You keep opening new doors without losing the sound that feels like yours."
    if behaviour == "Collector":
        return "Songs matter, but the larger world around them earns your attention too."
    if repeat >= discovery:
        return "You build a private soundtrack from favourites that keep proving their worth."
    return "You follow curiosity, but only the right atmosphere earns a permanent place."


def _fallback_explanation(top_sound: str, traits: list[str], repeat: float, discovery: float, stability: float) -> str:
    texture = ", ".join(traits[:2]) if traits else "a consistent emotional texture"
    behaviour = (
        "Trusted songs have strong repeat gravity"
        if repeat >= discovery
        else "Discovery keeps the rotation moving"
    )
    continuity = "long-running anchors remain visible" if stability >= 55 else "the profile still leaves room to shift"
    return f"{behaviour}, while {top_sound} supplies the main sound-world through {texture}. Across the available history, {continuity}."


def _score_from_character(character: dict[str, Any], key: str) -> float:
    scores = character.get("key_scores") if isinstance(character.get("key_scores"), dict) else {}
    return _number(scores.get(key))


def _number(value: Any) -> float:
    try:
        return max(0.0, min(100.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
