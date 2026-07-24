from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


LISTENING_EVENT_SCHEMA_VERSION = 1
PLAY_EVENT = "play_event"
ELIGIBLE_MUSIC_CLASSIFICATIONS = {"confirmed_music", "probable_music"}


def normalise_identity_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def event_identity(
    *,
    source: str,
    source_event_id: str | None,
    stable_track_id: str | None,
    title: str,
    artist: str,
    timestamp_utc: str | None,
    timestamp_status: str,
) -> tuple[str, str] | None:
    """Return the strongest safe identity and its stable event id input."""
    if source_event_id:
        return "source_event_id", f"{source}|event|{source_event_id}"
    if timestamp_status != "valid" or not timestamp_utc:
        return None
    if stable_track_id:
        return "track_timestamp", f"{source}|track|{stable_track_id}|{timestamp_utc}"
    title_key = normalise_identity_text(title)
    artist_key = normalise_identity_text(artist)
    if title_key:
        return "text_timestamp", f"{source}|text|{title_key}|{artist_key}|{timestamp_utc}"
    return None


def event_id_for(identity: str | None, import_batch_id: str | None, sequence: int) -> str:
    # Invalid timestamps intentionally have no cross-import identity. The batch and
    # source position preserve them without merging unrelated records.
    seed = identity or f"invalid|{import_batch_id or 'unknown'}|{sequence}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class ListeningEvent:
    event_id: str
    source: str
    evidence_type: str
    timestamp_utc: str | None
    raw_timestamp: str | None
    timestamp_status: str
    track_id: str | None
    video_id: str | None
    title: str
    artist: str
    artists: list[str]
    album: str | None
    duration_seconds: int | None
    duration_source: str | None
    music_classification: str
    import_batch_id: str | None
    parser_schema_version: int | None
    source_event_id: str | None = None
    event_schema_version: int = LISTENING_EVENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "id": self.event_id,
            "source": self.source,
            "evidence_type": self.evidence_type,
            "timestamp_utc": self.timestamp_utc,
            "played_at": self.timestamp_utc,
            "raw_timestamp": self.raw_timestamp,
            "played_date_raw": self.raw_timestamp,
            "timestamp_status": self.timestamp_status,
            "timestamp_invalid": self.timestamp_status in {"invalid", "missing"},
            "track_id": self.track_id,
            "video_id": self.video_id,
            "title": self.title,
            "primary_artist": self.artist,
            "artist": self.artist,
            "artists": self.artists,
            "album": self.album,
            "duration_seconds": self.duration_seconds,
            "duration_source": self.duration_source,
            "music_classification": self.music_classification,
            "import_batch_id": self.import_batch_id,
            "parser_schema_version": self.parser_schema_version,
            "event_schema_version": self.event_schema_version,
            "source_event_id": self.source_event_id,
        }
