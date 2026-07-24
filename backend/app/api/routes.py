from __future__ import annotations

import shutil
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse

from app.analysis.duration import annotate_normalised_durations
from app.analysis.demo_data import demo_raw_collection
from app.analysis.insights import insights_payload
from app.analysis.media import ensure_album_image_cache_schema, ensure_artist_image_cache_schema
from app.analysis.music_character import MUSIC_CHARACTER_CLASSIFIER_VERSION, character_payload
from app.analysis.musical_age import MUSICAL_AGE_CALCULATION_VERSION
from app.analysis.normalizer import NORMALISED_DATA_SCHEMA_VERSION, normalise_collection
from app.analysis.period_profile import ANALYTICS_VERSION, GENRE_MAP_VERSION, build_period_profile
from app.models.listening_event import LISTENING_EVENT_SCHEMA_VERSION
from app.analysis.overview import (
    OVERVIEW_LANGUAGE_CACHE_VERSION,
    OVERVIEW_SCHEMA_VERSION,
    apply_overview_language,
    build_overview_response,
    overview_language_evidence,
    overview_language_fingerprint,
)
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
from app.analysis.persona_report import build_persona_report_evidence, compose_persona_report
from app.analysis.spotify_adapter import SPOTIFY_LIMITATION_NOTE, spotify_raw_to_collection
from app.config import settings
from app.database.repository import JsonRepository
from app.schemas.responses import (
    AuthStatusResponse,
    InsightsResponse,
    OverviewAnalysisResponse,
    PlaylistCreateRequest,
    PlaylistCreateResponse,
    PrerequisiteItem,
    PrerequisitesResponse,
    PersonaReportResponse,
    RefreshRequest,
    RefreshResponse,
    ReportRequest,
    TakeoutImportQueuedResponse,
    TakeoutImportStatusResponse,
)
from app.services.ollama_service import OllamaService
from app.services.recommendations import generate_recommendations
from app.services.spotify_service import SpotifyService
from app.services.takeout_import_jobs import (
    TakeoutImportAlreadyRunning,
    TakeoutImportCoordinator,
    TakeoutImportTimedOut,
)
from app.services.takeout_service import TAKEOUT_PARSER_SCHEMA_VERSION, TakeoutParseError, parse_takeout_file
from app.services.ytmusic_service import YTMusicService


router = APIRouter(prefix="/api")
repo = JsonRepository(settings.db_path)
ytmusic = YTMusicService(settings)
ollama = OllamaService(settings)
spotify = SpotifyService(settings)
takeout_imports = TakeoutImportCoordinator(repo, settings.takeout_import_timeout_seconds)

PERSONA_REPORT_SCHEMA_VERSION = 5
PERSONA_REPORT_PROMPT_VERSION = 5
PERSONA_REPORT_PERIOD = "rolling_year"
OVERVIEW_FALLBACK_CACHE_SECONDS = 300
INSIGHTS_RESPONSE_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}
INSIGHTS_RESPONSE_CACHE_LIMIT = 24
TAKEOUT_CACHE_METADATA_KEY = "takeout_history_meta"

SPOTIFY_CACHE_KEYS = [
    "spotify_tokens",
    "spotify_profile",
    "spotify_raw",
    "spotify_normalised",
    "spotify_analysis",
    "spotify_last_refresh_meta",
    "spotify_latest_report",
    "spotify_recommendations",
    "spotify_oauth_state",
]


def persona_report_fingerprint(profile: dict[str, Any]) -> str:
    compact = {key: value for key, value in profile.items() if key != "languageEvidence"}
    payload = json.dumps(compact, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def persona_report_cache_key(source: str, mode: str, analytics_fingerprint: str) -> str:
    model_fingerprint = hashlib.sha256(settings.ollama_model.encode("utf-8")).hexdigest()[:8]
    return (
        f"persona_report:{source}:{PERSONA_REPORT_PERIOD}:v{PERSONA_REPORT_SCHEMA_VERSION}:"
        f"analytics{ANALYTICS_VERSION}:genre{GENRE_MAP_VERSION}:"
        f"calc{MUSICAL_AGE_CALCULATION_VERSION}:classifier{MUSIC_CHARACTER_CLASSIFIER_VERSION}:"
        f"prompt{PERSONA_REPORT_PROMPT_VERSION}:"
        f"model{model_fingerprint}:{analytics_fingerprint}:{mode}"
    )


def persona_report_pointer_key(source: str) -> str:
    return f"persona_report_pointer:{source}:{PERSONA_REPORT_PERIOD}:v{PERSONA_REPORT_SCHEMA_VERSION}"

def require_cache(key: str) -> Any:
    if key in {"normalised", "analysis", "recommendations"}:
        validate_takeout_cache_schema()
    value = repo.load_json(key)
    if value is None:
        raise HTTPException(status_code=404, detail={"error": "No data yet", "detail": "Refresh music data first or enable demo data.", "code": "no_cached_data"})
    return value


def normalise_source(source: str | None) -> str:
    value = (source or "youtube").strip().lower()
    if value in {"youtube", "ytmusic", "youtube_music"}:
        return "youtube"
    if value == "spotify":
        return "spotify"
    raise HTTPException(status_code=400, detail={"error": "Unknown music source", "detail": "Use source=youtube or source=spotify.", "code": "unknown_source"})


def cache_key(key: str, source: str | None = "youtube") -> str:
    return key if normalise_source(source) == "youtube" else f"spotify_{key}"


def require_source_cache(key: str, source: str | None = "youtube") -> Any:
    resolved_source = normalise_source(source)
    if resolved_source == "youtube":
        return require_cache(key)
    value = repo.load_json(cache_key(key, resolved_source))
    if value is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "No Spotify data yet",
                "detail": "Connect Spotify in Settings, then refresh Spotify data.",
                "code": "no_spotify_data",
            },
        )
    return value


