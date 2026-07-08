from __future__ import annotations

from datetime import date, timedelta

from app.analysis.music_character import CHARACTER_DEFINITIONS, character_payload
from app.analysis.normalizer import normalise_collection


def _history_item(video_id: str, title: str, artist: str, played: str, album: str | None = None, duration: int = 180) -> dict:
    item = {
        "videoId": video_id,
        "title": title,
        "artists": [{"name": artist}],
        "played": played,
        "duration_seconds": duration,
        "source": "test",
    }
    if album:
        item["album"] = {"name": album, "id": f"album-{album.lower().replace(' ', '-')}"}
    return item


def test_character_catalog_contains_requested_twenty_characters() -> None:
    ids = {item["id"] for item in CHARACTER_DEFINITIONS}
    assert len(CHARACTER_DEFINITIONS) == 20
    assert "heavy_but_melodic_negotiator" in ids
    assert "single_song_prisoner" in ids
    assert "album_loyalist" in ids
    assert "soundtrack_side_quest" in ids


def test_character_selection_is_deterministic_and_period_aware() -> None:
    history = []
    start = date(2026, 7, 1)
    for index in range(35):
        history.append(_history_item(f"bmth-{index}", f"BMTH {index}", "Bring Me The Horizon", (start + timedelta(days=index % 6)).isoformat(), "Heavy Album"))
    for index in range(15):
        history.append(_history_item(f"deftones-{index}", f"Deftones {index}", "Deftones", (start + timedelta(days=index % 6)).isoformat(), "Heavy Album"))
    for index in range(8):
        history.append(_history_item(f"mcr-{index}", f"MCR {index}", "My Chemical Romance", (start + timedelta(days=index % 6)).isoformat(), "The Black Parade"))
    normalised = normalise_collection({"history": history}, today=date(2026, 7, 7))
    first = character_payload(normalised, "month", "2026-07")
    second = character_payload(normalised, "month", "2026-07")

    assert first["deterministic"] is True
    assert first["primary"] == second["primary"]
    assert first["period"]["label"] == "July 2026"
    assert first["primary"]["id"] in {"heavy_but_melodic_negotiator", "cathartic_chaos_enjoyer", "im_fine_alternative_listener"}
    assert first["evidence_chips"]


def test_character_returns_forming_profile_for_weak_sample() -> None:
    normalised = normalise_collection({"history": [_history_item("one", "One", "Unknown Artist", "2026-07-01")]}, today=date(2026, 7, 7))
    payload = character_payload(normalised, "month", "2026-07")
    assert payload["primary"]["id"] == "forming"
    assert payload["sample_warning"]
