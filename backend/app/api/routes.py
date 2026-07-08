from __future__ import annotations

import shutil
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.analysis.duration import annotate_normalised_durations
from app.analysis.demo_data import demo_raw_collection
from app.analysis.music_character import character_payload
from app.analysis.normalizer import normalise_collection
from app.analysis.periods import (
    album_songs_payload,
    albums_payload,
    artist_songs_payload,
    filter_events,
    listening_minutes_payload,
    normalised_for_events,
    resolve_period,
    taste_dna_comparison_payload,
    taste_dna_payload,
    top_payload,
)
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
    TakeoutImportResponse,
)
from app.services.ollama_service import OllamaService
from app.services.recommendations import generate_recommendations
from app.services.takeout_service import TakeoutParseError, parse_takeout_upload
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


def normalise_with_duration_cache(
    raw: dict[str, Any],
    warnings: list[str] | None = None,
    allow_enrichment: bool = False,
    allow_artist_image_enrichment: bool = False,
) -> dict[str, Any]:
    artist_cache = repo.load_json("artist_image_cache") or {}
    if artist_cache:
        raw["artist_image_cache"] = {**artist_cache, **(raw.get("artist_image_cache") or {})}
    if allow_artist_image_enrichment:
        try:
            stats = ytmusic.enrich_artist_image_cache(raw, artist_cache)
            if stats.get("seeded") or stats.get("attempted"):
                repo.save_json("artist_image_cache", artist_cache)
                if warnings is not None:
                    warnings.append(
                        f"Artist image cache checked {stats['attempted']} artist(s), added {stats['added']} official image(s), and reused {stats['seeded']} library artist image(s)."
                    )
        except Exception as exc:  # noqa: BLE001
            if warnings is not None:
                warnings.append(f"Artist image enrichment skipped: {exc}")
    normalised = normalise_collection(raw)
    duration_cache = repo.load_json("duration_cache") or {}
    if duration_cache:
        normalised = annotate_normalised_durations(normalised, duration_cache)
    if allow_enrichment:
        try:
            stats = ytmusic.enrich_duration_cache(normalised, duration_cache, settings.duration_enrichment_limit)
            if stats.get("attempted"):
                repo.save_json("duration_cache", duration_cache)
                normalised = annotate_normalised_durations(normalised, duration_cache)
                if warnings is not None:
                    warnings.append(
                        f"Duration enrichment checked {stats['attempted']} track(s), added {stats['added']} usable duration(s), and cached {stats['failed']} unavailable result(s)."
                    )
        except Exception as exc:  # noqa: BLE001
            if warnings is not None:
                warnings.append(f"Duration enrichment skipped: {exc}")
    return normalised


def analysis_for_period(period: str, month: str | None, timezone_name: str | None) -> tuple[dict[str, Any], dict[str, Any], int]:
    normalised = require_cache("normalised")
    spec = resolve_period(normalised, period, month, timezone_name or settings.local_timezone)
    events = filter_events(normalised, spec)
    period_normalised = normalised_for_events(normalised, events, spec)
    return build_analysis(period_normalised), spec, len(events)


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
        local_timezone=settings.local_timezone,
        duration_enrichment_limit=settings.duration_enrichment_limit,
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
        live_connected = False
    else:
        takeout_history = repo.load_json("takeout_history")
        status = ytmusic.auth_status()
        live_connected = bool(status["connected"])
        if not status["connected"] and not takeout_history:
            raise HTTPException(status_code=400, detail={"error": "YouTube Music is not connected", "detail": status["message"], "code": "ytmusic_not_connected"})
        if status["connected"]:
            raw = ytmusic.fetch_library()
            warnings.extend(raw.get("warnings") or [])
            ytmusic.save_raw_snapshot(settings.raw_dir, raw)
        else:
            raw = {"source": "google_takeout", "history": [], "warnings": []}
            warnings.append(f"Live YouTube Music sync skipped: {status['message']}")
    takeout_history = repo.load_json("takeout_history")
    if takeout_history:
        raw["takeout_history"] = takeout_history
        warnings.append("Google Takeout history is merged as the longest available play-history source.")
    normalised = normalise_with_duration_cache(
        raw,
        warnings,
        allow_enrichment=(not request.use_demo and request.enrich_durations),
        allow_artist_image_enrichment=live_connected,
    )
    refreshed_at = datetime.now(timezone.utc).isoformat()
    normalised["refreshed_at"] = refreshed_at
    normalised = annotate_normalised_durations(normalised, repo.load_json("duration_cache") or {})
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


