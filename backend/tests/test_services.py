from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.api.routes import persona_report_cache_key, persona_report_fingerprint
from app.analysis.thumbnails import best_thumbnail_url
from app.analysis.media import album_id_key, album_name_artist_key, artist_id_key, artist_name_key
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


def test_v2_persona_report_json_is_sanitized_and_artist_limited() -> None:
    service = OllamaService(Settings())
    report = service.parse_report(
        """```json
        {
          "personaReportSchemaVersion": 2,
          "personaName": "The Dramatic Alternative Night Walker With Too Many Words",
          "openingHook": "Your headphones enter the room wearing eyeliner and carrying a suspiciously emotional guitar.",
          "coreSound": {"headline": "Alternative guitars hold the centre", "body": "This is a focused chapter about supplied evidence, with enough words to feel written but not enough to become a dashboard essay.", "pullQuote": "Cathartic and guitar-driven"},
          "comfortLoop": {"headline": "The returns matter", "body": "Repeat behaviour is interpreted here without inventing new numbers or pretending the model calculated anything itself.", "pullQuote": "Comfort with standards"},
          "mainCharacters": [
            {"artistName": "Bring Me The Horizon", "role": "The emotional anchor", "line": "They hold the loud centre."},
            {"artistName": "Imaginary Artist", "role": "Fake", "line": "Should not survive."},
            {"artistName": "Bring Me The Horizon", "role": "Duplicate", "line": "Should not duplicate."},
            {"artistName": "My Chemical Romance", "role": "The theatre kid", "line": "They keep the drama legible."}
          ],
          "plotTwist": {"headline": "Consistency is the twist", "body": "The model reports stability because the supplied evidence does not justify a fake surprise."},
          "closing": {"headline": "Closing credits", "body": "The listener is described through supplied sound families and anchor artists, not through invented psychology or unsupported biography.", "finalLine": "Roll the next song with intent."}
        }
        ```""",
        {
            "headline_persona": "Fallback",
            "top_artists": [{"artist": "Bring Me The Horizon"}, {"artist": "My Chemical Romance"}],
        },
    )
    assert report.personaReportSchemaVersion == 2
    assert len(report.personaName.split()) <= 8
    assert [item.artistName for item in report.mainCharacters[:2]] == ["Bring Me The Horizon", "My Chemical Romance"]
    assert all(item.artistName != "Imaginary Artist" for item in report.mainCharacters)
    assert report.coreSound.headline
    assert report.closing.finalLine


def test_report_generation_marks_fresh_gemma_source() -> None:
    service = FakeOllamaReportService(
        response={
            "response": """
            {
              "personaReportSchemaVersion": 2,
              "personaName": "Alternative Night Driver",
              "openingHook": "Your headphones keep choosing stormy guitars with a bright pop exit sign.",
              "coreSound": {"headline": "Guitars Hold The Centre", "body": "Alternative rock is the main lane, with pop edges keeping the report readable and direct.", "pullQuote": "Stormy, but catchy"},
              "comfortLoop": {"headline": "The Returns Matter", "body": "Repeat behaviour points to trusted songs earning their place instead of random looping.", "pullQuote": "Comfort with standards"},
              "mainCharacters": [{"artistName": "Bring Me The Horizon", "role": "The anchor", "line": "They hold the loud centre."}],
              "plotTwist": {"headline": "Consistency Is The Twist", "body": "The supplied evidence supports steadiness more than a fake reinvention."},
              "closing": {"headline": "Closing Credits", "body": "The profile closes around guitars, repeatable anchors, and a taste for drama that still wants hooks.", "finalLine": "Roll the next song with intent."}
            }
            """
        }
    )
    report = service.generate_report({"top_artists": [{"artist": "Bring Me The Horizon"}]}, "serious")
    assert report.generationSource == "gemma"
    assert report.fallback is False
    assert report.fallbackReason is None
    assert report.model == "gemma3:4b"
    assert report.durationMs is not None
    assert service.generate_calls == 1


