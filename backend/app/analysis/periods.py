from __future__ import annotations

import calendar
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone, tzinfo
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.analysis.duration import duration_quality, usable_duration_seconds
from app.analysis.media import (
    album_image_source as resolve_album_image_source,
    album_image_url as resolve_album_image_url,
    artist_image_source as resolve_artist_image_source,
    artist_image_url as resolve_artist_image_url,
    track_image_source as resolve_track_image_source,
    track_image_url as resolve_track_image_url,
)
from app.analysis.normalizer import UNKNOWN_ARTIST
from app.analysis.taste_model import build_taste_model, profile_for_artist
from app.analysis.thumbnails import best_thumbnail_url


MIN_COMPARISON_PLAYS = 25
MIN_STRONG_SAMPLE_PLAYS = 50

CLUSTER_ANCHORS: dict[str, tuple[float, float]] = {
    "Alternative / Indie Rock": (42, 46),
    "Emo / Pop Punk / Post-Hardcore": (34, 64),
    "Heavy Alternative / Metalcore": (48, 72),
    "Pop / Pop Rock Crossover": (64, 48),
    "Electronic / Atmospheric": (66, 28),
    "Cinematic / Soundtrack": (50, 22),
    "Hip-Hop / Rap": (78, 62),
}


COMMON_TIMEZONES = {
    "Asia/Kuala_Lumpur": timezone(timedelta(hours=8)),
    "UTC": timezone.utc,
}


@lru_cache(maxsize=32)
def safe_timezone(name: str | None, default: str = "Asia/Kuala_Lumpur") -> tzinfo:
    key = name or default
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError:
        fallback = COMMON_TIMEZONES.get(key) or COMMON_TIMEZONES.get(default)
        if fallback:
            return fallback
        return timezone.utc


def local_today(timezone_name: str | None = None) -> date:
    return datetime.now(safe_timezone(timezone_name)).date()


def event_local_date(event: dict[str, Any], timezone_name: str | None = None) -> date | None:
    value = event.get("played_at") or event.get("played_date_raw")
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.date()
        return value.astimezone(safe_timezone(timezone_name)).date()
    return _event_local_date_from_text(str(value).strip(), timezone_name)


@lru_cache(maxsize=200_000)
def _event_local_date_from_text(text: str, timezone_name: str | None) -> date | None:
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.date()
    return dt.astimezone(safe_timezone(timezone_name)).date()


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def month_bounds(month: str, today: date) -> tuple[date, date]:
    year, month_number = [int(part) for part in month.split("-", 1)]
    start = date(year, month_number, 1)
    end = date(year, month_number, calendar.monthrange(year, month_number)[1])
    if start <= today <= end:
        end = today
    return start, end


def available_months(normalised: dict[str, Any], timezone_name: str | None = None) -> list[dict[str, str]]:
    timezone_key = timezone_name or "Asia/Kuala_Lumpur"
    metadata = normalised.setdefault("metadata", {})
    cached_by_timezone = metadata.setdefault("available_months_by_timezone", {})
    cached = cached_by_timezone.get(timezone_key)
    if isinstance(cached, list):
        return cached
    months = sorted(
        {
            day.strftime("%Y-%m")
            for event in normalised.get("play_events") or []
            for day in [event_local_date(event, timezone_name)]
            if day is not None
        }
    )
    result = [{"value": month, "label": datetime.strptime(month, "%Y-%m").strftime("%B %Y")} for month in months]
    cached_by_timezone[timezone_key] = result
    return result


