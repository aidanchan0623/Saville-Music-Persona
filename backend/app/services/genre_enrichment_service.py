from __future__ import annotations

import math
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.analysis.taste_model import has_usable_artist, profile_for_artist, source_genres_for_artist
from app.data.artist_genres import normalise_artist_name, normalise_genre


MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"
GENRE_METADATA_CACHE_VERSION = 3
NEGATIVE_CACHE_TTL_DAYS = 30
POSITIVE_CACHE_TTL_DAYS = 180


class MusicBrainzGenreService:
    """Resolve conservative artist-level genres without turning fuzzy matches into facts."""

    def __init__(self, request_interval_seconds: float = 1.05, timeout_seconds: float = 12.0) -> None:
        self.request_interval_seconds = request_interval_seconds
        self.timeout_seconds = timeout_seconds
        self._last_request_at = 0.0

    def enrich(
        self,
        normalised: dict[str, Any],
        cache: dict[str, Any] | None,
        *,
        limit: int,
        deadline: float,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(cache, dict) or cache.get("schemaVersion") != GENRE_METADATA_CACHE_VERSION:
            clear_musicbrainz_genres(normalised)
        prepared_cache = ensure_genre_cache(cache)
        items = prepared_cache["items"]
        applied_cached = self.apply_cached_matches(normalised, items)
        play_counts = unknown_artist_play_counts(normalised)
        candidates = [
            (artist, plays)
            for artist, plays in play_counts.most_common()
            if should_refresh(items.get(normalise_artist_name(artist)))
        ]
        attempted = 0
        matched = 0
        matched_events = 0
        failed = 0
        provider_error: str | None = None

        with httpx.Client(timeout=self.timeout_seconds) as client:
            for artist, plays in candidates[: max(0, limit)]:
                try:
                    self.check_deadline(deadline)
                    record = self.resolve_artist(client, artist, deadline)
                except TimeoutError:
                    provider_error = "musicbrainz_time_limit_reached"
                    break
                except httpx.HTTPError:
                    failed += 1
                    provider_error = "musicbrainz_temporarily_unavailable"
                    break
                items[normalise_artist_name(artist)] = record
                attempted += 1
                if record["status"] == "matched":
                    apply_genre_record(normalised, artist, record)
                    matched += 1
                    matched_events += plays

        prepared_cache["updatedAt"] = utc_now()
        remaining = max(0, len(candidates) - attempted)
        stats = {
            "attempted": attempted,
            "matched": matched,
            "matchedEventCount": matched_events,
            "appliedCached": applied_cached,
            "failed": failed,
            "providerError": provider_error,
            "remainingCandidates": remaining,
            "unknownArtistCount": len(play_counts),
        }
        return prepared_cache, stats

    def apply_cached_matches(self, normalised: dict[str, Any], items: dict[str, Any]) -> int:
        applied = 0
        for artist in artist_names(normalised):
            record = items.get(normalise_artist_name(artist))
            if isinstance(record, dict) and record.get("status") == "matched" and record.get("genres"):
                apply_genre_record(normalised, artist, record)
                applied += 1
        return applied

    def resolve_artist(self, client: httpx.Client, artist: str, deadline: float) -> dict[str, Any]:
        query = f'artist:"{lucene_phrase(artist)}"'
        search = self._get_json(
            client,
            f"{MUSICBRAINZ_API_URL}/artist/",
            {"query": query, "fmt": "json", "limit": 5},
            deadline,
        )
        exact = unique_exact_candidates(search.get("artists"), artist)
        checked_at = utc_now()
        if not exact:
            return cache_record(artist, "not_found", checked_at=checked_at)
        if len(exact) != 1:
            return cache_record(artist, "ambiguous", checked_at=checked_at)

        match = exact[0]
        artist_id = str(match.get("id") or "")
        if not artist_id:
            return cache_record(artist, "not_found", checked_at=checked_at)
        detail = self._get_json(
            client,
            f"{MUSICBRAINZ_API_URL}/artist/{artist_id}",
            {"inc": "genres", "fmt": "json"},
            deadline,
        )
        genres = supported_genres(detail.get("genres"))
        if not genres:
            return cache_record(
                artist,
                "no_supported_genres",
                provider_artist_id=artist_id,
                matched_name=str(match.get("name") or artist),
                checked_at=checked_at,
            )
        return cache_record(
            artist,
            "matched",
            genres=genres,
            provider_artist_id=artist_id,
            matched_name=str(match.get("name") or artist),
            checked_at=checked_at,
        )

    def _get_json(
        self,
        client: httpx.Client,
        url: str,
        params: dict[str, Any],
        deadline: float,
    ) -> dict[str, Any]:
        response: httpx.Response | None = None
        for attempt in range(3):
            self._wait_for_rate_limit(deadline)
            response = client.get(
                url,
                params=params,
                headers={"User-Agent": "SavilleMusicPersona/0.1 (https://github.com/aidanchan0623/Saville-Music-Persona)"},
            )
            self._last_request_at = time.monotonic()
            if response.status_code not in {429, 503} or attempt == 2:
                break
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else float(2 ** (attempt + 1))
            if time.monotonic() + delay > deadline:
                raise TimeoutError
            time.sleep(delay)
        if response is None:
            raise httpx.RequestError("MusicBrainz request did not produce a response", request=httpx.Request("GET", url))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _wait_for_rate_limit(self, deadline: float) -> None:
        remaining = self.request_interval_seconds - (time.monotonic() - self._last_request_at)
        if remaining > 0:
            if time.monotonic() + remaining > deadline:
                raise TimeoutError
            time.sleep(remaining)
        self.check_deadline(deadline)

    @staticmethod
    def check_deadline(deadline: float) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError


def ensure_genre_cache(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schemaVersion") != GENRE_METADATA_CACHE_VERSION:
        return {
            "schemaVersion": GENRE_METADATA_CACHE_VERSION,
            "provider": "musicbrainz",
            "updatedAt": None,
            "items": {},
        }
    items = value.get("items")
    value["items"] = items if isinstance(items, dict) else {}
    return value


def cache_record(
    artist: str,
    status: str,
    *,
    genres: list[str] | None = None,
    provider_artist_id: str | None = None,
    matched_name: str | None = None,
    checked_at: str,
) -> dict[str, Any]:
    return {
        "artistName": artist,
        "status": status,
        "genres": list(genres or []),
        "provider": "musicbrainz",
        "providerArtistId": provider_artist_id,
        "matchedName": matched_name,
        "confidence": "medium" if status == "matched" else "unavailable",
        "checkedAt": checked_at,
    }


def unique_exact_candidates(value: Any, artist: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    target = normalise_artist_name(artist)
    matches: dict[str, dict[str, Any]] = {}
    for candidate in value:
        if not isinstance(candidate, dict) or int(candidate.get("score") or 0) < 98:
            continue
        names = [candidate.get("name")]
        names.extend(alias.get("name") for alias in candidate.get("aliases") or [] if isinstance(alias, dict))
        if target not in {normalise_artist_name(str(name or "")) for name in names}:
            continue
        candidate_id = str(candidate.get("id") or "")
        if candidate_id:
            matches[candidate_id] = candidate
    return list(matches.values())


def supported_genres(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    genres: list[str] = []
    ordered = sorted(
        (item for item in value if isinstance(item, dict) and item.get("name")),
        key=lambda item: int(item.get("count") or 0),
        reverse=True,
    )
    top_count = int(ordered[0].get("count") or 0) if ordered else 0
    minimum_count = max(1, math.ceil(top_count * 0.1))
    for item in ordered:
        if int(item.get("count") or 0) < minimum_count:
            continue
        normalised = normalise_genre(str(item["name"]))
        if normalised:
            name = normalised[1].casefold()
            if name not in genres:
                genres.append(name)
    return genres[:8]


def unknown_artist_play_counts(normalised: dict[str, Any]) -> Counter[str]:
    tracks = {track.get("track_id"): track for track in normalised.get("tracks") or [] if isinstance(track, dict)}
    metadata = normalised.get("artist_metadata") if isinstance(normalised.get("artist_metadata"), dict) else {}
    counts: Counter[str] = Counter()
    for event in normalised.get("play_events") or []:
        if not isinstance(event, dict):
            continue
        track = tracks.get(event.get("track_id")) or {}
        artist = str(track.get("primary_artist") or event.get("primary_artist") or "").strip()
        if not has_usable_artist(artist):
            continue
        genres = source_genres_for_artist(track, metadata, artist)
        if not profile_for_artist(artist, genres).get("canonical_genres"):
            counts[artist] += 1
    return counts


def artist_names(normalised: dict[str, Any]) -> set[str]:
    names = {
        str(track.get("primary_artist") or "").strip()
        for track in normalised.get("tracks") or []
        if isinstance(track, dict) and has_usable_artist(track.get("primary_artist"))
    }
    return {name for name in names if name}


def apply_genre_record(normalised: dict[str, Any], artist: str, record: dict[str, Any]) -> None:
    metadata = normalised.setdefault("artist_metadata", {})
    existing_name = next((name for name in metadata if normalise_artist_name(str(name)) == normalise_artist_name(artist)), artist)
    item = metadata.setdefault(existing_name, {})
    if item.get("genres"):
        return
    item["genres"] = list(record.get("genres") or [])
    item["genre_source"] = "musicbrainz_artist_genres"
    item["genre_confidence"] = "medium"
    item["musicbrainz_artist_id"] = record.get("providerArtistId")
    item["genre_checked_at"] = record.get("checkedAt")


def clear_musicbrainz_genres(normalised: dict[str, Any]) -> None:
    metadata = normalised.get("artist_metadata")
    if not isinstance(metadata, dict):
        return
    for item in metadata.values():
        if not isinstance(item, dict) or item.get("genre_source") != "musicbrainz_artist_genres":
            continue
        item["genres"] = []
        for key in ("genre_source", "genre_confidence", "musicbrainz_artist_id", "genre_checked_at"):
            item.pop(key, None)


def should_refresh(record: Any) -> bool:
    if not isinstance(record, dict):
        return True
    checked_at = parse_timestamp(record.get("checkedAt"))
    if not checked_at:
        return True
    ttl = POSITIVE_CACHE_TTL_DAYS if record.get("status") == "matched" else NEGATIVE_CACHE_TTL_DAYS
    return checked_at < datetime.now(timezone.utc) - timedelta(days=ttl)


def parse_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def lucene_phrase(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
