from __future__ import annotations

from app.api import routes


def _item(index: int) -> dict[str, object]:
    return {"key": f"item-{index}", "artist": f"Artist {index}", "title": f"Track {index}"}


def test_top_endpoints_return_only_ten_ranked_items(monkeypatch) -> None:
    profile = {
        "period": {"period": "this_month"},
        "top_tracks": [_item(index) for index in range(12)],
        "top_artists": [_item(index) for index in range(14)],
        "figures": {"accepted_play_count": 24},
        "minutes": {"duration_quality": {}},
        "genre_shares": {"items": []},
        "dataFingerprint": "fixture",
    }
    monkeypatch.setattr(routes, "require_source_cache", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(routes, "build_period_profile", lambda *_args, **_kwargs: profile)

    tracks = routes.top_tracks()
    artists = routes.top_artists()
    period_tracks = routes.period_top(type="tracks")
    period_artists = routes.period_top(type="artists")

    assert len(tracks) == 10
    assert len(artists) == 10
    assert len(period_tracks["items"]) == 10
    assert len(period_artists["items"]) == 10
    assert period_tracks["totalAvailableResults"] == 12
    assert period_artists["totalAvailableResults"] == 14
    assert [item["rank"] for item in period_tracks["items"]] == list(range(1, 11))
    assert [item["rank"] for item in period_artists["items"]] == list(range(1, 11))
