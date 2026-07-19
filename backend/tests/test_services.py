from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.analysis.thumbnails import best_thumbnail_url
from app.services.ollama_service import OllamaService
from app.services.recommendations import dedupe_candidates
from app.services.ytmusic_service import YTMusicService, friendly_auth_error, normalise_artist_name


def test_malformed_llm_json_is_repaired() -> None:
    service = OllamaService(Settings())
    report = service.parse_report('noise {"headline":"Hi","summary":123} end', {"headline_persona": "Fallback"})
    assert report.headline == "Hi"
    assert report.summary
    assert report.listener_type_cards


def test_partial_llm_report_is_filled_from_evidence() -> None:
    service = OllamaService(Settings())
    report = service.parse_report(
        '{"headline":"Only headline"}',
        {
            "headline_persona": "Fallback",
            "coverage": {"days_represented": 7, "history_items_returned": 200, "earliest_detected_play": "2026-06-30", "latest_detected_play": "2026-07-06"},
            "top_artists": [{"artist": "Bring Me The Horizon"}, {"artist": "My Chemical Romance"}],
            "top_tracks": [{"title": "Drown"}],
            "scores": [{"name": "Taste confidence", "label": "useful but partial"}],
            "mood_profile": [{"tag": "late-night"}],
        },
    )
    assert report.headline == "Only headline"
    assert report.core_identity_paragraph
    assert "Bring Me The Horizon" in report.comfort_artists
    assert report.personality_tags
    assert report.listener_type_cards


def test_recommendation_duplicate_removal() -> None:
    candidates = [
        {"videoId": "1", "title": "Song (Official Video)", "artists": [{"name": "Artist"}]},
        {"videoId": "2", "title": "Song", "artists": [{"name": "Artist"}]},
        {"videoId": "3", "title": "Different", "artists": [{"name": "Artist"}]},
    ]
    result = dedupe_candidates(candidates, existing_keys=set(), existing_video_ids=set())
    assert [item["videoId"] for item in result] == ["1", "3"]


def test_no_authenticated_youtube_music_account(tmp_path: Path) -> None:
    settings = Settings()
    settings.private_dir = tmp_path
    settings.ytmusic_auth_file = tmp_path / "oauth.json"
    settings.ytmusic_browser_auth_file = tmp_path / "browser.json"
    settings.ytmusic_client_id = ""
    settings.ytmusic_client_secret = ""
    service = YTMusicService(settings)
    status = service.auth_status()
    assert status["connected"] is False
    assert status["auth_file_exists"] is False


def test_verbose_youtube_account_menu_error_is_sanitized() -> None:
    message = friendly_auth_error(KeyError("Unable to find 'header' on {'multiPageMenuRenderer': {'secret': 'value'}}"), is_browser=True)
    assert "account menu" in message
    assert "secret" not in message


