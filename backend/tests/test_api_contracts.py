from __future__ import annotations

import pytest
from datetime import date
from pydantic import ValidationError

from app.analysis.insights import insights_payload
from app.analysis.normalizer import normalise_collection
from app.analysis.overview import build_overview_response
from app.analysis.period_profile import build_period_profile
from app.api.routes import analytics_envelope
from app.schemas.contracts import ContractDataQuality


def fixture_normalised() -> dict:
    return normalise_collection(
        {
            "source": "google_takeout",
            "takeout_import_batch_id": "fixture-batch",
            "takeout_parser_schema_version": 3,
            "history": [
                {"videoId": "first", "title": "First", "artists": [{"name": "Artist One"}], "played": "2026-07-02T10:00:00+00:00", "duration_seconds": 180},
                {"videoId": "first", "title": "First", "artists": [{"name": "Artist One"}], "played": "2026-07-03T10:00:00+00:00", "duration_seconds": 180},
                {"videoId": "second", "title": "Second", "artists": [{"name": "Artist Two"}], "played": "2026-07-04T10:00:00+00:00", "duration_seconds": 240},
            ],
        }
    )


def test_envelope_projects_one_canonical_period_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.analysis.periods.local_today", lambda _timezone=None: date(2026, 7, 7))
    normalised = fixture_normalised()
    profile = build_period_profile(normalised, "this_month", timezone_name="Asia/Kuala_Lumpur")
    overview = build_overview_response(normalised, "this_month", timezone_name="Asia/Kuala_Lumpur")
    insights = insights_payload(normalised, "this_month", timezone_name="Asia/Kuala_Lumpur")
    envelope = analytics_envelope("youtube", profile, normalised, overview)

    assert envelope.apiSchemaVersion == 1
    assert envelope.period.timezone == "Asia/Kuala_Lumpur"
    assert envelope.dataQuality.acceptedPlayCount == profile["figures"]["accepted_play_count"]
    assert overview["overview"]["canonical_figures"]["accepted_play_count"] == insights["canonicalFigures"]["accepted_play_count"]
    assert overview["overview"]["canonical_figures"]["detected_minutes"] == insights["summary"]["detectedMinutes"]
    assert overview["topFive"]["artists"][0]["name"] == profile["top_artists"][0]["artist"]
    assert overview["topFive"]["songs"][0]["title"] == profile["top_tracks"][0]["title"]


def test_contract_percentages_are_bounded() -> None:
    with pytest.raises(ValidationError):
        ContractDataQuality(
            acceptedPlayCount=1,
            timestampCoverage=101,
            durationCoverage=50,
            genreCoverage=0,
            releaseYearCoverage=0,
        )


def test_overview_active_days_and_range_follow_selected_timezone() -> None:
    normalised = normalise_collection({"history": [
        {"videoId": "first", "title": "First", "artists": [{"name": "Artist One"}], "played": "2026-06-30T17:00:00Z", "duration_seconds": 180},
        {"videoId": "second", "title": "Second", "artists": [{"name": "Artist Two"}], "played": "2026-07-01T10:00:00Z", "duration_seconds": 180},
    ]})
    response = build_overview_response(normalised, "month", "2026-07", "Asia/Kuala_Lumpur", today=date(2026, 7, 7))
    coverage = response["overview"]["coverage"]
    assert coverage["days_represented"] == 1
    assert coverage["earliest_detected_play"] == "2026-07-01"
    assert coverage["latest_detected_play"] == "2026-07-01"
    assert response["overview"]["canonical_figures"]["active_days"] == 1
