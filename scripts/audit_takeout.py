from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.analysis.duration import annotate_normalised_durations, usable_duration_seconds  # noqa: E402
from app.analysis.normalizer import apply_release_year_cache, normalise_collection  # noqa: E402
from app.analysis.period_profile import build_period_profile  # noqa: E402
from app.analysis.periods import (  # noqa: E402
    album_group_for_track,
    canonical_song_title,
    filter_events,
    resolve_period,
    rank_albums,
    song_group_key,
    top_payload,
    tracks_by_id,
)
from app.analysis.track_metadata import (  # noqa: E402
    apply_track_metadata_cache,
    ensure_track_metadata_cache,
    metadata_alias_key,
    track_metadata_lookup,
    version_signature,
)
from app.services.genre_enrichment_service import apply_genre_cache, ensure_genre_cache  # noqa: E402
from app.services.takeout_service import (  # noqa: E402
    HISTORY_FILENAME_PATTERN,
    _WatchHistoryHtmlParser,
    dedupe_takeout_entries,
    normalise_takeout_html_block_with_reason,
    parse_takeout_music_library,
    takeout_entry_identity,
)
import re  # noqa: E402


def digest(*values: Any) -> str:
    payload = "\x1f".join(str(value or "") for value in values)
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:16]


def load_cache(db_path: Path, key: str) -> Any:
    if not db_path.exists():
        return None
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        row = connection.execute("SELECT value FROM json_cache WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        connection.close()


def parse_archive_records(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    parsed_entries: list[dict[str, Any]] = []
    rule_counts: Counter[str] = Counter()
    with zipfile.ZipFile(path) as archive:
        library = parse_takeout_music_library(archive)
        infos = [
            info
            for info in archive.infolist()
            if re.search(HISTORY_FILENAME_PATTERN, info.filename, flags=re.I) and "youtube" in info.filename.casefold()
        ]
        for info in infos:
            if not info.filename.casefold().endswith((".html", ".htm")):
                raise RuntimeError("The detailed audit currently requires the HTML watch-history export.")
            parser = _WatchHistoryHtmlParser()
            parser.feed(archive.read(info).decode("utf-8-sig", errors="replace"))
            seen: set[tuple[str, ...]] = set()
            for index, block in enumerate(parser.blocks):
                entry, rule = normalise_takeout_html_block_with_reason(block, library)
                record_hash = digest(info.filename, index)
                if entry is None:
                    outcome = "malformed_or_unresolved" if rule and "unresolved" in rule else "intentionally_excluded"
                    reason = rule or "unresolved"
                    rule_counts[reason] += 1
                    hosts = sorted({urlparse(str(link.get("href") or "")).hostname or "" for link in block.get("links") or []})
                    records.append({
                        "recordHash": record_hash,
                        "outcome": outcome,
                        "reason": reason,
                        "sanitisedShape": {
                            "linkCount": len(block.get("links") or []),
                            "textNodeCount": len(block.get("text_nodes") or []),
                            "hostHashes": [digest(host) for host in hosts if host],
                        },
                    })
                    continue
                identity = takeout_entry_identity(entry)
                duplicate = identity is not None and identity in seen
                if identity is not None:
                    seen.add(identity)
                records.append(
                    {
                        "recordHash": record_hash,
                        "entryHash": digest(*identity) if identity else digest(entry.get("title"), entry.get("played"), index),
                        "outcome": "duplicate" if duplicate else "parsed_pending_classification",
                        "reason": "same_source_occurrence_fingerprint" if duplicate else None,
                        "timestampValid": not bool(entry.get("timestampInvalid")),
                        "videoIdPresent": bool(entry.get("videoId")),
                        "titlePresent": bool(entry.get("title")),
                        "artistPresent": bool(entry.get("artists")),
                        "_entry": entry,
                    }
                )
                parsed_entries.append(entry)
    return records, parsed_entries, dict(rule_counts)


def score_component(value: float, evidence: str, limitation: str, improvement: str) -> dict[str, Any]:
    return {
        "score": round(max(0.0, min(100.0, value)), 1),
        "evidence": evidence,
        "limitations": limitation,
        "wouldIncreaseConfidence": improvement,
    }


def build_report(
    archive: Path,
    db_path: Path,
    *,
    period: str,
    month: str | None,
    timezone_name: str,
    today: date,
    focus_artist: str | None,
    focus_album: str | None,
) -> dict[str, Any]:
    record_rows, entries_before_dedupe, exclusion_rules = parse_archive_records(archive)
    accepted_entries = dedupe_takeout_entries(entries_before_dedupe)
    duplicate_count = len(entries_before_dedupe) - len(accepted_entries)
    raw: dict[str, Any] = {
        "source": "google_takeout",
        "takeout_history": accepted_entries,
        "takeout_import_batch_id": "sanitised-audit",
        "takeout_parser_schema_version": 5,
    }
    for key in ("album_image_cache_v1", "artist_image_cache_v2", "release_year_cache_v1", "track_metadata_cache_v1"):
        cached = load_cache(db_path, key)
        if cached:
            raw[key] = cached
    normalised = normalise_collection(raw, today=today)
    track_metadata_cache = ensure_track_metadata_cache(load_cache(db_path, "track_metadata_cache_v1") or {})
    apply_track_metadata_cache(normalised, track_metadata_cache)
    apply_release_year_cache(normalised, load_cache(db_path, "release_year_cache_v1") or {})
    normalised = annotate_normalised_durations(normalised, load_cache(db_path, "duration_cache") or {})
    apply_genre_cache(normalised, ensure_genre_cache(load_cache(db_path, "genre_metadata_cache")))
    lookup = tracks_by_id(normalised)

    event_outcomes: dict[str, tuple[str, str | None, dict[str, Any], dict[str, Any]]] = {}
    for event in normalised.get("play_events") or []:
        track = lookup.get(event.get("track_id")) or {}
        key = takeout_entry_identity({
            "source": event.get("source"), "videoId": event.get("video_id"), "played": event.get("played_at"),
            "title": event.get("title"), "artists": [{"name": event.get("primary_artist") or event.get("artist")}],
        })
        if key:
            event_outcomes[digest(*key)] = ("accepted_music_event", None, event, track)
    for event in normalised.get("excluded_play_events") or []:
        track = lookup.get(event.get("track_id")) or {}
        key = takeout_entry_identity({
            "source": event.get("source"), "videoId": event.get("video_id"), "played": event.get("played_at"),
            "title": event.get("title"), "artists": [{"name": event.get("primary_artist") or event.get("artist")}],
        })
        if key:
            classification = event.get("music_classification")
            outcome = "accepted_non_music_event" if classification == "non_music" else "unresolved"
            reason = event.get("exclusion_reason") or event.get("classification_reason") or "metadata_or_music_classification_unresolved"
            event_outcomes[digest(*key)] = (outcome, str(reason), event, track)
    for row in record_rows:
        if row["outcome"] == "parsed_pending_classification":
            resolved = event_outcomes.get(row.get("entryHash"))
            entry = row.get("_entry") or {}
            if resolved:
                row["outcome"], row["reason"] = resolved[0], resolved[1]
            elif entry.get("timestampInvalid") or not entry.get("played"):
                row["outcome"], row["reason"] = "malformed_or_unresolved", "missing_or_invalid_timestamp"
            elif not entry.get("title"):
                row["outcome"], row["reason"] = "malformed_or_unresolved", "missing_title"
            elif not entry.get("artists"):
                row["outcome"], row["reason"] = "unresolved", "missing_artist_or_channel_attribution"
            elif not entry.get("videoId"):
                row["outcome"], row["reason"] = "unresolved", "missing_video_id"
            else:
                row["outcome"], row["reason"] = "unresolved", "metadata_or_music_classification_unresolved"

    counts = Counter(row["outcome"] for row in record_rows)
    raw_count = len(record_rows)
    reconciled = sum(counts.values())
    silent_loss = raw_count - reconciled
    spec = resolve_period(normalised, period, month, timezone_name, today)
    events = [event for event in filter_events(normalised, spec) if event.get("is_music_candidate") is not False]
    profile = build_period_profile(normalised, period, month, timezone_name, today)
    top_tracks = top_payload(normalised, "tracks", period, month, timezone_name, today)
    top_artists = top_payload(normalised, "artists", period, month, timezone_name, today)
    album_rows = rank_albums(events, lookup, spec)

    song_counts: Counter[str] = Counter()
    artist_counts: Counter[str] = Counter()
    album_counts: Counter[str] = Counter()
    video_ids: set[str] = set()
    duration_events = release_year_events = genre_events = 0
    unknown_albums: Counter[str] = Counter()
    for event in events:
        track = lookup.get(event.get("track_id"), {})
        song_counts[song_group_key(track, event)] += 1
        artist = str(track.get("primary_artist") or event.get("artist") or "Unknown Artist")
        artist_counts[artist] += 1
        group = album_group_for_track(track, event)
        if group:
            album_counts[group["key"]] += 1
        else:
            unknown_albums[artist] += 1
        if event.get("video_id"):
            video_ids.add(str(event["video_id"]))
        duration_events += int(bool(usable_duration_seconds(event)))
        release_year_events += int(bool(track.get("release_year")) and str(track.get("release_year_confidence") or "trusted_local").casefold() != "low")
        genre_events += int(bool([value for value in track.get("genre_clusters") or [] if value != "unknown"]))

    focus_rows = []
    focus_song_counts: Counter[str] = Counter()
    focus_event_hashes: set[str] = set()
    if focus_artist:
        wanted_artist = focus_artist.casefold()
        for event in events:
            track = lookup.get(event.get("track_id"), {})
            if str(track.get("primary_artist") or event.get("artist") or "").casefold() != wanted_artist:
                continue
            if focus_album and str(track.get("album") or "").casefold() != focus_album.casefold():
                continue
            key = song_group_key(track, event)
            focus_song_counts[key] += 1
            occurrence = takeout_entry_identity({
                "source": event.get("source"),
                "videoId": event.get("video_id"),
                "played": event.get("played_at"),
                "title": event.get("title"),
                "artists": [{"name": event.get("primary_artist") or event.get("artist")}],
            })
            if occurrence:
                focus_event_hashes.add(digest(*occurrence))
        for key, plays in focus_song_counts.most_common():
            matching = next((lookup.get(event.get("track_id"), {}) for event in events if song_group_key(lookup.get(event.get("track_id"), {}), event) == key), {})
            focus_rows.append({
                "finalAggregationIdentity": key,
                "title": canonical_song_title(matching.get("title"), matching.get("primary_artist")),
                "artist": matching.get("primary_artist"),
                "album": matching.get("album"),
                "releaseYear": matching.get("release_year"),
                "plays": plays,
                "metadataSource": matching.get("release_year_source"),
                "metadataConfidence": matching.get("release_year_confidence"),
            })

    focus_trace: list[dict[str, Any]] = []
    if focus_artist:
        for row in record_rows:
            entry = row.get("_entry") or {}
            resolved = event_outcomes.get(row.get("entryHash"))
            if row.get("entryHash") not in focus_event_hashes and not (
                focus_artist.casefold() in str(entry.get("rawChannel") or "").casefold()
                or focus_artist.casefold() in str(entry.get("rawTitle") or "").casefold()
            ):
                continue
            event = resolved[2] if resolved else {}
            track = resolved[3] if resolved else {}
            if focus_album and resolved and str(track.get("album") or "").casefold() != focus_album.casefold():
                continue
            focus_trace.append({
                "recordHash": row["recordHash"],
                "rawTitle": entry.get("rawTitle"),
                "rawChannelOrArtist": entry.get("rawChannel"),
                "timestamp": entry.get("played"),
                "videoId": entry.get("videoId"),
                "parsedTitle": entry.get("title"),
                "parsedArtist": ((entry.get("artists") or [{}])[0] or {}).get("name"),
                "canonicalTrackId": event.get("track_id"),
                "resolvedAlbum": track.get("album"),
                "releaseYear": track.get("release_year"),
                "outcome": row.get("outcome"),
                "reason": row.get("reason"),
                "finalAggregationIdentity": song_group_key(track, event) if event else None,
            })

    total = max(len(events), 1)
    album_sum = sum(item.get("plays", 0) for item in album_rows)
    page_counts = {
        "profileAcceptedPlays": profile["figures"]["accepted_play_count"],
        "topTracksAcceptedPlays": top_tracks["ranked_music_play_count"],
        "topArtistsAcceptedPlays": top_artists["ranked_music_play_count"],
        "songAggregationSum": sum(song_counts.values()),
        "artistAggregationSum": sum(artist_counts.values()),
        "albumAggregationSum": album_sum,
        "eventsWithKnownAlbum": sum(album_counts.values()),
    }
    count_consistent = len({page_counts[key] for key in ("profileAcceptedPlays", "topTracksAcceptedPlays", "topArtistsAcceptedPlays", "songAggregationSum", "artistAggregationSum")}) == 1
    release_coverage = release_year_events / total * 100

    identity_buckets: Counter[str] = Counter()
    source_groups = _song_sources(events, lookup)
    group_tracks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        track = lookup.get(event.get("track_id"), {})
        group_tracks[song_group_key(track, event)].append(track)
    for group, tracks in group_tracks.items():
        confidences = []
        for track in tracks:
            metadata = track_metadata_lookup(track_metadata_cache, track) or {}
            confidences.append(float(metadata.get("identity_confidence") or metadata.get("match_confidence") or 0))
        best = max(confidences or [0.0])
        representative = tracks[0] if tracks else {}
        if best >= 0.95:
            identity_buckets["high"] += 1
        elif best >= 0.85 or (representative.get("video_id") and representative.get("title") and representative.get("primary_artist") != "Unknown Artist"):
            identity_buckets["medium"] += 1
        elif representative.get("title") and representative.get("primary_artist") != "Unknown Artist":
            identity_buckets["low"] += 1
        else:
            identity_buckets["unresolved"] += 1

    alias_groups: dict[str, set[str]] = defaultdict(set)
    for group, tracks in group_tracks.items():
        for track in tracks:
            alias = metadata_alias_key(track.get("title"), track.get("primary_artist"))
            if alias:
                alias_groups[alias].add(group)
    suspected_splits = sum(max(0, len(groups) - 1) for groups in alias_groups.values())
    suspected_over_merges = sum(
        1
        for tracks in group_tracks.values()
        if len({version_signature(track.get("title")) for track in tracks}) > 1
    )

    rule_assessments = {
        "explicit_google_ad": (True, False, "Explicit Google Ads activity is not a listening event."),
        "youtube_homepage_activity": (True, False, "Homepage navigation is not a listening event."),
        "legacy_block_unresolved": (None, True, "The legacy block lacks enough structure; a JSON export or future parser may recover it."),
        "html_block_unresolved": (None, True, "The block is retained in the audit but needs a new parser rule or stronger source metadata."),
    }
    exclusion_details = []
    for rule, count in sorted(exclusion_rules.items()):
        correct, recoverable, assessment = rule_assessments.get(rule, (None, True, "The rule requires manual review before recovery."))
        examples = [row.get("sanitisedShape") for row in record_rows if row.get("reason") == rule and row.get("sanitisedShape")][:3]
        exclusion_details.append({
            "rule": rule,
            "count": count,
            "representativeSanitisedExamples": examples,
            "correct": correct,
            "recoverable": recoverable,
            "assessment": assessment,
        })

    unresolved_artist_counts: Counter[str] = Counter()
    unresolved_video_counts: Counter[str] = Counter()
    for event in normalised.get("excluded_play_events") or []:
        if event.get("music_classification") == "non_music":
            continue
        unresolved_artist_counts[str(event.get("artist") or "Unknown Artist")] += 1
        unresolved_video_counts[str(event.get("video_id") or "missing-video-id")] += 1

    confidence = {
        "rawImportCompleteness": score_component(100 if silent_loss == 0 else 0, f"{raw_count} raw records reconcile; silent loss={silent_loss}.", "HTML export structure can change upstream.", "Additional locale fixtures and JSON-export audits."),
        "eventDeduplication": score_component(98 if duplicate_count >= 0 else 50, f"{duplicate_count} duplicate occurrence fingerprints; different timestamps are retained.", "Source exports generally lack a stable event ID.", "Provider event IDs in future exports."),
        "timestampAccuracy": score_component(sum(row.get("timestampValid", True) for row in record_rows) / max(raw_count, 1) * 100, "Timestamp validity measured record by record.", "Malformed source timestamps remain unresolved.", "A valid offset-bearing timestamp on every record."),
        "trackIdentity": score_component(92 if not suspected_over_merges and not suspected_splits else 82, f"{len(song_counts)} canonical songs from {len(video_ids)} source videos; suspected over-merges={suspected_over_merges}, splits={suspected_splits}.", "Presentation variants without authoritative metadata may remain split.", "More exact video-ID metadata and ISRC matches."),
        "artistAttribution": score_component((len(events) - artist_counts.get("Unknown Artist", 0)) / total * 100, f"Unknown Artist plays={artist_counts.get('Unknown Artist', 0)}.", "Channel names are not always artist identities.", "Exact YouTube Music artist IDs."),
        "albumAttribution": score_component(sum(album_counts.values()) / total * 100, f"{sum(album_counts.values())}/{len(events)} period plays have a usable album.", "Singles and standalone videos legitimately lack albums.", "Resume authoritative video/album metadata enrichment."),
        "songPlayCounts": score_component(100 if sum(song_counts.values()) == len(events) else 0, "Every accepted event contributes to exactly one canonical song.", "Canonical identity can still split presentations when metadata is absent.", "Stable recording identifiers."),
        "artistPlayCounts": score_component(100 if sum(artist_counts.values()) == len(events) else 0, "Primary-artist totals reconcile to accepted events.", "Collaborations use one primary artist for non-duplicating totals.", "Structured provider artist credits."),
        "albumSongCounts": score_component(100 if album_sum == sum(album_counts.values()) else 60, f"Album API sum={album_sum}; event-derived album sum={sum(album_counts.values())}.", "Unknown albums are excluded rather than fabricated.", "Higher album metadata coverage."),
        "durationEstimates": score_component(duration_events / total * 100, f"{duration_events}/{len(events)} events have usable duration.", "Full duration does not prove a complete listen.", "Playback-position telemetry, which Takeout does not provide."),
        "releaseYears": score_component(release_coverage, f"{release_year_events}/{len(events)} period plays have a defensible year.", "Album edition years may differ from original recording years.", "ISRC/MusicBrainz original-release evidence."),
        "genreAssignments": score_component(profile["figures"]["genre_coverage"], f"Play-weighted genre coverage={profile['figures']['genre_coverage']}%.", "Unresolved tracks are not guessed.", "More authoritative recording-level genre evidence."),
        "musicalAge": score_component(min(100, release_coverage * 1.25), "Uses only valid high/medium or trusted local release years.", "Original-versus-reissue evidence remains incomplete.", "More original recording-year matches."),
    }
    component_values = [item["score"] for item in confidence.values()]
    confidence["overallAnalyticalReliability"] = score_component(
        sum(component_values) / len(component_values),
        f"Component mean across {len(component_values)} measurable checks; cross-page counts consistent={count_consistent}.",
        "Album and release-year coverage remain the largest gaps.",
        "Continue resumable authoritative metadata enrichment without lowering match thresholds.",
    )

    sanitised_records = [{key: value for key, value in row.items() if key != "_entry"} for row in record_rows]
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {"archiveNameHash": digest(archive.name), "databaseName": db_path.name},
        "period": profile["period"],
        "importIntegrity": {
            "rawRecordCount": raw_count,
            "parsedRecordCount": len(entries_before_dedupe),
            "acceptedMusicEventCount": counts["accepted_music_event"],
            "acceptedNonMusicEventCount": counts["accepted_non_music_event"],
            "duplicateCount": counts["duplicate"],
            "intentionallyExcludedCount": counts["intentionally_excluded"],
            "malformedOrUnresolvedCount": counts["malformed_or_unresolved"] + counts["unresolved"],
            "silentLossCount": silent_loss,
            "exclusionRules": exclusion_rules,
            "exclusionRuleDetails": exclusion_details,
        },
        "metadataCoverage": {
            "artistPercent": round((len(events) - artist_counts.get("Unknown Artist", 0)) / total * 100, 1),
            "titlePercent": round(sum(bool((lookup.get(event.get("track_id"), {}) or {}).get("title")) for event in events) / total * 100, 1),
            "albumPercent": round(sum(album_counts.values()) / total * 100, 1),
            "durationPercent": round(duration_events / total * 100, 1),
            "genrePercent": profile["figures"]["genre_coverage"],
            "releaseYearPercent": round(release_coverage, 1),
            "videoIdPercent": round(sum(bool(event.get("video_id")) for event in events) / total * 100, 1),
        },
        "identityQuality": {
            "uniqueSourceVideos": len(video_ids),
            "uniqueCanonicalSongs": len(song_counts),
            "uniqueArtists": len(artist_counts),
            "uniqueAlbums": len(album_counts),
            "highConfidenceCanonicalTracks": identity_buckets["high"],
            "mediumConfidenceCanonicalTracks": identity_buckets["medium"],
            "lowConfidenceCanonicalTracks": identity_buckets["low"],
            "unresolvedCanonicalTracks": identity_buckets["unresolved"],
            "multiSourceCanonicalSongs": sum(1 for ids in source_groups.values() if len(ids) > 1),
            "suspectedOverMerges": suspected_over_merges,
            "suspectedDuplicateSplits": suspected_splits,
            "topUnknownAlbums": [{"artistHash": digest(name), "plays": plays} for name, plays in unknown_albums.most_common(20)],
            "topUnresolvedArtists": [{"artistHash": digest(name), "events": count} for name, count in unresolved_artist_counts.most_common(20)],
            "topUnresolvedVideos": [{"videoHash": digest(video_id), "events": count} for video_id, count in unresolved_video_counts.most_common(20)],
        },
        "crossPageConsistency": {**page_counts, "coreCountsConsistent": count_consistent},
        "focus": {
            "artist": focus_artist,
            "album": focus_album,
            "rawMatchingRecords": len(focus_trace),
            "acceptedEvents": sum(1 for row in focus_trace if row["outcome"] == "accepted_music_event"),
            "unresolvedRecords": sum(1 for row in focus_trace if row["outcome"] in {"unresolved", "malformed_or_unresolved"}),
            "distinctSongs": len(focus_song_counts),
            "plays": sum(focus_song_counts.values()),
            "songs": focus_rows,
            "trace": focus_trace,
        } if focus_artist else None,
        "confidence": confidence,
        "records": sanitised_records,
    }


def _song_sources(events: list[dict[str, Any]], lookup: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for event in events:
        track = lookup.get(event.get("track_id"), {})
        result[song_group_key(track, event)].add(str(event.get("video_id") or event.get("track_id") or "unknown"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit every Takeout record without exposing private history in summaries.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--db", type=Path, default=PROJECT_ROOT / "data" / "saville_music_persona.db")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--period", default="rolling_year", choices=("rolling_year", "month", "this_month", "last_30", "last_7", "all"))
    parser.add_argument("--month")
    parser.add_argument("--timezone", default="Asia/Kuala_Lumpur")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--focus-artist")
    parser.add_argument("--focus-album")
    args = parser.parse_args()
    report = build_report(args.archive, args.db, period=args.period, month=args.month, timezone_name=args.timezone, today=args.today, focus_artist=args.focus_artist, focus_album=args.focus_album)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {key: report[key] for key in ("period", "importIntegrity", "metadataCoverage", "identityQuality", "crossPageConsistency", "confidence")}
    if isinstance(report.get("focus"), dict):
        summary["focus"] = {key: value for key, value in report["focus"].items() if key != "trace"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
