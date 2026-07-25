from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


API_SCHEMA_VERSION = 1
AnalyticsStatus = Literal["complete", "partial", "insufficient_data", "stale_import", "processing", "failed"]
T = TypeVar("T")


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContractPeriod(StrictContract):
    type: Literal["this_month", "month", "last_7", "last_30", "rolling_year", "all"]
    month: str | None = None
    start: str
    end: str
    timezone: str
    label: str


class ContractProvenance(StrictContract):
    importBatchId: str | None = None
    dataFingerprint: str
    parserVersion: int | None = None
    eventSchemaVersion: int
    analyticsVersion: int


class ContractDataQuality(StrictContract):
    acceptedPlayCount: int = Field(ge=0)
    timestampCoverage: float = Field(ge=0, le=100)
    durationCoverage: float = Field(ge=0, le=100)
    genreCoverage: float = Field(ge=0, le=100)
    releaseYearCoverage: float = Field(ge=0, le=100)


class ContractWarning(StrictContract):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    affectedFields: list[str] = Field(default_factory=list)


class AnalyticsEnvelope(StrictContract, Generic[T]):
    apiSchemaVersion: Literal[API_SCHEMA_VERSION] = API_SCHEMA_VERSION
    status: AnalyticsStatus
    source: Literal["youtube", "spotify"]
    period: ContractPeriod
    provenance: ContractProvenance
    dataQuality: ContractDataQuality
    warnings: list[ContractWarning] = Field(default_factory=list)
    data: T


class Top10ContractData(StrictContract):
    type: Literal["tracks", "artists"]
    totalPlayCount: int = Field(ge=0)
    totalAvailableResults: int = Field(ge=0)
    items: list[dict[str, Any]] = Field(default_factory=list)
    methodology: str


class RecommendationsContractData(StrictContract):
    items: list[dict[str, Any]] = Field(default_factory=list)
