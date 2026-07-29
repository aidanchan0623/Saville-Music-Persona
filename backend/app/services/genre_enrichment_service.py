from __future__ import annotations

import math
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import httpx

from app.analysis.taste_model import has_usable_artist, primary_genre_for_profile, profile_for_artist, source_genres_for_artist
from app.data.artist_genres import normalise_artist_name, normalise_genre


MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"
GENRE_METADATA_CACHE_VERSION = 5
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
        on_cache_update: Callable[[dict[str, Any]], None] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(cache, dict) or cache.get("schemaVersion") not in {3, 4, GENRE_METADATA_CACHE_VERSION}:
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
                record = merge_cache_record(prepared_cache, artist, record)
                attempted += 1
                if record["status"] == "matched":
                    apply_genre_record(normalised, artist, record)
                    matched += 1
                    matched_events += plays
                prepared_cache["updatedAt"] = utc_now()
                if on_cache_update:
                    on_cache_update(prepared_cache)

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
            {"inc": "genres+tags", "fmt": "json"},
            deadline,
        )
        # MusicBrainz exposes both its genre list and community tags. Both are
        # attached to the exact MBID resolved above; unsupported labels are
        # still rejected by Saville's canonical genre map.
        genre_rows = detail.get("genres") if isinstance(detail.get("genres"), list) else []
        tag_rows = detail.get("tags") if isinstance(detail.get("tags"), list) else []
        genres = supported_genres([*genre_rows, *tag_rows])
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
    if not isinstance(value, dict) or value.get("schemaVersion") not in {3, 4, GENRE_METADATA_CACHE_VERSION}:
        return {
            "schemaVersion": GENRE_METADATA_CACHE_VERSION,
            "provider": "multi_source",
            "updatedAt": None,
            "items": {},
        }
    migrated = {
        "schemaVersion": GENRE_METADATA_CACHE_VERSION,
        "provider": "multi_source",
        "updatedAt": value.get("updatedAt"),
        "items": {},
    }
    previous_version = int(value.get("schemaVersion") or 0)
    for key, record in (value.get("items") or {}).items():
        if isinstance(record, dict):
            prepared = normalise_cache_record(record)
            # v5 started reading exact-artist MusicBrainz tags in addition to
            # genres. Recheck only old negative results; durable positive
            # evidence remains valid and offline-capable.
            if previous_version < 5 and prepared.get("status") != "matched":
                prepared["checkedAt"] = None
            migrated["items"][str(key)] = prepared
    return migrated


def apply_genre_cache(normalised: dict[str, Any], cache: dict[str, Any] | None) -> int:
    """Reapply durable trusted genre matches after any canonical profile rebuild."""
    prepared = ensure_genre_cache(cache)
    applied = 0
    for artist in artist_names(normalised):
        record = prepared["items"].get(normalise_artist_name(artist))
        if isinstance(record, dict) and record.get("status") == "matched" and record.get("genres"):
            apply_genre_record(normalised, artist, record)
            applied += 1
    return applied


