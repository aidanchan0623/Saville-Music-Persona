from __future__ import annotations

from datetime import date, timedelta

from app.analysis.musical_age import (
    AGE_MAX,
    AGE_MIN,
    age_from_factor_scores,
    calculate_musical_age,
    category_for_age,
)
from app.analysis.overview import apply_overview_language, build_overview_response, overview_language_evidence, overview_language_fingerprint
from app.analysis.overview_identity import compose_identity, deterministic_identity, validate_identity_language


TODAY = date(2026, 7, 22)


def test_musical_age_is_deterministic_and_bounded() -> None:
    normalised = _stable_cross_era_profile()
    first = calculate_musical_age(normalised, today=TODAY)
    second = calculate_musical_age(normalised, today=TODAY)
    assert first == second
    assert AGE_MIN <= first["age"] <= AGE_MAX
    assert all(0 <= value <= 100 for value in first["factors"].values())


def test_minimum_middle_and_maximum_factor_profiles() -> None:
    minimum = {
        "tasteStability": 0,
        "catalogMaturity": 0,
        "albumDepth": 0,
        "discovery": 100,
        "crossEraBreadth": 0,
        "reflectiveListening": 0,
        "longTermArtistLoyalty": 0,
        "emotionalIntensity": 0,
    }
    middle = {key: 50 for key in minimum}
    maximum = {**{key: 100 for key in minimum}, "discovery": 0, "emotionalIntensity": 0}
    assert age_from_factor_scores(minimum) == AGE_MIN
    assert AGE_MIN < age_from_factor_scores(middle) < AGE_MAX
    assert age_from_factor_scores(maximum) == AGE_MAX


def test_category_boundaries() -> None:
    assert category_for_age(14) == "The Mood Mirror"
    assert category_for_age(15) == "The Catharsis Engine"
    assert category_for_age(21) == "The Identity Explorer"
    assert category_for_age(22) == "The Self-Aware Regulator"
    assert category_for_age(27) == "The Curated Balancer"
    assert category_for_age(35) == "The Reflective Curator"
    assert category_for_age(50) == "The Meaning Keeper"
    assert category_for_age(65) == "The Timeless Integrator"


def test_missing_release_metadata_reduces_confidence_without_becoming_year_zero() -> None:
    complete = _stable_cross_era_profile(include_years=True)
    incomplete = _stable_cross_era_profile(include_years=False)
    complete_result = calculate_musical_age(complete, today=TODAY)
    incomplete_result = calculate_musical_age(incomplete, today=TODAY)
    assert incomplete_result["metadataCoverage"]["releaseYearPercent"] == 0
    assert incomplete_result["factors"]["catalogMaturity"] == 50
    assert incomplete_result["confidence"] < complete_result["confidence"]
    assert incomplete_result["likelyMax"] - incomplete_result["likelyMin"] >= complete_result["likelyMax"] - complete_result["likelyMin"]


def test_low_play_count_has_limited_confidence_and_wide_range() -> None:
    normalised = _normalised(
        tracks=[_track("one", "Only Song", "Wisp", "One Album", 2025, ["atmospheric"])],
        events=[_event("one", TODAY)],
    )
    result = calculate_musical_age(normalised, today=TODAY)
    assert result["confidenceLabel"] == "Limited confidence"
    assert result["likelyMax"] - result["likelyMin"] >= 12


def test_high_repeat_intensity_and_high_discovery_profiles_remain_distinct() -> None:
    repeat_profile = _repeat_intensity_profile()
    discovery_profile = _high_discovery_profile()
    repeat_result = calculate_musical_age(repeat_profile, today=TODAY)
    discovery_result = calculate_musical_age(discovery_profile, today=TODAY)
    assert repeat_result["factors"]["repeatAttachment"] > discovery_result["factors"]["repeatAttachment"]
    assert repeat_result["factors"]["emotionalIntensity"] > 50
    assert discovery_result["factors"]["discovery"] > repeat_result["factors"]["discovery"]


def test_overview_top_five_uses_selected_period_and_has_no_duplicates() -> None:
    normalised = _stable_cross_era_profile()
    response = build_overview_response(normalised, "month", "2026-07", today=TODAY)
    assert response["schemaVersion"] == 3
    assert response["selectedPeriod"]["label"] == "July 2026"
    assert response["topFive"]["period"] == response["selectedPeriod"]
    songs = response["topFive"]["songs"]
    artists = response["topFive"]["artists"]
    assert len({(item["title"], item["artist"]) for item in songs}) == len(songs)
    assert len({item["name"] for item in artists}) == len(artists)
    assert all(item["detectedPlays"] > 0 for item in songs + artists)


def test_period_labels_are_human_readable() -> None:
    response = build_overview_response(_stable_cross_era_profile(), "rolling_year", today=TODAY)
    assert response["selectedPeriod"]["label"].startswith("Rolling year")
    assert "2025" in response["selectedPeriod"]["label"]
    assert "2026" in response["selectedPeriod"]["label"]


