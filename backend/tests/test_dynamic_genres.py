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


def test_each_play_contributes_one_integer_count_to_one_primary_genre() -> None:
    history = [
        {"videoId": f"gem-{index}", "title": f"GEM {index}", "artists": [{"name": "G.E.M."}], "played": "2026-07-01"}
        for index in range(4)
    ] + [
        {"videoId": f"jay-{index}", "title": f"Jay {index}", "artists": [{"name": "周杰倫 Jay Chou"}], "played": "2026-07-02"}
        for index in range(3)
    ]
    profile = _insights(history)
    mandopop = next(axis for axis in profile["axes"] if axis["label"] == "Mandopop")

    assert mandopop["detectedPlays"] == 7
    assert mandopop["value"] == 100.0
    assert all(axis["label"] not in {"C-pop", "R&B / Soul"} for axis in profile["axes"])
    assert all(isinstance(axis["detectedPlays"], int) for axis in profile["axes"])


def test_low_coverage_does_not_fabricate_axes() -> None:
    profile = _insights([{"videoId": "unknown", "title": "Song", "artists": [{"name": "Unknown artist"}], "played": "2026-07-01"}])
    assert profile["axes"] == []
    assert profile["coverage"] == 0


def test_profile_is_limited_to_six_specific_genres_without_other_bucket() -> None:
    profile = _insights([
        {"videoId": f"song-{index}", "title": "Song", "artists": [{"name": artist}], "played": "2026-07-01"}
        for index, artist in enumerate(["Bring Me The Horizon", "My Chemical Romance", "Wisp", "Oasis", "Deftones", "Hans Zimmer", "Radiohead"])
    ])
    assert len(profile["axes"]) <= 6
    assert all(axis["key"] != "other" for axis in profile["axes"])
