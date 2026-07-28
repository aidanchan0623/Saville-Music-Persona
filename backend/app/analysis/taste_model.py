from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from app.analysis.normalizer import UNKNOWN_ARTIST
from app.data.artist_genres import (
    ArtistGenreProfile,
    clusters_for_genres,
    get_curated_artist_profile,
    get_exact_curated_artist_profile,
    normalise_artist_name,
    normalise_genre,
)


CORE_THRESHOLD = 6.0
SECONDARY_THRESHOLD = 4.0
SIDE_THRESHOLD = 1.0


def profile_for_artist(artist: str, source_genres: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    curated = get_exact_curated_artist_profile(artist)
    if curated:
        return profile_payload(curated)
    trusted_genres = list(dict.fromkeys(normalised[1] for genre in (source_genres or []) if str(genre).strip() for normalised in [normalise_genre(str(genre))] if normalised))
    source_clusters = clusters_for_genres(trusted_genres)
    if trusted_genres:
        return {
            "canonical_genres": trusted_genres,
            "broad_clusters": source_clusters,
            "sonic_traits": [],
            "confidence": "medium",
            "confidence_label": "Medium - source-provided genres",
            "source": "trusted source genre metadata",
            "display_genres": trusted_genres,
            "taste_role_hint": None,
            "is_curated": False,
        }
    curated = get_curated_artist_profile(artist)
    if curated:
        return profile_payload(curated)
    return {
        "canonical_genres": [],
        "broad_clusters": [],
        "sonic_traits": [],
        "confidence": "low",
        "confidence_label": "Unavailable / low-confidence",
        "source": "unavailable genre metadata",
        "display_genres": [],
        "is_curated": False,
    }


def source_genres_for_artist(
    track: dict[str, Any],
    artist_metadata: dict[str, dict[str, Any]] | None,
    artist: str,
) -> list[str]:
    target = normalise_artist_name(artist)
    collected: list[str] = []

    def add_genres(genres: Any) -> None:
        if not isinstance(genres, (list, tuple)):
            return
        for genre in genres:
            value = str(genre).strip()
            if value and value not in collected:
                collected.append(value)

    track_genres = track.get("artist_genres") or {}
    if isinstance(track_genres, dict):
        for name, genres in track_genres.items():
            if normalise_artist_name(str(name)) == target:
                add_genres(genres)
    if normalise_artist_name(str(track.get("primary_artist") or "")) == target:
        add_genres(track.get("primary_artist_genres") or [])
        # Recording-level evidence is a supplemental fallback. It is attached
        # only after identity, evidence and taxonomy confidence clear the
        # automatic-application threshold in the durable recording catalog.
        add_genres(track.get("recording_genres") or [])
    metadata = (artist_metadata or {}).get(target)
    if isinstance(metadata, dict):
        add_genres(metadata.get("genres") or [])
    else:
        # Callers outside the hot aggregation path may pass display-name keys.
        for name, candidate in (artist_metadata or {}).items():
            if normalise_artist_name(str(name)) == target and isinstance(candidate, dict):
                add_genres(candidate.get("genres") or [])
    return collected


def has_usable_artist(artist: Any) -> bool:
    value = str(artist or "").strip()
    return bool(value and normalise_artist_name(value) not in {"unknown artist", "unknown", "unavailable artist", normalise_artist_name(UNKNOWN_ARTIST)})


def profile_payload(profile: ArtistGenreProfile) -> dict[str, Any]:
    derived_clusters = clusters_for_genres(profile.canonical_genres)
    regional_keys = {
        "malay / nusantara pop", "malay / nusantara rock & indie", "dangdut",
        "mandopop", "c-pop", "cantopop", "k-pop", "j-pop", "j-rock",
        "j-pop / j-rock", "tamil / indian film & pop",
    }
    has_regional_genre = any(
        " ".join(str(genre).casefold().split()) in regional_keys
        for genre in profile.canonical_genres
    )
    return {
        "canonical_genres": list(profile.canonical_genres),
        # Re-project curated genres through the current taxonomy so older
        # hand-written clusters cannot hide regional genres under generic Pop.
        "broad_clusters": list(derived_clusters if has_regional_genre and derived_clusters else profile.broad_clusters or derived_clusters),
        "sonic_traits": list(profile.sonic_traits),
        "confidence": profile.confidence,
        "confidence_label": "High - curated genre mapping" if profile.confidence == "high" else profile.confidence.title(),
        "source": profile.source,
        "display_genres": list(profile.canonical_genres) if profile.confidence in {"high", "medium"} else [],
        "taste_role_hint": profile.taste_role_hint,
        "is_curated": profile.confidence == "high",
    }


def artist_taste_role(share: float, profile: dict[str, Any]) -> str:
    hint = profile.get("taste_role_hint")
    if share >= 6:
        return hint or "Core influence"
    if share >= 2:
        return hint or "Secondary influence"
    if share >= 0.75:
        return hint or "Distinctive side interest"
    return "Light trace"


def artist_why_it_matters(artist: str, share: float, profile: dict[str, Any]) -> str:
    genres = profile.get("display_genres") or []
    traits = profile.get("sonic_traits") or []
    if not genres:
        return "Genre profile is unavailable, so this artist is counted in play totals without adding speculative genre claims."
    genre_text = ", ".join(genres[:3])
    trait_text = ", ".join(traits[:3]) if traits else "its strongest mapped traits"
    return f"{artist} contributes {share:.1f}% of detected plays and brings {genre_text} into the profile, adding {trait_text}."


def weighted_cluster_counts(events: list[dict[str, Any]], tracks_by_id: dict[str, dict[str, Any]], artist_metadata: dict[str, dict[str, Any]] | None = None) -> tuple[Counter[str], Counter[str], Counter[str], Counter[str], Counter[str], int, Counter[str]]:
    cluster_counts: Counter[str] = Counter()
    genre_counts: Counter[str] = Counter()
    trait_counts: Counter[str] = Counter()
    coverage_counts: Counter[str] = Counter()
    unknown_artists: Counter[str] = Counter()
    invalid_artist_events = 0
    unmatched_variants: Counter[str] = Counter()
    # This function is called for every dashboard/report projection.  The
    # metadata is static for a period, so normalising and scanning it for every
    # listening event was the dominant report-generation cost on large Takeout
    # profiles.
    metadata_by_artist = {
        normalise_artist_name(str(name)): value
        for name, value in (artist_metadata or {}).items()
        if isinstance(value, dict)
    }
    source_genre_cache: dict[tuple[str, str], tuple[str, ...]] = {}
    profile_cache: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for event in events:
        track = tracks_by_id.get(event["track_id"], {})
        artist = track.get("primary_artist", event.get("primary_artist", "Unknown Artist"))
        if not has_usable_artist(artist):
            invalid_artist_events += 1
            continue
        artist_key = normalise_artist_name(str(artist))
        track_key = str(track.get("track_id") or event.get("track_id") or "")
        cache_key = (track_key, artist_key)
        source_genres = source_genre_cache.get(cache_key)
        if source_genres is None:
            source_genres = tuple(source_genres_for_artist(track, metadata_by_artist, str(artist)))
            source_genre_cache[cache_key] = source_genres
        profile_key = (artist_key, source_genres)
        profile = profile_cache.get(profile_key)
        if profile is None:
            profile = profile_for_artist(artist, source_genres)
            profile_cache[profile_key] = profile
        if profile["is_curated"]:
            coverage_counts["curated"] += 1
        elif profile["canonical_genres"]:
            coverage_counts["inferred"] += 1
        else:
            coverage_counts["unknown"] += 1
            unknown_artists[artist] += 1
            normalised = normalise_artist_name(str(artist))
            simple = " ".join(str(artist).strip().casefold().split())
            if normalised != simple:
                unmatched_variants[f"{artist} -> {normalised}"] += 1
        clusters = profile.get("broad_clusters") or []
        genres = profile.get("canonical_genres") or []
        traits = profile.get("sonic_traits") or []
        if clusters:
            weight = 1 / len(clusters)
            for cluster in clusters:
                cluster_counts[cluster] += weight
        if genres:
            weight = 1 / len(genres)
            for genre in genres:
                genre_counts[genre] += weight
        for trait in traits:
            trait_counts[trait] += 1
    return cluster_counts, genre_counts, trait_counts, coverage_counts, unknown_artists, invalid_artist_events, unmatched_variants


def rounded_share(count: float, total: int) -> float:
    return round(count / total * 100, 1) if total else 0.0


def cluster_items(cluster_counts: Counter[str], total: int) -> list[dict[str, Any]]:
    return [
        {"name": name, "share": rounded_share(count, total), "value": rounded_share(count, total), "play_weight": round(count, 1)}
        for name, count in cluster_counts.most_common()
        if rounded_share(count, total) >= 0.5
    ]


def classify_clusters(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    core = [item for item in items if item["share"] >= CORE_THRESHOLD]
    secondary = [item for item in items if SECONDARY_THRESHOLD <= item["share"] < CORE_THRESHOLD and item["name"] != "Cinematic / Soundtrack"]
    side = [item for item in items if SIDE_THRESHOLD <= item["share"] < SECONDARY_THRESHOLD or (item["name"] == "Cinematic / Soundtrack" and item["share"] < CORE_THRESHOLD)]
    if not core and items:
        core = items[:1]
        secondary = [item for item in items[1:] if item["share"] >= SECONDARY_THRESHOLD]
    return {"core": core[:4], "secondary": secondary[:5], "side_quests": side[:5]}


def entropy_score(items: list[float]) -> float:
    usable = [item for item in items if item > 0]
    if len(usable) <= 1:
        return 0.0
    total = sum(usable)
    entropy = -sum((item / total) * math.log(item / total) for item in usable)
    return round(entropy / math.log(len(usable)) * 100, 1)


def diversity_label(broad_score: float, within_score: float, top_cluster: str | None) -> str:
    if top_cluster and "Rock" in top_cluster and within_score >= 45:
        return "Rock-centred, internally varied"
    if broad_score >= 70:
        return "Broadly varied"
    if broad_score >= 45:
        return "Several worlds, one clear centre"
    if within_score >= 45:
        return "Focused world, varied within it"
    return "Focused and confidence-aware"


def build_taste_model(normalised: dict[str, Any], artist_counts: Counter[str], total_plays: int) -> dict[str, Any]:
    tracks = normalised.get("tracks", [])
    events = normalised.get("play_events", [])
    tracks_by_id = {track["track_id"]: track for track in tracks}
    cluster_counts, genre_counts, trait_counts, coverage_counts, unknown_artists, invalid_artist_events, unmatched_variants = weighted_cluster_counts(events, tracks_by_id, normalised.get("artist_metadata"))
    coverage_total = sum(coverage_counts.values())
    clusters = cluster_items(cluster_counts, coverage_total)
    layers = classify_clusters(clusters)
    top_cluster = clusters[0]["name"] if clusters else None
    broad_score = entropy_score(list(cluster_counts.values()))
    within_score = entropy_score(list(genre_counts.values()))
    classified_count = coverage_counts["curated"] + coverage_counts["inferred"]
    genre_coverage = round(classified_count / coverage_total * 100, 1) if coverage_total else 0.0
    unknown_coverage = round(100 - genre_coverage, 1) if coverage_total else 0.0
    coverage = {
        "totalEventCount": len(events),
        "usableArtistEventCount": coverage_total,
        "invalidArtistEventCount": invalid_artist_events,
        "classifiedEventCount": classified_count,
        "curatedEventCount": coverage_counts["curated"],
        "sourceGenreEventCount": coverage_counts["inferred"],
        "unknownEventCount": coverage_counts["unknown"],
        "genreCoveragePercent": genre_coverage,
        "genre_coverage_percent": genre_coverage,
        "curated_artist_coverage_percent": round(coverage_counts["curated"] / coverage_total * 100, 1) if coverage_total else 0,
        "inferred_artist_coverage_percent": round(coverage_counts["inferred"] / coverage_total * 100, 1) if coverage_total else 0,
        "unknown_artist_coverage_percent": unknown_coverage,
        "topUnknownArtists": [{"artist": artist, "playCount": plays, "playShare": round(plays / coverage_total * 100, 2)} for artist, plays in unknown_artists.most_common(10)],
        "unmatchedNameVariants": [{"variant": variant, "playCount": plays} for variant, plays in unmatched_variants.most_common(10)],
    }
    traits = [trait for trait, _ in trait_counts.most_common(10)]
    core_names = [item["name"] for item in layers["core"][:4]]
    secondary_names = [item["name"] for item in layers["secondary"][:3]]
    summary = deterministic_summary(core_names, secondary_names, traits, coverage)
    evidence = evidence_lines(artist_counts, total_plays)
    return {
        "core_genre_families": layers["core"],
        "secondary_genre_families": layers["secondary"],
        "side_quests": layers["side_quests"],
        "cluster_shares": clusters,
        "canonical_genre_shares": [
            {"name": name, "share": rounded_share(count, coverage_total), "value": rounded_share(count, coverage_total)}
            for name, count in genre_counts.most_common(16)
        ],
        "sonic_traits": traits[:8],
        "listening_character": listening_character(normalised, artist_counts, total_plays),
        "evidence": evidence,
        "summary": summary,
        "coverage": coverage,
        "diversity": {
            "broad_cluster_score": broad_score,
            "within_cluster_score": within_score,
            "label": diversity_label(broad_score, within_score, top_cluster),
        },
        "taste_dna": build_taste_dna(layers, traits, normalised, artist_counts, total_plays),
    }


def deterministic_summary(core_names: list[str], secondary_names: list[str], traits: list[str], coverage: dict[str, float]) -> str:
    core = ", ".join(core_names) or "the reliably classified part of your library"
    secondary = ", ".join(secondary_names)
    trait_text = ", ".join(traits[:5]) or "clearly mapped sonic traits"
    sentence = f"Your listening centres on {core}, with a profile that sounds {trait_text}."
    if secondary:
        sentence += f" Secondary colour comes from {secondary}."
    if coverage.get("unknown_artist_coverage_percent", 0) > 30:
        sentence += " Smaller artists could not all be confidently classified, so the core pattern is stronger than the fine-grained tail."
    return sentence


def evidence_lines(artist_counts: Counter[str], total_plays: int) -> list[str]:
    lines = []
    for artist, count in artist_counts.most_common(8):
        profile = profile_for_artist(artist)
        if not profile.get("display_genres"):
            continue
        lines.append(f"{artist} contributes {round(count / total_plays * 100, 1) if total_plays else 0}% of detected plays")
    return lines[:6]


def listening_character(normalised: dict[str, Any], artist_counts: Counter[str], total_plays: int) -> list[str]:
    tracks = normalised.get("tracks", [])
    repeat_tracks = sum(1 for track in tracks if track.get("play_count_in_period", 0) >= 10)
    top5_share = sum(count for _, count in artist_counts.most_common(5)) / total_plays * 100 if total_plays else 0
    chars = []
    if top5_share >= 20:
        chars.append("artist-led")
    if repeat_tracks >= 20:
        chars.append("comfort-listening")
    chars.append("genre-loyal but not narrow")
    if normalised.get("coverage", {}).get("full_365_day_analysis"):
        chars.append("full-year evidence")
    return chars


def build_taste_dna(layers: dict[str, list[dict[str, Any]]], traits: list[str], normalised: dict[str, Any], artist_counts: Counter[str], total_plays: int) -> dict[str, Any]:
    top5_share = round(sum(count for _, count in artist_counts.most_common(5)) / total_plays * 100, 1) if total_plays else 0
    repeat_inputs = len({event["track_id"] for event in normalised.get("play_events", [])})
    total_events = len(normalised.get("play_events", []))
    repeat_share = round((1 - repeat_inputs / total_events) * 100, 1) if total_events else 0
    core_dna = []
    names = {item["name"] for item in layers.get("core", []) + layers.get("secondary", [])}
    if "Alternative / Indie Rock" in names:
        core_dna.append("Emotional Alternative")
    if "Emo / Pop Punk / Post-Hardcore" in names:
        core_dna.append("Cathartic Rock")
    if "Heavy Alternative / Metalcore" in names:
        core_dna.append("Heavy Pop Crossover")
    if any("shoegaze" in trait for trait in traits) or "atmospheric" in traits:
        core_dna.append("Shoegaze Atmosphere")
    if "Cinematic / Soundtrack" in names:
        core_dna.append("Cinematic Drama")
    return {
        "core_dna": core_dna[:5] or [item["name"] for item in layers.get("core", [])[:3]],
        "secondary_influences": [item["name"] for item in layers.get("secondary", [])[:4]],
        "sonic_traits": traits[:6],
        "era_preference": "Release-year metadata is limited; era preference is not asserted.",
        "artist_concentration": {"label": "artist-led" if top5_share >= 20 else "spread across many artists", "value": top5_share},
        "exploration_vs_comfort": {"label": "comfort-leaning" if repeat_share >= 45 else "exploratory with repeat anchors", "value": repeat_share},
    }


def enrich_artist(artist: dict[str, Any], total_plays: int, source_genres: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
    share = artist.get("share_of_listens") or ((artist.get("play_count", 0) / total_plays * 100) if total_plays else 0)
    profile = profile_for_artist(artist.get("artist", ""), source_genres)
    artist["genre_profile"] = profile
    artist["related_genres"] = profile["display_genres"] or ["Genre data unavailable"]
    artist["broad_clusters"] = profile.get("broad_clusters", [])
    artist["genre_confidence"] = profile["confidence"]
    artist["genre_confidence_label"] = profile["confidence_label"]
    artist["taste_role"] = artist_taste_role(float(share), profile)
    artist["why_it_matters"] = artist_why_it_matters(artist.get("artist", "This artist"), float(share), profile)
    return artist
