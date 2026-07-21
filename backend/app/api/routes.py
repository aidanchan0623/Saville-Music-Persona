from __future__ import annotations

import shutil
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse

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
from app.analysis.spotify_adapter import SPOTIFY_LIMITATION_NOTE, spotify_raw_to_collection
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
from app.services.spotify_service import SpotifyService
from app.services.takeout_service import TakeoutParseError, parse_takeout_upload
from app.services.ytmusic_service import YTMusicService


router = APIRouter(prefix="/api")
repo = JsonRepository(settings.db_path)
ytmusic = YTMusicService(settings)
ollama = OllamaService(settings)
spotify = SpotifyService(settings)

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


def require_cache(key: str) -> Any:
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
        if key in {"analysis", "normalised"}:
            ensure_youtube_artist_images()
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
    preferred_artist_images: list[str] | None = None,
) -> dict[str, Any]:
    artist_cache = repo.load_json("artist_image_cache") or {}
    if artist_cache:
        raw["artist_image_cache"] = {**artist_cache, **(raw.get("artist_image_cache") or {})}
    if allow_artist_image_enrichment:
        try:
            stats = ytmusic.enrich_artist_image_cache(raw, artist_cache, preferred_artists=preferred_artist_images)
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
def coverage(source: str = Query("youtube")) -> dict[str, Any]:
    return require_source_cache("analysis", source)["coverage"]


@router.get("/analysis/overview")
def overview(source: str = Query("youtube")) -> dict[str, Any]:
    resolved_source = normalise_source(source)
    analysis = require_source_cache("analysis", resolved_source)
    meta = repo.load_json(cache_key("last_refresh_meta", resolved_source)) or {}
    payload = dict(analysis["overview"])
    payload["last_refreshed_at"] = meta.get("refreshed_at")
    payload["use_demo"] = meta.get("use_demo", False)
    payload["warnings"] = meta.get("warnings", [])
    payload["source"] = resolved_source
    payload["source_label"] = "Spotify" if resolved_source == "spotify" else "YouTube Music"
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
    return top_payload(require_source_cache("normalised", source), kind, period, month, timezone_name or settings.local_timezone)


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
) -> dict[str, Any]:
    return albums_payload(require_source_cache("normalised", source), period, month, timezone_name or settings.local_timezone)


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
    normalised = require_source_cache("normalised", source)
    analysis = require_source_cache("analysis", source)
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
    source = normalise_source(request.source)
    profile = report_profile_with_characters(source)
    status = ollama.status()
    if not status["reachable"] or not status["model_installed"]:
        raise HTTPException(status_code=503, detail={"error": "Ollama report unavailable", "detail": status["message"], "code": "ollama_unavailable"})
    report = ollama.generate_report(profile, request.mode)
    payload = report.model_dump()
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["source"] = source
    repo.save_json(cache_key("latest_report", source), payload)
    return payload


@router.get("/report/latest")
def latest_report(source: str = Query("youtube")) -> dict[str, Any]:
    return require_source_cache("latest_report", source)


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
