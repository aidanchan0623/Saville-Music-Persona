from app.analysis.overview_identity import deterministic_identity


def test_unknown_genre_does_not_become_an_asserted_sound():
    identity = deterministic_identity({"topGenre": "unknown"})
    assert identity["mostActiveSound"]["label"] == "Still mapping"
    assert "metadata is incomplete" in identity["explanation"]
    assert "unknown supplies" not in identity["explanation"]
