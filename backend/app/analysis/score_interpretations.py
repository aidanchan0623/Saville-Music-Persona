from __future__ import annotations

from typing import Any


def attach_score_interpretations(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**score, "interpretation": interpret_score(score)} for score in scores]


def interpret_score(score: dict[str, Any]) -> dict[str, Any]:
    key = score.get("key")
    value = float(score.get("value") or 0)
    inputs = score.get("inputs") if isinstance(score.get("inputs"), dict) else {}
    if key == "repeat":
        return repeat_interpretation(value, inputs)
    if key == "artist_loyalty":
        return artist_loyalty_interpretation(value, inputs)
    if key == "discovery":
        return discovery_interpretation(value, inputs)
    if key == "nostalgia":
        return nostalgia_interpretation(value, inputs)
    if key == "mainstream_niche":
        return mainstream_interpretation(value, inputs)
    if key == "broad_cluster_diversity":
        return broad_cluster_interpretation(value, inputs)
    if key == "within_cluster_diversity":
        return within_cluster_interpretation(value, inputs)
    if key == "taste_confidence":
        return confidence_interpretation(value, inputs)
    return {
        "status_title": score.get("label") or "Calculated signal",
        "plain_english": score.get("explanation") or "This score is calculated from the available listening data.",
        "confidence": "Calculated",
        "evidence": evidence_from_inputs(inputs),
    }


def repeat_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    if value <= 25:
        title = "Exploration-led listener"
        text = "You rarely stay with the same tracks for long. Your listening is driven more by variety than replay."
    elif value <= 50:
        title = "Balanced revisiter"
        text = "You return to favourites, but still keep your listening rotation moving."
    elif value <= 75:
        title = "Comfort listener"
        text = "You build familiarity through replay. Favourite songs are part of your routine rather than occasional visits."
    else:
        title = "Emotional loop specialist"
        text = "You are a strong replay listener. Your taste is not about constantly chasing new songs; it is about finding tracks that hit properly and returning to them until they become part of your personal soundtrack."
    return {"status_title": title, "plain_english": text, "confidence": "High" if inputs.get("total_track_plays", 0) >= 100 else "Limited sample", "evidence": evidence_from_inputs(inputs)}


def artist_loyalty_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    if value <= 30:
        title = "Broadly roaming, not artist-locked"
        text = "You are not attached to only a few artists. You explore across a wide artist pool, even when your broader sound remains consistent."
    elif value <= 55:
        title = "Lightly artist-led"
        text = "A few artists clearly matter, but they do not fully dominate the profile. Your listening is partly artist-led and partly sound-led."
    else:
        title = "Trusted-artist builder"
        text = "You build your listening around a smaller group of trusted artists. Their discographies shape your profile strongly."
    return {"status_title": title, "plain_english": text, "confidence": "High" if inputs.get("unique_artists_listened", 0) >= 25 else "Limited sample", "evidence": evidence_from_inputs(inputs)}


def discovery_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    if "dated_plays" in inputs or "earlier_tracks" in inputs:
        return {
            "status_title": "Discovery baseline unavailable",
            "plain_english": "There is not enough dated before-and-after listening to fairly separate recent discovery from earlier favourites.",
            "confidence": "Limited sample",
            "evidence": evidence_from_inputs(inputs),
        }
    if value <= 35:
        title = "Selective explorer"
        text = "You do discover music, but your recent listening is still led by known favourites and familiar artists."
    elif value <= 65:
        title = "Active explorer"
        text = "New artists and songs form a meaningful part of your recent listening."
    else:
        title = "Discovery-driven"
        text = "Your recent taste is actively changing through new artists and unfamiliar tracks."
    return {"status_title": title, "plain_english": text, "confidence": "High" if inputs.get("recent_plays", 0) >= 30 else "Limited sample", "evidence": evidence_from_inputs(inputs)}


