from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class FriendlyError(BaseModel):
    error: str
    detail: str
    code: str = "request_failed"


class PrerequisiteItem(BaseModel):
    name: str
    available: bool
    detail: str


class PrerequisitesResponse(BaseModel):
    ok: bool
    items: list[PrerequisiteItem]
    ollama_model: str
    ollama_reachable: bool
    model_installed: bool
    local_timezone: str
    duration_enrichment_limit: int


class AuthStatusResponse(BaseModel):
    connected: bool
    auth_file_exists: bool
    auth_file_path: str
    oauth_client_configured: bool
    account_name: str | None = None
    message: str
    cached_data_available: bool = False
    last_refreshed_at: str | None = None


class RefreshRequest(BaseModel):
    use_demo: bool = False
    enrich_durations: bool = False


class RefreshResponse(BaseModel):
    refreshed_at: str
    use_demo: bool
    warnings: list[str] = Field(default_factory=list)
    coverage: dict[str, Any]
    track_count: int
    play_count: int


class TakeoutImportResponse(BaseModel):
    imported_count: int
    earliest_play: str | None = None
    latest_play: str | None = None
    message: str


class OverviewPeriod(BaseModel):
    key: str
    month: str | None = None
    label: str
    timezone: str
    startDate: str
    endDate: str
    availableMonths: list[dict[str, str]] = Field(default_factory=list)


class MostActiveSound(BaseModel):
    label: str
    description: str


class OverviewIdentity(BaseModel):
    characterTitle: str
    tagline: str
    explanation: str
    mostActiveSound: MostActiveSound
    generationSource: Literal["gemma", "cache-gemma", "fallback"]


class MusicalAgeFactors(BaseModel):
    repeatAttachment: float
    discovery: float
    tasteStability: float
    catalogMaturity: float
    albumDepth: float
    crossEraBreadth: float
    emotionalIntensity: float
    reflectiveListening: float


class MusicalAge(BaseModel):
    age: int
    likelyMin: int
    likelyMax: int
    title: str
    summary: str
    explanation: str
    confidence: float
    confidenceLabel: str
    factors: MusicalAgeFactors
    calculationVersion: int
    generationSource: Literal["gemma", "cache-gemma", "fallback"]
    sourcePeriod: OverviewPeriod
    strongestFactors: list[str] = Field(default_factory=list)
    metadataCoverage: dict[str, float] = Field(default_factory=dict)


class TopFiveSong(BaseModel):
    rank: int
    title: str
    artist: str
    album: str | None = None
    imageUrl: str | None = None
    detectedPlays: int
    detectedMinutes: float | None = None


class TopFiveArtist(BaseModel):
    rank: int
    name: str
    imageUrl: str | None = None
    detectedPlays: int
    uniqueSongs: int


class TopFive(BaseModel):
    period: OverviewPeriod
    songs: list[TopFiveSong] = Field(default_factory=list)
    artists: list[TopFiveArtist] = Field(default_factory=list)


class OverviewAnalysisResponse(BaseModel):
    schemaVersion: int
    source: Literal["youtube", "spotify"]
    sourceLabel: str
    selectedPeriod: OverviewPeriod
    musicalAgePeriod: OverviewPeriod
    overview: dict[str, Any]
    identity: OverviewIdentity
    musicalAge: MusicalAge
    topFive: TopFive
    languageFingerprint: str


class ReportRequest(BaseModel):
    mode: Literal["serious", "playful", "roast"] = "serious"
    source: Literal["youtube", "spotify"] = "youtube"


class PlaylistCreateRequest(BaseModel):
    confirm: bool = False
    title: str = "Saville Recommendations"


class PlaylistCreateResponse(BaseModel):
    playlist_id: str
    title: str
    added_count: int
    message: str
