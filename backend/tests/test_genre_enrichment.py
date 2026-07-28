from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.analysis.taste_model import profile_for_artist
from app.services.genre_enrichment_service import MusicBrainzGenreService


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
    assert cache["schemaVersion"] == 3
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
