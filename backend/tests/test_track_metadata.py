from __future__ import annotations

from datetime import date

from app.analysis.musical_age import calculate_musical_age
from app.analysis.periods import rank_items, tracks_by_id
from app.analysis.track_metadata import (
    apply_track_metadata_cache,
    cache_track_metadata,
    display_recording_title,
    ensure_track_metadata_cache,
    metadata_alias_key,
)
from app.config import Settings
from app.services.ytmusic_service import YTMusicService


def test_presentation_titles_merge_without_collapsing_recording_versions() -> None:
    assert display_recording_title("Wisp - Mimi (Audio)", "Wisp") == "Mimi"
    assert display_recording_title("Wisp — Mimi ｜ Official Music Video", "Wisp") == "Mimi"
    assert display_recording_title("Mimi (Live)", "Wisp") == "Mimi (Live)"
    assert display_recording_title("Mimi (Slowed + Reverb)", "Wisp") == "Mimi (Slowed + Reverb)"
    assert metadata_alias_key("Mimi (Audio)", "Wisp") != metadata_alias_key("Mimi (Live)", "Wisp")


def test_album_alias_repairs_alternate_presentations_without_merging_events() -> None:
    cache = ensure_track_metadata_cache({})
    cache_track_metadata(
        cache,
        {
            "status": "resolved",
            "title": "Mimi",
            "primary_artist": "Wisp",
            "artists": ["Wisp"],
            "album": "Pandora",
            "album_id": "album-pandora",
            "album_release_year": 2024,
            "album_art_url": "https://img.example/pandora.jpg",
            "album_art_source": "youtube_album_cover",
            "identity_confidence": 0.95,
            "match_confidence": 0.95,
            "release_year_confidence": "medium",
            "match_method": "authoritative_album_tracklist",
            "source": "ytmusicapi.public.album_tracklist",
            "version_signature": [],
        },
        video_id="album-audio-id",
    )
    normalised = {
        "tracks": [
            {
                "track_id": "video:official-video-id",
                "video_id": "official-video-id",
                "title": "Wisp - Mimi (Official Music Video)",
                "primary_artist": "Wisp",
                "artists": ["Wisp"],
                "album": None,
            }
        ],
        "play_events": [
            {"event_id": "one", "track_id": "video:official-video-id"},
            {"event_id": "two", "track_id": "video:official-video-id"},
        ],
        "excluded_play_events": [],
        "listening_events": [],
    }

    assert apply_track_metadata_cache(normalised, cache) == 1
    track = normalised["tracks"][0]
    assert track["title"] == "Mimi"
    assert track["album"] == "Pandora"
    assert track["release_year"] == 2024
    assert track["album_art_url"] == "https://img.example/pandora.jpg"
    assert track["release_year_source"] == "ytmusicapi.public.album_tracklist"
    assert [event["event_id"] for event in normalised["play_events"]] == ["one", "two"]


def test_period_ranking_merges_audio_and_video_but_keeps_live_separate() -> None:
    normalised = {
        "tracks": [
            {"track_id": "video:audio", "video_id": "audio", "title": "Mimi (Audio)", "primary_artist": "Wisp", "artists": ["Wisp"]},
            {"track_id": "video:video", "video_id": "video", "title": "Wisp - Mimi (Official Music Video)", "primary_artist": "Wisp", "artists": ["Wisp"]},
            {"track_id": "video:live", "video_id": "live", "title": "Mimi (Live)", "primary_artist": "Wisp", "artists": ["Wisp"]},
        ],
        "play_events": [
            {"event_id": "1", "track_id": "video:audio", "played_at": "2026-07-01T00:00:00+00:00"},
            {"event_id": "2", "track_id": "video:video", "played_at": "2026-07-02T00:00:00+00:00"},
            {"event_id": "3", "track_id": "video:live", "played_at": "2026-07-03T00:00:00+00:00"},
        ],
    }

    ranked = rank_items(normalised["play_events"], tracks_by_id(normalised), "tracks")
    assert [(item["title"], item["play_count"]) for item in ranked] == [("Mimi", 2), ("Mimi (Live)", 1)]


