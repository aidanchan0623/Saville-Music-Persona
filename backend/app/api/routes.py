from __future__ import annotations

import shutil
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.analysis.demo_data import demo_raw_collection
from app.analysis.normalizer import normalise_collection
from app.analysis.scoring import build_analysis
from app.config import settings
from app.database.repository import JsonRepository
from app.schemas.responses import (
    AuthStatusResponse,
    PlaylistCreateRequest,
    PlaylistCreateResponse,
    PrerequisiteItem,
    PrerequisitesResponse,
    RefreshRequest,
    RefreshResponse,
    ReportRequest,
)
from app.services.ollama_service import OllamaService
from app.services.recommendations import generate_recommendations
from app.services.ytmusic_service import YTMusicService


router = APIRouter(prefix="/api")
repo = JsonRepository(settings.db_path)
ytmusic = YTMusicService(settings)
ollama = OllamaService(settings)


def require_cache(key: str) -> Any:
    value = repo.load_json(key)
    if value is None:
        raise HTTPException(status_code=404, detail={"error": "No data yet", "detail": "Refresh music data first or enable demo data.", "code": "no_cached_data"})
    return value


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "app": "Saville Music Persona", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/prerequisites", response_model=PrerequisitesResponse)
def prerequisites() -> PrerequisitesResponse:
    ollama_status = ollama.status()
    items = [
        PrerequisiteItem(name="Git", available=shutil.which("git") is not None, detail=shutil.which("git") or "git not found on PATH"),
        PrerequisiteItem(name="Node.js", available=shutil.which("node") is not None, detail=shutil.which("node") or "node not found on PATH"),
        PrerequisiteItem(name="npm", available=shutil.which("npm.cmd") is not None or shutil.which("npm") is not None, detail=shutil.which("npm.cmd") or shutil.which("npm") or "npm not found on PATH"),
        PrerequisiteItem(name="Ollama", available=ollama_status["reachable"], detail=ollama_status["message"]),
    ]
    return PrerequisitesResponse(
        ok=all(item.available for item in items[:-1]) and ollama_status["reachable"] and ollama_status["model_installed"],
        items=items,
        ollama_model=settings.ollama_model,
        ollama_reachable=ollama_status["reachable"],
        model_installed=ollama_status["model_installed"],
    )


@router.get("/auth/status", response_model=AuthStatusResponse)
def auth_status() -> AuthStatusResponse:
    return AuthStatusResponse(**ytmusic.auth_status())


@router.post("/auth/setup")
def auth_setup() -> dict[str, Any]:
    return ytmusic.setup_instructions()


@router.post("/data/refresh", response_model=RefreshResponse)
def refresh_data(request: RefreshRequest) -> RefreshResponse:
    settings.ensure_local_dirs()
    warnings: list[str] = []
    if request.use_demo:
        raw = demo_raw_collection()
        warnings.append("Demo data is enabled; no private account data was fetched.")
    else:
        status = ytmusic.auth_status()
        if not status["connected"]:
            raise HTTPException(status_code=400, detail={"error": "YouTube Music is not connected", "detail": status["message"], "code": "ytmusic_not_connected"})
        raw = ytmusic.fetch_library()
        warnings.extend(raw.get("warnings") or [])
        ytmusic.save_raw_snapshot(settings.raw_dir, raw)
    normalised = normalise_collection(raw)
    refreshed_at = datetime.now(timezone.utc).isoformat()
    normalised["refreshed_at"] = refreshed_at
    analysis = build_analysis(normalised)
    repo.save_json("raw", raw)
    repo.save_json("normalised", normalised)
    repo.save_json("analysis", analysis)
    repo.save_json("last_refresh_meta", {"refreshed_at": refreshed_at, "use_demo": request.use_demo, "warnings": warnings})
    return RefreshResponse(
        refreshed_at=refreshed_at,
        use_demo=request.use_demo,
        warnings=warnings,
        coverage=analysis["coverage"],
        track_count=normalised["metadata"]["track_count"],
        play_count=normalised["metadata"]["play_count"],
    )


