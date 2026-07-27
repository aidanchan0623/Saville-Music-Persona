from datetime import date

from app.analysis.musical_age import calculate_musical_age


TODAY = date(2026, 7, 22)


def profile(years: list[int | None]) -> dict:
    tracks = [{"track_id": str(i), "release_year": year, "primary_artist": "Artist", "title": str(i)} for i, year in enumerate(years)]
    events = [{"track_id": str(i), "played_at": TODAY.isoformat(), "is_music_candidate": True} for i in range(len(years))]
    return {"tracks": tracks, "play_events": events, "coverage": {"date_data_available": True, "days_represented": 1, "earliest_detected_play": TODAY.isoformat(), "latest_detected_play": TODAY.isoformat()}, "metadata": {"source": "youtube"}}


def test_weighted_median_range_and_dominant_decade() -> None:
    result = calculate_musical_age(profile([2010, 2010, 2010, 2020, 2025]), today=TODAY)
    assert result["weightedMedianReleaseYear"] == 2010
    assert result["age"] == 16
    assert result["likelyMin"] == 6 and result["likelyMax"] == 16
    assert result["dominantDecade"] == "2010s"


def test_musical_age_is_only_release_year_dependent() -> None:
    base = profile([2005, 2010, 2015, 2020])
    noisy = {**base, "repeat": 100, "discovery": 0, "personality": "anything"}
    assert calculate_musical_age(base, today=TODAY)["age"] == calculate_musical_age(noisy, today=TODAY)["age"]


def test_missing_years_lower_confidence() -> None:
    assert calculate_musical_age(profile([2010] * 20), today=TODAY)["confidence"] > calculate_musical_age(profile([2010, None] * 10), today=TODAY)["confidence"]
