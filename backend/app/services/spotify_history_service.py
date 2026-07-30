from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SPOTIFY_HISTORY_PARSER_SCHEMA_VERSION = 1
MAX_ARCHIVE_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024


class SpotifyHistoryParseError(ValueError):
    pass


@dataclass(frozen=True)
class SpotifyHistoryParseResult:
    entries: list[dict[str, Any]]
    raw_event_count: int
    diagnostics: dict[str, int]


def parse_spotify_history_file(
    path: Path,
    *,
    on_event: Callable[[str, dict[str, Any]], None] | None = None,
    check_timeout: Callable[[], None] | None = None,
) -> SpotifyHistoryParseResult:
    suffix = path.suffix.casefold()
    if suffix == ".zip":
        records = _records_from_zip(path, on_event=on_event, check_timeout=check_timeout)
    elif suffix == ".json":
        records = _records_from_json_bytes(path.read_bytes(), path.name)
    else:
        raise SpotifyHistoryParseError("Upload a Spotify streaming-history ZIP or JSON file.")

    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    diagnostics = {
        "raw_events": 0,
        "accepted_events": 0,
        "duplicates": 0,
        "non_music_events": 0,
        "zero_playback_events": 0,
        "invalid_events": 0,
        "missing_track_ids": 0,
    }
    for record in records:
        if check_timeout:
            check_timeout()
        diagnostics["raw_events"] += 1
        parsed, reason = _adapt_record(record)
        if parsed is None:
            diagnostics[reason] = diagnostics.get(reason, 0) + 1
            continue
        source_event_id = str(parsed["sourceEventId"])
        if source_event_id in seen:
            diagnostics["duplicates"] += 1
            continue
        seen.add(source_event_id)
        if not parsed.get("spotifyTrackUri"):
            diagnostics["missing_track_ids"] += 1
        entries.append(parsed)
    diagnostics["accepted_events"] = len(entries)
    if on_event:
        on_event("spotify_history_parsed", dict(diagnostics))
    return SpotifyHistoryParseResult(entries=entries, raw_event_count=diagnostics["raw_events"], diagnostics=diagnostics)


def _records_from_zip(
    path: Path,
    *,
    on_event: Callable[[str, dict[str, Any]], None] | None,
    check_timeout: Callable[[], None] | None,
) -> list[dict[str, Any]]:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise SpotifyHistoryParseError("The Spotify ZIP could not be opened.") from exc
    with archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        if len(entries) > MAX_ARCHIVE_ENTRIES:
            raise SpotifyHistoryParseError("The Spotify ZIP contains too many files.")
        if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
            raise SpotifyHistoryParseError("The expanded Spotify ZIP is too large to process safely.")
        json_entries = [entry for entry in entries if entry.filename.casefold().endswith(".json")]
        if not json_entries:
            raise SpotifyHistoryParseError("No JSON files were found in the Spotify ZIP.")
        records: list[dict[str, Any]] = []
        matched_files = 0
        for entry in json_entries:
            if check_timeout:
                check_timeout()
            if entry.flag_bits & 0x1:
                raise SpotifyHistoryParseError("Password-protected Spotify ZIP files are not supported.")
            try:
                payload = archive.read(entry)
                parsed = _records_from_json_bytes(payload, entry.filename, allow_unrelated=True)
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise SpotifyHistoryParseError(f"Could not read {Path(entry.filename).name} from the Spotify ZIP.") from exc
            if parsed:
                matched_files += 1
                records.extend(parsed)
        if not matched_files:
            raise SpotifyHistoryParseError("No Spotify audio streaming-history records were found in the ZIP.")
        if on_event:
            on_event("spotify_history_files_found", {"jsonFileCount": matched_files, "recordCount": len(records)})
        return records


def _records_from_json_bytes(payload: bytes, name: str, *, allow_unrelated: bool = False) -> list[dict[str, Any]]:
    try:
        value = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        if allow_unrelated:
            return []
        raise SpotifyHistoryParseError(f"{Path(name).name} is not valid Spotify JSON.") from exc
    if isinstance(value, dict):
        for key in ("items", "history", "streaming_history"):
            if isinstance(value.get(key), list):
                value = value[key]
                break
    if not isinstance(value, list):
        if allow_unrelated:
            return []
        raise SpotifyHistoryParseError("Spotify streaming-history JSON must contain a list of listening records.")
    records = [item for item in value if isinstance(item, dict)]
    if allow_unrelated and records and not any(_looks_like_history_record(item) for item in records[:20]):
        return []
    return records


def _looks_like_history_record(record: dict[str, Any]) -> bool:
    keys = set(record)
    return bool(keys & {"master_metadata_track_name", "trackName"}) and bool(keys & {"ts", "endTime"})


def _adapt_record(record: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    title = _text(record.get("master_metadata_track_name") or record.get("trackName"))
    artist = _text(record.get("master_metadata_album_artist_name") or record.get("artistName"))
    episode = _text(record.get("episode_name") or record.get("episodeName") or record.get("audiobook_title"))
    if episode and not title:
        return None, "non_music_events"
    if not title or not artist:
        return None, "invalid_events"
    timestamp = _normalise_timestamp(record.get("ts") or record.get("endTime"))
    if not timestamp:
        return None, "invalid_events"
    milliseconds = _int(record.get("ms_played") if "ms_played" in record else record.get("msPlayed"))
    if milliseconds <= 0:
        return None, "zero_playback_events"
    album = _text(record.get("master_metadata_album_album_name") or record.get("albumName"))
    uri = _spotify_track_uri(record.get("spotify_track_uri") or record.get("spotifyTrackUri"))
    identity = uri or f"text:{_identity_text(title)}:{_identity_text(artist)}"
    # Exact Spotify URIs plus timestamps align with the recent-play API and
    # safely deduplicate the same event across OAuth and an export. Legacy
    # rows only have minute-level timestamps, so retain milliseconds played to
    # avoid collapsing two genuine plays inside the same minute.
    event_identity = f"{identity}|{timestamp}" if uri else f"{identity}|{timestamp}|{milliseconds}"
    source_event_id = hashlib.sha256(event_identity.encode("utf-8")).hexdigest()[:24]
    source_track_id = uri or f"spotify:track:local:{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:24]}"
    return (
        {
            "source": "spotify",
            "event_source": "spotify_play",
            "sourceEventId": source_event_id,
            "source_track_id": source_track_id,
            "spotifyTrackUri": uri,
            "title": title,
            "artists": [{"name": artist, "id": None, "genres": []}],
            "album": {"name": album, "id": None, "year": None},
            "played": timestamp,
            "rawTimestamp": str(record.get("ts") or record.get("endTime") or ""),
            "playback_seconds": max(1, round(milliseconds / 1000)),
            "ms_played": milliseconds,
            "source_types": ["spotify_history_import"],
            "spotify_signal_label": "Spotify exported play",
            "parserSchemaVersion": SPOTIFY_HISTORY_PARSER_SCHEMA_VERSION,
        },
        "accepted_events",
    )


def _normalise_timestamp(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    candidates = [text, text.replace("Z", "+00:00")]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    for pattern in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            parsed = datetime.strptime(text, pattern).replace(tzinfo=timezone.utc)
            return parsed.isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    return None


def _spotify_track_uri(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.fullmatch(r"spotify:track:([A-Za-z0-9]+)", text)
    return f"spotify:track:{match.group(1)}" if match else None


def _identity_text(value: Any) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", str(value or "").casefold(), flags=re.UNICODE).split())


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