def seed_cache_from_source(
    cache: dict[str, Any] | None,
    source_normalised: dict[str, Any] | None,
    *,
    provider: str,
) -> tuple[dict[str, Any], int]:
    """Add exact-name genres from an authenticated catalogue without fuzzy identity guesses."""
    prepared = ensure_genre_cache(cache)
    if not isinstance(source_normalised, dict):
        return prepared, 0
    added = 0
    metadata = source_normalised.get("artist_metadata")
    if not isinstance(metadata, dict):
        return prepared, 0
    for artist, item in metadata.items():
        if not isinstance(item, dict) or not has_usable_artist(artist):
            continue
        if provider == "spotify":
            artist_id = str(item.get("artist_id") or "")
            if item.get("source") != "spotify" and not artist_id.startswith("spotify:artist:"):
                continue
        genres = supported_genre_names(item.get("genres"))
        if not genres:
            continue
        provider_artist_id = str(item.get("artist_id") or "").strip() or None
        current = prepared["items"].get(normalise_artist_name(str(artist)))
        current_evidence = current.get("evidence") if isinstance(current, dict) else []
        source_identity = evidence_identity(
            {"provider": provider, "providerArtistId": provider_artist_id, "matchedName": str(artist)}
        )
        if any(
            evidence_identity(evidence) == source_identity
            and genre_keys(evidence.get("genres")) == genre_keys(genres)
            for evidence in current_evidence or []
            if isinstance(evidence, dict)
        ):
            continue
        record = cache_record(
            str(artist),
            "matched",
            genres=genres,
            provider=provider,
            provider_artist_id=provider_artist_id,
            matched_name=str(artist),
            checked_at=utc_now(),
            confidence="medium",
            match_method="exact_normalised_artist_name",
        )
        before = prepared["items"].get(normalise_artist_name(str(artist)))
        merged = merge_cache_record(prepared, str(artist), record)
        if before != merged:
            added += 1
    if added:
        prepared["updatedAt"] = utc_now()
    return prepared, added


def cache_record(
    artist: str,
    status: str,
    *,
    genres: list[str] | None = None,
    provider: str = "musicbrainz",
    provider_artist_id: str | None = None,
    matched_name: str | None = None,
    checked_at: str,
    confidence: str | None = None,
    match_method: str = "unique_exact_artist_alias",
) -> dict[str, Any]:
    record = {
        "artistName": artist,
        "status": status,
        "genres": list(genres or []),
        "provider": provider,
        "providerArtistId": provider_artist_id,
        "matchedName": matched_name,
        "confidence": confidence or ("medium" if status == "matched" else "unavailable"),
        "matchMethod": match_method if status == "matched" else None,
        "checkedAt": checked_at,
    }
    record["evidence"] = [evidence_from_record(record)] if status == "matched" else []
    return record


def normalise_cache_record(record: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(record)
    prepared["genres"] = supported_genre_names(record.get("genres"))
    evidence = [dict(item) for item in record.get("evidence") or [] if isinstance(item, dict)]
    if record.get("status") == "matched" and prepared["genres"] and not evidence:
        evidence = [evidence_from_record(prepared)]
    prepared["evidence"] = evidence
    return prepared


def evidence_from_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": record.get("provider"),
        "providerArtistId": record.get("providerArtistId"),
        "matchedName": record.get("matchedName") or record.get("artistName"),
        "genres": supported_genre_names(record.get("genres")),
        "confidence": record.get("confidence") or "medium",
        "matchMethod": record.get("matchMethod") or "unique_exact_artist_alias",
        "checkedAt": record.get("checkedAt"),
    }


def merge_cache_record(cache: dict[str, Any], artist: str, incoming: dict[str, Any]) -> dict[str, Any]:
    key = normalise_artist_name(artist)
    current = cache["items"].get(key)
    if incoming.get("status") != "matched" or not incoming.get("genres"):
        if not isinstance(current, dict) or current.get("status") != "matched":
            cache["items"][key] = normalise_cache_record(incoming)
        return cache["items"].get(key) or incoming

    records = []
    if isinstance(current, dict) and current.get("status") == "matched":
        records.extend(item for item in current.get("evidence") or [] if isinstance(item, dict))
        if not records:
            records.append(evidence_from_record(current))
    incoming_evidence = [item for item in incoming.get("evidence") or [] if isinstance(item, dict)]
    if not incoming_evidence:
        incoming_evidence = [evidence_from_record(incoming)]
    replacement_keys = {evidence_identity(item) for item in incoming_evidence}
    records = [item for item in records if evidence_identity(item) not in replacement_keys]
    records.extend(incoming_evidence)

    unique: dict[tuple[str, str, tuple[str, ...]], dict[str, Any]] = {}
    for evidence in records:
        genres = tuple(supported_genre_names(evidence.get("genres")))
        identity = (str(evidence.get("provider") or ""), str(evidence.get("providerArtistId") or ""), genres)
        if genres:
            unique[identity] = {**evidence, "genres": list(genres)}
    evidence = list(unique.values())
    genres = combined_evidence_genres(evidence)
    providers = sorted({str(item.get("provider")) for item in evidence if item.get("provider")})
    consensus = has_genre_consensus(evidence)
    merged = {
        **normalise_cache_record(incoming),
        "artistName": artist,
        "status": "matched",
        "genres": genres,
        "provider": "+".join(providers) if providers else incoming.get("provider"),
        "confidence": "high" if consensus else "medium",
        "matchMethod": "provider_consensus" if consensus else "multi_provider_exact_match" if len(providers) > 1 else incoming.get("matchMethod"),
        "evidence": evidence,
    }
    cache["items"][key] = merged
    return merged