@router.post("/data/import-takeout", response_model=TakeoutImportResponse)
async def import_takeout(file: UploadFile = File(...)) -> TakeoutImportResponse:
    settings.ensure_local_dirs()
    content = await file.read()
    try:
        entries = parse_takeout_upload(file.filename or "takeout", content)
    except TakeoutParseError as exc:
        raise HTTPException(status_code=400, detail={"error": "Takeout import failed", "detail": str(exc), "code": "takeout_import_failed"}) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"error": "Takeout import failed", "detail": f"Could not parse this Takeout file: {exc}", "code": "takeout_import_failed"}) from exc
    repo.save_json("takeout_history", entries)
    raw = repo.load_json("raw") or {"source": "takeout_import", "history": []}
    raw["takeout_history"] = entries
    ytmusic_connected = bool(ytmusic.auth_status()["connected"])
    normalised = normalise_with_duration_cache(
        raw,
        warnings := ["Google Takeout history imported and merged with local metadata."],
        allow_enrichment=False,
        allow_artist_image_enrichment=ytmusic_connected,
    )
    refreshed_at = datetime.now(timezone.utc).isoformat()
    normalised["refreshed_at"] = refreshed_at
    normalised = annotate_normalised_durations(normalised, repo.load_json("duration_cache") or {})
    analysis = build_analysis(normalised)
    repo.save_json("raw", raw)
    repo.save_json("normalised", normalised)
    repo.save_json("analysis", analysis)
    repo.save_json(
        "last_refresh_meta",
        {"refreshed_at": refreshed_at, "use_demo": False, "warnings": warnings},
    )
    dated = sorted(entry["played"] for entry in entries if entry.get("played"))
    return TakeoutImportResponse(
        imported_count=len(entries),
        earliest_play=dated[0] if dated else None,
        latest_play=dated[-1] if dated else None,
        message="Google Takeout history imported. Dashboard analysis was rebuilt with the longest available history source.",
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
def scores(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> list[dict[str, Any]]:
    analysis, spec, event_count = analysis_for_period(period, month, timezone_name)
    scores_payload = analysis["scores"]
    if spec["period"] in {"this_month", "month"} and event_count < 50:
        for score in scores_payload:
            score.setdefault("inputs", {})["confidence_note"] = "Limited sample for this month"
    for score in scores_payload:
        score.setdefault("inputs", {})["period_label"] = spec["label"]
        score.setdefault("inputs", {})["period_detected_plays"] = event_count
    return scores_payload


@router.get("/analysis/charts")
def charts(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    analysis, _, _ = analysis_for_period(period, month, timezone_name)
    return analysis["charts"]


@router.get("/analytics/listening-minutes")
def listening_minutes(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    return listening_minutes_payload(require_cache("normalised"), period, month, timezone_name or settings.local_timezone)


@router.get("/analytics/listening-minutes/daily")
def listening_minutes_daily(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> list[dict[str, Any]]:
    return listening_minutes_payload(require_cache("normalised"), period, month, timezone_name or settings.local_timezone)["daily"]


@router.get("/analytics/listening-minutes/heatmap")
def listening_minutes_heatmap(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> list[dict[str, Any]]:
    return listening_minutes_payload(require_cache("normalised"), period, month, timezone_name or settings.local_timezone)["heatmap"]


@router.get("/top")
def period_top(
    period: str = Query("this_month"),
    type: str = Query("tracks"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    kind = "artists" if type == "artists" else "tracks"
    return top_payload(require_cache("normalised"), kind, period, month, timezone_name or settings.local_timezone)


@router.get("/top/artist-songs")
def period_artist_songs(
    artist: str = Query(...),
    period: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    return artist_songs_payload(require_cache("normalised"), artist, period, month, timezone_name or settings.local_timezone)


@router.get("/top/albums")
def period_albums(
    period: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    return albums_payload(require_cache("normalised"), period, month, timezone_name or settings.local_timezone)


@router.get("/top/album-songs")
def period_album_songs(
    album: str = Query(...),
    artist: str | None = Query(None),
    period: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    return album_songs_payload(require_cache("normalised"), album, artist, period, month, timezone_name or settings.local_timezone)


@router.get("/taste-dna")
def taste_dna(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    return taste_dna_payload(require_cache("normalised"), period, month, timezone_name or settings.local_timezone)


@router.get("/taste-dna/compare")
def taste_dna_compare(
    base: str = Query("rolling_year"),
    compare: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    return taste_dna_comparison_payload(require_cache("normalised"), base, compare, month, timezone_name or settings.local_timezone)


@router.get("/scores/interpretations")
def score_interpretations(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> list[dict[str, Any]]:
    return scores(period, month, timezone_name)


@router.get("/persona/character")
def persona_character(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
) -> dict[str, Any]:
    return character_payload(require_cache("normalised"), period, month, timezone_name or settings.local_timezone)


@router.post("/persona/character/rewrite")
def persona_character_rewrite(payload: dict[str, Any]) -> dict[str, Any]:
    period = str(payload.get("period") or "rolling_year")
    month = payload.get("month")
    mode = str(payload.get("mode") or "playful")
    profile = character_payload(require_cache("normalised"), period, str(month) if month else None, settings.local_timezone)
    status = ollama.status()
    if not status["reachable"] or not status["model_installed"]:
        raise HTTPException(status_code=503, detail={"error": "Ollama rewrite unavailable", "detail": status["message"], "code": "ollama_unavailable"})
    return ollama.generate_character_rewrite(profile, mode)


def report_profile_with_characters() -> dict[str, Any]:
    normalised = require_cache("normalised")
    analysis = require_cache("analysis")
    profile = dict(analysis["report_profile"])
    rolling_character = character_payload(normalised, "rolling_year", timezone_name=settings.local_timezone)
    current_character = character_payload(normalised, "this_month", timezone_name=settings.local_timezone)
    profile["music_character"] = rolling_character
    profile["current_month_character"] = current_character
    profile["current_vs_long_term"] = character_comparison(rolling_character, current_character)
    profile["plain_language_scores"] = plain_language_scores(profile.get("scores", []))
    profile["listener_axis"] = listener_axis(profile, rolling_character)
    profile["album_or_track_behavior"] = album_or_track_behavior(rolling_character)
    return profile


def character_comparison(rolling: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    rolling_primary = rolling.get("primary") if isinstance(rolling.get("primary"), dict) else {}
    current_primary = current.get("primary") if isinstance(current.get("primary"), dict) else {}
    rolling_id = rolling_primary.get("id")
    current_id = current_primary.get("id")
    has_current_sample = bool((current.get("period") or {}).get("start_date")) if isinstance(current.get("period"), dict) else False
    return {
        "rolling_year": rolling_primary.get("name"),
        "current_month": current_primary.get("name"),
        "has_contrast": bool(has_current_sample and rolling_id and current_id and rolling_id != current_id),
        "rolling_roast": rolling_primary.get("roast"),
        "current_roast": current_primary.get("roast"),
    }


def plain_language_scores(scores: list[Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for score in scores:
        if not isinstance(score, dict):
            continue
        key = str(score.get("key") or score.get("name") or "").strip()
        interpretation = score.get("interpretation") if isinstance(score.get("interpretation"), dict) else {}
        label = str(score.get("label") or "")
        plain = str(interpretation.get("plain_english") or "")
        if key:
            result[key] = plain or label
    return result


def listener_axis(profile: dict[str, Any], character: dict[str, Any]) -> dict[str, str]:
    scores = {str(item.get("key") or item.get("name")): item for item in profile.get("scores", []) if isinstance(item, dict)}
    loyalty_value = float((scores.get("artist_loyalty") or {}).get("value") or 0)
    discovery_value = float((scores.get("discovery") or {}).get("value") or 0)
    repeat_value = float((scores.get("repeat") or {}).get("value") or 0)
    primary = character.get("primary") if isinstance(character.get("primary"), dict) else {}
    modifier = character.get("modifier") if isinstance(character.get("modifier"), dict) else {}
    artist_or_sound = (
        "The profile is artist-led: a small set of artists acts as the main anchor."
        if loyalty_value >= 65 or primary.get("id") == "one_artist_cult_member"
        else "The profile is sound-led: the larger emotional and sonic world matters more than one artist owning everything."
    )
    discovery_or_comfort = (
        "Discovery is active, but it still seems to chase a familiar emotional shape."
        if discovery_value >= 55
        else "Discovery is selective; comfort and fit matter more than constant novelty."
    )
    repeat_or_variety = (
        "Replay is a major behaviour pattern, so songs become part of the identity by surviving repeat listens."
        if repeat_value >= 55 or modifier.get("id") in {"comfort_loop_specialist", "single_song_prisoner"}
        else "The profile leaves more room for rotation and variety than pure fixation."
    )
    return {
        "artist_or_sound_led": artist_or_sound,
        "discovery_or_comfort": discovery_or_comfort,
        "repeat_or_variety": repeat_or_variety,
    }


def album_or_track_behavior(character: dict[str, Any]) -> str:
    modifier = character.get("modifier") if isinstance(character.get("modifier"), dict) else {}
    modifier_id = modifier.get("id")
    if modifier_id == "album_loyalist":
        return "The profile has album-depth behaviour: full projects matter, not just isolated singles."
    if modifier_id == "single_song_prisoner":
        return "The profile has track-fixation behaviour: a few songs can dominate the phase once they click."
    return "Album-vs-track behaviour is not the loudest signal, so the character read leans more on sound, replay, and artist patterns."


@router.post("/report/generate")
def generate_report(request: ReportRequest) -> dict[str, Any]:
    profile = report_profile_with_characters()
    status = ollama.status()
    if not status["reachable"] or not status["model_installed"]:
        raise HTTPException(status_code=503, detail={"error": "Ollama report unavailable", "detail": status["message"], "code": "ollama_unavailable"})
    report = ollama.generate_report(profile, request.mode)
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