def load_current_takeout_history() -> list[dict[str, Any]] | None:
    validate_takeout_cache_schema()
    history = repo.load_json("takeout_history")
    return history if isinstance(history, list) and history else None


def validate_takeout_cache_schema() -> None:
    if repo.updated_at("takeout_history") is None:
        return
    metadata = repo.load_json(TAKEOUT_CACHE_METADATA_KEY)
    if (
        not isinstance(metadata, dict)
        or metadata.get("parser_schema_version") != TAKEOUT_PARSER_SCHEMA_VERSION
        or metadata.get("event_schema_version") != LISTENING_EVENT_SCHEMA_VERSION
        or metadata.get("data_schema_version") != NORMALISED_DATA_SCHEMA_VERSION
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Google Takeout data needs to be re-imported",
                "detail": "The listening-event schema changed. Re-upload the Takeout JSON, HTML, or ZIP so analytics can be rebuilt accurately.",
                "code": "takeout_event_schema_outdated",
            },
        )


def ensure_youtube_artist_images() -> None:
    analysis = repo.load_json("analysis")
    normalised_cache = repo.load_json("normalised")
    missing_artists = missing_artist_image_names(analysis, normalised_cache)
    if not missing_artists:
        return
    raw = repo.load_json("raw")
    if not isinstance(raw, dict):
        return
    warnings: list[str] = []
    normalised = normalise_with_duration_cache(raw, warnings, allow_artist_image_enrichment=True, preferred_artist_images=missing_artists)
    refreshed_at = (repo.load_json("last_refresh_meta") or {}).get("refreshed_at") or datetime.now(timezone.utc).isoformat()
    normalised["refreshed_at"] = refreshed_at
    normalised = annotate_normalised_durations(normalised, repo.load_json("duration_cache") or {})
    rebuilt = build_analysis(normalised)
    repo.save_json("raw", raw)
    repo.save_json("normalised", normalised)
    repo.save_json("analysis", rebuilt)
    if warnings:
        meta = repo.load_json("last_refresh_meta") or {"refreshed_at": refreshed_at, "use_demo": False, "warnings": []}
        meta["warnings"] = list(dict.fromkeys([*(meta.get("warnings") or []), *warnings]))
        repo.save_json("last_refresh_meta", meta)


def top_artist_images_missing(analysis: Any) -> bool:
    if not isinstance(analysis, dict):
        return False
    top_artists = analysis.get("top_artists") or []
    return any(isinstance(artist, dict) and not artist.get("image") for artist in top_artists[:5])


def missing_artist_image_names(analysis: Any, normalised: Any) -> list[str]:
    names: list[str] = []
    if isinstance(analysis, dict):
        for key, limit in (("top_3_artists", 3), ("top_artists", 8)):
            for artist in (analysis.get(key) or [])[:limit]:
                if isinstance(artist, dict) and artist.get("artist") and not artist.get("image"):
                    names.append(str(artist["artist"]))
    if isinstance(normalised, dict):
        try:
            current = top_payload(normalised, "artists", "this_month", timezone_name=settings.local_timezone)
            for artist in (current.get("items") or [])[:10]:
                if isinstance(artist, dict) and artist.get("artist") and not artist.get("thumbnail"):
                    names.append(str(artist["artist"]))
        except Exception:  # noqa: BLE001
            pass
    seen: set[str] = set()
    result: list[str] = []
    for name in names:
        key = " ".join(name.lower().split())
        if key and key not in seen:
            seen.add(key)
            result.append(name)
    return result


