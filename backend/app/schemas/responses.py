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


class AuthStatusResponse(BaseModel):
    connected: bool
    auth_file_exists: bool
    auth_file_path: str
    oauth_client_configured: bool
    account_name: str | None = None
    message: str


class RefreshRequest(BaseModel):
    use_demo: bool = False


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


class ReportRequest(BaseModel):
    mode: Literal["serious", "playful", "roast"] = "serious"


class PlaylistCreateRequest(BaseModel):
    confirm: bool = False
    title: str = "Saville Recommendations"


class PlaylistCreateResponse(BaseModel):
    playlist_id: str
    title: str
    added_count: int
    message: str
