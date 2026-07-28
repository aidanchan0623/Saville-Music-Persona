from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.analysis.taste_model import profile_for_artist
from app.api import routes
from app.database.repository import JsonRepository
from app.services.genre_enrichment_service import (
    GENRE_METADATA_CACHE_VERSION,
    MusicBrainzGenreService,
    apply_genre_cache,
    ensure_genre_cache,
    seed_cache_from_source,
)


class FakeMusicBrainzGenreService(MusicBrainzGenreService):
    def __init__(self, responses: list[Any]) -> None:
        super().__init__(request_interval_seconds=0)
        self.responses = list(responses)

    def _get_json(self, _client: Any, _url: str, _params: dict[str, Any], _deadline: float) -> dict[str, Any]:
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def unknown_profile(artist: str = "LONOWN", plays: int = 3) -> dict[str, Any]:
    return normalise_collection(
        {
            "history": [
                {
                    "videoId": f"track-{index}",
                    "title": f"Track {index}",
                    "artists": [{"name": artist}],
                    "played": "2026-07-01",
                }
                for index in range(plays)
            ]
        },
        today=date(2026, 7, 7),
    )


def test_unique_exact_musicbrainz_match_applies_supported_genres() -> None:
    normalised = unknown_profile()
    service = FakeMusicBrainzGenreService(
        [
            {"artists": [{"id": "artist-id", "name": "LONOWN", "score": 100}]},
            {"genres": [{"name": "electronic", "count": 2}, {"name": "vaporwave", "count": 1}]},
        ]
    )
    cache, stats = service.enrich(normalised, None, limit=1, deadline=time.monotonic() + 10)
    assert stats["matched"] == 1
    assert stats["matchedEventCount"] == 3
    assert normalised["artist_metadata"]["LONOWN"]["genres"] == ["electronic", "vaporwave"]
    assert normalised["artist_metadata"]["LONOWN"]["genre_confidence"] == "medium"
    assert cache["items"]["lonown"]["providerArtistId"] == "artist-id"
    coverage = build_analysis(normalised)["overview"]["taste_interpretation"]["coverage"]
    assert coverage["sourceGenreEventCount"] == 3
    assert coverage["genreCoveragePercent"] == 100


def test_duplicate_exact_artist_names_are_rejected_as_ambiguous() -> None:
    normalised = unknown_profile("Same Name", 1)
    service = FakeMusicBrainzGenreService(
        [
            {
                "artists": [
                    {"id": "one", "name": "Same Name", "score": 100},
                    {"id": "two", "name": "Same Name", "score": 100},
                ]
            }
        ]
    )
    cache, stats = service.enrich(normalised, None, limit=1, deadline=time.monotonic() + 10)
    assert stats["matched"] == 0
    assert cache["items"]["same name"]["status"] == "ambiguous"
    assert not normalised["artist_metadata"].get("Same Name", {}).get("genres")


def test_unsupported_musicbrainz_genres_remain_unknown() -> None:
    normalised = unknown_profile("Spoken Artist", 2)
    service = FakeMusicBrainzGenreService(
        [
            {"artists": [{"id": "spoken", "name": "Spoken Artist", "score": 100}]},
            {"genres": [{"name": "spoken word", "count": 8}, {"name": "comedy", "count": 3}]},
        ]
    )
    cache, stats = service.enrich(normalised, None, limit=1, deadline=time.monotonic() + 10)
    assert stats["matched"] == 0
    assert cache["items"]["spoken artist"]["status"] == "no_supported_genres"
    coverage = build_analysis(normalised)["overview"]["taste_interpretation"]["coverage"]
    assert coverage["genreCoveragePercent"] == 0


