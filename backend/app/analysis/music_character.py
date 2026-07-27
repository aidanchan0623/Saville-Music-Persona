from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from app.analysis.periods import albums_payload, filter_events, normalised_for_events, resolve_period, taste_dna_payload, top_payload
from app.analysis.scoring import build_analysis


MUSIC_CHARACTER_CLASSIFIER_VERSION = 2
THRESHOLD = 20.0


def _definition(id: str, name: str, category: str, profile: str, roast: str, priority: int, terms: tuple[str, ...], clusters: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"id": id, "name": name, "category": category, "profile": profile, "roast": roast, "priority": priority, "terms": terms, "clusters": clusters}


# These are deliberately a catalogue of sound identities, not behaviours or eras.
CHARACTER_DEFINITIONS = [
    _definition("divorced_dad_rock_station", "The Divorced-Dad Rock Station", "Rock", "Big riffs, familiar choruses and guitar anthems sit at the centre of your listening profile.", "Your air-guitar has a more reliable commute than most people.", 8, ("classic rock", "post-grunge", "arena rock", "blues rock", "hard rock", "guitar-driven", "anthemic", "road-trip", "singalong"), ("rock",)),
    _definition("never_a_phase", "It Was Never a Phase", "Emo / Pop Punk", "Emotionally direct choruses, catharsis and dramatic alternative music remain close to the centre.", "The eyeliner may be gone; the chorus still has your emergency contact.", 4, ("emo", "pop-punk", "post-hardcore", "screamo", "punk rock", "cathartic", "theatrical", "nostalgic", "dramatic"), ("emo", "pop punk")),
    _definition("tiktok_slop_connoisseur", "The TikTok Slop Connoisseur", "Singles", "Fast hooks and individual tracks take over the rotation before the next earworm arrives.", "Your rotation has the reflexes of a very well-dressed algorithm.", 12, (), ()),
    _definition("classical_supremacist", "The Classical Supremacist", "Classical", "Formal composition, orchestral scale and carefully arranged music carry your profile.", "You do not queue songs; you schedule movements.", 3, ("classical", "orchestral", "opera", "chamber", "composer", "cinematic classical", "formal", "arranged"), ("classical", "cinematic")),
    _definition("girly_pop_commander", "The Girly-Pop Commander", "Pop", "Hooks are policy, bridges are sacred and every journey has stadium-tour potential.", "Every mundane errand has apparently been promoted to a victory lap.", 7, ("pop", "dance-pop", "synth-pop", "electropop", "k-pop", "c-pop", "bright", "polished", "melodic", "romantic"), ("pop",)),
    _definition("club_closing_time_resident", "The Club-Closing-Time Resident", "Electronic", "Rhythm, bass and forward momentum matter more than sitting quietly with the lyrics.", "Your internal clock appears to be set by the last good drop.", 6, ("house", "techno", "trance", "edm", "dance", "drum and bass", "club", "driving", "rhythmic", "high-energy"), ("electronic",)),
    _definition("main_character_rain_scene", "The Main Character in a Rain Scene", "Alternative / Indie", "Atmosphere, introspection and emotional world-building turn familiar songs into entire environments.", "You do not walk home; you stage the scene between raindrops.", 1, ("shoegaze", "dream pop", "indie pop", "bedroom pop", "atmospheric", "melancholic", "hazy", "dreamy", "introspective"), ("alternative", "indie")),
    _definition("heavy_music_therapist", "The Heavy-Music Therapist", "Heavy Alternative", "Distorted guitars, intensity and cathartic choruses provide your preferred emotional processing.", "Your coping mechanism has a breakdown, then an even bigger chorus.", 2, ("metalcore", "alternative metal", "nu metal", "heavy metal", "post-hardcore", "heavy", "aggressive", "cathartic", "high-energy"), ("heavy", "metalcore")),
    _definition("late_night_rnb_philosopher", "The Late-Night R&B Philosopher", "R&B / Soul", "Smooth, intimate and reflective music turns the listening profile into a late-night internal monologue.", "Somewhere, a draft message is being respectfully overthought.", 9, ("r&b", "rnb", "alternative r&b", "soul", "neo-soul", "smooth", "intimate", "romantic", "late-night"), ("r&b", "soul")),
    _definition("aux_cord_menace", "The Aux-Cord Menace", "Hip-Hop / Rap", "Bass, confidence and immediate impact make control of the aux cable feel like a position of authority.", "The aux is not a privilege in your hands; it is a regime.", 5, ("rap", "trap", "drill", "grime", "phonk", "bass-heavy", "confident", "aggressive", "hype"), ("hip-hop", "rap")),
    _definition("campfire_lore_keeper", "The Campfire Lore Keeper", "Folk / Country", "Stories, places and human detail matter more than flashy production.", "You have made a compelling case for listening with a thermos nearby.", 10, ("folk", "country", "americana", "singer-songwriter", "indie folk", "acoustic", "organic", "narrative", "reflective"), ("folk", "country", "acoustic")),
    _definition("jazz_bar_overthinker", "The Jazz-Bar Overthinker", "Jazz", "Improvisation, rhythm and instrumental detail reward listening closely rather than treating music as background noise.", "You heard one tasteful chord substitution and made it your whole evening.", 11, ("jazz", "jazz fusion", "bebop", "swing", "big band", "blues", "improvisational", "complex", "instrumental"), ("jazz",)),
]