@router.get("/data/coverage")
def coverage() -> dict[str, Any]:
    return require_cache("analysis")["coverage"]


@router.get("/analysis/overview")
def overview() -> dict[str, Any]:
    analysis = require_cache("analysis")
    meta = repo.load_json("last_refresh_meta") or {}
    payload = dict(analysis["overview"])
    payload["last_refreshed_at"] = meta.get("refreshed_at")
    payload["use_demo"] = meta.get("use_demo", False)
    payload["warnings"] = meta.get("warnings", [])
    return payload


@router.get("/analysis/top-tracks")
def top_tracks() -> list[dict[str, Any]]:
    return require_cache("analysis")["top_tracks"]


@router.get("/analysis/top-artists")
def top_artists() -> list[dict[str, Any]]:
    return require_cache("analysis")["top_artists"]


@router.get("/analysis/scores")
def scores() -> list[dict[str, Any]]:
    return require_cache("analysis")["scores"]


@router.get("/analysis/charts")
def charts() -> dict[str, Any]:
    return require_cache("analysis")["charts"]


@router.post("/report/generate")
def generate_report(request: ReportRequest) -> dict[str, Any]:
    analysis = require_cache("analysis")
    status = ollama.status()
    if not status["reachable"] or not status["model_installed"]:
        raise HTTPException(status_code=503, detail={"error": "Ollama report unavailable", "detail": status["message"], "code": "ollama_unavailable"})
    report = ollama.generate_report(analysis["report_profile"], request.mode)
    payload = report.model_dump()
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    repo.save_json("latest_report", payload)
    return payload


@router.get("/report/latest")
def latest_report() -> dict[str, Any]:
    return require_cache("latest_report")


@router.get("/recommendations")
def latest_recommendations() -> list[dict[str, Any]]:
    return require_cache("recommendations")


@router.post("/recommendations/generate")
def generate_recommendation_endpoint() -> list[dict[str, Any]]:
    normalised = require_cache("normalised")
    analysis = require_cache("analysis")
    candidates: list[dict[str, Any]] = []
    if (repo.load_json("last_refresh_meta") or {}).get("use_demo") is not True:
        try:
            candidates = ytmusic.search_candidates(analysis)
        except Exception:
            candidates = []
    recommendations = generate_recommendations(normalised, analysis, candidates)
    explanations = ollama.generate_recommendation_explanations(analysis["report_profile"], recommendations)
    if explanations:
        explanation_map = {f"{item['track_title']}::{item['artist']}": item["why_this_fits"] for item in explanations}
        recommendations = generate_recommendations(normalised, analysis, candidates, explanation_map)
    repo.save_json("recommendations", recommendations)
    return recommendations


@router.post("/recommendations/create-playlist", response_model=PlaylistCreateResponse)
def create_playlist(request: PlaylistCreateRequest) -> PlaylistCreateResponse:
    if not request.confirm:
        raise HTTPException(status_code=400, detail={"error": "Confirmation required", "detail": "Playlist creation only runs after explicit confirmation.", "code": "confirmation_required"})
    recommendations = require_cache("recommendations")
    video_ids = [item["video_id"] for item in recommendations if item.get("video_id")]
    if not video_ids:
        raise HTTPException(status_code=400, detail={"error": "No playlist items", "detail": "Recommendations do not include YouTube video IDs.", "code": "missing_video_ids"})
    status = ytmusic.auth_status()
    if not status["connected"]:
        raise HTTPException(status_code=400, detail={"error": "YouTube Music is not connected", "detail": status["message"], "code": "ytmusic_not_connected"})
    playlist_id = ytmusic.create_private_playlist(request.title, video_ids)
    return PlaylistCreateResponse(
        playlist_id=playlist_id,
        title=request.title,
        added_count=len(video_ids),
        message="Private YouTube Music playlist created.",
    )