def test_artist_image_enrichment_uses_existing_artist_id() -> None:
    fake = FakeYTMusic(
        artist_pages={
            "UC-a": {
                "artist": "Artist A",
                "browseId": "UC-a",
                "thumbnails": [
                    {"url": "https://img.example/a-60.jpg", "width": 60, "height": 60},
                    {"url": "https://img.example/a-600.jpg", "width": 600, "height": 600},
                ],
            }
        }
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A", "UC-a")]}, cache)
    assert stats["added"] == 1
    assert fake.get_artist_calls == ["UC-a"]
    assert fake.search_calls == []
    assert cache["Artist A"]["thumbnail_url"] == "https://img.example/a-600.jpg"


def test_artist_image_enrichment_does_not_choose_non_exact_search_result() -> None:
    fake = FakeYTMusic(search_results={"Artist A": [{"artist": "Artist Adjacent", "browseId": "UC-other", "thumbnails": [{"url": "https://img.example/other.jpg"}]}]})
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["failed"] == 1
    assert cache["Artist A"]["thumbnail_url"] is None
    assert cache["Artist A"]["failure_reason"] == "no_exact_artist_match"
    assert fake.get_artist_calls == []


def test_artist_image_enrichment_selects_exact_match_among_multiple_results() -> None:
    fake = FakeYTMusic(
        search_results={
            "Artist A": [
                {"artist": "Artist Adjacent", "browseId": "UC-other"},
                {"artist": "Artist A", "browseId": "UC-a"},
            ]
        },
        artist_pages={"UC-a": {"artist": "Artist A", "browseId": "UC-a", "thumbnails": [{"url": "https://img.example/a.jpg", "width": 512, "height": 512}]}},
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["added"] == 1
    assert fake.get_artist_calls == ["UC-a"]
    assert cache["Artist A"]["browse_id"] == "UC-a"


def test_artist_image_enrichment_records_missing_thumbnails() -> None:
    fake = FakeYTMusic(
        search_results={"Artist A": [{"artist": "Artist A", "browseId": "UC-a"}]},
        artist_pages={"UC-a": {"artist": "Artist A", "browseId": "UC-a", "thumbnails": []}},
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["failed"] == 1
    assert cache["Artist A"]["failure_reason"] == "missing_thumbnails"


def test_best_thumbnail_prefers_highest_resolution_https() -> None:
    assert best_thumbnail_url(
        [
            {"url": "http://img.example/insecure.jpg", "width": 2000, "height": 2000},
            {"url": "https://img.example/small.jpg", "width": 120, "height": 120},
            {"url": "https://img.example/wide.jpg", "width": 640},
            {"url": "https://img.example/large.jpg", "width": 512, "height": 512},
        ]
    ) == "https://img.example/large.jpg"


def test_artist_image_enrichment_cache_hit_skips_upstream_calls() -> None:
    fake = FakeYTMusic()
    cache = {"Artist A": {"thumbnail_url": "https://img.example/cached.jpg", "thumbnails": [{"url": "https://img.example/cached.jpg"}]}}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["attempted"] == 0
    assert fake.search_calls == []
    assert fake.get_artist_calls == []


def test_artist_image_enrichment_keeps_list_on_upstream_exception() -> None:
    fake = FakeYTMusic(raise_search=True)
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["failed"] == 1
    assert cache["Artist A"]["failure_reason"] == "upstream_exception"


def test_artist_name_matching_handles_unicode_and_topic_suffix() -> None:
    assert normalise_artist_name("Beyoncé - Topic") == normalise_artist_name("Beyonce")
    fake = FakeYTMusic(
        search_results={"Beyoncé - Topic": [{"artist": "Beyonce", "browseId": "UC-b"}]},
        artist_pages={"UC-b": {"artist": "Beyonce", "browseId": "UC-b", "thumbnails": [{"url": "https://img.example/beyonce.jpg", "width": 400, "height": 400}]}},
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Beyoncé - Topic")]}, cache)
    assert stats["added"] == 1
    assert cache["Beyoncé - Topic"]["thumbnail_url"] == "https://img.example/beyonce.jpg"


class FakeYTMusic:
    def __init__(
        self,
        search_results: dict[str, list[dict[str, object]]] | None = None,
        artist_pages: dict[str, dict[str, object]] | None = None,
        raise_search: bool = False,
    ) -> None:
        self.search_results = search_results or {}
        self.artist_pages = artist_pages or {}
        self.raise_search = raise_search
        self.search_calls: list[tuple[str, str | None, int | None]] = []
        self.get_artist_calls: list[str] = []

    def search(self, query: str, filter: str | None = None, limit: int | None = None) -> list[dict[str, object]]:
        self.search_calls.append((query, filter, limit))
        if self.raise_search:
            raise RuntimeError("search failed")
        return self.search_results.get(query, [])

    def get_artist(self, browse_id: str) -> dict[str, object]:
        self.get_artist_calls.append(browse_id)
        payload = self.artist_pages.get(browse_id)
        if payload is None:
            raise RuntimeError("artist page failed")
        return payload


def fake_service(fake: FakeYTMusic) -> YTMusicService:
    service = YTMusicService(Settings())
    service.client = lambda prefer_browser=True: fake  # type: ignore[method-assign]
    return service


def _history_artist(name: str, artist_id: str | None = None) -> dict[str, object]:
    artist: dict[str, object] = {"name": name}
    if artist_id:
        artist["id"] = artist_id
    return {"videoId": f"v-{normalise_artist_name(name)}", "title": "Song", "artists": [artist]}