def resolve_period(
    normalised: dict[str, Any],
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    anchor = today or local_today(timezone_name)
    period_key = period or "rolling_year"
    if period_key in {"this_month", "current_month"}:
        start = date(anchor.year, anchor.month, 1)
        end = anchor
        label = anchor.strftime("%B %Y")
        period_key = "this_month"
    elif period_key in {"month", "selected_month"}:
        selected_month = month or (available_months(normalised, timezone_name)[-1]["value"] if available_months(normalised, timezone_name) else anchor.strftime("%Y-%m"))
        start, end = month_bounds(selected_month, anchor)
        label = datetime.strptime(selected_month, "%Y-%m").strftime("%B %Y")
        period_key = "month"
    elif period_key == "last_7":
        start = anchor - timedelta(days=6)
        end = anchor
        label = "Last 7 days"
    elif period_key == "last_30":
        start = anchor - timedelta(days=29)
        end = anchor
        label = "Last 30 days"
    elif period_key == "all":
        dates = [event_local_date(event, timezone_name) for event in normalised.get("play_events") or []]
        usable = [day for day in dates if day is not None and day <= anchor]
        start = min(usable) if usable else anchor
        end = max(usable) if usable else anchor
        label = "All available history"
    else:
        start = anchor - timedelta(days=364)
        end = anchor
        period_key = "rolling_year"
        label = "Rolling 365 days"
    return {
        "period": period_key,
        "month": month,
        "timezone": timezone_name or "Asia/Kuala_Lumpur",
        "start_date": start,
        "end_date": end,
        "label": label,
        "today": anchor,
        "available_months": available_months(normalised, timezone_name),
    }


def previous_period(spec: dict[str, Any]) -> dict[str, Any] | None:
    start: date = spec["start_date"]
    end: date = spec["end_date"]
    period = spec["period"]
    if period in {"this_month", "month"}:
        previous_month = add_months(start, -1).strftime("%Y-%m")
        prev_start, prev_end = month_bounds(previous_month, start - timedelta(days=1))
        return {**spec, "period": "month", "month": previous_month, "start_date": prev_start, "end_date": prev_end, "label": datetime.strptime(previous_month, "%Y-%m").strftime("%B %Y")}
    if period == "rolling_year":
        prev_end = start - timedelta(days=1)
        return {**spec, "start_date": prev_end - timedelta(days=364), "end_date": prev_end, "label": "Previous rolling 365 days"}
    if period == "last_7":
        prev_end = start - timedelta(days=1)
        return {**spec, "start_date": prev_end - timedelta(days=6), "end_date": prev_end, "label": "Previous 7 days"}
    if period == "last_30":
        prev_end = start - timedelta(days=1)
        return {**spec, "start_date": prev_end - timedelta(days=29), "end_date": prev_end, "label": "Previous 30 days"}
    return None


def filter_events(normalised: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    start: date = spec["start_date"]
    end: date = spec["end_date"]
    timezone_name = spec.get("timezone")
    result = []
    for event in normalised.get("play_events") or []:
        day = event_local_date(event, timezone_name)
        if day is None or day < start or day > end:
            continue
        result.append(event)
    return result


def filter_excluded_play_events(normalised: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    start: date = spec["start_date"]
    end: date = spec["end_date"]
    timezone_name = spec.get("timezone")
    return [
        event
        for event in normalised.get("excluded_play_events") or []
        if (day := event_local_date(event, timezone_name)) is not None and start <= day <= end
    ]


def tracks_by_id(normalised: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {track["track_id"]: track for track in normalised.get("tracks") or [] if track.get("track_id")}


def normalised_for_events(normalised: dict[str, Any], events: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(event.get("track_id") for event in events)
    last_played: dict[str, str] = {}
    first_played: dict[str, str] = {}
    for event in events:
        track_id = event.get("track_id")
        played = str(event.get("played_at") or "")
        if not track_id or not played:
            continue
        last_played[track_id] = max(last_played.get(track_id, ""), played)
        first_played[track_id] = min(first_played.get(track_id, played), played)
    tracks = []
    for track in normalised.get("tracks") or []:
        item = dict(track)
        track_id = item.get("track_id")
        item["play_count_in_period"] = counts.get(track_id, 0)
        item["last_played"] = last_played.get(track_id)
        item["first_played_in_period"] = first_played.get(track_id)
        tracks.append(item)
    payload = deepcopy(normalised)
    payload["tracks"] = tracks
    payload["play_events"] = list(events)
    payload["coverage"] = {
        **(normalised.get("coverage") or {}),
        "period_label": spec["label"],
        "period_start": spec["start_date"].isoformat(),
        "period_end": spec["end_date"].isoformat(),
    }
    payload["duration_quality"] = duration_quality(events)
    return payload


def artist_counts_for_events(events: list[dict[str, Any]], track_lookup: dict[str, dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for event in events:
        track = track_lookup.get(event.get("track_id"), {})
        artist = track.get("primary_artist") or event.get("primary_artist") or UNKNOWN_ARTIST
        counts[str(artist)] += 1
    return counts


def seconds_for_events(events: list[dict[str, Any]]) -> int:
    return sum(usable_duration_seconds(event) or 0 for event in events)


def round_minutes(seconds: int | float) -> float:
    return round(float(seconds) / 60, 1)


def format_detected_minutes(minutes: float) -> str:
    total = int(round(minutes))
    hours, mins = divmod(total, 60)
    if hours <= 0:
        return f"{mins} minutes"
    return f"{hours:,} hr {mins:02d} min"


def date_range(start: date, end: date) -> list[date]:
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def listening_minutes_payload(
    normalised: dict[str, Any],
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = filter_events(normalised, spec)
    daily_seconds: dict[date, int] = {day: 0 for day in date_range(spec["start_date"], spec["end_date"])}
    active_play_days: set[date] = set()
    for event in events:
        day = event_local_date(event, spec["timezone"])
        if day is None:
            continue
        seconds = usable_duration_seconds(event) or 0
        daily_seconds[day] = daily_seconds.get(day, 0) + seconds
        if event.get("is_music_candidate") is not False:
            active_play_days.add(day)
    daily = [{"date": day.isoformat(), "name": day.strftime("%b %d"), "value": round_minutes(seconds)} for day, seconds in sorted(daily_seconds.items())]
    total_seconds = sum(daily_seconds.values())
    active_minute_days = [day for day, seconds in daily_seconds.items() if seconds > 0]
    active_days = len(active_play_days)
    longest_day = max(daily_seconds.items(), key=lambda item: item[1], default=(None, 0))
    quietest_candidates = [(day, seconds) for day, seconds in daily_seconds.items() if seconds > 0]
    quietest_day = min(quietest_candidates, key=lambda item: item[1], default=(None, 0))
    today_day = spec["today"]
    streak = 0
    cursor = today_day
    all_active = {
        day
        for event in normalised.get("play_events") or []
        for day in [event_local_date(event, spec["timezone"])]
        if day is not None and event.get("is_music_candidate") is not False
    }
    while cursor in all_active:
        streak += 1
        cursor -= timedelta(days=1)
    weekly = aggregate_by_week(daily_seconds)
    monthly = aggregate_by_month(daily_seconds)
    quality = duration_quality([*events, *filter_excluded_play_events(normalised, spec)])
    selected_days = max(len(daily_seconds), 1)
    active_minute_day_count = max(len(active_minute_days), 1)
    this_month_spec = resolve_period(normalised, "this_month", timezone_name=spec["timezone"], today=today_day)
    rolling_spec = resolve_period(normalised, "rolling_year", timezone_name=spec["timezone"], today=today_day)
    today_spec = {**spec, "start_date": today_day, "end_date": today_day}
    yesterday = today_day - timedelta(days=1)
    yesterday_spec = {**spec, "start_date": yesterday, "end_date": yesterday}
    week_start = today_day - timedelta(days=today_day.weekday())
    week_spec = {**spec, "start_date": week_start, "end_date": today_day}
    summary_sentence = pattern_sentence(spec, total_seconds, active_minute_day_count, longest_day)
    return {
        "period": serialise_spec(spec),
        "metrics": {
            "today_detected_minutes": round_minutes(seconds_for_events(filter_events(normalised, today_spec))),
            "yesterday_detected_minutes": round_minutes(seconds_for_events(filter_events(normalised, yesterday_spec))),
            "current_week_total_minutes": round_minutes(seconds_for_events(filter_events(normalised, week_spec))),
            "current_month_total_minutes": round_minutes(seconds_for_events(filter_events(normalised, this_month_spec))),
            "rolling_365_total_minutes": round_minutes(seconds_for_events(filter_events(normalised, rolling_spec))),
            "selected_period_total_minutes": round_minutes(total_seconds),
            "selected_period_total_formatted": format_detected_minutes(round_minutes(total_seconds)),
            "daily_average_minutes": round(round_minutes(total_seconds) / selected_days, 1),
            "average_active_day_minutes": round(round_minutes(total_seconds) / active_minute_day_count, 1) if active_minute_days else 0,
            "longest_detected_listening_day": day_payload(longest_day),
            "quietest_active_day": day_payload(quietest_day),
            "active_listening_days": active_days,
            "current_listening_streak_days": streak,
        },
        "duration_quality": quality,
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "heatmap": heatmap(daily_seconds),
        "summary_sentence": summary_sentence,
        "methodology": "Detected listening minutes are estimated from full track durations. Duration coverage is shown because skips, partial listens, and missing durations cannot be measured exactly.",
    }


def serialise_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "period": spec["period"],
        "month": spec.get("month"),
        "label": spec["label"],
        "timezone": spec["timezone"],
        "start_date": spec["start_date"].isoformat(),
        "end_date": spec["end_date"].isoformat(),
        "available_months": spec.get("available_months", []),
    }


def day_payload(day_item: tuple[date | None, int]) -> dict[str, Any] | None:
    day, seconds = day_item
    if day is None or seconds <= 0:
        return None
    return {"date": day.isoformat(), "minutes": round_minutes(seconds), "formatted": format_detected_minutes(round_minutes(seconds))}


def aggregate_by_week(daily_seconds: dict[date, int]) -> list[dict[str, Any]]:
    grouped: dict[date, int] = defaultdict(int)
    for day, seconds in daily_seconds.items():
        start = day - timedelta(days=day.weekday())
        grouped[start] += seconds
    return [{"date": day.isoformat(), "name": day.strftime("%b %d"), "value": round_minutes(seconds)} for day, seconds in sorted(grouped.items())]


def aggregate_by_month(daily_seconds: dict[date, int]) -> list[dict[str, Any]]:
    grouped: dict[str, int] = defaultdict(int)
    for day, seconds in daily_seconds.items():
        grouped[day.strftime("%Y-%m")] += seconds
    return [{"date": month, "name": datetime.strptime(month, "%Y-%m").strftime("%b %Y"), "value": round_minutes(seconds)} for month, seconds in sorted(grouped.items())]


def heatmap(daily_seconds: dict[date, int]) -> list[dict[str, Any]]:
    return [
        {
            "date": day.isoformat(),
            "week_start": (day - timedelta(days=day.weekday())).isoformat(),
            "weekday": day.strftime("%a"),
            "weekday_index": day.weekday(),
            "value": round_minutes(seconds),
        }
        for day, seconds in sorted(daily_seconds.items())
    ]


def pattern_sentence(spec: dict[str, Any], total_seconds: int, active_day_count: int, longest_day: tuple[date | None, int]) -> str:
    total_minutes = round_minutes(total_seconds)
    average = round(total_minutes / max(active_day_count, 1), 1) if total_minutes else 0
    longest = day_payload(longest_day)
    if not total_minutes:
        return f"{spec['label']} has no detected listening minutes with usable duration yet."
    if longest:
        return f"{spec['label']} averages {average:g} detected minutes per active day. The highest detected listening day was {longest['formatted']} on {longest['date']}."
    return f"{spec['label']} averages {average:g} detected minutes per active day."


def top_payload(
    normalised: dict[str, Any],
    kind: str = "tracks",
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = filter_events(normalised, spec)
    previous = previous_period(spec)
    previous_events = filter_events(normalised, previous) if previous else []
    rolling_spec = resolve_period(normalised, "rolling_year", timezone_name=spec["timezone"], today=spec["today"])
    rolling_events = filter_events(normalised, rolling_spec)
    ranking_events = [event for event in events if event.get("is_music_candidate") is not False]
    previous_ranking_events = [event for event in previous_events if event.get("is_music_candidate") is not False]
    rolling_ranking_events = [event for event in rolling_events if event.get("is_music_candidate") is not False]
    track_lookup = tracks_by_id(normalised)
    artist_metadata = normalised.get("artist_metadata") or {}
    current_ranked = rank_items(ranking_events, track_lookup, kind, artist_metadata)
    previous_ranked = rank_items(previous_ranking_events, track_lookup, kind, artist_metadata)
    rolling_ranked = rank_items(rolling_ranking_events, track_lookup, kind, artist_metadata)
    previous_ranks = {item["key"]: index + 1 for index, item in enumerate(previous_ranked)}
    rolling_ranks = {item["key"]: index + 1 for index, item in enumerate(rolling_ranked)}
    rolling_shares = {item["key"]: item["share_of_period"] for item in rolling_ranked}
    comparison_allowed = len(previous_events) >= MIN_COMPARISON_PLAYS
    items = []
    for index, item in enumerate(current_ranked[:10], 1):
        movement = movement_payload(index, previous_ranks.get(item["key"]), comparison_allowed)
        if normalised.get("metadata", {}).get("source") == "spotify":
            label = "Spotify top artist" if kind == "artists" else item.get("spotify_signal_label") or "Spotify top track"
        else:
            label = classification_label(
                rank=index,
                share=item["share_of_period"],
                period=spec["period"],
                movement=movement,
                rolling_rank=rolling_ranks.get(item["key"]),
                rolling_share=rolling_shares.get(item["key"], 0),
            )
        items.append({**item, "rank": index, "movement": movement, "interpretation_label": label})
    spotify_source = normalised.get("metadata", {}).get("source") == "spotify"
    return {
        "period": serialise_spec(spec),
        "type": "artists" if kind == "artists" else "tracks",
        "total_play_count": len(events),
        "ranked_music_play_count": len(ranking_events),
        "duration_quality": duration_quality(events),
        "sample_warning": "Limited sample: avoid treating this period as a strong taste change." if len(events) < MIN_STRONG_SAMPLE_PLAYS else None,
        "items": items,
        "methodology": (
            "Spotify top lists use top-item, saved-library, playlist and recent-sync signals. Exact full historical Spotify play counts are not available from the API."
            if spotify_source
            else "Top lists are ranked by deterministic detected play counts. Detected listening minutes are estimated from full track durations with duration coverage shown."
        ),
        "classification_rules": [
            "Current obsession: strong current rank and not a rolling-year anchor.",
            "Long-term anchor: highly ranked in both the selected period and rolling-year profile.",
            "Returning favourite: present now after weak or absent immediately prior activity.",
            "One-month spike: current share is much higher than rolling-year share.",
        ],
    }


GENERIC_ALBUM_NAMES = {"", "unknown", "unknown album", "album unavailable", "unavailable", "music", "single", "singles"}


def normalise_match_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def youtube_video_thumbnail(video_id: Any) -> str | None:
    if not video_id:
        return None
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def thumbnail_url(thumbnails: Any, video_id: Any = None) -> str | None:
    return best_thumbnail_url(thumbnails) or youtube_video_thumbnail(video_id)


def artist_metadata_for(
    artist: str,
    artist_metadata: dict[str, dict[str, Any]],
    normalised_lookup: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if artist in artist_metadata:
        return artist_metadata[artist]
    lookup = normalised_lookup if normalised_lookup is not None else {normalise_match_text(name): meta for name, meta in artist_metadata.items()}
    return lookup.get(normalise_match_text(artist), {})


def artist_names_for(track: dict[str, Any], event: dict[str, Any] | None = None) -> list[str]:
    names: list[str] = []
    for source in ((track.get("artists") if track else None), (event or {}).get("artists") if event else None):
        if isinstance(source, list):
            for item in source:
                name = item.get("name") if isinstance(item, dict) else item
                if name:
                    names.append(str(name).strip())
        elif isinstance(source, str):
            names.append(source.strip())
    for name in (track.get("primary_artist") if track else None, (event or {}).get("primary_artist") if event else None):
        if name:
            names.append(str(name).strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = normalise_match_text(name)
        if key and key not in seen:
            seen.add(key)
            deduped.append(name)
    return deduped or [UNKNOWN_ARTIST]


def album_name_is_usable(album: Any) -> bool:
    text = normalise_match_text(album)
    return bool(text and text not in GENERIC_ALBUM_NAMES)


def album_group_for_track(track: dict[str, Any], event: dict[str, Any] | None = None) -> dict[str, str] | None:
    album = str(track.get("album") or "").strip()
    if not album_name_is_usable(album):
        return None
    artists = artist_names_for(track, event)
    artist = artists[0] if artists else UNKNOWN_ARTIST
    album_id = str(track.get("album_id") or "").strip()
    key = f"id:{album_id}" if album_id else f"title:{normalise_match_text(album)}::artist:{normalise_match_text(artist)}"
    return {"key": key, "album": album, "artist": artist, "album_id": album_id}


def rank_items(events: list[dict[str, Any]], track_lookup: dict[str, dict[str, Any]], kind: str, artist_metadata: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    seconds: Counter[str] = Counter()
    usable_counts: Counter[str] = Counter()
    unique_tracks: dict[str, set[str]] = defaultdict(set)
    top_song: dict[str, Counter[str]] = defaultdict(Counter)
    last_played: dict[str, str] = {}
    total = len(events)
    for event in events:
        track = track_lookup.get(event.get("track_id"), {})
        if kind == "artists":
            key = str(track.get("primary_artist") or event.get("primary_artist") or UNKNOWN_ARTIST)
        else:
            key = str(event.get("track_id"))
        counts[key] += 1
        sec = usable_duration_seconds(event) or 0
        seconds[key] += sec
        if sec:
            usable_counts[key] += 1
        unique_tracks[key].add(str(event.get("track_id")))
        title = str(track.get("title") or event.get("title") or "Unknown track")
        artist = str(track.get("primary_artist") or event.get("primary_artist") or UNKNOWN_ARTIST)
        top_song[key][f"{title} - {artist}"] += 1
        played = str(event.get("played_at") or "")
        if played:
            last_played[key] = max(last_played.get(key, ""), played)
    ranked = sorted(
        counts,
        key=lambda key: (-counts[key], -seconds[key], str(key).lower()),
    )
    result = []
    metadata = artist_metadata or {}
    normalised_metadata_lookup = {normalise_match_text(name): meta for name, meta in metadata.items()} if kind == "artists" and metadata else {}
    for key in ranked:
        if kind == "artists":
            artist = key
            meta_track = None
            title = None
            artist_meta = artist_metadata_for(artist, metadata, normalised_metadata_lookup)
            artist_art = resolve_artist_image_url(artist_meta)
            image = artist_art
            most_played_song = top_song[key].most_common(1)[0][0].rsplit(" - ", 1)[0] if top_song[key] else None
            album = None
            source = artist_meta.get("source")
            source_track_id = None
            source_artist_id = artist_meta.get("artist_id")
            artist_image_source = resolve_artist_image_source(artist_meta)
            track_art = None
            track_art_source = None
            album_art = None
            album_art_source = None
            spotify_time_range = artist_meta.get("spotify_time_range")
            spotify_rank = artist_meta.get("spotify_rank")
            spotify_signal_label = None
        else:
            meta_track = track_lookup.get(key, {})
            artist = str(meta_track.get("primary_artist") or UNKNOWN_ARTIST)
            title = str(meta_track.get("title") or "Unknown track")
            track_art = resolve_track_image_url(meta_track)
            album_art = resolve_album_image_url(meta_track)
            image = track_art or album_art
            most_played_song = None
            album = meta_track.get("album")
            source = meta_track.get("source")
            source_track_id = meta_track.get("source_track_id")
            source_artist_id = None
            artist_art = None
            artist_image_source = None
            track_art_source = resolve_track_image_source(meta_track)
            album_art_source = resolve_album_image_source(meta_track)
            spotify_time_range = meta_track.get("spotify_time_range")
            spotify_rank = meta_track.get("spotify_rank")
            spotify_signal_label = meta_track.get("spotify_signal_label")
        play_count = counts[key]
        result.append(
            {
                "key": key,
                "track_id": key if kind != "artists" else None,
                "video_id": meta_track.get("video_id") if meta_track else None,
                "source": source,
                "source_track_id": source_track_id,
                "source_artist_id": source_artist_id,
                "title": title,
                "artist": artist,
                "album": album,
                "thumbnail": image,
                "artist_image_url": artist_art,
                "artist_image_source": artist_image_source,
                "track_image_url": track_art,
                "track_image_source": track_art_source,
                "album_art_url": album_art,
                "album_art_source": album_art_source,
                "play_count": play_count,
                "detected_minutes": round_minutes(seconds[key]),
                "detected_minutes_formatted": format_detected_minutes(round_minutes(seconds[key])),
                "share_of_period": round(play_count / total * 100, 1) if total else 0,
                "duration_coverage_percent": round(usable_counts[key] / play_count * 100, 1) if play_count else 0,
                "unique_songs": len(unique_tracks[key]) if kind == "artists" else None,
                "most_played_song": most_played_song,
                "last_played": last_played.get(key),
                "spotify_time_range": spotify_time_range,
                "spotify_rank": spotify_rank,
                "spotify_signal_label": spotify_signal_label,
            }
        )
    return result


def artist_songs_payload(
    normalised: dict[str, Any],
    artist: str,
    period: str = "this_month",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = [event for event in filter_events(normalised, spec) if event.get("is_music_candidate") is not False]
    track_lookup = tracks_by_id(normalised)
    target = normalise_match_text(artist)
    matched = [
        event
        for event in events
        if target and target in {normalise_match_text(name) for name in artist_names_for(track_lookup.get(event.get("track_id"), {}), event)}
    ]
    ranked = rank_items(matched, track_lookup, "tracks")
    first_played = first_played_by_track(matched)
    songs = [drilldown_song_payload(item, index, "artist", first_played) for index, item in enumerate(ranked, 1)]
    top_song = songs[0]["title"] if songs else None
    artist_meta = artist_metadata_for(artist, normalised.get("artist_metadata") or {})
    artist_thumbnail = resolve_artist_image_url(artist_meta)
    return {
        "artist": artist,
        "artist_thumbnail": artist_thumbnail,
        "artist_image_url": artist_thumbnail,
        "artist_image_source": resolve_artist_image_source(artist_meta),
        "period_label": spec["label"],
        "period": serialise_spec(spec),
        "total_plays": len(matched),
        "unique_songs": len({event.get("track_id") for event in matched if event.get("track_id")}),
        "detected_minutes": round_minutes(seconds_for_events(matched)),
        "detected_minutes_formatted": format_detected_minutes(round_minutes(seconds_for_events(matched))),
        "duration_coverage_percent": duration_quality(matched)["duration_coverage_percent"],
        "most_replayed_song": top_song,
        "songs": songs,
    }


def albums_payload(
    normalised: dict[str, Any],
    period: str = "this_month",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = [event for event in filter_events(normalised, spec) if event.get("is_music_candidate") is not False]
    track_lookup = tracks_by_id(normalised)
    albums = rank_albums(events, track_lookup, spec)
    return {
        "period": serialise_spec(spec),
        "period_label": spec["label"],
        "total_play_count": len(events),
        "duration_quality": duration_quality(events),
        "sample_warning": "Limited monthly sample - this view may be shaped by short-term spikes." if len(events) < MIN_STRONG_SAMPLE_PLAYS and spec["period"] in {"this_month", "month"} else None,
        "albums": albums[: max(1, min(int(limit or 10), 20))],
        "methodology": "Favourite albums are ranked from existing local listening events grouped by album metadata. Albums without usable album names are excluded instead of being guessed.",
    }


def rank_albums(events: list[dict[str, Any]], track_lookup: dict[str, dict[str, Any]], spec: dict[str, Any]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "album": "",
            "artist": UNKNOWN_ARTIST,
            "album_id": None,
            "thumbnail": None,
            "album_image_url": None,
            "album_image_source": None,
            "plays": 0,
            "seconds": 0,
            "usable": 0,
            "tracks": set(),
            "song_counts": Counter(),
            "song_titles": {},
            "last_played": "",
        }
    )
    total = len(events)
    for event in events:
        track = track_lookup.get(event.get("track_id"), {})
        group = album_group_for_track(track, event)
        if not group:
            continue
        key = group["key"]
        stat = stats[key]
        stat["album"] = stat["album"] or group["album"]
        stat["artist"] = stat["artist"] if stat["artist"] != UNKNOWN_ARTIST else group["artist"]
        stat["album_id"] = stat["album_id"] or group["album_id"] or None
        album_art = resolve_album_image_url(track)
        stat["album_image_url"] = stat["album_image_url"] or album_art
        stat["album_image_source"] = stat["album_image_source"] or resolve_album_image_source(track)
        stat["thumbnail"] = stat["thumbnail"] or album_art
        stat["plays"] += 1
        sec = usable_duration_seconds(event) or 0
        stat["seconds"] += sec
        if sec:
            stat["usable"] += 1
        track_id = str(event.get("track_id") or "")
        if track_id:
            stat["tracks"].add(track_id)
            stat["song_counts"][track_id] += 1
            stat["song_titles"][track_id] = str(track.get("title") or event.get("title") or "Unknown track")
        played = str(event.get("played_at") or "")
        if played:
            stat["last_played"] = max(stat["last_played"], played)
    ranked = sorted(
        stats.values(),
        key=lambda item: (-int(item["plays"]), -float(item["seconds"]), -len(item["tracks"]), str(item["album"]).lower()),
    )
    result = []
    for index, item in enumerate(ranked, 1):
        play_count = int(item["plays"])
        unique_songs = len(item["tracks"])
        most_played_id, most_played_count = item["song_counts"].most_common(1)[0] if item["song_counts"] else ("", 0)
        most_played_song = item["song_titles"].get(most_played_id)
        result.append(
            {
                "rank": index,
                "key": str(item.get("album_id") or f"{item['album']}::{item['artist']}"),
                "album": item["album"],
                "artist": item["artist"],
                "album_id": item.get("album_id"),
                "thumbnail": item.get("thumbnail"),
                "album_image_url": item.get("album_image_url"),
                "album_image_source": item.get("album_image_source"),
                "plays": play_count,
                "detected_minutes": round_minutes(item["seconds"]),
                "detected_minutes_formatted": format_detected_minutes(round_minutes(item["seconds"])),
                "unique_songs": unique_songs,
                "most_played_song": most_played_song,
                "share": round(play_count / total * 100, 1) if total else 0,
                "duration_coverage_percent": round(int(item["usable"]) / play_count * 100, 1) if play_count else 0,
                "last_played": item.get("last_played") or None,
                "label": album_label(str(item["album"]), unique_songs, play_count, spec),
                "album_signal_note": album_signal_note(most_played_song, most_played_count, play_count, unique_songs),
            }
        )
    return result


def album_label(album: str, unique_songs: int, play_count: int, spec: dict[str, Any]) -> str:
    lowered = album.lower()
    if "soundtrack" in lowered or lowered in {"ost", "score"}:
        return "Soundtrack side quest"
    if unique_songs <= 1 and play_count >= 3:
        return "Single-led album signal"
    if unique_songs >= 5:
        return "Album anchor"
    if spec["period"] in {"this_month", "month"} and play_count >= 3:
        return "Current album phase"
    if unique_songs >= 3:
        return "Deep-cut album"
    return "Album signal"


def album_signal_note(most_played_song: str | None, most_played_count: int, play_count: int, unique_songs: int) -> str:
    if not most_played_song:
        return "Album signal is based on available track metadata for this period."
    if unique_songs <= 1 or (play_count and most_played_count / play_count >= 0.65):
        return f"Mostly driven by {most_played_song}."
    return "Real album-level signal."


def album_songs_payload(
    normalised: dict[str, Any],
    album: str,
    artist: str | None = None,
    period: str = "this_month",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = [event for event in filter_events(normalised, spec) if event.get("is_music_candidate") is not False]
    track_lookup = tracks_by_id(normalised)
    target_album = normalise_match_text(album)
    target_artist = normalise_match_text(artist)
    matched = []
    for event in events:
        track = track_lookup.get(event.get("track_id"), {})
        if normalise_match_text(track.get("album")) != target_album:
            continue
        if target_artist and target_artist not in {normalise_match_text(name) for name in artist_names_for(track, event)}:
            continue
        matched.append(event)
    ranked = rank_items(matched, track_lookup, "tracks")
    first_played = first_played_by_track(matched)
    songs = [drilldown_song_payload(item, index, "album", first_played) for index, item in enumerate(ranked, 1)]
    top_song = songs[0]["title"] if songs else None
    return {
        "album": album,
        "artist": artist,
        "period_label": spec["label"],
        "period": serialise_spec(spec),
        "total_plays": len(matched),
        "unique_songs": len({event.get("track_id") for event in matched if event.get("track_id")}),
        "detected_minutes": round_minutes(seconds_for_events(matched)),
        "detected_minutes_formatted": format_detected_minutes(round_minutes(seconds_for_events(matched))),
        "duration_coverage_percent": duration_quality(matched)["duration_coverage_percent"],
        "most_played_song": top_song,
        "songs": songs,
    }


def first_played_by_track(events: list[dict[str, Any]]) -> dict[str, str]:
    first: dict[str, str] = {}
    for event in events:
        track_id = str(event.get("track_id") or "")
        played = str(event.get("played_at") or "")
        if not track_id or not played:
            continue
        first[track_id] = min(first.get(track_id, played), played)
    return first


def drilldown_song_payload(item: dict[str, Any], rank: int, scope: str, first_played: dict[str, str]) -> dict[str, Any]:
    payload = {
        "rank": rank,
        "track_id": item.get("track_id"),
        "video_id": item.get("video_id"),
        "title": item.get("title"),
        "artist": item.get("artist"),
        "album": item.get("album"),
        "thumbnail": item.get("thumbnail"),
        "track_image_url": item.get("track_image_url"),
        "track_image_source": item.get("track_image_source"),
        "album_art_url": item.get("album_art_url"),
        "album_art_source": item.get("album_art_source"),
        "plays": item.get("play_count", 0),
        "detected_minutes": item.get("detected_minutes", 0),
        "detected_minutes_formatted": item.get("detected_minutes_formatted"),
        "last_played": item.get("last_played"),
        "first_played": first_played.get(str(item.get("track_id") or "")),
        "duration_coverage_percent": item.get("duration_coverage_percent", 0),
    }
    share_key = "share_of_artist_plays" if scope == "artist" else "share_of_album_plays"
    payload[share_key] = item.get("share_of_period", 0)
    return payload


def movement_payload(current_rank: int, previous_rank: int | None, comparison_allowed: bool) -> dict[str, Any] | None:
    if not comparison_allowed:
        return None
    if previous_rank is None:
        return {"direction": "new", "previous_rank": None, "rank_delta": None, "label": "New"}
    delta = previous_rank - current_rank
    if delta > 0:
        direction = "up"
        label = f"Up {delta}"
    elif delta < 0:
        direction = "down"
        label = f"Down {abs(delta)}"
    else:
        direction = "no_change"
        label = "Stable"
    return {"direction": direction, "previous_rank": previous_rank, "rank_delta": delta, "label": label}


def classification_label(rank: int, share: float, period: str, movement: dict[str, Any] | None, rolling_rank: int | None, rolling_share: float) -> str:
    if period == "rolling_year" or (rolling_rank is not None and rolling_rank <= 10 and rank <= 10):
        return "Long-term anchor"
    if share >= max(6.0, rolling_share * 2.5) and period in {"this_month", "month"}:
        return "One-month spike"
    if rank <= 3 and (rolling_rank is None or rolling_rank > 10):
        return "Current obsession"
    if movement and movement.get("direction") == "new":
        return "New arrival"
    if movement and movement.get("direction") == "up":
        return "Returning favourite"
    return "Comfort favourite"


def taste_dna_payload(
    normalised: dict[str, Any],
    period: str = "rolling_year",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = filter_events(normalised, spec)
    track_lookup = tracks_by_id(normalised)
    artist_counts = artist_counts_for_events(events, track_lookup)
    period_norm = normalised_for_events(normalised, events, spec)
    taste = build_taste_model(period_norm, artist_counts, len(events))
    nodes = taste_nodes(events, track_lookup, taste)
    traits = trait_nodes(events, track_lookup, len(events))
    return {
        "period": serialise_spec(spec),
        "summary": taste.get("summary"),
        "core_identity": core_identity(taste),
        "taste_interpretation": taste,
        "duration_quality": duration_quality(events),
        "nodes": nodes,
        "traits": traits,
        "structured_summary": structured_taste_summary(taste, nodes),
        "sample_warning": "Limited monthly sample - this view may be shaped by short-term spikes." if len(events) < MIN_STRONG_SAMPLE_PLAYS else None,
        "methodology": "Sound Profile uses detected plays, curated artist genre mappings, and duration-aware period filters. It is music analysis, not a psychological diagnosis.",
    }


def core_identity(taste: dict[str, Any]) -> str:
    dna = taste.get("taste_dna", {})
    core = dna.get("core_dna") or [item.get("name") for item in taste.get("core_genre_families", [])]
    return " / ".join([str(item) for item in core[:3] if item]) or "Mapped listening core"


def taste_nodes(events: list[dict[str, Any]], track_lookup: dict[str, dict[str, Any]], taste: dict[str, Any]) -> list[dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"play_weight": 0.0, "seconds": 0.0, "artists": Counter(), "songs": Counter(), "genres": Counter(), "traits": Counter()})
    for event in events:
        track = track_lookup.get(event.get("track_id"), {})
        artist = str(track.get("primary_artist") or event.get("primary_artist") or UNKNOWN_ARTIST)
        profile = profile_for_artist(artist)
        clusters = profile.get("broad_clusters") or []
        if not clusters:
            continue
        weight = 1 / len(clusters)
        seconds = (usable_duration_seconds(event) or 0) * weight
        title = str(track.get("title") or event.get("title") or "Unknown track")
        for cluster in clusters:
            stats[cluster]["play_weight"] += weight
            stats[cluster]["seconds"] += seconds
            stats[cluster]["artists"][artist] += 1
            stats[cluster]["songs"][f"{title} - {artist}"] += 1
            for genre in profile.get("canonical_genres") or []:
                stats[cluster]["genres"][genre] += 1
            for trait in profile.get("sonic_traits") or []:
                stats[cluster]["traits"][trait] += 1
    layer_by_name = {}
    for item in taste.get("core_genre_families", []):
        layer_by_name[item["name"]] = "Core"
    for item in taste.get("secondary_genre_families", []):
        layer_by_name[item["name"]] = "Secondary"
    for item in taste.get("side_quests", []):
        layer_by_name[item["name"]] = "Side Quest"
    nodes = []
    for cluster in taste.get("cluster_shares", []):
        name = cluster["name"]
        detail = stats.get(name, {})
        share = float(cluster.get("share", 0))
        anchor = CLUSTER_ANCHORS.get(name, (50, 50))
        nodes.append(
            {
                "id": name,
                "name": name,
                "share": share,
                "size": round(max(44, min(92, 40 + share * 2.4)), 1),
                "x": anchor[0],
                "y": anchor[1],
                "layer": layer_by_name.get(name, "Trace"),
                "detected_minutes": round_minutes(detail.get("seconds", 0)),
                "detected_minutes_formatted": format_detected_minutes(round_minutes(detail.get("seconds", 0))),
                "top_artists": [{"name": artist, "plays": count} for artist, count in detail.get("artists", Counter()).most_common(5)],
                "top_songs": [{"name": song, "plays": count} for song, count in detail.get("songs", Counter()).most_common(5)],
                "canonical_genres": [genre for genre, _ in detail.get("genres", Counter()).most_common(8)],
                "sonic_traits": [trait for trait, _ in detail.get("traits", Counter()).most_common(8)],
                "confidence": taste.get("coverage", {}).get("genre_coverage_percent", 0),
                "role": node_role(name, layer_by_name.get(name, "Trace"), detail),
            }
        )
    return nodes


def node_role(name: str, layer: str, detail: dict[str, Any]) -> str:
    artists = [artist for artist, _ in detail.get("artists", Counter()).most_common(3)]
    if not artists:
        return f"{name} is present, but the app has limited artist-level evidence for this period."
    return f"{name} is a {layer.lower()} part of the profile here, led by {', '.join(artists)}."


def trait_nodes(events: list[dict[str, Any]], track_lookup: dict[str, dict[str, Any]], total_events: int) -> list[dict[str, Any]]:
    trait_counts: Counter[str] = Counter()
    trait_artists: dict[str, Counter[str]] = defaultdict(Counter)
    trait_clusters: dict[str, Counter[str]] = defaultdict(Counter)
    classified = 0
    for event in events:
        track = track_lookup.get(event.get("track_id"), {})
        artist = str(track.get("primary_artist") or event.get("primary_artist") or UNKNOWN_ARTIST)
        profile = profile_for_artist(artist)
        traits = profile.get("sonic_traits") or []
        clusters = profile.get("broad_clusters") or []
        if traits:
            classified += 1
        for trait in traits:
            trait_counts[trait] += 1
            trait_artists[trait][artist] += 1
            for cluster in clusters:
                trait_clusters[trait][cluster] += 1
    denominator = classified or total_events or 1
    return [
        {
            "trait": trait,
            "support_percent": round(count / denominator * 100, 1),
            "confidence": "High" if count >= 20 else "Medium" if count >= 5 else "Limited",
            "supporting_artists": [{"name": artist, "plays": plays} for artist, plays in trait_artists[trait].most_common(5)],
            "supporting_clusters": [{"name": cluster, "plays": plays} for cluster, plays in trait_clusters[trait].most_common(5)],
            "explanation": f"{trait} is supported by mapped artist and genre evidence. It describes sound, not personality or mental state.",
        }
        for trait, count in trait_counts.most_common(10)
    ]


def structured_taste_summary(taste: dict[str, Any], nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"label": "Core", "items": [item.get("name") for item in taste.get("core_genre_families", [])]},
        {"label": "Secondary", "items": [item.get("name") for item in taste.get("secondary_genre_families", [])]},
        {"label": "Side Quest", "items": [item.get("name") for item in taste.get("side_quests", [])]},
        {"label": "Strongest evidence", "items": [f"{node['name']} ({node['share']}%)" for node in nodes[:5]]},
    ]


def taste_dna_comparison_payload(
    normalised: dict[str, Any],
    base: str = "rolling_year",
    compare: str = "this_month",
    month: str | None = None,
    timezone_name: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    base_payload = taste_dna_payload(normalised, base, timezone_name=timezone_name, today=today)
    compare_payload = taste_dna_payload(normalised, compare, month=month, timezone_name=timezone_name, today=today)
    base_nodes = {node["name"]: node for node in base_payload.get("nodes", [])}
    compare_nodes = {node["name"]: node for node in compare_payload.get("nodes", [])}
    deltas = []
    for name in sorted(set(base_nodes) | set(compare_nodes)):
        base_share = float(base_nodes.get(name, {}).get("share", 0))
        compare_share = float(compare_nodes.get(name, {}).get("share", 0))
        deltas.append({"name": name, "base_share": base_share, "compare_share": compare_share, "delta": round(compare_share - base_share, 1)})
    sufficient = (compare_payload.get("duration_quality", {}).get("total_detected_plays", 0) or 0) >= MIN_STRONG_SAMPLE_PLAYS
    growing = max(deltas, key=lambda item: item["delta"], default=None)
    declining = min(deltas, key=lambda item: item["delta"], default=None)
    new_side = next((item for item in sorted(deltas, key=lambda item: item["compare_share"], reverse=True) if item["base_share"] < 0.5 and item["compare_share"] >= 1), None)
    stable = [
        item["name"]
        for item in deltas
        if item["name"] in {node["name"] for node in compare_payload.get("nodes", []) if node.get("layer") == "Core"}
        and item["base_share"] >= 4
        and abs(item["delta"]) <= 2
    ][:3]
    claims = {
        "growing_cluster": growing if sufficient and growing and growing["delta"] >= 2 else None,
        "declining_cluster": declining if sufficient and declining and declining["delta"] <= -2 else None,
        "new_side_interest": new_side if sufficient else None,
        "stable_core_identity": stable if sufficient else [],
    }
    if sufficient and claims["growing_cluster"]:
        name = claims["growing_cluster"]["name"]
        delta = claims["growing_cluster"]["delta"]
        sentence = f"{name} is unusually strong in {compare_payload['period']['label']} compared with the {base_payload['period']['label']} baseline (+{delta} points)."
    elif sufficient and claims["declining_cluster"]:
        name = claims["declining_cluster"]["name"]
        delta = claims["declining_cluster"]["delta"]
        sentence = f"{name} is lower in {compare_payload['period']['label']} than the {base_payload['period']['label']} baseline ({delta} points), while no cluster has enough growth for a strong growth claim."
    else:
        sentence = "There is not enough reliable period contrast to make a strong sound-profile change claim yet."
    return {
        "base_period": base_payload["period"],
        "compare_period": compare_payload["period"],
        "deltas": deltas,
        "claims": claims,
        "summary_sentence": sentence,
        "sample_warning": None if sufficient else "Limited sample: comparison claims are suppressed until the selected period has enough detected plays.",
    }