def test_cached_match_is_reapplied_without_network_after_reimport() -> None:
    normalised = unknown_profile("Narvent", 2)
    cache = {
        "schemaVersion": 3,
        "provider": "musicbrainz",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "items": {
            "narvent": {
                "artistName": "Narvent",
                "status": "matched",
                "genres": ["synthwave"],
                "provider": "musicbrainz",
                "providerArtistId": "mbid",
                "confidence": "medium",
                "checkedAt": datetime.now(timezone.utc).isoformat(),
            }
        },
    }
    service = FakeMusicBrainzGenreService([])
    _, stats = service.enrich(normalised, cache, limit=0, deadline=time.monotonic() + 10)
    assert stats["attempted"] == 0
    assert stats["appliedCached"] == 1
    assert normalised["artist_metadata"]["Narvent"]["genres"] == ["synthwave"]


def test_lower_scoring_name_match_is_not_accepted() -> None:
    normalised = unknown_profile("Small Artist", 1)
    service = FakeMusicBrainzGenreService(
        [{"artists": [{"id": "weak", "name": "Small Artist", "score": 92}]}]
    )
    cache, stats = service.enrich(normalised, None, limit=1, deadline=time.monotonic() + 10)
    assert stats["matched"] == 0
    assert cache["items"]["small artist"]["status"] == "not_found"


def test_provider_failure_keeps_matches_completed_earlier_in_the_batch() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": "one", "title": "One", "artists": [{"name": "LONOWN"}], "played": "2026-07-01"},
                {"videoId": "two", "title": "Two", "artists": [{"name": "Second Artist"}], "played": "2026-07-01"},
            ]
        },
        today=date(2026, 7, 7),
    )
    request = httpx.Request("GET", "https://musicbrainz.org/ws/2/artist/")
    service = FakeMusicBrainzGenreService(
        [
            {"artists": [{"id": "lonown", "name": "LONOWN", "score": 100}]},
            {"genres": [{"name": "electronic", "count": 2}]},
            httpx.ConnectError("temporary outage", request=request),
        ]
    )
    cache, stats = service.enrich(normalised, None, limit=2, deadline=time.monotonic() + 10)
    assert stats["matched"] == 1
    assert stats["failed"] == 1
    assert stats["providerError"] == "musicbrainz_temporarily_unavailable"
    assert cache["items"]["lonown"]["status"] == "matched"


def test_time_limit_keeps_matches_completed_earlier_in_the_batch() -> None:
    normalised = normalise_collection(
        {"history": [
            {"videoId": "one", "title": "One", "artists": [{"name": "LONOWN"}], "played": "2026-07-01"},
            {"videoId": "two", "title": "Two", "artists": [{"name": "Second Artist"}], "played": "2026-07-01"},
        ]},
        today=date(2026, 7, 7),
    )
    service = FakeMusicBrainzGenreService([])
    outcomes = iter([
        {"artistName": "LONOWN", "status": "matched", "genres": ["electronic"], "providerArtistId": "lonown", "checkedAt": datetime.now(timezone.utc).isoformat()},
        TimeoutError(),
    ])
    def resolve(_client: Any, _artist: str, _deadline: float) -> dict[str, Any]:
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
    service.resolve_artist = resolve  # type: ignore[method-assign]
    cache, stats = service.enrich(normalised, None, limit=2, deadline=time.monotonic() + 10)
    assert stats["matched"] == 1
    assert stats["providerError"] == "musicbrainz_time_limit_reached"
    assert cache["items"]["lonown"]["status"] == "matched"
    assert normalised["artist_metadata"]["LONOWN"]["genres"] == ["electronic"]


def test_low_vote_outlier_genres_are_excluded_for_well_tagged_artists() -> None:
    normalised = unknown_profile("Popular Artist", 1)
    service = FakeMusicBrainzGenreService(
        [
            {"artists": [{"id": "popular", "name": "Popular Artist", "score": 100}]},
            {
                "genres": [
                    {"name": "pop", "count": 23},
                    {"name": "dance-pop", "count": 20},
                    {"name": "americana", "count": 1},
                ]
            },
        ]
    )
    _, stats = service.enrich(normalised, None, limit=1, deadline=time.monotonic() + 10)
    assert stats["matched"] == 1
    assert normalised["artist_metadata"]["Popular Artist"]["genres"] == ["pop", "dance-pop"]