def test_report_generation_marks_ollama_unavailable_fallback() -> None:
    service = FakeOllamaReportService(status={"reachable": False, "model_installed": False, "model": "gemma3:4b", "message": "offline"})
    report = service.generate_report({"headline_persona": "Fallback"}, "serious")
    assert report.generationSource == "fallback"
    assert report.fallback is True
    assert report.fallbackReason == "ollama_unavailable"
    assert service.generate_calls == 0


def test_report_generation_marks_malformed_response_fallback() -> None:
    service = FakeOllamaReportService(response={"response": "not json"})
    report = service.generate_report({"headline_persona": "Fallback"}, "serious")
    assert report.generationSource == "fallback"
    assert report.fallbackReason == "invalid_or_missing_story_json"
    assert report.personaReportSchemaVersion == 2


def test_report_generation_marks_timeout_fallback() -> None:
    service = FakeOllamaReportService(error=TimeoutError("too slow"))
    report = service.generate_report({"headline_persona": "Fallback"}, "serious")
    assert report.generationSource == "fallback"
    assert report.fallbackReason == "ollama_timeout"


def test_report_cache_key_uses_source_schema_period_and_fingerprint() -> None:
    profile = {
        "total_detected_plays": 12,
        "top_artists": [{"artist": "Artist A", "play_count": 4}],
        "top_tracks": [{"title": "Song A", "artist": "Artist A", "play_count": 3}],
    }
    changed = {
        "total_detected_plays": 13,
        "top_artists": [{"artist": "Artist A", "play_count": 4}],
        "top_tracks": [{"title": "Song A", "artist": "Artist A", "play_count": 3}],
    }
    fingerprint = persona_report_fingerprint(profile)
    assert fingerprint != persona_report_fingerprint(changed)
    key = persona_report_cache_key("youtube", "serious", fingerprint)
    assert "youtube" in key
    assert "rolling_year" in key
    assert "v2" in key
    assert fingerprint in key


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
    assert cache_record(cache, "Artist A", "UC-a")["url"] == "https://img.example/a-600.jpg"
    assert cache_record(cache, "Artist A", "UC-a")["mediaType"] == "artist"


def test_album_image_enrichment_uses_existing_album_id() -> None:
    fake = FakeYTMusic(
        album_pages={
            "MPRE-a": {
                "title": "The Black Parade",
                "browseId": "MPRE-a",
                "thumbnails": [
                    {"url": "https://img.example/black-parade-120.jpg", "width": 120, "height": 120},
                    {"url": "https://img.example/black-parade-544.jpg", "width": 544, "height": 544},
                ],
            }
        }
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_album_image_cache({"history": [_history_album("The Black Parade", "My Chemical Romance", "MPRE-a")]}, cache)
    assert stats["added"] == 1
    assert fake.get_album_calls == ["MPRE-a"]
    assert fake.search_calls == []
    record = album_cache_record(cache, "The Black Parade", "My Chemical Romance", "MPRE-a")
    assert record["album_image_url"] == "https://img.example/black-parade-544.jpg"
    assert record["mediaType"] == "album"


def test_album_image_enrichment_searches_takeout_album_names() -> None:
    fake = FakeYTMusic(
        search_results={
            "Sempiternal Bring Me The Horizon": [
                {"title": "Sempiternal", "browseId": "MPRE-bmth", "artists": [{"name": "Bring Me The Horizon"}]},
            ]
        },
        album_pages={
            "MPRE-bmth": {
                "title": "Sempiternal",
                "browseId": "MPRE-bmth",
                "thumbnails": [{"url": "https://img.example/sempiternal.jpg", "width": 512, "height": 512}],
            }
        },
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_album_image_cache({"takeout_history": [_history_album("Sempiternal", "Bring Me The Horizon")]}, cache)
    assert stats["added"] == 1
    assert fake.search_calls == [("Sempiternal Bring Me The Horizon", "albums", 5)]
    assert fake.get_album_calls == ["MPRE-bmth"]
    assert album_cache_record(cache, "Sempiternal", "Bring Me The Horizon")["album_image_url"] == "https://img.example/sempiternal.jpg"


def test_artist_image_enrichment_prioritises_preferred_artists() -> None:
    fake = FakeYTMusic(
        search_results={
            "Current Artist": [{"artist": "Current Artist", "browseId": "UC-current"}],
            "History Artist": [{"artist": "History Artist", "browseId": "UC-history"}],
        },
        artist_pages={
            "UC-current": {"artist": "Current Artist", "browseId": "UC-current", "thumbnails": [{"url": "https://img.example/current.jpg", "width": 500, "height": 500}]},
            "UC-history": {"artist": "History Artist", "browseId": "UC-history", "thumbnails": [{"url": "https://img.example/history.jpg", "width": 500, "height": 500}]},
        },
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("History Artist")]}, cache, preferred_artists=["Current Artist"])
    assert stats["added"] == 2
    assert fake.search_calls[0][0] == "Current Artist"
    assert cache_record(cache, "Current Artist", "UC-current")["url"] == "https://img.example/current.jpg"


