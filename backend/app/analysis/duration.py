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
    "playlist",
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

MUSIC_LONGFORM_TITLE_PATTERNS = (
    "full album",
    "album stream",
    "full concert",
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


def extract_duration_milliseconds(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        milliseconds = int(value)
    elif isinstance(value, str) and value.strip().isdigit():
        milliseconds = int(value.strip())
    else:
        return None
    if milliseconds <= 0:
        return None
    return max(1, round(milliseconds / 1000))


def duration_from_item(item: dict[str, Any]) -> int | None:
    for key in ("duration_seconds", "durationSeconds", "lengthSeconds", "length_seconds"):
        seconds = extract_duration_seconds(item.get(key))
        if seconds:
            return seconds
    seconds = extract_duration_seconds(item.get("duration"))
    if seconds:
        return seconds
    for key in ("duration_ms", "durationMs", "lengthMilliseconds", "length_ms"):
        seconds = extract_duration_milliseconds(item.get(key))
        if seconds:
            return seconds
    return None


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
    is_music_longform = any(pattern in title_text for pattern in MUSIC_LONGFORM_TITLE_PATTERNS)
    if duration_seconds is None:
        return "music_candidate", True, "missing_duration"
    if duration_seconds <= 0:
        return "music_candidate", True, "invalid_duration"
    if duration_seconds < MIN_TRACK_DURATION_SECONDS:
        # Short ads, clips and UI sounds are common in Watch History.  They
        # should not affect song rankings or personality merely because they
        # have a title and channel attribution.
        return "non_music_or_shortform", False, "duration_too_short"
    if duration_seconds > MAX_TRACK_DURATION_SECONDS:
        if is_music_longform:
            return "music_longform", True, None
        return "longform_video", False, "too_long_for_track"
    if is_music_longform:
        return "music_longform", True, None
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
        cached_identity = (duration_cache or {}).get(str(video_id)) if video_id else None
        if isinstance(cached_identity, dict) and cached_identity.get("music_classification") == "confirmed_music":
            apply_verified_track_identity(track, cached_identity)
            track["verified_music_classification"] = "confirmed_music"
            track["verified_music_classification_source"] = cached_identity.get("music_classification_source")
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

    reconcile_verified_music_events(normalised, track_lookup, duration_cache or {})

    imported_at = normalised.get("refreshed_at") or datetime.now(timezone.utc).isoformat()
    all_events = [
        *[event for event in normalised.get("play_events") or [] if isinstance(event, dict)],
        *[event for event in normalised.get("excluded_play_events") or [] if isinstance(event, dict)],
    ]
    for index, event in enumerate(all_events):
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


def reconcile_verified_music_events(
    normalised: dict[str, Any],
    track_lookup: dict[str, dict[str, Any]],
    duration_cache: dict[str, Any],
) -> None:
    """Promote quarantined Watch History only after exact-video music proof."""

    original_play_events = [event for event in normalised.get("play_events") or [] if isinstance(event, dict)]
    original_play_object_ids = {id(event) for event in original_play_events}
    original_play_keys = {
        str(event.get("event_id") or event.get("id") or event.get("dedupe_key") or "")
        for event in original_play_events
        if event.get("event_id") or event.get("id") or event.get("dedupe_key")
    }
    listening = [
        event
        for event in normalised.get("listening_events") or []
        if isinstance(event, dict) and event.get("evidence_type") == "play_event"
    ]
    if not listening:
        listening = [
            event
            for event in [*(normalised.get("play_events") or []), *(normalised.get("excluded_play_events") or [])]
            if isinstance(event, dict)
        ]
    accepted: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for event in listening:
        track = track_lookup.get(event.get("track_id"), {})
        video_id = str(event.get("video_id") or track.get("video_id") or "")
        cached = duration_cache.get(video_id)
        if isinstance(cached, dict) and cached.get("music_classification") == "confirmed_music":
            apply_verified_track_identity(track, cached)
            event.update(
                {
                    "title": track.get("title") or event.get("title"),
                    "artist": track.get("primary_artist") or event.get("artist"),
                    "artists": list(track.get("artists") or event.get("artists") or []),
                    "music_classification": "confirmed_music",
                    "music_classification_source": cached.get("music_classification_source"),
                }
            )
        event_key = str(event.get("event_id") or event.get("id") or event.get("dedupe_key") or "")
        was_previously_accepted = id(event) in original_play_object_ids or bool(event_key and event_key in original_play_keys)
        if event.get("music_classification") in {"confirmed_music", "probable_music"} or (event.get("music_classification") in {None, ""} and was_previously_accepted):
            accepted.append(event)
        else:
            excluded.append(event)
    normalised["play_events"] = accepted
    normalised["excluded_play_events"] = excluded
    metadata = normalised.get("metadata")
    if isinstance(metadata, dict):
        metadata["play_count"] = len(accepted)
    diagnostics = normalised.get("import_diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics["accepted_music_plays"] = len(accepted)
        diagnostics["unknown_classifications"] = sum(event.get("music_classification") == "unknown" for event in listening)


def apply_verified_track_identity(track: dict[str, Any], cached: dict[str, Any]) -> None:
    media_title = str(cached.get("media_title") or "").strip()
    media_author = re.sub(r"\s*-\s*Topic$", "", str(cached.get("media_author") or "").strip(), flags=re.IGNORECASE).strip()
    current_artist = str(track.get("primary_artist") or "").strip()
    is_unknown = current_artist.casefold() in {"", "unknown", "unknown artist", "unavailable artist"}
    confidence = str(cached.get("identity_confidence") or "")
    if confidence == "high" and media_author and is_unknown:
        track["primary_artist"] = media_author
        track["artists"] = [media_author]
    elif confidence == "medium" and media_author and media_title and is_unknown:
        prefix = re.split(r"\s+[-\u2013\u2014|]\s+", media_title, maxsplit=1)
        if len(prefix) == 2 and simple_identity(prefix[0]) == simple_identity(media_author):
            track["primary_artist"] = media_author
            track["artists"] = [media_author]
            media_title = prefix[1]
    if media_title and confidence == "high":
        track["title"] = media_title


def simple_identity(value: Any) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", str(value or "").casefold(), flags=re.UNICODE).split())


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