def normalise_with_duration_cache(
    raw: dict[str, Any],
    warnings: list[str] | None = None,
    allow_enrichment: bool = False,
    allow_artist_image_enrichment: bool = False,
    allow_album_image_enrichment: bool = False,
    preferred_artist_images: list[str] | None = None,
) -> dict[str, Any]:
    artist_cache = ensure_artist_image_cache_schema(repo.load_json("artist_image_cache_v2") or {})
    album_cache = ensure_album_image_cache_schema(repo.load_json("album_image_cache_v1") or {})
    raw.pop("artist_image_cache", None)
    raw.pop("album_image_cache", None)
    raw["artist_image_cache_v2"] = artist_cache
    raw["album_image_cache_v1"] = album_cache
    repo.delete_json("artist_image_cache")
    repo.delete_json("album_image_cache")
    if artist_cache:
        raw["artist_image_cache_v2"] = artist_cache
    if album_cache:
        raw["album_image_cache_v1"] = album_cache
    if allow_artist_image_enrichment:
        try:
            stats = ytmusic.enrich_artist_image_cache(raw, artist_cache, preferred_artists=preferred_artist_images)
            if stats.get("seeded") or stats.get("attempted"):
                repo.save_json("artist_image_cache_v2", artist_cache)
                if warnings is not None:
                    warnings.append(
                        f"Artist image cache checked {stats['attempted']} artist(s), added {stats['added']} official image(s), and reused {stats['seeded']} library artist image(s)."
                    )
        except Exception as exc:  # noqa: BLE001
            if warnings is not None:
                warnings.append(f"Artist image enrichment skipped: {exc}")
    if allow_album_image_enrichment:
        try:
            stats = ytmusic.enrich_album_image_cache(raw, album_cache)
            if stats.get("seeded") or stats.get("attempted"):
                repo.save_json("album_image_cache_v1", album_cache)
                if warnings is not None:
                    warnings.append(
                        f"Album image cache checked {stats['attempted']} album(s), added {stats['added']} official cover(s), and reused {stats['seeded']} library album cover(s)."
                    )
        except Exception as exc:  # noqa: BLE001
            if warnings is not None:
                warnings.append(f"Album image enrichment skipped: {exc}")
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


def analysis_for_period(period: str, month: str | None, timezone_name: str | None, source: str | None = "youtube") -> tuple[dict[str, Any], dict[str, Any], int]:
    normalised = require_source_cache("normalised", source)
    spec = resolve_period(normalised, period, month, timezone_name or settings.local_timezone)
    events = filter_events(normalised, spec)
    period_normalised = normalised_for_events(normalised, events, spec)
    return build_analysis(period_normalised), spec, len(events)


def rebuild_spotify_cache() -> dict[str, Any]:
    settings.ensure_local_dirs()
    raw = spotify.fetch_all(repo)
    repo.save_json("spotify_profile", raw.get("profile") or {})
    collection = spotify_raw_to_collection(raw)
    normalised = normalise_collection(collection)
    refreshed_at = datetime.now(timezone.utc).isoformat()
    normalised["refreshed_at"] = refreshed_at
    normalised = annotate_normalised_durations(normalised, repo.load_json("duration_cache") or {})
    analysis = build_analysis(normalised)
    repo.save_json("spotify_raw", raw)
    repo.save_json("spotify_normalised", normalised)
    repo.save_json("spotify_analysis", analysis)
    repo.save_json("spotify_last_refresh_meta", {"refreshed_at": refreshed_at, "warnings": [SPOTIFY_LIMITATION_NOTE], "use_demo": False})
    return {
        "refreshed_at": refreshed_at,
        "warnings": [SPOTIFY_LIMITATION_NOTE],
        "coverage": analysis["coverage"],
        "track_count": normalised["metadata"]["track_count"],
        "play_count": normalised["metadata"]["play_count"],
        "profile": raw.get("profile") or {},
    }


def quick_youtube_auth_status() -> dict[str, Any]:
    browser_file_exists = settings.ytmusic_browser_auth_file.exists()
    oauth_file_exists = settings.ytmusic_auth_file.exists()
    cached_data_available = repo.load_json("normalised") is not None
    if browser_file_exists:
        auth_file_path = settings.ytmusic_browser_auth_file
    else:
        auth_file_path = settings.ytmusic_auth_file
    if cached_data_available:
        message = "Cached YouTube Music profile is available. Use Recheck Connection to test live YouTube auth."
    elif browser_file_exists or oauth_file_exists:
        message = "Saved YouTube auth file exists. Use Recheck Connection to verify live YouTube access."
    else:
        message = "No YouTube auth file found. Import Google Takeout or set up YouTube Music auth in Settings."
    return {
        "connected": False,
        "auth_file_exists": browser_file_exists or oauth_file_exists,
        "auth_file_path": str(auth_file_path),
        "oauth_client_configured": bool(settings.ytmusic_client_id and settings.ytmusic_client_secret),
        "account_name": None,
        "message": message,
    }


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
def auth_status(live: bool = Query(False)) -> AuthStatusResponse:
    status = ytmusic.auth_status() if live else quick_youtube_auth_status()
    meta = repo.load_json("last_refresh_meta") or {}
    return AuthStatusResponse(
        **status,
        cached_data_available=repo.load_json("normalised") is not None,
        last_refreshed_at=meta.get("refreshed_at"),
    )


@router.post("/auth/setup")
def auth_setup() -> dict[str, Any]:
    return ytmusic.setup_instructions()


@router.get("/spotify/status")
def spotify_status() -> dict[str, Any]:
    return spotify.status(repo)


@router.get("/spotify/health")
def spotify_health() -> dict[str, Any]:
    return {"ok": True, "spotify_router": "registered"}


@router.get("/spotify/login")
def spotify_login() -> RedirectResponse:
    state = spotify.new_state()
    repo.save_json("spotify_oauth_state", {"state": state, "created_at": datetime.now(timezone.utc).isoformat()})
    try:
        return RedirectResponse(spotify.login_url(state))
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Spotify is not configured. Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, "
                "and SPOTIFY_REDIRECT_URI in backend/private/.env."
            ),
        ) from exc