def test_artist_image_enrichment_falls_back_to_public_client() -> None:
    fake = FakeYTMusic(
        search_results={"Artist A": [{"artist": "Artist A", "browseId": "UC-a"}]},
        artist_pages={"UC-a": {"artist": "Artist A", "browseId": "UC-a", "thumbnails": [{"url": "https://img.example/a.jpg", "width": 500, "height": 500}]}},
    )
    service = YTMusicService(Settings())
    service.client = lambda prefer_browser=True: (_ for _ in ()).throw(RuntimeError("auth unavailable"))  # type: ignore[method-assign]
    service.public_client = lambda: fake  # type: ignore[method-assign]
    cache: dict[str, object] = {}
    stats = service.enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["added"] == 1
    assert fake.search_calls == [("Artist A", "artists", 5)]
    assert cache_record(cache, "Artist A", "UC-a")["url"] == "https://img.example/a.jpg"


def test_artist_image_enrichment_does_not_choose_non_exact_search_result() -> None:
    fake = FakeYTMusic(search_results={"Artist A": [{"artist": "Artist Adjacent", "browseId": "UC-other", "thumbnails": [{"url": "https://img.example/other.jpg"}]}]})
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["failed"] == 1
    assert cache_record(cache, "Artist A")["url"] is None
    assert cache_record(cache, "Artist A")["failureReason"] == "no_exact_artist_match"
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
    assert cache_record(cache, "Artist A", "UC-a")["browse_id"] == "UC-a"


