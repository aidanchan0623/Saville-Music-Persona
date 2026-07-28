from __future__ import annotations

from datetime import date

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.analysis.taste_model import build_taste_model, profile_for_artist
from app.config import Settings
from app.data.artist_genres import clusters_for_genres, normalise_artist_name
from app.services.recommendations import generate_recommendations
from app.services.ollama_service import OllamaService


def test_curated_artist_mapping_overrides_weak_metadata() -> None:
    profile = profile_for_artist("Bring Me The Horizon", ["rap"])
    assert profile["confidence"] == "high"
    assert "metalcore" in profile["canonical_genres"]
    assert "post-hardcore" in profile["canonical_genres"]
    assert "r&b / soul" not in profile["canonical_genres"]
    assert "rap" not in profile["canonical_genres"]


def test_normalised_alias_unicode_and_topic_names_match_curated_profiles() -> None:
    assert profile_for_artist("Blink 182")["is_curated"] is True
    assert profile_for_artist("Bring Me The Horizon - Topic")["is_curated"] is True
    assert profile_for_artist("Noel Gallagher’s High Flying Birds")["is_curated"] is True
    assert normalise_artist_name("  Bring Me The Horizon — Topic  ") == "bring me the horizon"


def test_artist_genre_fallback_remains_low_confidence() -> None:
    profile = profile_for_artist("Totally Unknown Local Artist")
    assert profile["confidence"] == "low"
    assert profile["display_genres"] == []
    assert profile["confidence_label"] == "Unavailable / low-confidence"


def test_trusted_source_genres_are_used_only_when_they_map_to_known_clusters() -> None:
    profile = profile_for_artist("Unmapped Artist", ["indie rock"])
    assert profile["confidence"] == "medium"
    assert "Alternative / Indie Rock" in profile["broad_clusters"]
    unknown = profile_for_artist("Still Unmapped", ["made-up genre"])
    assert unknown["confidence"] == "low"


def test_regional_and_non_cluster_source_genres_are_retained_when_normalised() -> None:
    profile = profile_for_artist("Unmapped regional artist", ["korean pop", "mandarin pop"])
    assert profile["confidence"] == "medium"
    assert profile["canonical_genres"] == ["K-pop", "Mandopop"]


def test_regional_pop_remains_visible_in_broad_report_clusters() -> None:
    gem = profile_for_artist("G.E.M.")

    assert "Mandopop / C-pop" in gem["broad_clusters"]
    assert "Pop / Pop Rock Crossover" not in gem["broad_clusters"]
    assert "R&B / Soul / Funk" in gem["broad_clusters"]


def test_verified_regional_aliases_keep_distinct_genres() -> None:
    nick = profile_for_artist("周湯豪 NICKTHEREAL")
    skai = profile_for_artist("攬佬SKAI ISYOURGOD")
    mayday = profile_for_artist("五月天 (Mayday)")

    assert "mandopop" in nick["canonical_genres"]
    assert "Mandopop / C-pop" in nick["broad_clusters"]
    assert "hip-hop" in skai["canonical_genres"]
    assert "mandopop" not in skai["canonical_genres"]
    assert "mandopop" in mayday["canonical_genres"]


def test_spotify_track_genres_reach_event_weighted_taste_classification() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {
                    "source": "spotify",
                    "source_track_id": "spotify:track:one",
                    "title": "Source Track",
                    "artists": [{"name": "Unmapped Spotify Artist", "genres": ["indie rock"]}],
                    "played": "2026-07-01",
                }
            ]
        },
        today=date(2026, 7, 7),
    )
    assert normalised["tracks"][0]["primary_artist_genres"] == ["indie rock"]
    taste = build_analysis(normalised)["overview"]["taste_interpretation"]
    assert taste["coverage"]["sourceGenreEventCount"] == 1
    assert taste["coverage"]["genreCoveragePercent"] == 100


def test_unstructured_band_names_are_not_split_on_ampersands_or_commas() -> None:
    normalised = normalise_collection(
        {"history": [{"videoId": "band", "title": "Song", "artist": "Earth, Wind & Fire", "played": "2026-07-01"}]},
        today=date(2026, 7, 7),
    )
    assert normalised["tracks"][0]["artists"] == ["Earth, Wind & Fire"]


def test_canonical_genres_map_to_broad_clusters() -> None:
    clusters = clusters_for_genres(["emo", "metalcore", "film score"])
    assert "Emo / Pop Punk / Post-Hardcore" in clusters
    assert "Heavy Alternative / Metalcore" in clusters
    assert "Cinematic / Soundtrack" in clusters
    expanded = clusters_for_genres(["vaporwave", "neo-soul", "classical", "country", "classic rock", "reggaeton"])
    assert "Electronic / Atmospheric" in expanded
    assert "R&B / Soul / Funk" in expanded
    assert "Jazz / Classical" in expanded
    assert "Folk / Country / Acoustic" in expanded
    assert "Rock / Classic Rock" in expanded
    assert "Latin / Reggaeton" in expanded


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


def test_unknown_artists_remain_in_event_weighted_coverage_and_diagnostics() -> None:
    history = [
        {"videoId": f"unknown-{index}", "title": f"Unknown {index}", "artists": [{"name": "Unknown Local Act"}], "played": "2026-07-01"}
        for index in range(3)
    ] + [
        {"videoId": f"other-{index}", "title": f"Other {index}", "artists": [{"name": "Another Unknown Act"}], "played": "2026-07-01"}
        for index in range(2)
    ] + [{"videoId": "known", "title": "Known", "artists": [{"name": "Oasis"}], "played": "2026-07-01"}]
    normalised = normalise_collection({"history": history}, today=date(2026, 7, 7))
    coverage = build_analysis(normalised)["overview"]["taste_interpretation"]["coverage"]
    assert coverage["totalEventCount"] == 6
    assert coverage["classifiedEventCount"] == 1
    assert coverage["unknownEventCount"] == 5
    assert coverage["genreCoveragePercent"] == 16.7
    assert coverage["unknown_artist_coverage_percent"] == 83.3
    assert coverage["genreCoveragePercent"] + coverage["unknown_artist_coverage_percent"] == 100
    assert coverage["topUnknownArtists"][:2] == [
        {"artist": "Unknown Local Act", "playCount": 3, "playShare": 50.0},
        {"artist": "Another Unknown Act", "playCount": 2, "playShare": 33.33},
    ]


def test_youtube_without_genre_metadata_stays_honestly_unknown() -> None:
    normalised = normalise_collection(
        {"history": [{"videoId": "yt", "title": "Song", "artists": [{"name": "Genuinely Unknown YouTube Artist"}], "played": "2026-07-01"}]},
        today=date(2026, 7, 7),
    )
    coverage = build_analysis(normalised)["overview"]["taste_interpretation"]["coverage"]
    assert coverage["sourceGenreEventCount"] == 0
    assert coverage["unknownEventCount"] == 1
    assert coverage["genreCoveragePercent"] == 0


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
