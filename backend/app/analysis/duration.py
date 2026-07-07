from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any


MAX_TRACK_DURATION_SECONDS = 20 * 60
MIN_TRACK_DURATION_SECONDS = 20

NON_MUSIC_TITLE_PATTERNS = (
    "podcast",
    "interview",
    "reaction",
    "documentary",
    "livestream",
    "live stream",
    "full album",
    "full concert",
    "playlist",
    "episode",
    "tutorial",
    "behind the scenes",
    "press conference",
    "advertisement",
    "commercial",
    "sponsored",
    "promo",
    "iklan",
    "lactogrow",
    "probio",
    "tumbesaran",
)


def extract_duration_seconds(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        seconds = int(value)
        return seconds if seconds > 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.isdigit():
        seconds = int(text)
        return seconds if seconds > 0 else None
    parts = text.split(":")
    try:
        nums = [int(part) for part in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        seconds = nums[0] * 60 + nums[1]
    elif len(nums) == 3:
        seconds = nums[0] * 3600 + nums[1] * 60 + nums[2]
    else:
        return None
    return seconds if seconds > 0 else None


def duration_from_item(item: dict[str, Any]) -> int | None:
    for key in ("duration_seconds", "durationSeconds", "lengthSeconds", "length_seconds"):
        seconds = extract_duration_seconds(item.get(key))
        if seconds:
            return seconds
    return extract_duration_seconds(item.get("duration"))


def duration_from_cache(video_id: str | None, duration_cache: dict[str, Any] | None) -> tuple[int | None, str | None, str | None]:
    if not video_id or not duration_cache:
        return None, None, None
    cached = duration_cache.get(video_id)
    if not isinstance(cached, dict):
        return None, None, None
    seconds = extract_duration_seconds(cached.get("duration_seconds"))
    if not seconds:
        return None, None, None
    return seconds, str(cached.get("duration_source") or "duration_cache"), str(cached.get("duration_confidence") or "medium")


def content_type_for(title: str | None, duration_seconds: int | None) -> tuple[str, bool, str | None]:
    title_text = (title or "").lower()
    if any(pattern in title_text for pattern in NON_MUSIC_TITLE_PATTERNS):
        return "non_music_or_longform", False, "non_music_content"
    if duration_seconds is None:
        return "music_candidate", True, "missing_duration"
    if duration_seconds <= 0:
        return "music_candidate", True, "invalid_duration"
    if duration_seconds < MIN_TRACK_DURATION_SECONDS:
        return "music_candidate", True, "duration_too_short"
    if duration_seconds > MAX_TRACK_DURATION_SECONDS:
        return "longform_video", False, "too_long_for_track"
    return "music_track", True, None


def duration_confidence_for(duration_source: str | None, excluded_reason: str | None) -> str:
    if excluded_reason in {"missing_duration", "invalid_duration"}:
        return "missing"
    if excluded_reason:
        return "excluded"
    if duration_source in {"source_item", "ytmusicapi", "ytmusicapi.get_song", "duration_cache"}:
        return "high"
    return "medium"


def annotate_normalised_durations(normalised: dict[str, Any], duration_cache: dict[str, Any] | None = None) -> dict[str, Any]:
    tracks = normalised.get("tracks") or []
    track_lookup: dict[str, dict[str, Any]] = {}
    for track in tracks:
        if not isinstance(track, dict):
            continue
        video_id = track.get("video_id")
        duration = extract_duration_seconds(track.get("duration_seconds"))
        source = "source_item" if duration else None
        cache_duration, cache_source, cache_confidence = duration_from_cache(str(video_id) if video_id else None, duration_cache)
        if not duration and cache_duration:
            duration = cache_duration
            source = cache_source or "duration_cache"
        content_type, is_music_candidate, excluded_reason = content_type_for(track.get("title"), duration)
        confidence = cache_confidence if source and source != "source_item" else duration_confidence_for(source, excluded_reason)
        track["duration_seconds"] = duration
        track["duration_source"] = source or "unavailable"
        track["duration_confidence"] = confidence
        track["content_type"] = content_type
        track["is_music_candidate"] = is_music_candidate
        track["excluded_from_minutes_reason"] = excluded_reason
        track_lookup[track.get("track_id")] = track

    imported_at = normalised.get("refreshed_at") or datetime.now(timezone.utc).isoformat()
    for index, event in enumerate(normalised.get("play_events") or []):
        if not isinstance(event, dict):
            continue
        track = track_lookup.get(event.get("track_id"), {})
        duration = extract_duration_seconds(event.get("duration_seconds")) or extract_duration_seconds(track.get("duration_seconds"))
        content_type = str(track.get("content_type") or "music_candidate")
        is_music_candidate = bool(track.get("is_music_candidate", True))
        excluded_reason = track.get("excluded_from_minutes_reason")
        if duration is None and excluded_reason is None:
            excluded_reason = "missing_duration"
        played_at = event.get("played_at")
        dedupe_base = f"{event.get('track_id')}::{played_at}::{index}"
        event["id"] = event.get("id") or hashlib.sha1(dedupe_base.encode("utf-8")).hexdigest()[:20]
        event["artists_json"] = event.get("artists_json") or list(event.get("artists") or track.get("artists") or [])
        event["played_date_raw"] = event.get("played_date_raw") or played_at
        event["source"] = event.get("source") or "history"
        event["imported_at"] = event.get("imported_at") or imported_at
        event["dedupe_key"] = event.get("dedupe_key") or hashlib.sha1(dedupe_base.encode("utf-8")).hexdigest()
        event["duration_seconds"] = duration
        track_source = track.get("duration_source") or "unavailable"
        current_source = event.get("duration_source")
        event["duration_source"] = track_source if current_source in (None, "", "unavailable") else current_source
        track_confidence = track.get("duration_confidence") or duration_confidence_for(track_source, excluded_reason)
        current_confidence = event.get("duration_confidence")
        event["duration_confidence"] = track_confidence if current_confidence in (None, "", "missing") else current_confidence
        event["content_type"] = content_type
        event["is_music_candidate"] = is_music_candidate
        event["excluded_from_minutes_reason"] = excluded_reason

    normalised["duration_quality"] = duration_quality(normalised.get("play_events") or [])
    return normalised


def usable_duration_seconds(event: dict[str, Any]) -> int | None:
    if event.get("excluded_from_minutes_reason"):
        return None
    if event.get("is_music_candidate") is False:
        return None
    return extract_duration_seconds(event.get("duration_seconds"))


def duration_quality(events: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(events)
    music_candidates = [event for event in events if event.get("is_music_candidate") is not False]
    usable = [event for event in music_candidates if usable_duration_seconds(event)]
    excluded = [event for event in events if not usable_duration_seconds(event)]
    reasons = Counter(str(event.get("excluded_from_minutes_reason") or "not_music_candidate") for event in excluded)
    total_seconds = sum(usable_duration_seconds(event) or 0 for event in usable)
    coverage = round(len(usable) / len(music_candidates) * 100, 1) if music_candidates else 0.0
    return {
        "total_detected_plays": total,
        "detected_music_plays": len(music_candidates),
        "plays_with_usable_duration": len(usable),
        "duration_coverage_percent": coverage,
        "total_minutes_included": round(total_seconds / 60, 1),
        "events_excluded_from_minutes": len(excluded),
        "main_exclusion_reasons": [{"reason": reason, "count": count} for reason, count in reasons.most_common(6)],
        "confidence_badge": duration_confidence_badge(coverage),
        "methodology": "Detected listening minutes are estimated from full track durations. Skips, partial listens and videos without duration cannot be measured exactly.",
    }


def duration_confidence_badge(coverage: float) -> str:
    if coverage >= 90:
        return "High confidence"
    if coverage >= 75:
        return "Good coverage"
    if coverage >= 50:
        return "Partial coverage"
    return "Limited"