@router.get("/spotify/callback")
def spotify_callback(
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
) -> RedirectResponse:
    if error:
        return RedirectResponse(f"{settings.frontend_url}?source=spotify&spotify_error={error}")
    if not code:
        raise HTTPException(status_code=400, detail={"error": "Spotify callback failed", "detail": "Spotify did not return an authorization code.", "code": "spotify_missing_code"})
    stored_state = repo.load_json("spotify_oauth_state") or {}
    if stored_state.get("state") and state != stored_state.get("state"):
        raise HTTPException(status_code=400, detail={"error": "Spotify callback failed", "detail": "OAuth state did not match.", "code": "spotify_state_mismatch"})
    tokens = spotify.exchange_code(code)
    repo.save_json("spotify_tokens", tokens)
    repo.delete_json("spotify_oauth_state")
    try:
        rebuild_spotify_cache()
    except Exception as exc:  # noqa: BLE001
        repo.save_json(
            "spotify_last_refresh_meta",
            {
                "refreshed_at": datetime.now(timezone.utc).isoformat(),
                "warnings": [f"Spotify connected, but initial data refresh failed: {exc}"],
                "use_demo": False,
            },
        )
    return RedirectResponse(f"{settings.frontend_url}?source=spotify")


@router.post("/spotify/disconnect")
def spotify_disconnect() -> dict[str, Any]:
    repo.delete_json_many(SPOTIFY_CACHE_KEYS)
    return {"connected": False, "message": "Spotify disconnected. YouTube Music and Google Takeout data were left untouched."}


@router.post("/spotify/refresh")
def spotify_refresh() -> dict[str, Any]:
    try:
        return rebuild_spotify_cache()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail={"error": "Spotify refresh failed", "detail": str(exc), "code": "spotify_refresh_failed"}) from exc


@router.post("/data/refresh", response_model=RefreshResponse)
def refresh_data(request: RefreshRequest) -> RefreshResponse:
    settings.ensure_local_dirs()
    warnings: list[str] = []
    if request.use_demo:
        raw = demo_raw_collection()
        warnings.append("Demo data is enabled; no private account data was fetched.")
        live_connected = False
    else:
        takeout_history = load_current_takeout_history()
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
    takeout_history = None if request.use_demo else load_current_takeout_history()
    if takeout_history:
        raw["takeout_history"] = takeout_history
        raw["takeout_import_batch_id"] = (repo.load_json(TAKEOUT_CACHE_METADATA_KEY) or {}).get("import_batch_id")
        warnings.append("Google Takeout history is merged as the longest available play-history source.")
    normalised = normalise_with_duration_cache(
        raw,
        warnings,
        allow_enrichment=(not request.use_demo and request.enrich_durations),
        allow_artist_image_enrichment=live_connected,
        allow_album_image_enrichment=not request.use_demo,
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


@router.post("/data/import-takeout", response_model=TakeoutImportQueuedResponse, status_code=202)
async def import_takeout(file: UploadFile = File(...)) -> TakeoutImportQueuedResponse:
    settings.ensure_local_dirs()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".zip", ".json", ".html", ".htm"}:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Unsupported Takeout file",
                "detail": "Upload a Google Takeout watch-history JSON, HTML, or ZIP file.",
                "code": "takeout_file_type_invalid",
            },
        )
    try:
        job_id = takeout_imports.reserve(suffix)
    except TakeoutImportAlreadyRunning as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "Takeout import already running", "detail": str(exc), "code": "takeout_import_in_progress"},
        ) from exc

    import_dir = settings.private_dir / "takeout-imports"
    import_dir.mkdir(parents=True, exist_ok=True)
    upload_path = import_dir / f"{job_id}{suffix}"
    file_size = 0
    try:
        with upload_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > settings.takeout_max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail={
                            "error": "Takeout upload is too large",
                            "detail": f"The upload exceeds the configured {settings.takeout_max_upload_bytes // (1024 * 1024)} MB limit.",
                            "code": "takeout_upload_too_large",
                        },
                    )
                destination.write(chunk)
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail={"error": "Takeout file is empty", "detail": "Choose a non-empty Takeout export.", "code": "takeout_upload_empty"},
            )
        takeout_imports.queue(job_id, upload_path, file_size, process_takeout_import)
    except HTTPException:
        upload_path.unlink(missing_ok=True)
        takeout_imports.release_reservation(job_id)
        raise
    except Exception as exc:  # noqa: BLE001
        upload_path.unlink(missing_ok=True)
        takeout_imports.release_reservation(job_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "Takeout upload failed", "detail": "The file could not be stored locally.", "code": "takeout_upload_failed"},
        ) from exc
    finally:
        await file.close()
    takeout_imports.log(job_id, "response_returned", status="queued")
    return TakeoutImportQueuedResponse(jobId=job_id, status="queued")