def test_cache_version_change_removes_stale_enriched_genres_before_rechecking() -> None:
    normalised = unknown_profile("Versioned Artist", 1)
    normalised["artist_metadata"]["Versioned Artist"] = {
        "genres": ["americana"],
        "genre_source": "musicbrainz_artist_genres",
        "genre_confidence": "medium",
    }
    old_cache = {"schemaVersion": 1, "items": {}}
    service = FakeMusicBrainzGenreService([{"artists": []}])
    cache, stats = service.enrich(normalised, old_cache, limit=1, deadline=time.monotonic() + 10)
    assert stats["attempted"] == 1
    assert cache["schemaVersion"] == GENRE_METADATA_CACHE_VERSION
    assert normalised["artist_metadata"]["Versioned Artist"]["genres"] == []


def test_regional_musicbrainz_tags_are_kept_and_count_as_classified() -> None:
    normalised = unknown_profile("Regional Artist", 2)
    service = FakeMusicBrainzGenreService(
        [
            {"artists": [{"id": "regional", "name": "Regional Artist", "score": 100}]},
            {"genres": [{"name": "korean pop", "count": 8}, {"name": "mandarin pop", "count": 6}]},
        ]
    )
    _, stats = service.enrich(normalised, None, limit=1, deadline=time.monotonic() + 10)
    assert stats["matched"] == 1
    assert normalised["artist_metadata"]["Regional Artist"]["genres"] == ["k-pop", "mandopop"]
    assert profile_for_artist("Regional Artist", ["k-pop", "mandopop"])["canonical_genres"]


def test_musicbrainz_tags_fill_genres_when_the_genre_list_is_empty() -> None:
    normalised = unknown_profile("Tag Only Artist", 2)
    service = FakeMusicBrainzGenreService(
        [
            {"artists": [{"id": "tag-only", "name": "Tag Only Artist", "score": 100}]},
            {"genres": [], "tags": [{"name": "japanese pop", "count": 12}, {"name": "rock", "count": 6}]},
        ]
    )

    _, stats = service.enrich(normalised, None, limit=1, deadline=time.monotonic() + 10)

    assert stats["matched"] == 1
    assert normalised["artist_metadata"]["Tag Only Artist"]["genres"] == ["j-pop", "rock"]


def test_v4_negative_cache_is_rechecked_for_new_musicbrainz_tag_support() -> None:
    checked_at = datetime.now(timezone.utc).isoformat()
    migrated = ensure_genre_cache(
        {"schemaVersion": 4, "items": {"tag artist": {"artistName": "Tag Artist", "status": "no_supported_genres", "genres": [], "checkedAt": checked_at}}}
    )

    assert migrated["items"]["tag artist"]["checkedAt"] is None


def test_v3_musicbrainz_cache_migrates_without_losing_matches() -> None:
    checked_at = datetime.now(timezone.utc).isoformat()
    legacy = {
        "schemaVersion": 3,
        "provider": "musicbrainz",
        "updatedAt": checked_at,
        "items": {
            "narvent": {
                "artistName": "Narvent",
                "status": "matched",
                "genres": ["synthwave"],
                "provider": "musicbrainz",
                "providerArtistId": "mbid",
                "matchedName": "Narvent",
                "confidence": "medium",
                "checkedAt": checked_at,
            }
        },
    }

    migrated = ensure_genre_cache(legacy)

    assert migrated["schemaVersion"] == GENRE_METADATA_CACHE_VERSION
    assert migrated["items"]["narvent"]["genres"] == ["synthwave"]
    assert migrated["items"]["narvent"]["evidence"][0]["provider"] == "musicbrainz"