def test_musical_age_prefers_original_year_and_ignores_low_confidence_years() -> None:
    normalised = {
        "tracks": [
            {
                "track_id": "verified",
                "title": "Song",
                "primary_artist": "Artist",
                "original_release_year": 2004,
                "edition_release_year": 2024,
                "release_year": 2024,
                "release_year_confidence": "high",
            },
            {
                "track_id": "guess",
                "title": "Guess",
                "primary_artist": "Artist",
                "release_year": 1980,
                "release_year_confidence": "low",
            },
        ],
        "play_events": [
            {"track_id": "verified", "played_at": "2026-07-01T00:00:00+00:00", "is_music_candidate": True},
            {"track_id": "guess", "played_at": "2026-07-02T00:00:00+00:00", "is_music_candidate": True},
        ],
        "coverage": {"date_data_available": True, "days_represented": 2},
        "metadata": {"source": "youtube"},
    }

    result = calculate_musical_age(normalised, today=date(2026, 7, 29))
    assert result["weightedMedianReleaseYear"] == 2004
    assert result["releaseYearCoverage"] == 50.0


def test_authoritative_album_tracklist_seeds_reusable_aliases() -> None:
    class Catalogue:
        def get_watch_playlist(self, videoId: str, limit: int) -> dict:
            assert videoId == "mimi-video"
            return {
                "tracks": [
                    {
                        "videoId": "mimi-video",
                        "title": "Mimi",
                        "artists": [{"name": "Wisp"}],
                        "album": {"name": "Pandora", "id": "pandora-id"},
                    }
                ]
            }

        def get_album(self, browse_id: str) -> dict:
            assert browse_id == "pandora-id"
            return {
                "title": "Pandora",
                "year": "2024",
                "thumbnails": [{"url": "https://img.example/pandora.jpg", "width": 544, "height": 544}],
                "artists": [{"name": "Wisp"}],
                "tracks": [
                    {"videoId": "pandora-audio", "title": "Pandora", "artists": [{"name": "Wisp"}]},
                    {"videoId": "mimi-audio", "title": "Mimi", "artists": [{"name": "Wisp"}]},
                ],
            }

        def search(self, *_args, **_kwargs) -> list:
            raise AssertionError("Exact video metadata already supplied the album")

    service = YTMusicService(Settings())
    service.public_client = lambda: Catalogue()  # type: ignore[method-assign]
    cache: dict = {}
    normalised = {
        "tracks": [{"track_id": "video:mimi-video", "video_id": "mimi-video", "title": "Wisp - Mimi (Audio)", "primary_artist": "Wisp"}],
        "play_events": [{"track_id": "video:mimi-video"}] * 4,
    }

    stats = service.enrich_track_metadata_cache(normalised, cache, limit=1)
    prepared = ensure_track_metadata_cache(cache)
    assert stats == {"attempted": 1, "added": 1, "failed": 0, "albumAliases": 2, "remaining": 0}
    assert prepared["items"]["mimi-video"]["album"] == "Pandora"
    assert prepared["items"]["mimi-video"]["album_art_url"] == "https://img.example/pandora.jpg"
    assert prepared["aliases"][metadata_alias_key("Pandora", "Wisp")]["album"] == "Pandora"


def test_watch_playlist_never_accepts_a_different_video_as_an_exact_id_match() -> None:
    class Catalogue:
        def get_watch_playlist(self, videoId: str, limit: int) -> dict:
            return {"tracks": [{"videoId": "different-video", "title": "Wrong Song", "artists": [{"name": "Other Artist"}]}]}

        def search(self, query: str, filter: str, limit: int) -> list:
            return [{
                "videoId": "catalogue-audio",
                "title": "Right Song",
                "artists": [{"name": "Right Artist"}],
                "album": {"name": "Right Album", "id": "right-album"},
            }]

        def get_album(self, browse_id: str) -> dict:
            return {"title": "Right Album", "year": "2020", "artists": [{"name": "Right Artist"}], "tracks": []}

    service = YTMusicService(Settings())
    service.public_client = lambda: Catalogue()  # type: ignore[method-assign]
    cache: dict = {}
    normalised = {
        "tracks": [{"track_id": "video:requested-video", "video_id": "requested-video", "title": "Right Song", "primary_artist": "Right Artist"}],
        "play_events": [{"track_id": "video:requested-video"}],
    }

    stats = service.enrich_track_metadata_cache(normalised, cache, limit=1)

    assert stats["added"] == 1
    assert cache["items"]["requested-video"]["title"] == "Right Song"
    assert cache["items"]["requested-video"]["match_method"] == "exact_title_artist_song_search"
    assert cache["items"]["requested-video"]["identity_confidence"] == 0.90
