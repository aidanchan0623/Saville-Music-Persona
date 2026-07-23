from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any, Callable

from app.analysis.periods import albums_payload, filter_events, normalised_for_events, resolve_period, taste_dna_payload, top_payload
from app.analysis.scoring import build_analysis


THRESHOLD = 20.0
MUSIC_CHARACTER_CLASSIFIER_VERSION = 1
MODIFIER_IDS = {"comfort_loop_specialist", "album_loyalist", "single_song_prisoner", "genre_tourist", "one_artist_cult_member"}


def character_payload(
    normalised: dict[str, Any],
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = filter_events(normalised, spec)
    period_normalised = normalised_for_events(normalised, events, spec)
    analysis = build_analysis(period_normalised)
    sound = taste_dna_payload(normalised, spec["period"], spec.get("month"), spec["timezone"], today=spec["today"])
    tracks = top_payload(normalised, "tracks", spec["period"], spec.get("month"), spec["timezone"], today=spec["today"])
    artists = top_payload(normalised, "artists", spec["period"], spec.get("month"), spec["timezone"], today=spec["today"])
    albums = albums_payload(normalised, spec["period"], spec.get("month"), spec["timezone"], today=spec["today"])
    signals = build_signals(analysis, sound, tracks, artists, albums, events)
    matches = [score_character(definition, signals) for definition in CHARACTER_DEFINITIONS]
    matches.sort(key=lambda item: (-item["match_score"], item["priority"], item["name"]))

    primary_candidate = next((item for item in matches if item["id"] not in MODIFIER_IDS and item["match_score"] >= THRESHOLD), matches[0] if matches else None)
    if signals["total_plays"] < 8 or not primary_candidate or primary_candidate["match_score"] < THRESHOLD:
        primary = forming_character(signals)
        secondary = None
    else:
        primary = primary_candidate
        secondary = next((item for item in matches if item["id"] != primary["id"] and item["id"] not in MODIFIER_IDS and item["match_score"] >= THRESHOLD and not contradictory(primary["id"], item["id"])), None)

    modifier = next(
        (
            item
            for item in matches
            if item["id"] in MODIFIER_IDS
            and item["id"] != primary["id"]
            and item["match_score"] >= THRESHOLD
            and not contradictory(primary["id"], item["id"])
        ),
        None,
    )
    chips = evidence_chips(primary, secondary, modifier, signals)
    sample_warning = "Limited monthly sample - this view may reflect a short-term phase." if spec["period"] in {"this_month", "month"} and signals["total_plays"] < 50 else None
    return {
        "period": {
            "period": spec["period"],
            "month": spec.get("month"),
            "label": spec["label"],
            "timezone": spec["timezone"],
            "start_date": spec["start_date"].isoformat(),
            "end_date": spec["end_date"].isoformat(),
            "available_months": spec.get("available_months", []),
        },
        "primary": public_character(primary),
        "secondary": public_character(secondary) if secondary else None,
        "modifier": public_character(modifier) if modifier else None,
        "evidence_chips": chips[:8],
        "top_artists": signals["top_artists"][:5],
        "top_clusters": signals["top_clusters"][:5],
        "sonic_traits": signals["traits"][:8],
        "key_scores": signals["scores"],
        "sample_warning": sample_warning,
        "deterministic": True,
        "classifier_version": MUSIC_CHARACTER_CLASSIFIER_VERSION,
        "methodology": "Music Character is selected by deterministic rule scores from local listening data. Gemma can rewrite the wording, but it does not choose the character.",
    }


def build_signals(
    analysis: dict[str, Any],
    sound: dict[str, Any],
    tracks: dict[str, Any],
    artists: dict[str, Any],
    albums: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    score_map = {score.get("key"): score for score in analysis.get("scores", [])}
    top_clusters = sound.get("nodes") or []
    cluster_map = {str(item.get("name")).lower(): float(item.get("share") or 0) for item in top_clusters}
    traits = [str(item.get("trait") or "").lower() for item in sound.get("traits", []) if item.get("trait")]
    canonical = [
        str(genre).lower()
        for node in top_clusters
        for genre in node.get("canonical_genres", [])
        if genre
    ]
    top_artists = artists.get("items") or []
    artist_names = [str(item.get("artist") or "").lower() for item in top_artists]
    top_tracks = tracks.get("items") or []
    album_items = albums.get("albums") or []
    max_album_unique = max((int(item.get("unique_songs") or 0) for item in album_items), default=0)
    max_album_plays = max((int(item.get("plays") or 0) for item in album_items), default=0)
    top_track_share = max((float(item.get("share_of_period") or 0) for item in top_tracks), default=0)
    top_artist_share = float((score_map.get("artist_loyalty") or {}).get("inputs", {}).get("top_artist_share") or 0)
    hour_counts: Counter[int] = Counter()
    for event in events:
        played = str(event.get("played_at") or "")
        if "T" in played:
            try:
                hour_counts[int(played.split("T", 1)[1][:2])] += 1
            except ValueError:
                pass
    late_night_share = sum(count for hour, count in hour_counts.items() if hour >= 22 or hour <= 3) / max(sum(hour_counts.values()), 1) * 100
    return {
        "total_plays": len(events),
        "clusters": cluster_map,
        "traits": traits,
        "canonical": canonical,
        "top_artists": [
            {"name": item.get("artist"), "plays": item.get("play_count")}
            for item in top_artists
            if item.get("artist")
        ],
        "artist_names": artist_names,
        "top_clusters": [{"name": item.get("name"), "share": item.get("share")} for item in top_clusters if item.get("name")],
        "top_tracks": top_tracks,
        "albums": album_items,
        "scores": {
            "repeat": score_value(score_map, "repeat"),
            "artist_loyalty": score_value(score_map, "artist_loyalty"),
            "discovery": score_value(score_map, "discovery"),
            "nostalgia": score_value(score_map, "nostalgia"),
            "mainstream_niche": score_value(score_map, "mainstream_niche"),
            "broad_cluster_diversity": score_value(score_map, "broad_cluster_diversity"),
        },
        "album_depth": min(max_album_unique * 12 + max_album_plays * 2, 100),
        "single_dominance": min(top_track_share * 10, 100),
        "top_artist_share": top_artist_share,
        "late_night_share": late_night_share,
    }


def score_value(score_map: dict[str, dict[str, Any]], key: str) -> float:
    return float((score_map.get(key) or {}).get("value") or 0)


def cluster(signals: dict[str, Any], name: str) -> float:
    return signals["clusters"].get(name.lower(), 0.0)


def has_any(values: list[str], needles: list[str]) -> bool:
    text = " ".join(values)
    return any(needle in text for needle in needles)


def artist_hit(signals: dict[str, Any], names: list[str]) -> bool:
    artists = " ".join(signals["artist_names"])
    return any(name.lower() in artists for name in names)


def clamp(value: float, high: float = 100.0) -> float:
    return max(0.0, min(high, value))


def weighted(*parts: float) -> float:
    return clamp(sum(parts))


def score_character(definition: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    score, evidence = definition["score"](signals)
    payload = {**definition, "match_score": round(clamp(score), 1), "confidence": confidence_for(score), "evidence": evidence}
    payload.pop("score", None)
    return payload


def confidence_for(score: float) -> str:
    if score >= 65:
        return "High"
    if score >= 40:
        return "Medium"
    return "Limited"


def public_character(character: dict[str, Any] | None) -> dict[str, Any] | None:
    if not character:
        return None
    return {
        "id": character["id"],
        "name": character["name"],
        "category": character["category"],
        "roast": character["roast"],
        "profile": character["profile"],
        "match_score": character["match_score"],
        "confidence": character["confidence"],
        "priority": character["priority"],
        "evidence": character.get("evidence", []),
        "trigger_rules": character.get("trigger_rules", []),
    }


def forming_character(signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "forming",
        "name": "Current profile is still forming",
        "category": "fallback",
        "trigger_rules": ["Not enough reliable period data for a strong character."],
        "roast": "The app has the pen out, but the music evidence has not finished introducing itself yet.",
        "profile": "There is not enough listening data in this period to make a strong character claim. Refresh data or choose a broader period for a clearer read.",
        "match_score": 0,
        "confidence": "Limited",
        "priority": 999,
        "evidence": [f"{signals['total_plays']} detected plays in this period"],
    }


def evidence_chips(primary: dict[str, Any], secondary: dict[str, Any] | None, modifier: dict[str, Any] | None, signals: dict[str, Any]) -> list[str]:
    chips = list(primary.get("evidence", []))
    if secondary:
        chips.append(f"Secondary: {secondary['name']}")
    if modifier:
        chips.append(f"Modifier: {modifier['name']}")
    for cluster_item in signals["top_clusters"][:2]:
        chips.append(str(cluster_item["name"]))
    if signals["scores"]["repeat"] >= 55:
        chips.append("High replay score")
    if signals["album_depth"] >= 45:
        chips.append("Album-level listening")
    result: list[str] = []
    seen: set[str] = set()
    for chip in chips:
        clean = str(chip).strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            result.append(clean)
    return result


def contradictory(first: str, second: str) -> bool:
    pair = {first, second}
    return pair in [
        {"album_loyalist", "single_song_prisoner"},
        {"genre_tourist", "one_artist_cult_member"},
        {"playlist_npc", "algorithm_escapee"},
    ]


def make_definition(
    id: str,
    name: str,
    category: str,
    trigger_rules: list[str],
    roast: str,
    profile: str,
    priority: int,
    score: Callable[[dict[str, Any]], tuple[float, list[str]]],
) -> dict[str, Any]:
    return {
        "id": id,
        "name": name,
        "category": category,
        "trigger_rules": trigger_rules,
        "roast": roast,
        "profile": profile,
        "priority": priority,
        "score": score,
    }


CHARACTER_DEFINITIONS = [
    make_definition(
        "classical_superiority_complex",
        "The Classical Superiority Complex",
        "sound",
        ["High classical, orchestral, opera, film-score, or composer-heavy listening."],
        "You don't listen to music, you audit civilisation.",
        "Your taste leans formal, dramatic and composition-heavy. You seem drawn to music that feels arranged, cinematic, or intellectually satisfying.",
        9,
        lambda s: (weighted(cluster(s, "Cinematic / Soundtrack") * 4, 25 if has_any(s["canonical"], ["classical", "orchestral", "opera"]) else 0), ["Cinematic or orchestral signal"]),
    ),
    make_definition(
        "main_character_rain_scene",
        "The Main Character in a Rain Scene",
        "sound",
        ["Sad indie, shoegaze, dream pop, atmospheric traits, melancholic traits, and high repeat."],
        "You do not walk home. You emotionally soundtrack your walk home like the final scene of a film nobody funded.",
        "Your taste is atmospheric, introspective and mood-heavy. You return to songs that create a whole emotional environment.",
        3,
        lambda s: (weighted(cluster(s, "Alternative / Indie Rock") * 1.5, 18 if has_any(s["canonical"], ["shoegaze", "dream pop", "bedroom"]) else 0, 18 if has_any(s["traits"], ["atmospheric", "melancholic", "hazy"]) else 0, s["scores"]["repeat"] * 0.18), ["Atmospheric alternative signal", "Repeat-friendly mood listening"]),
    ),
    make_definition(
        "cathartic_chaos_enjoyer",
        "The Cathartic Chaos Enjoyer",
        "sound",
        ["Metalcore, post-hardcore, alternative metal, screamo, heavy rock, high-energy or cathartic traits."],
        "Your idea of emotional regulation is letting someone scream over a breakdown and calling it healing.",
        "Your listening favours intensity, release and big emotional impact. You like music that hits hard rather than politely staying in the background.",
        2,
        lambda s: (weighted(cluster(s, "Heavy Alternative / Metalcore") * 4, cluster(s, "Emo / Pop Punk / Post-Hardcore") * 1.4, 20 if has_any(s["traits"], ["cathartic", "high-energy", "dramatic", "heavy"]) else 0), ["Heavy alt signal", "Cathartic traits"]),
    ),
    make_definition(
        "pop_punk_time_traveller",
        "The Pop-Punk Time Traveller",
        "era",
        ["Pop-punk, emo, 2000s/2010s alternative rock, or adjacent artists."],
        "You are one chorus away from texting someone you definitely should not text.",
        "Your taste carries a strong nostalgic, emotionally direct streak. Hooks, drama and big singalong energy matter a lot here.",
        6,
        lambda s: (weighted(cluster(s, "Emo / Pop Punk / Post-Hardcore") * 4, 18 if artist_hit(s, ["My Chemical Romance", "Paramore", "Fall Out Boy", "Green Day", "Blink-182"]) else 0, s["scores"]["nostalgia"] * 0.2), ["Emo/pop-punk signal", "Big chorus nostalgia"]),
    ),
    make_definition(
        "indie_gatekeeper_soft_launch",
        "The Indie Gatekeeper, Soft Launch Edition",
        "sound",
        ["Indie rock, alternative, lower-mainstream artists, high niche score, broad artist range."],
        "You liked the artist before they were popular, but you are trying very hard to act normal about it.",
        "Your taste leans discovery-driven and artist-varied, but still has a clear sonic centre around alternative and indie textures.",
        12,
        lambda s: (weighted(cluster(s, "Alternative / Indie Rock") * 2, s["scores"]["mainstream_niche"] * 0.3, s["scores"]["discovery"] * 0.2, max(0, 45 - s["top_artist_share"]) * 0.25), ["Alternative/indie centre", "Niche-leaning artist pool"]),
    ),
    make_definition(
        "one_artist_cult_member",
        "The One-Artist Cult Member",
        "modifier",
        ["Very high artist concentration and one artist dominating songs or months."],
        "At this point you are not a listener, you are unpaid regional marketing.",
        "Your profile is strongly artist-led. One artist or a small group of artists defines the emotional and sonic centre of your listening.",
        17,
        lambda s: (weighted(s["top_artist_share"] * 2.4, s["scores"]["artist_loyalty"] * 0.35), ["Top artist concentration"]),
    ),
    make_definition(
        "playlist_npc",
        "The Playlist NPC",
        "sound",
        ["Mainstream-facing artists, low niche score, low album depth, popular-single behaviour."],
        "Your music taste has excellent Wi-Fi and zero desire to leave the algorithm's suggested route.",
        "Your listening is strongly connected to popular, accessible tracks. You favour songs that are immediate, familiar and easy to return to.",
        20,
        lambda s: (weighted(max(0, 55 - s["scores"]["mainstream_niche"]) * 1.2, max(0, 35 - s["album_depth"]) * 0.5, s["single_dominance"] * 0.2), ["Mainstream-facing signal", "Single-led listening"]),
    ),
    make_definition(
        "album_loyalist",
        "The Album Loyalist",
        "modifier",
        ["Many plays across multiple songs from the same album and low single dominance."],
        "You still believe albums are sacred texts, and honestly, you might be right.",
        "You do not only chase singles. Your listening shows album-level attachment, meaning you connect with full projects and not just isolated tracks.",
        11,
        lambda s: (weighted(s["album_depth"] * 0.9, max(0, 40 - s["single_dominance"]) * 0.45), ["Album-level listening"]),
    ),
    make_definition(
        "single_song_prisoner",
        "The Single-Song Prisoner",
        "modifier",
        ["One song dominates an album or artist, high repeat, low unique song ratio, or high top-track share."],
        "You found one song that works and decided personal growth could wait.",
        "Your listening shows strong track fixation. Certain songs become repeat anchors and carry a large part of your music identity.",
        13,
        lambda s: (weighted(s["single_dominance"] * 1.25, s["scores"]["repeat"] * 0.45), ["Track fixation", "Replay-heavy behaviour"]),
    ),
    make_definition(
        "soundtrack_side_quest",
        "The Soundtrack Side Quest",
        "sound",
        ["Film scores, game OSTs, anime OSTs, cinematic, orchestral, dramatic traits."],
        "You are doing normal tasks with the emotional stakes of a final boss fight.",
        "Your taste has a cinematic side. Even outside normal songs, you are drawn to scale, atmosphere and dramatic world-building.",
        7,
        lambda s: (weighted(cluster(s, "Cinematic / Soundtrack") * 4, 20 if artist_hit(s, ["Hans Zimmer", "Ramin Djawadi", "Ludwig"]) else 0, 14 if has_any(s["traits"], ["cinematic", "orchestral", "dramatic"]) else 0), ["Cinematic side colour"]),
    ),
    make_definition(
        "gym_arc_villain",
        "The Gym Arc Villain",
        "sound",
        ["Aggressive rap, phonk, hard rock, metal, high-energy, workout, rage, or hype signals."],
        "You do not listen to music, you queue entrance themes for imaginary enemies.",
        "Your listening leans high-impact and adrenaline-driven. It is built around momentum, confidence and physical energy.",
        16,
        lambda s: (weighted(cluster(s, "Heavy Alternative / Metalcore") * 2, cluster(s, "Hip-Hop / Rap") * 2, 25 if has_any(s["traits"], ["high-energy", "aggression", "heavy", "driving"]) else 0), ["High-impact energy"]),
    ),
    make_definition(
        "late_night_rnb_philosopher",
        "The Late-Night R&B Philosopher",
        "sound",
        ["R&B, alternative R&B, soul, moody pop, romantic, introspective, smooth traits, or late-night timestamps."],
        "You listen like you are about to send a paragraph that starts with 'I've been thinking.'",
        "Your profile favours smooth, intimate and emotionally reflective music. The sound is less explosive and more late-night internal monologue.",
        18,
        lambda s: (weighted(28 if has_any(s["canonical"], ["r&b", "soul", "alternative r&b"]) else 0, 20 if has_any(s["traits"], ["introspective", "romantic", "smooth", "late-night"]) else 0, s["late_night_share"] * 0.4), ["Late-night reflective signal"]),
    ),
    make_definition(
        "genre_tourist",
        "The Genre Tourist",
        "modifier",
        ["High broad-cluster diversity, low repeat, low artist loyalty, and no dominant sound family."],
        "Your taste has no home address, only recently visited locations.",
        "Your listening is exploratory and wide-ranging. You move across different sound worlds instead of settling into one strong identity.",
        19,
        lambda s: (weighted(s["scores"]["broad_cluster_diversity"] * 0.7, max(0, 45 - s["scores"]["repeat"]) * 0.35, max(0, 50 - s["scores"]["artist_loyalty"]) * 0.2), ["Broad sound-family spread"]),
    ),
    make_definition(
        "comfort_loop_specialist",
        "The Comfort Loop Specialist",
        "modifier",
        ["High repeat, medium or low discovery, and comfort-listening behaviour."],
        "You are not stuck in a loop. You have simply chosen a very specific emotional furniture arrangement.",
        "You build safety and familiarity through repetition. Your favourite songs work like reliable places to return to.",
        10,
        lambda s: (weighted(s["scores"]["repeat"] * 0.8, max(0, 55 - s["scores"]["discovery"]) * 0.4), ["Replay comfort pattern"]),
    ),
    make_definition(
        "im_fine_alternative_listener",
        "The 'I'm Fine' Alternative Listener",
        "sound",
        ["Alternative rock, emo, shoegaze, post-hardcore, melancholic indie, cathartic, dramatic, or nostalgic traits."],
        "Your music taste says 'I'm fine' in the same tone people use before staring out a window for 40 minutes.",
        "Your taste sits around emotionally charged alternative music. It blends melody, intensity, atmosphere and catharsis.",
        5,
        lambda s: (weighted(cluster(s, "Alternative / Indie Rock") * 2.2, cluster(s, "Emo / Pop Punk / Post-Hardcore") * 2, 18 if has_any(s["traits"], ["cathartic", "dramatic", "nostalgic", "melancholic"]) else 0), ["Emotionally charged alternative"]),
    ),
    make_definition(
        "old_soul_aux_cable",
        "The Old-Soul Aux Cable",
        "era",
        ["High nostalgia score, older release years, classic rock, old pop, jazz, soul, or era-shaped listening."],
        "You treat modern music like it personally failed a vibe check.",
        "Your listening is strongly era-shaped. Older music carries the emotional and stylistic centre of your profile.",
        14,
        lambda s: (weighted(s["scores"]["nostalgia"] * 0.8, 15 if has_any(s["canonical"], ["classic", "jazz", "soul", "britpop"]) else 0), ["Era-shaped listening"]),
    ),
    make_definition(
        "algorithm_escapee",
        "The Algorithm Escapee",
        "sound",
        ["High niche score, high discovery, low mainstream estimate, many uncommon artists, and low repetition."],
        "The algorithm keeps recommending normal songs and you keep escaping into the woods.",
        "Your taste is curiosity-led and less attached to mainstream popularity. You seem to enjoy finding music outside the obvious centre.",
        15,
        lambda s: (weighted(s["scores"]["mainstream_niche"] * 0.45, s["scores"]["discovery"] * 0.4, max(0, 45 - s["scores"]["repeat"]) * 0.25), ["Niche/discovery signal"]),
    ),
    make_definition(
        "soft_pop_emotional_support",
        "The Soft Pop Emotional Support Human",
        "sound",
        ["Pop, indie pop, bedroom pop, soft rock, acoustic pop, melodic, romantic, nostalgic traits, and medium repeat."],
        "Your playlists are basically emotional support blankets with choruses.",
        "Your taste values melody, warmth and emotional accessibility. You like songs that feel easy to live with but still personally meaningful.",
        21,
        lambda s: (weighted(cluster(s, "Pop / Pop Rock Crossover") * 2.4, 18 if has_any(s["traits"], ["melodic", "romantic", "nostalgic", "soft"]) else 0, max(0, 70 - abs(s["scores"]["repeat"] - 45)) * 0.2), ["Melodic pop crossover"]),
    ),
    make_definition(
        "heavy_but_melodic_negotiator",
        "The Heavy-but-Melodic Negotiator",
        "sound",
        ["Bring Me The Horizon, Deftones, Linkin Park-style artists, alternative metal, metalcore, electronic rock, heavy plus melodic traits."],
        "You want the guitars heavy, the chorus huge, and the breakdown emotionally well-formatted.",
        "Your taste balances heaviness with melody. You like intensity, but not at the cost of hooks, atmosphere and emotional readability.",
        1,
        lambda s: (weighted(cluster(s, "Heavy Alternative / Metalcore") * 3.2, cluster(s, "Alternative / Indie Rock") * 1.2, 18 if artist_hit(s, ["Bring Me The Horizon", "Deftones", "Linkin Park"]) else 0, 16 if has_any(s["traits"], ["melodic", "polished heavy production", "anthemic"]) else 0), ["Heavy alt signal", "Melodic/polished traits"]),
    ),
    make_definition(
        "not_just_a_phase_listener",
        "The 'I Swear It's Not Just a Phase' Listener",
        "era",
        ["Emo, pop-punk, alt-rock, nostalgic 2000s/2010s music, repeat-heavy behaviour, and stable long-term artists."],
        "The phase did not end. It got better headphones.",
        "Your profile has strong continuity. Certain emotional sounds and artists have stayed with you rather than disappearing after a trend.",
        8,
        lambda s: (weighted(cluster(s, "Emo / Pop Punk / Post-Hardcore") * 2.8, s["scores"]["repeat"] * 0.35, s["scores"]["nostalgia"] * 0.25, 14 if artist_hit(s, ["My Chemical Romance", "Paramore", "Green Day", "Blink-182"]) else 0), ["Long-running emo/alt continuity"]),
    ),
]