def test_exact_spotify_catalogue_genres_merge_with_musicbrainz_evidence() -> None:
    checked_at = datetime.now(timezone.utc).isoformat()
    cache = ensure_genre_cache(
        {
            "schemaVersion": 3,
            "items": {
                "regional artist": {
                    "artistName": "Regional Artist",
                    "status": "matched",
                    "genres": ["k-pop"],
                    "provider": "musicbrainz",
                    "providerArtistId": "mbid",
                    "checkedAt": checked_at,
                }
            },
        }
    )
    spotify_normalised = {
        "artist_metadata": {
            "Regional Artist": {
                "artist_id": "spotify:artist:123",
                "source": "spotify",
                "genres": ["korean pop", "dance pop"],
            }
        }
    }

    merged, added = seed_cache_from_source(cache, spotify_normalised, provider="spotify")
    target = unknown_profile("Regional Artist", 2)
    applied = apply_genre_cache(target, merged)

    assert added == 1
    assert applied == 1
    assert merged["items"]["regional artist"]["confidence"] == "high"
    assert set(merged["items"]["regional artist"]["genres"]) == {"k-pop", "dance pop"}
    assert target["artist_metadata"]["Regional Artist"]["genre_providers"] == ["musicbrainz", "spotify"]


def test_normalisation_reapplies_durable_genres_after_rebuild(tmp_path, monkeypatch) -> None:
    repository = JsonRepository(tmp_path / "durable-genres.db")
    checked_at = datetime.now(timezone.utc).isoformat()
    repository.save_json(
        "genre_metadata_cache",
        {
            "schemaVersion": 3,
            "items": {
                "narvent": {
                    "artistName": "Narvent",
                    "status": "matched",
                    "genres": ["synthwave"],
                    "provider": "musicbrainz",
                    "providerArtistId": "mbid",
                    "confidence": "medium",
                    "checkedAt": checked_at,
                }
            },
        },
    )
    monkeypatch.setattr(routes, "repo", repository)

    rebuilt = routes.normalise_with_duration_cache(
        {
            "history": [
                {
                    "videoId": "narvent-track",
                    "title": "Track",
                    "artists": [{"name": "Narvent"}],
                    "played": "2026-07-01",
                }
            ]
        }
    )

    assert rebuilt["artist_metadata"]["Narvent"]["genres"] == ["synthwave"]
    assert repository.load_json("genre_metadata_cache")["schemaVersion"] == GENRE_METADATA_CACHE_VERSION


def test_provider_refresh_replaces_its_stale_genres_instead_of_accumulating_them() -> None:
    spotify_v1 = {
        "artist_metadata": {
            "Changing Artist": {
                "artist_id": "spotify:artist:changing",
                "source": "spotify",
                "genres": ["indie pop", "old tag"],
            }
        }
    }
    cache, _ = seed_cache_from_source(None, spotify_v1, provider="spotify")
    spotify_v2 = {
        "artist_metadata": {
            "Changing Artist": {
                "artist_id": "spotify:artist:changing",
                "source": "spotify",
                "genres": ["indie pop", "dream pop"],
            }
        }
    }

    refreshed, _ = seed_cache_from_source(cache, spotify_v2, provider="spotify")

    assert refreshed["items"]["changing artist"]["genres"] == ["indie pop", "dream pop"]
    assert len(refreshed["items"]["changing artist"]["evidence"]) == 1


def test_each_completed_provider_lookup_is_checkpointed() -> None:
    normalised = unknown_profile("Checkpoint Artist", 1)
    service = FakeMusicBrainzGenreService(
        [
            {"artists": [{"id": "checkpoint", "name": "Checkpoint Artist", "score": 100}]},
            {"genres": [{"name": "electronic", "count": 2}]},
        ]
    )
    checkpoints: list[dict[str, Any]] = []

    service.enrich(
        normalised,
        None,
        limit=1,
        deadline=time.monotonic() + 10,
        on_cache_update=lambda cache: checkpoints.append(ensure_genre_cache(cache)),
    )

    assert checkpoints
    assert checkpoints[-1]["items"]["checkpoint artist"]["status"] == "matched"