def test_fallback_identity_is_composed_and_gemma_output_is_validated() -> None:
    evidence = {
        "topGenre": "Alternative / Indie Rock",
        "sonicTraits": ["cathartic", "atmospheric"],
        "repeatAttachment": 82,
        "discovery": 25,
        "tasteStability": 72,
        "albumDepth": 66,
        "emotionalIntensity": 80,
        "reflectiveListening": 55,
        "topArtists": ["Known Artist"],
    }
    fallback = deterministic_identity(evidence)
    assert fallback["characterTitle"] == "The Cathartic Album Repeater"
    assert not fallback["characterTitle"].startswith("The Alternative")
    valid = {
        "characterTitle": "The Cathartic Night-Drive Loyalist",
        "tagline": "You keep trusted choruses close without closing the door on atmosphere.",
        "explanation": "Cathartic texture and repeat gravity shape a focused soundtrack. Discovery still adds a smaller current around the centre.",
    }
    assert validate_identity_language(valid, evidence) == valid
    composed = compose_identity(evidence, valid, "gemma")
    assert composed["generationSource"] == "gemma"
    invalid = {**valid, "characterTitle": "The Alternative Rock Listener"}
    assert validate_identity_language(invalid, evidence) is None
    invented = {**valid, "explanation": "Imaginary Artist controls the entire story."}
    assert validate_identity_language(invented, evidence) is None


def test_overview_language_is_applied_without_changing_calculated_facts() -> None:
    response = build_overview_response(_stable_cross_era_profile(), "rolling_year", today=TODAY)
    original_age = response["musicalAge"]["age"]
    original_top_five = response["topFive"]
    language = {
        "identity": {
            "characterTitle": "The Reflective Soundtrack Curator",
            "tagline": "You keep a stable centre while letting atmosphere widen the edges.",
            "explanation": "Repeat gravity gives the profile continuity. Discovery still moves around that centre without replacing it.",
        },
        "musicalAge": {
            "summary": "A settled centre with enough curiosity to keep the rotation moving.",
            "explanation": "Long-running favourites provide continuity while discovery keeps the wider library active.",
        },
    }
    updated = apply_overview_language(response, language, "gemma")
    assert updated["identity"]["characterTitle"] == language["identity"]["characterTitle"]
    assert updated["identity"]["generationSource"] == "gemma"
    assert updated["musicalAge"]["age"] == original_age
    assert updated["topFive"] == original_top_five


def test_overview_language_cache_changes_with_period_and_source() -> None:
    normalised = _stable_cross_era_profile()
    rolling = build_overview_response(normalised, "rolling_year", today=TODAY)
    monthly = build_overview_response(normalised, "month", "2026-07", today=TODAY)
    rolling_evidence = overview_language_evidence(rolling)
    monthly_evidence = overview_language_evidence(monthly)
    youtube = overview_language_fingerprint(rolling_evidence, "youtube", "gemma3:4b")
    spotify = overview_language_fingerprint(rolling_evidence, "spotify", "gemma3:4b")
    assert youtube != spotify
    assert youtube != overview_language_fingerprint(monthly_evidence, "youtube", "gemma3:4b")


def _stable_cross_era_profile(include_years: bool = True) -> dict:
    artists = ["Oasis", "Radiohead", "Hans Zimmer", "Bring Me The Horizon"]
    years = [1995, 2001, 2014, 2025]
    tracks = []
    for artist_index, artist in enumerate(artists):
        for track_index in range(4):
            tracks.append(
                _track(
                    f"stable-{artist_index}-{track_index}",
                    f"Stable {artist_index}-{track_index}",
                    artist,
                    f"Album {artist_index}",
                    years[artist_index] if include_years else None,
                    ["atmospheric", "cinematic"] if artist == "Hans Zimmer" else ["anthemic"],
                )
            )
    events = []
    for index in range(240):
        track = tracks[index % len(tracks)]
        day = TODAY - timedelta(days=330 - (index * 330 // 239))
        events.append(_event(track["track_id"], day))
    return _normalised(tracks, events)


def _repeat_intensity_profile() -> dict:
    tracks = [
        _track("repeat-a", "Repeat A", "Bring Me The Horizon", "Catharsis", 2024, ["cathartic", "metalcore", "high-energy"]),
        _track("repeat-b", "Repeat B", "Bring Me The Horizon", "Catharsis", 2024, ["dramatic", "post-hardcore"]),
    ]
    events = [_event("repeat-a" if index % 5 else "repeat-b", TODAY - timedelta(days=index % 120)) for index in range(240)]
    return _normalised(tracks, events)


def _high_discovery_profile() -> dict:
    tracks = [
        _track(f"new-{index}", f"New Song {index}", f"Artist {index}", f"Album {index}", 2026, ["melodic"])
        for index in range(100)
    ]
    events = [_event(track["track_id"], TODAY - timedelta(days=99 - index)) for index, track in enumerate(tracks)]
    return _normalised(tracks, events)


def _track(track_id: str, title: str, artist: str, album: str, year: int | None, traits: list[str]) -> dict:
    return {
        "track_id": track_id,
        "title": title,
        "primary_artist": artist,
        "artists": [artist],
        "album": album,
        "release_year": year,
        "sonic_traits": traits,
        "genre_clusters": traits,
    }


def _event(track_id: str, day: date) -> dict:
    return {
        "track_id": track_id,
        "played_at": day.isoformat(),
        "duration_seconds": 210,
        "is_music_candidate": True,
    }


def _normalised(tracks: list[dict], events: list[dict]) -> dict:
    return {
        "tracks": tracks,
        "play_events": events,
        "artist_metadata": {},
        "coverage": {
            "date_data_available": bool(events),
            "days_represented": len({event["played_at"] for event in events}),
            "earliest_detected_play": min((event["played_at"] for event in events), default=None),
            "latest_detected_play": max((event["played_at"] for event in events), default=None),
        },
        "metadata": {"source": "youtube"},
    }
