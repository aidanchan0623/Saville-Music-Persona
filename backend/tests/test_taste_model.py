from __future__ import annotations

from datetime import date

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.analysis.taste_model import build_taste_model, profile_for_artist
from app.config import Settings
from app.data.artist_genres import clusters_for_genres
from app.services.recommendations import generate_recommendations
from app.services.ollama_service import OllamaService


def test_curated_artist_mapping_overrides_weak_metadata() -> None:
    profile = profile_for_artist("Bring Me The Horizon")
    assert profile["confidence"] == "high"
    assert "metalcore" in profile["canonical_genres"]
    assert "post-hardcore" in profile["canonical_genres"]
    assert "r&b / soul" not in profile["canonical_genres"]


def test_artist_genre_fallback_remains_low_confidence() -> None:
    profile = profile_for_artist("Totally Unknown Local Artist")
    assert profile["confidence"] == "low"
    assert profile["display_genres"] == []
    assert profile["confidence_label"] == "Unavailable / low-confidence"


def test_canonical_genres_map_to_broad_clusters() -> None:
    clusters = clusters_for_genres(["emo", "metalcore", "film score"])
    assert "Emo / Pop Punk / Post-Hardcore" in clusters
    assert "Heavy Alternative / Metalcore" in clusters
    assert "Cinematic / Soundtrack" in clusters


def test_weighted_cluster_calculation_and_layers() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": f"bmth-{index}", "title": f"BMTH {index}", "artists": [{"name": "Bring Me The Horizon"}], "played": "2026-07-01"}
                for index in range(10)
            ]
            + [
                {"videoId": f"mcr-{index}", "title": f"MCR {index}", "artists": [{"name": "My Chemical Romance"}], "played": "2026-07-01"}
                for index in range(6)
            ]
            + [
                {"videoId": f"zimmer-{index}", "title": f"Score {index}", "artists": [{"name": "Hans Zimmer"}], "played": "2026-07-01"}
                for index in range(2)
            ]
        },
        today=date(2026, 7, 7),
    )
    analysis = build_analysis(normalised)
    taste = analysis["overview"]["taste_interpretation"]
    core_names = {item["name"] for item in taste["core_genre_families"]}
    side_names = {item["name"] for item in taste["side_quests"]}
    assert "Emo / Pop Punk / Post-Hardcore" in core_names
    assert "Alternative / Indie Rock" in core_names
    assert "Cinematic / Soundtrack" in side_names
    assert taste["coverage"]["curated_artist_coverage_percent"] == 100


def test_genre_diversity_uses_broad_clusters_and_within_cluster_categories() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": "a", "title": "A", "artists": [{"name": "Bring Me The Horizon"}], "played": "2026-07-01"},
                {"videoId": "b", "title": "B", "artists": [{"name": "My Chemical Romance"}], "played": "2026-07-01"},
                {"videoId": "c", "title": "C", "artists": [{"name": "Wisp"}], "played": "2026-07-01"},
                {"videoId": "d", "title": "D", "artists": [{"name": "Oasis"}], "played": "2026-07-01"},
            ]
        },
        today=date(2026, 7, 7),
    )
    analysis = build_analysis(normalised)
    broad = next(score for score in analysis["scores"] if score["key"] == "broad_cluster_diversity")
    within = next(score for score in analysis["scores"] if score["key"] == "within_cluster_diversity")
    assert broad["inputs"]["top_clusters"]
    assert within["inputs"]["top_canonical_genres"]
    assert broad["label"] != "single-lane"


def test_no_incorrect_artist_tags_when_data_absent() -> None:
    normalised = normalise_collection(
        {"history": [{"videoId": "x", "title": "Mystery", "artists": [{"name": "Unknown Test Artist"}], "played": "2026-07-01"}]},
        today=date(2026, 7, 7),
    )
    analysis = build_analysis(normalised)
    artist = analysis["top_artists"][0]
    assert artist["related_genres"] == ["Genre data unavailable"]
    assert artist["genre_confidence"] == "low"


def test_ai_prompt_receives_structured_interpretation_data() -> None:
    normalised = normalise_collection(
        {"history": [{"videoId": "a", "title": "Drown", "artists": [{"name": "Bring Me The Horizon"}], "played": "2026-07-01"}]},
        today=date(2026, 7, 7),
    )
    analysis = build_analysis(normalised)
    evidence = {
        "personality": {"id": "forming", "title": analysis["report_profile"]["headline_persona"]},
        "strongestSignals": analysis["report_profile"].get("mood_profile", []),
        "knownArtists": [item["artist"] for item in analysis["top_artists"]],
        "knownGenres": analysis["report_profile"].get("genre_profile", []),
    }
    prompt = OllamaService(Settings())._build_persona_language_prompt(evidence, "serious")
    assert "CALCULATED_EVIDENCE_JSON" in prompt
    assert "knownArtists" in prompt
    assert "Analytics already chose every fact" in prompt
    assert "r&b / soul" not in prompt


def test_recommendations_use_new_taste_groups_and_connections() -> None:
    normalised = normalise_collection(
        {"history": [{"videoId": "a", "title": "Drown", "artists": [{"name": "Bring Me The Horizon"}], "played": "2026-07-01"}]},
        today=date(2026, 7, 7),
    )
    analysis = build_analysis(normalised)
    recommendations = generate_recommendations(
        normalised,
        analysis,
        [
            {"videoId": "new1", "title": "New MCR Song", "artists": [{"name": "My Chemical Romance"}], "recommendation_source": "related artist"},
            {"videoId": "new2", "title": "New Zimmer Cue", "artists": [{"name": "Hans Zimmer"}], "recommendation_source": "soundtrack bridge"},
        ],
    )
    assert {item["recommendation_group"] for item in recommendations} <= {"Safe bets", "One step sideways", "Worth the risk"}
    assert all(item["musical_connection"] for item in recommendations)
