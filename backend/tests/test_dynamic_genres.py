from datetime import date

from app.analysis.insights import insights_payload
from app.analysis.normalizer import normalise_collection


def _insights(history: list[dict]):
    normalised = normalise_collection({"history": history}, today=date(2026, 7, 7))
    return insights_payload(normalised, "rolling_year", today=date(2026, 7, 7))["musicProfile"]


def test_k_pop_is_data_driven_and_fixed_families_are_not_inserted() -> None:
    profile = _insights([
        {"videoId": f"k{index}", "title": "Song", "artists": [{"name": "FIFTY FIFTY"}], "played": "2026-07-01"}
        for index in range(6)
    ])
    labels = [axis["label"] for axis in profile["axes"]]
    assert labels[0] == "K-pop"
    assert "Classical / Cinematic" not in labels


def test_regional_pop_aliases_stay_distinct() -> None:
    profile = _insights([
        {"videoId": "jay", "title": "Song", "artists": [{"name": "Jay Chou"}], "played": "2026-07-01"},
        {"source": "spotify", "source_track_id": "spotify:track:source", "videoId": "source", "title": "Song", "artists": [{"name": "Unmapped", "genres": ["cantonese pop"]}], "played": "2026-07-02"},
    ])
    labels = {axis["label"] for axis in profile["axes"]}
    assert "Mandopop" in labels
    assert "Cantopop" in labels


def test_low_coverage_does_not_fabricate_axes() -> None:
    profile = _insights([{"videoId": "unknown", "title": "Song", "artists": [{"name": "Unknown artist"}], "played": "2026-07-01"}])
    assert profile["axes"] == []
    assert profile["coverage"] == 0
