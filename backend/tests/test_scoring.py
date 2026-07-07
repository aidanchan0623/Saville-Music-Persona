from __future__ import annotations

from datetime import date

from app.analysis.demo_data import demo_raw_collection
from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis, repeat_score


def test_repeat_score_formula() -> None:
    metric = repeat_score(total_track_plays=10, unique_tracks=4)
    assert metric["value"] == 60.0
    assert metric["label"] == "comfort listener"


def test_empty_libraries_do_not_crash() -> None:
    normalised = normalise_collection({"history": [], "liked_songs": {"tracks": []}}, today=date(2026, 7, 1))
    analysis = build_analysis(normalised)
    assert analysis["overview"]["total_detected_plays"] == 0
    assert analysis["scores"][0]["value"] == 0


def test_demo_analysis_has_top_tracks_and_confidence() -> None:
    normalised = normalise_collection(demo_raw_collection(today=date(2026, 7, 1)), today=date(2026, 7, 1))
    analysis = build_analysis(normalised)
    assert analysis["top_tracks"]
    confidence = next(score for score in analysis["scores"] if score["key"] == "taste_confidence")
    assert confidence["value"] > 0


def test_top_tracks_explain_low_confidence_when_no_repeats() -> None:
    normalised = normalise_collection(
        {
            "history": [
                {"videoId": "a", "title": "A", "artists": [{"name": "Artist"}], "played": "Today"},
                {"videoId": "b", "title": "B", "artists": [{"name": "Artist"}], "played": "Yesterday"},
            ]
        },
        today=date(2026, 7, 7),
    )
    analysis = build_analysis(normalised)
    assert analysis["top_tracks"][0]["ranking_confidence"] == "low_no_repeat_signal"
    assert "recent detected song" in analysis["top_tracks"][0]["why_it_ranked"]
