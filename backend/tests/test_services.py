from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.services.ollama_service import OllamaService
from app.services.recommendations import dedupe_candidates
from app.services.ytmusic_service import YTMusicService


def test_malformed_llm_json_is_repaired() -> None:
    service = OllamaService(Settings())
    report = service.parse_report('noise {"headline":"Hi","summary":123} end', {"headline_persona": "Fallback"})
    assert report.headline == "Hi"
    assert report.summary == "123"


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