def personality_catalogue() -> list[dict[str, Any]]:
    return [{key: value for key, value in item.items() if key in {"id", "name", "category", "profile"}} for item in CHARACTER_DEFINITIONS]


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _text_score(definition: dict[str, Any], signals: dict[str, Any]) -> float:
    values = " ".join([*signals.get("canonical", []), *signals.get("traits", []), *signals.get("clusters", [])]).casefold()
    hits = sum(term in values for term in definition["terms"])
    cluster_hits = sum(cluster in values for cluster in definition["clusters"])
    return _clamp(hits * 14 + cluster_hits * 18)


def score_personalities(signals: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for definition in CHARACTER_DEFINITIONS:
        score = _text_score(definition, signals)
        if definition["id"] == "tiktok_slop_connoisseur":
            score = _clamp(signals.get("single_dominance", 0) * 0.55 + max(0, 60 - signals.get("album_depth", 0)) * 0.30 + max(0, 55 - signals.get("mainstream_niche", 50)) * 0.25)
        elif definition["id"] == "never_a_phase":
            score = _clamp(score + signals.get("repeat", 0) * 0.15 + signals.get("artist_loyalty", 0) * 0.10)
        elif definition["id"] in {"main_character_rain_scene", "late_night_rnb_philosopher", "club_closing_time_resident"}:
            score = _clamp(score + signals.get("late_night_share", 0) * 0.12)
        # Avoid the two documented false positives.
        if definition["id"] == "classical_supremacist" and "jazz" in " ".join(signals.get("canonical", [])).casefold() and not any(term in " ".join(signals.get("canonical", [])).casefold() for term in ("classical", "orchestral", "opera", "chamber")):
            score = 0
        if definition["id"] == "jazz_bar_overthinker" and not any(term in " ".join(signals.get("canonical", [])).casefold() for term in ("jazz", "bebop", "swing", "fusion", "big band")):
            score = 0
        if definition["id"] == "divorced_dad_rock_station" and any(term in " ".join(signals.get("canonical", [])).casefold() for term in ("metalcore", "emo", "post-hardcore")):
            score *= 0.45
        results.append({**definition, "match_score": score})
    return sorted(results, key=lambda item: (-item["match_score"], item["priority"], item["name"]))


def select_habits(signals: dict[str, Any]) -> list[str]:
    candidates = {
        "Artist-Focused": max(signals.get("top_artist_share", 0) * 5, signals.get("artist_loyalty", 0)),
        "Album Loyalist": signals.get("album_depth", 0) if signals.get("album_depth", 0) >= 55 else 0,
        "Track Fixation": max(signals.get("single_dominance", 0), signals.get("top_track_share", 0) * 5) if max(signals.get("single_dominance", 0), signals.get("top_track_share", 0) * 5) >= 50 else 0,
        "Comfort Repeater": signals.get("repeat", 0) if signals.get("repeat", 0) >= 60 and signals.get("discovery", 100) <= 55 else 0,
        "Genre Explorer": signals.get("broad_cluster_diversity", 0) if signals.get("broad_cluster_diversity", 0) >= 65 and signals.get("top_cluster_share", 100) <= 55 else 0,
        "Niche Explorer": min(signals.get("mainstream_niche", 0), signals.get("discovery", 0)) if signals.get("mainstream_niche", 0) >= 65 and signals.get("discovery", 0) >= 50 else 0,
    }
    ranked = [name for name, score in sorted(candidates.items(), key=lambda item: (-item[1], item[0])) if score]
    if "Album Loyalist" in ranked and "Track Fixation" in ranked:
        ranked.remove("Track Fixation" if candidates["Album Loyalist"] >= candidates["Track Fixation"] else "Album Loyalist")
    return ranked[:3]


def _signals(analysis: dict[str, Any], sound: dict[str, Any], tracks: dict[str, Any], artists: dict[str, Any], albums: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    scores = {str(item.get("key")): float(item.get("value") or 0) for item in analysis.get("scores", [])}
    nodes = sound.get("nodes") or []
    canonical = [str(genre).casefold() for node in nodes for genre in node.get("canonical_genres", []) if genre]
    clusters = [str(node.get("name") or "").casefold() for node in nodes]
    traits = [str(item.get("trait") or "").casefold() for item in sound.get("traits", []) if item.get("trait")]
    top_tracks = tracks.get("items") or []
    top_artist_share = float((next((item for item in analysis.get("scores", []) if item.get("key") == "artist_loyalty"), {}).get("inputs") or {}).get("top_artist_share") or 0)
    album_items = albums.get("albums") or []
    max_album_unique = max((int(item.get("unique_songs") or 0) for item in album_items), default=0)
    max_album_plays = max((int(item.get("plays") or 0) for item in album_items), default=0)
    hours = Counter()
    for event in events:
        played = str(event.get("played_at") or "")
        if "T" in played:
            try: hours[int(played.split("T", 1)[1][:2])] += 1
            except ValueError: pass
    return {
        "canonical": canonical, "clusters": clusters, "traits": traits, "total_plays": len(events),
        "repeat": scores.get("repeat", 0), "artist_loyalty": scores.get("artist_loyalty", 0), "discovery": scores.get("discovery", 0),
        "mainstream_niche": scores.get("mainstream_niche", 50), "broad_cluster_diversity": scores.get("broad_cluster_diversity", 0),
        "top_artist_share": top_artist_share, "top_track_share": max((float(item.get("share_of_period") or 0) for item in top_tracks), default=0),
        "single_dominance": min(100, max((float(item.get("share_of_period") or 0) for item in top_tracks), default=0) * 10),
        "album_depth": min(100, max_album_unique * 12 + max_album_plays * 2),
        "top_cluster_share": max((float(node.get("share") or 0) for node in nodes), default=100),
        "late_night_share": sum(count for hour, count in hours.items() if hour >= 22 or hour <= 3) / max(sum(hours.values()), 1) * 100,
    }


def _public(character: dict[str, Any]) -> dict[str, Any]:
    return {key: character[key] for key in ("id", "name", "category", "profile", "roast", "match_score")}


def character_payload(normalised: dict[str, Any], period: str = "rolling_year", month: str | None = None, timezone_name: str | None = None, today: date | None = None) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = filter_events(normalised, spec)
    local = normalised_for_events(normalised, events, spec)
    analysis = build_analysis(local)
    sound = taste_dna_payload(normalised, spec["period"], spec.get("month"), spec["timezone"], today=spec["today"])
    signals = _signals(analysis, sound, top_payload(normalised, "tracks", spec["period"], spec.get("month"), spec["timezone"], today=spec["today"]), top_payload(normalised, "artists", spec["period"], spec.get("month"), spec["timezone"], today=spec["today"]), albums_payload(normalised, spec["period"], spec.get("month"), spec["timezone"], today=spec["today"]), events)
    ranked = score_personalities(signals)
    primary = ranked[0] if signals["total_plays"] >= 8 and ranked[0]["match_score"] >= THRESHOLD else {"id": "forming", "name": "Current profile is still forming", "category": "Fallback", "profile": "There is not enough reliable genre information in this period to choose a musical personality.", "roast": "Your taste is still warming up, but the repeat button already has opinions.", "match_score": 0}
    secondary = next((item for item in ranked[1:] if item["match_score"] >= THRESHOLD), None)
    habits = select_habits(signals)
    return {"period": {"period": spec["period"], "month": spec.get("month"), "label": spec["label"], "timezone": spec["timezone"], "start_date": spec["start_date"].isoformat(), "end_date": spec["end_date"].isoformat(), "available_months": spec.get("available_months", [])}, "primary": _public(primary), "secondary": _public(secondary) if secondary else None, "habits": habits, "evidence_chips": habits, "top_artists": [], "top_clusters": [], "sonic_traits": signals["traits"][:8], "key_scores": {key: signals[key] for key in ("repeat", "artist_loyalty", "discovery", "mainstream_niche", "broad_cluster_diversity")}, "sample_warning": "Limited monthly sample - this view may reflect a short-term phase." if spec["period"] in {"this_month", "month"} and signals["total_plays"] < 50 else None, "deterministic": True, "classifier_version": MUSIC_CHARACTER_CLASSIFIER_VERSION}