def evidence_identity(evidence: dict[str, Any]) -> tuple[str, str]:
    provider = str(evidence.get("provider") or "")
    entity = str(evidence.get("providerArtistId") or evidence.get("matchedName") or "")
    return provider, normalise_artist_name(entity)


def has_genre_consensus(evidence: list[dict[str, Any]]) -> bool:
    provider_genres: dict[str, set[str]] = {}
    for item in evidence:
        provider = str(item.get("provider") or "")
        if not provider:
            continue
        keys = genre_keys(item.get("genres"))
        provider_genres.setdefault(provider, set()).update(keys)
    sets = list(provider_genres.values())
    return len(sets) > 1 and any(left & right for index, left in enumerate(sets) for right in sets[index + 1 :])


def genre_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    for genre in supported_genre_names(value):
        normalised = normalise_genre(genre)
        if normalised:
            keys.add(normalised[0])
    return keys


def combined_evidence_genres(evidence: list[dict[str, Any]]) -> list[str]:
    votes: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    labels: dict[str, str] = {}
    for item in evidence:
        for genre in supported_genre_names(item.get("genres")):
            normalised = normalise_genre(genre)
            if not normalised:
                continue
            key = normalised[0]
            votes[key] += 1
            first_seen.setdefault(key, len(first_seen))
            labels.setdefault(key, genre)
    ordered = sorted(votes, key=lambda key: (-votes[key], first_seen[key]))[:8]
    return [labels[key] for key in ordered]


def supported_genre_names(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    genres: list[str] = []
    for genre in value:
        normalised = normalise_genre(str(genre))
        if normalised and normalised[1].casefold() not in genres:
            genres.append(normalised[1].casefold())
    return genres[:8]


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
        if not primary_genre_for_profile(profile_for_artist(artist, genres)):
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
    if item.get("genres") and primary_genre_for_profile(profile_for_artist(artist, item.get("genres") or [])):
        return
    item["genres"] = list(record.get("genres") or [])
    providers = sorted({str(evidence.get("provider")) for evidence in record.get("evidence") or [] if isinstance(evidence, dict) and evidence.get("provider")})
    item["genre_source"] = "durable_genre_metadata"
    item["genre_confidence"] = record.get("confidence") or "medium"
    item["genre_providers"] = providers or [record.get("provider")]
    item["genre_evidence"] = list(record.get("evidence") or [])
    if any(provider == "musicbrainz" for provider in item["genre_providers"]):
        item["musicbrainz_artist_id"] = next(
            (evidence.get("providerArtistId") for evidence in item["genre_evidence"] if evidence.get("provider") == "musicbrainz"),
            record.get("providerArtistId"),
        )
    item["genre_checked_at"] = record.get("checkedAt")


def clear_musicbrainz_genres(normalised: dict[str, Any]) -> None:
    metadata = normalised.get("artist_metadata")
    if not isinstance(metadata, dict):
        return
    for item in metadata.values():
        if not isinstance(item, dict) or item.get("genre_source") not in {"musicbrainz_artist_genres", "durable_genre_metadata"}:
            continue
        item["genres"] = []
        for key in ("genre_source", "genre_confidence", "genre_providers", "genre_evidence", "musicbrainz_artist_id", "genre_checked_at"):
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
