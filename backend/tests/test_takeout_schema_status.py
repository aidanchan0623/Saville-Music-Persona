from __future__ import annotations

from app.api.routes import takeout_reimport_status
from app.analysis.normalizer import NORMALISED_DATA_SCHEMA_VERSION
from app.models.listening_event import LISTENING_EVENT_SCHEMA_VERSION
from app.services.takeout_service import TAKEOUT_PARSER_SCHEMA_VERSION
from app.api import routes
from app.analysis.demo_data import demo_raw_collection
from app.analysis.normalizer import normalise_collection
from app.analysis.period_profile import build_period_profile
from app.database.repository import JsonRepository
from fastapi import HTTPException
import pytest


def test_old_takeout_metadata_requires_a_reimport() -> None:
    status = takeout_reimport_status({"parser_schema_version": 1, "event_schema_version": 1, "data_schema_version": 1})
    assert status["requiresReimport"] is True
    assert status["currentParserVersion"] == TAKEOUT_PARSER_SCHEMA_VERSION


def test_current_takeout_metadata_is_usable() -> None:
    status = takeout_reimport_status(
        {
            "parser_schema_version": TAKEOUT_PARSER_SCHEMA_VERSION,
            "event_schema_version": LISTENING_EVENT_SCHEMA_VERSION,
            "data_schema_version": NORMALISED_DATA_SCHEMA_VERSION,
        }
    )
    assert status["requiresReimport"] is False


def test_demo_without_a_takeout_import_has_usable_analytics(tmp_path, monkeypatch) -> None:
    repository = JsonRepository(tmp_path / "demo.db")
    monkeypatch.setattr(routes, "repo", repository)
    normalised = normalise_collection(demo_raw_collection())
    profile = build_period_profile(normalised, "rolling_year")
    envelope = routes.analytics_envelope("youtube", profile, normalised, {})
    assert envelope.status in {"complete", "partial"}
    assert envelope.dataQuality.acceptedPlayCount > 0
    assert all(w.code != "TAKEOUT_REIMPORT_REQUIRED" for w in envelope.warnings)


def test_demo_is_usable_while_a_previous_takeout_import_needs_migration(tmp_path, monkeypatch) -> None:
    repository = JsonRepository(tmp_path / "demo-over-import.db")
    monkeypatch.setattr(routes, "repo", repository)
    normalised = normalise_collection(demo_raw_collection())
    repository.save_json("normalised", normalised)
    repository.save_json("takeout_history", [{"title": "Old fixture"}])
    repository.save_json(routes.TAKEOUT_CACHE_METADATA_KEY, {"parser_schema_version": 1})
    assert routes.require_cache("normalised")["metadata"]["source"] == "demo"
    envelope = routes.analytics_envelope("youtube", build_period_profile(normalised, "rolling_year"), normalised, {})
    assert envelope.status != "stale_import"
    assert envelope.provenance.importBatchId is None
    assert routes.active_takeout_reimport_status("youtube")["requiresReimport"] is False
    # A real refresh still checks the stored Takeout import before using it.
    with pytest.raises(HTTPException) as exc:
        routes.load_current_takeout_history()
    assert exc.value.status_code == 409