@router.get("/data/import-takeout/{job_id}", response_model=TakeoutImportStatusResponse)
def takeout_import_status(job_id: str) -> TakeoutImportStatusResponse:
    job = takeout_imports.get(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Takeout import job not found",
                "detail": "The backend may have restarted before the upload was queued. Retry the import.",
                "code": "takeout_import_job_not_found",
            },
        )
    return TakeoutImportStatusResponse.model_validate(job)


def process_takeout_import(
    job_id: str,
    upload_path: Path,
    coordinator: TakeoutImportCoordinator,
    deadline: float,
) -> None:
    coordinator.stage(job_id, "parsing", "Opening and parsing the Takeout export.")
    try:
        parsed = parse_takeout_file(
            upload_path,
            on_event=lambda event, fields: coordinator.log(job_id, event, **fields),
            check_timeout=lambda: coordinator.check_timeout(deadline),
        )
    except TakeoutParseError as exc:
        coordinator.fail(job_id, str(exc), "takeout_parse_failed", "parsing")
        return
    coordinator.check_timeout(deadline)
    coordinator.log(
        job_id,
        "deduplication_completed",
        rawEventCount=parsed.raw_event_count,
        acceptedEventCount=len(parsed.entries),
    )
    if not parsed.entries:
        coordinator.fail(
            job_id,
            "No usable YouTube Music play events were found. Check that the export contains watch history.",
            "takeout_no_accepted_events",
            "parsing",
        )
        return

    coordinator.stage(
        job_id,
        "normalizing",
        "Canonical events are ready. Building the local listening dataset.",
        importedCount=len(parsed.entries),
    )
    previous_raw = repo.load_json("raw")
    if not isinstance(previous_raw, dict) or previous_raw.get("source") == "demo":
        raw: dict[str, Any] = {"source": "google_takeout", "history": [], "warnings": []}
    else:
        raw = dict(previous_raw)
        raw["source"] = "google_takeout"
    raw["takeout_history"] = parsed.entries
    raw["takeout_parser_schema_version"] = TAKEOUT_PARSER_SCHEMA_VERSION
    raw["takeout_import_batch_id"] = job_id
    raw["takeout_import_diagnostics"] = parsed.diagnostics
    for key in ("artist_image_cache_v2", "album_image_cache_v1"):
        cached = repo.load_json(key)
        if cached:
            raw[key] = cached
    try:
        normalised = normalise_collection(raw)
        normalised = annotate_normalised_durations(normalised, repo.load_json("duration_cache") or {})
    except Exception:  # noqa: BLE001
        coordinator.fail(
            job_id,
            "Canonical event normalization failed. Your previous profile was preserved.",
            "takeout_normalization_failed",
            "normalizing",
        )
        return
    coordinator.check_timeout(deadline)
    if not normalised.get("play_events") or not normalised.get("tracks"):
        coordinator.fail(
            job_id,
            "The export contained no events usable for analysis. Your previous profile was preserved.",
            "takeout_profile_empty",
            "normalizing",
        )
        return

    coordinator.stage(job_id, "rebuilding", "Rebuilding Overview and listening profiles from local events.")
    coordinator.log(job_id, "profile_rebuild_started", playCount=len(normalised["play_events"]))
    try:
        refreshed_at = datetime.now(timezone.utc).isoformat()
        normalised["refreshed_at"] = refreshed_at
        analysis = build_analysis(normalised)
        if not analysis.get("top_tracks") or not analysis.get("coverage"):
            raise ValueError("analysis profile is incomplete")
        overview_profile = build_overview_response(
            normalised,
            "this_month",
            None,
            settings.local_timezone,
        )
        if overview_profile.get("schemaVersion") != OVERVIEW_SCHEMA_VERSION or not overview_profile.get("identity"):
            raise ValueError("overview profile is incomplete")
    except Exception:  # noqa: BLE001
        coordinator.fail(
            job_id,
            "Analytics rebuild failed. Your previous profile was preserved and remains usable.",
            "takeout_analytics_rebuild_failed",
            "rebuilding",
        )
        return
    coordinator.check_timeout(deadline)
    coordinator.log(
        job_id,
        "profile_rebuild_completed",
        trackCount=normalised["metadata"]["track_count"],
        playCount=normalised["metadata"]["play_count"],
    )

    unknown_tracks = sum(1 for track in normalised.get("tracks", []) if track.get("primary_artist") == "Unknown Artist")
    warnings = ["Google Takeout history imported and rebuilt from canonical local events."]
    if unknown_tracks:
        warnings.append(f"{unknown_tracks} track(s) have partial artist metadata; play counts are still included.")
    metadata = {
        "parser_schema_version": TAKEOUT_PARSER_SCHEMA_VERSION,
        "event_schema_version": LISTENING_EVENT_SCHEMA_VERSION,
        "data_schema_version": NORMALISED_DATA_SCHEMA_VERSION,
        "imported_at": refreshed_at,
        "import_batch_id": job_id,
        "diagnostics": normalised.get("import_diagnostics") or parsed.diagnostics,
    }
    coordinator.stage(job_id, "saving", "Saving the new profile and invalidating dependent caches.")
    coordinator.log(job_id, "cache_invalidation_started", cacheGroups=["persona_report", "overview_language", "recommendations"])
    try:
        repo.save_json_batch(
            {
                "takeout_history": parsed.entries,
                TAKEOUT_CACHE_METADATA_KEY: metadata,
                "raw": raw,
                "normalised": normalised,
                "analysis": analysis,
                "last_refresh_meta": {"refreshed_at": refreshed_at, "use_demo": False, "warnings": warnings},
            },
            delete_keys=["latest_report", "recommendations"],
            delete_prefixes=["persona_report:", "persona_report_pointer:", "overview_language:"],
        )
    except Exception:  # noqa: BLE001
        coordinator.fail(
            job_id,
            "The rebuilt profile could not be saved. Your previous profile was preserved.",
            "takeout_persistence_failed",
            "saving",
        )
        return
    coordinator.log(job_id, "cache_invalidated", cacheGroups=["persona_report", "overview_language", "recommendations"])
    coordinator.log(job_id, "persistence_completed", acceptedEventCount=len(parsed.entries))
    coordinator.stage(
        job_id,
        "complete",
        "Google Takeout history imported. Overview is ready.",
        importedCount=len(parsed.entries),
        trackCount=normalised["metadata"]["track_count"],
        playCount=normalised["metadata"]["play_count"],
    )


