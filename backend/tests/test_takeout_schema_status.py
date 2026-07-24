from __future__ import annotations

from app.api.routes import takeout_reimport_status
from app.analysis.normalizer import NORMALISED_DATA_SCHEMA_VERSION
from app.models.listening_event import LISTENING_EVENT_SCHEMA_VERSION
from app.services.takeout_service import TAKEOUT_PARSER_SCHEMA_VERSION


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