def nostalgia_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    coverage = int(inputs.get("tracks_with_release_year") or 0)
    if coverage < 25:
        return {
            "status_title": "Era preference unavailable",
            "plain_english": "Too little reliable release-year metadata is available to make a fair claim about whether you prefer older or newer music.",
            "confidence": "Low metadata coverage",
            "evidence": evidence_from_inputs(inputs),
        }
    if value <= 25:
        text = "Your dated release-year evidence leans current rather than catalog-heavy."
    elif value <= 50:
        text = "Your release-year evidence is balanced between newer music and older catalog listening."
    else:
        text = "Older catalog music has a meaningful pull in the tracks with reliable release-year metadata."
    return {"status_title": "Release-era signal", "plain_english": text, "confidence": "Calculated from available release years", "evidence": evidence_from_inputs(inputs)}


def mainstream_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    coverage = float(inputs.get("artist_subscriber_metadata_coverage") or 0)
    if value >= 65:
        title = "Niche-leaning listener"
        text = "Your detected artists skew away from the most broadly popular acts in the available metadata. This suggests you often listen beyond mainstream chart culture, though the estimate depends on incomplete subscriber/popularity coverage."
    elif value <= 35:
        title = "Mainstream-connected listener"
        text = "Your listening overlaps strongly with broadly popular artists and sounds. This is a reach estimate, not a judgement of quality."
    else:
        title = "Mainstream-adjacent with side paths"
        text = "Your artist reach sits between broadly recognisable acts and smaller scenes. This is a popularity proxy, not a quality ranking."
    confidence = "Good metadata coverage" if coverage >= 75 else "Partial metadata coverage" if coverage >= 50 else "Limited metadata coverage"
    return {"status_title": title, "plain_english": text, "confidence": confidence, "evidence": evidence_from_inputs(inputs)}


def broad_cluster_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    clusters = [str(item.get("name")) for item in inputs.get("top_clusters", []) if isinstance(item, dict) and item.get("name")]
    if value >= 65 and any("Rock" in cluster for cluster in clusters):
        text = "Your taste has a clear home base, but you explore several distinct worlds within and around it: alternative rock, emo/pop-punk, heavier metalcore, shoegaze atmosphere, pop-rock crossover and cinematic material."
        title = "Rock-centred, internally varied"
    elif value >= 65:
        text = "Your listening spreads across several major sound worlds without collapsing into a single lane."
        title = "Broadly varied"
    else:
        text = "You keep a tight sonic centre. The profile is concentrated rather than random, with fewer major genre worlds competing for attention."
        title = "Focused sound world"
    return {"status_title": title, "plain_english": text, "confidence": coverage_confidence(inputs.get("genre_data_coverage", 0)), "evidence": evidence_from_inputs(inputs)}


def within_cluster_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    genres = [str(item.get("name")) for item in inputs.get("top_canonical_genres", []) if isinstance(item, dict) and item.get("name")]
    if genres:
        text = f"Within your core sound, you move between {', '.join(genres[:5])}, so your taste is focused without being one-dimensional."
    else:
        text = "There is not enough canonical genre coverage to describe variation inside your core sound fairly."
    return {"status_title": "Focused without being flat" if value >= 45 else "Narrower internal range", "plain_english": text, "confidence": "Calculated from curated genre coverage", "evidence": evidence_from_inputs(inputs)}


def confidence_interpretation(value: float, inputs: dict[str, Any]) -> dict[str, Any]:
    if value >= 80:
        title = "High-confidence profile"
        text = "The listening window has enough play volume, date coverage and mapped genre evidence to support strong claims."
    elif value >= 60:
        title = "Solid signal"
        text = "The profile is useful and evidence-led, while some metadata gaps still limit fine-grained claims."
    else:
        title = "Partial signal"
        text = "The app can describe the strongest patterns, but the missing metadata means subtle claims should stay cautious."
    return {"status_title": title, "plain_english": text, "confidence": "Data-quality score", "evidence": evidence_from_inputs(inputs)}


def evidence_from_inputs(inputs: dict[str, Any]) -> list[str]:
    lines = []
    for key, value in inputs.items():
        label = key.replace("_", " ")
        lines.append(f"{label}: {value}")
    return lines[:8]


def coverage_confidence(value: Any) -> str:
    try:
        coverage = float(value)
    except (TypeError, ValueError):
        return "Unknown coverage"
    if coverage >= 90:
        return "High coverage"
    if coverage >= 75:
        return "Good coverage"
    if coverage >= 50:
        return "Partial coverage"
    return "Limited coverage"