@router.get("/data/coverage")
def coverage(source: str = Query("youtube")) -> dict[str, Any]:
    return require_source_cache("analysis", source)["coverage"]


@router.get("/analytics/diagnostics")
def analytics_diagnostics(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    """Developer-safe reconciliation; it exposes counts and versions, never events."""
    normalised = require_source_cache("normalised", source)
    profile = build_period_profile(normalised, period, month, timezone_name or settings.local_timezone)
    metadata = normalised.get("metadata") or {}
    return {
        "parserVersion": metadata.get("parser_schema_version"),
        "eventSchemaVersion": metadata.get("listening_event_schema_version"),
        "importBatchId": next((event.get("import_batch_id") for event in normalised.get("listening_events") or [] if event.get("import_batch_id")), None),
        "dataFingerprint": profile["dataFingerprint"],
        "analyticsVersion": ANALYTICS_VERSION,
        "genreMapVersion": GENRE_MAP_VERSION,
        "cache": {"status": "miss", "reason": "period profiles are computed from canonical local events"},
        "import": profile["reconciliation"],
        "profile": {**profile["period"], **profile["figures"]},
    }


@router.get("/analysis/overview", response_model=OverviewAnalysisResponse)
def overview(
    period: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    resolved_source = normalise_source(source)
    normalised = require_source_cache("normalised", resolved_source)
    meta = repo.load_json(cache_key("last_refresh_meta", resolved_source)) or {}
    payload = build_overview_response(normalised, period, month, timezone_name or settings.local_timezone)
    evidence = overview_language_evidence(payload)
    fingerprint = overview_language_fingerprint(evidence, resolved_source, settings.ollama_model)
    language_key = f"overview_language:v{OVERVIEW_LANGUAGE_CACHE_VERSION}:{resolved_source}:{fingerprint}"
    cached_language = repo.load_json(language_key)
    language: dict[str, Any] | None = None
    generation_source = "fallback"
    cache_matches = (
        isinstance(cached_language, dict)
        and cached_language.get("schemaVersion") == OVERVIEW_SCHEMA_VERSION
        and cached_language.get("fingerprint") == fingerprint
        and isinstance(cached_language.get("language"), dict)
    )
    cached_generation = str(cached_language.get("generationSource") or "") if cache_matches else ""
    fallback_cache_fresh = cache_matches and cached_generation == "fallback" and _cache_age_seconds(cached_language) < OVERVIEW_FALLBACK_CACHE_SECONDS
    if cache_matches and cached_generation != "fallback" and cached_language.get("language"):
        language = cached_language["language"]
        generation_source = "cache-gemma"
    elif fallback_cache_fresh:
        generation_source = "fallback"
    elif payload["selectedPeriod"]["key"] != PERSONA_REPORT_PERIOD:
        generation_source = "fallback"
    else:
        language = ollama.generate_overview_language(evidence)
        if isinstance(language, dict):
            generation_source = "gemma"
        repo.save_json(
            language_key,
            {
                "schemaVersion": OVERVIEW_SCHEMA_VERSION,
                "languageVersion": OVERVIEW_LANGUAGE_CACHE_VERSION,
                "fingerprint": fingerprint,
                "source": resolved_source,
                "model": settings.ollama_model,
                "generationSource": generation_source,
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "language": language or {},
            },
        )
    payload = apply_overview_language(payload, language, generation_source)
    payload["source"] = resolved_source
    payload["sourceLabel"] = "Spotify" if resolved_source == "spotify" else "YouTube Music"
    payload["languageFingerprint"] = fingerprint
    payload["overview"]["last_refreshed_at"] = meta.get("refreshed_at")
    payload["overview"]["use_demo"] = meta.get("use_demo", False)
    payload["overview"]["warnings"] = meta.get("warnings", [])
    payload["overview"]["source"] = resolved_source
    payload["overview"]["source_label"] = payload["sourceLabel"]
    age = payload["musicalAge"]
    print(f"[overview] period={payload['selectedPeriod']['key']} schema={OVERVIEW_SCHEMA_VERSION}", flush=True)
    print(
        f"[musical-age] age={age['age']} range={age['likelyMin']}-{age['likelyMax']} "
        f"confidence={age['confidence']:.2f} version={MUSICAL_AGE_CALCULATION_VERSION}",
        flush=True,
    )
    return payload


@router.get("/analysis/top-tracks")
def top_tracks(source: str = Query("youtube")) -> list[dict[str, Any]]:
    return require_source_cache("analysis", source)["top_tracks"]


@router.get("/analysis/top-artists")
def top_artists(source: str = Query("youtube")) -> list[dict[str, Any]]:
    return require_source_cache("analysis", source)["top_artists"]


@router.get("/analysis/scores")
def scores(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> list[dict[str, Any]]:
    analysis, spec, event_count = analysis_for_period(period, month, timezone_name, source)
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
    source: str = Query("youtube"),
) -> dict[str, Any]:
    analysis, _, _ = analysis_for_period(period, month, timezone_name, source)
    return analysis["charts"]


@router.get("/insights", response_model=InsightsResponse)
def insights(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> InsightsResponse:
    normalised = require_source_cache("normalised", source)
    metadata = normalised.get("metadata") or {}
    coverage = normalised.get("coverage") or {}
    cache_key = (
        source,
        period,
        month,
        timezone_name or settings.local_timezone,
        normalised.get("refreshed_at"),
        metadata.get("play_count"),
        coverage.get("latest_detected_play"),
        ANALYTICS_VERSION,
        GENRE_MAP_VERSION,
    )
    cached = INSIGHTS_RESPONSE_CACHE.get(cache_key)
    if cached is not None:
        return InsightsResponse(**cached)
    payload = insights_payload(
        normalised,
        period,
        month,
        timezone_name or settings.local_timezone,
    )
    if len(INSIGHTS_RESPONSE_CACHE) >= INSIGHTS_RESPONSE_CACHE_LIMIT:
        INSIGHTS_RESPONSE_CACHE.clear()
    INSIGHTS_RESPONSE_CACHE[cache_key] = payload
    return InsightsResponse(**payload)


@router.get("/analytics/listening-minutes")
def listening_minutes(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    return listening_minutes_payload(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone)


@router.get("/analytics/listening-minutes/daily")
def listening_minutes_daily(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> list[dict[str, Any]]:
    return listening_minutes_payload(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone)["daily"]


@router.get("/analytics/listening-minutes/heatmap")
def listening_minutes_heatmap(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> list[dict[str, Any]]:
    return listening_minutes_payload(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone)["heatmap"]


@router.get("/top")
def period_top(
    period: str = Query("this_month"),
    type: str = Query("tracks"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    kind = "artists" if type == "artists" else "tracks"
    profile = build_period_profile(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone)
    items = profile["top_artists"] if kind == "artists" else profile["top_tracks"]
    return {
        "period": profile["period"],
        "items": [{**item, "rank": index} for index, item in enumerate(items, 1)],
        "canonicalFigures": profile["figures"],
        "genreShares": profile["genre_shares"]["items"],
        "dataFingerprint": profile["dataFingerprint"],
    }


@router.get("/top/artist-songs")
def period_artist_songs(
    artist: str = Query(...),
    period: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    return artist_songs_payload(require_source_cache("normalised", source), artist, period, month, timezone_name or settings.local_timezone)


@router.get("/top/albums")
def period_albums(
    period: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
    limit: int = Query(10, ge=1, le=20),
) -> dict[str, Any]:
    return albums_payload(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone, limit=limit)


@router.get("/top/album-songs")
def period_album_songs(
    album: str = Query(...),
    artist: str | None = Query(None),
    period: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    return album_songs_payload(require_source_cache("normalised", source), album, artist, period, month, timezone_name or settings.local_timezone)


@router.get("/taste-dna")
def taste_dna(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    return taste_dna_payload(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone)


@router.get("/taste-dna/compare")
def taste_dna_compare(
    base: str = Query("rolling_year"),
    compare: str = Query("this_month"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    return taste_dna_comparison_payload(require_source_cache("normalised", source), base, compare, month, timezone_name or settings.local_timezone)


@router.get("/scores/interpretations")
def score_interpretations(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> list[dict[str, Any]]:
    return scores(period, month, timezone_name, source)


@router.get("/persona/character")
def persona_character(
    period: str = Query("rolling_year"),
    month: str | None = Query(None),
    timezone_name: str | None = Query(None, alias="timezone"),
    source: str = Query("youtube"),
) -> dict[str, Any]:
    return character_payload(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone)


@router.post("/persona/character/rewrite")
def persona_character_rewrite(payload: dict[str, Any]) -> dict[str, Any]:
    period = str(payload.get("period") or "rolling_year")
    month = payload.get("month")
    mode = str(payload.get("mode") or "playful")
    source = normalise_source(str(payload.get("source") or "youtube"))
    profile = character_payload(require_source_cache("normalised", source), period, str(month) if month else None, settings.local_timezone)
    status = ollama.status()
    if not status["reachable"] or not status["model_installed"]:
        raise HTTPException(status_code=503, detail={"error": "Ollama rewrite unavailable", "detail": status["message"], "code": "ollama_unavailable"})
    return ollama.generate_character_rewrite(profile, mode)


def report_profile_with_characters(source: str | None = "youtube") -> dict[str, Any]:
    resolved_source = normalise_source(source)
    normalised = require_cache("normalised") if resolved_source == "youtube" else require_source_cache("normalised", resolved_source)
    return build_persona_report_evidence(normalised, settings.local_timezone)


@router.post("/report/generate", response_model=PersonaReportResponse)
def generate_report(request: ReportRequest) -> PersonaReportResponse:
    source = normalise_source(request.source)
    profile = report_profile_with_characters(source)
    analytics_fingerprint = persona_report_fingerprint(profile)
    report_cache_key = persona_report_cache_key(source, request.mode, analytics_fingerprint)
    language = ollama.generate_persona_language(profile["languageEvidence"], request.mode).model_dump()
    generated_at = datetime.now(timezone.utc).isoformat()
    payload = compose_persona_report(
        profile,
        language,
        source=source,
        mode=request.mode,
        generated_at=generated_at,
        prompt_version=PERSONA_REPORT_PROMPT_VERSION,
        model=settings.ollama_model,
        analytics_fingerprint=analytics_fingerprint,
        cache_key=report_cache_key,
    )
    validated = PersonaReportResponse.model_validate(payload)
    repo.save_json(report_cache_key, payload)
    repo.save_json(
        persona_report_pointer_key(source),
        {
            "cacheKey": report_cache_key,
            "source": source,
            "mode": request.mode,
            "period": PERSONA_REPORT_PERIOD,
            "schemaVersion": PERSONA_REPORT_SCHEMA_VERSION,
            "promptVersion": PERSONA_REPORT_PROMPT_VERSION,
            "musicalAgeCalculationVersion": MUSICAL_AGE_CALCULATION_VERSION,
            "personalityClassifierVersion": MUSIC_CHARACTER_CLASSIFIER_VERSION,
            "model": settings.ollama_model,
            "analyticsFingerprint": analytics_fingerprint,
            "generatedAt": generated_at,
        },
    )
    return validated


@router.get("/report/latest", response_model=PersonaReportResponse)
def latest_report(source: str = Query("youtube")) -> PersonaReportResponse:
    resolved_source = normalise_source(source)
    profile = report_profile_with_characters(resolved_source)
    analytics_fingerprint = persona_report_fingerprint(profile)
    pointer = repo.load_json(persona_report_pointer_key(resolved_source))
    if (
        isinstance(pointer, dict)
        and pointer.get("schemaVersion") == PERSONA_REPORT_SCHEMA_VERSION
        and pointer.get("period") == PERSONA_REPORT_PERIOD
        and pointer.get("source") == resolved_source
        and pointer.get("promptVersion") == PERSONA_REPORT_PROMPT_VERSION
        and pointer.get("musicalAgeCalculationVersion") == MUSICAL_AGE_CALCULATION_VERSION
        and pointer.get("personalityClassifierVersion") == MUSIC_CHARACTER_CLASSIFIER_VERSION
        and pointer.get("model") == settings.ollama_model
        and pointer.get("analyticsFingerprint") == analytics_fingerprint
        and pointer.get("cacheKey")
    ):
        cached = repo.load_json(str(pointer["cacheKey"]))
        if isinstance(cached, dict) and cached.get("schemaVersion") == PERSONA_REPORT_SCHEMA_VERSION:
            payload = dict(cached)
            if (payload.get("generation") or {}).get("source") == "gemma":
                payload["generation"] = {**payload["generation"], "source": "cache-gemma"}
                payload["personality"] = {**payload["personality"], "generationSource": "cache-gemma"}
                payload["summary"] = {**payload["summary"], "generationSource": "cache-gemma"}
            return PersonaReportResponse.model_validate(payload)

    mode = str(pointer.get("mode") or "serious") if isinstance(pointer, dict) else "serious"
    language = ollama.fallback_persona_language(profile["languageEvidence"], "no_matching_gemma_cache").model_dump()
    generated_at = datetime.now(timezone.utc).isoformat()
    report_cache_key = persona_report_cache_key(resolved_source, mode, analytics_fingerprint)
    fallback_payload = compose_persona_report(
        profile,
        language,
        source=resolved_source,
        mode=mode,
        generated_at=generated_at,
        prompt_version=PERSONA_REPORT_PROMPT_VERSION,
        model=settings.ollama_model,
        analytics_fingerprint=analytics_fingerprint,
        cache_key=report_cache_key,
    )
    return PersonaReportResponse.model_validate(fallback_payload)


@router.get("/recommendations")
def latest_recommendations() -> list[dict[str, Any]]:
    return require_cache("recommendations")


def _cache_age_seconds(payload: dict[str, Any]) -> float:
    try:
        created_at = datetime.fromisoformat(str(payload.get("createdAt") or "").replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds())
    except (TypeError, ValueError):
        return float("inf")


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