def test_artist_image_enrichment_records_missing_thumbnails() -> None:
    fake = FakeYTMusic(
        search_results={"Artist A": [{"artist": "Artist A", "browseId": "UC-a"}]},
        artist_pages={"UC-a": {"artist": "Artist A", "browseId": "UC-a", "thumbnails": []}},
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["failed"] == 1
    assert cache_record(cache, "Artist A", "UC-a")["failureReason"] == "missing_thumbnails"


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
    cache = {
        "schemaVersion": 2,
        "items": {
            "artist-name:artist a": {
                "schemaVersion": 2,
                "mediaType": "artist",
                "entityName": "Artist A",
                "url": "https://img.example/cached.jpg",
                "thumbnail_url": "https://img.example/cached.jpg",
                "thumbnails": [{"url": "https://img.example/cached.jpg"}],
            }
        },
    }
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["attempted"] == 0
    assert fake.search_calls == []
    assert fake.get_artist_calls == []


def test_artist_image_enrichment_keeps_list_on_upstream_exception() -> None:
    fake = FakeYTMusic(raise_search=True)
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Artist A")]}, cache)
    assert stats["failed"] == 1
    assert cache_record(cache, "Artist A")["failureReason"] == "upstream_exception"


def test_artist_name_matching_handles_unicode_and_topic_suffix() -> None:
    assert normalise_artist_name("Beyoncé - Topic") == normalise_artist_name("Beyonce")
    fake = FakeYTMusic(
        search_results={"Beyoncé - Topic": [{"artist": "Beyonce", "browseId": "UC-b"}]},
        artist_pages={"UC-b": {"artist": "Beyonce", "browseId": "UC-b", "thumbnails": [{"url": "https://img.example/beyonce.jpg", "width": 400, "height": 400}]}},
    )
    cache: dict[str, object] = {}
    stats = fake_service(fake).enrich_artist_image_cache({"history": [_history_artist("Beyoncé - Topic")]}, cache)
    assert stats["added"] == 1
    assert cache_record(cache, "Beyoncé - Topic", "UC-b")["url"] == "https://img.example/beyonce.jpg"


class FakeYTMusic:
    def __init__(
        self,
        search_results: dict[str, list[dict[str, object]]] | None = None,
        artist_pages: dict[str, dict[str, object]] | None = None,
        album_pages: dict[str, dict[str, object]] | None = None,
        raise_search: bool = False,
    ) -> None:
        self.search_results = search_results or {}
        self.artist_pages = artist_pages or {}
        self.album_pages = album_pages or {}
        self.raise_search = raise_search
        self.search_calls: list[tuple[str, str | None, int | None]] = []
        self.get_artist_calls: list[str] = []
        self.get_album_calls: list[str] = []

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

    def get_album(self, browse_id: str) -> dict[str, object]:
        self.get_album_calls.append(browse_id)
        payload = self.album_pages.get(browse_id)
        if payload is None:
            raise RuntimeError("album page failed")
        return payload


class FakeOllamaReportService(OllamaService):
    def __init__(
        self,
        response: dict[str, object] | None = None,
        status: dict[str, object] | None = None,
        error: Exception | None = None,
    ) -> None:
        super().__init__(Settings())
        self.response = response or {"response": "{}"}
        self.status_payload = status or {"reachable": True, "model_installed": True, "model": "gemma3:4b", "message": "ready"}
        self.error = error
        self.generate_calls = 0

    def status(self) -> dict[str, object]:
        return self.status_payload

    def _request_json(self, method: str, path: str, payload: dict[str, object] | None = None, timeout: float = 10.0) -> dict[str, object]:
        if path == "/api/generate":
            self.generate_calls += 1
            if self.error:
                raise self.error
            return self.response
        return self.status_payload


def fake_service(fake: FakeYTMusic) -> YTMusicService:
    service = YTMusicService(Settings())
    service.client = lambda prefer_browser=True: fake  # type: ignore[method-assign]
    return service


def _history_artist(name: str, artist_id: str | None = None) -> dict[str, object]:
    artist: dict[str, object] = {"name": name}
    if artist_id:
        artist["id"] = artist_id
    return {"videoId": f"v-{normalise_artist_name(name)}", "title": "Song", "artists": [artist]}


def _history_album(album: str, artist: str, album_id: str | None = None) -> dict[str, object]:
    item: dict[str, object] = {
        "videoId": f"v-{normalise_artist_name(artist)}-{normalise_artist_name(album)}",
        "title": "Song",
        "artists": [{"name": artist}],
        "album": {"name": album},
    }
    if album_id:
        item["album"] = {"name": album, "id": album_id}
    return item


def cache_record(cache: dict[str, object], artist: str, artist_id: str | None = None) -> dict[str, object]:
    items = cache["items"]  # type: ignore[index]
    assert isinstance(items, dict)
    for key in (artist_id_key(artist_id), artist_name_key(artist)):
        if key and key in items:
            value = items[key]
            assert isinstance(value, dict)
            return value
    raise AssertionError(f"Missing cache record for {artist}")


def album_cache_record(cache: dict[str, object], album: str, artist: str, album_id: str | None = None) -> dict[str, object]:
    items = cache["items"]  # type: ignore[index]
    assert isinstance(items, dict)
    direct_key = album_id_key(album_id)
    if direct_key and direct_key in items:
        value = items[direct_key]
        assert isinstance(value, dict)
        return value
    index = cache.get("index")  # type: ignore[attr-defined]
    assert isinstance(index, dict)
    alias_key = album_name_artist_key(album, artist)
    mapped = index.get(alias_key) if alias_key else None
    if mapped and mapped in items:
        value = items[mapped]
        assert isinstance(value, dict)
        return value
    raise AssertionError(f"Missing album cache record for {album} by {artist}")
