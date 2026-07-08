from __future__ import annotations

import json
import re
import socket
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.config import Settings


class PersonalityTag(BaseModel):
    tag: str
    reason: str


class ReportCard(BaseModel):
    title: str
    body: str


class PersonaReport(BaseModel):
    headline: str = ""
    subheadline: str = ""
    core_identity_paragraph: str = ""
    listener_type_cards: list[ReportCard] = Field(default_factory=list)
    taste_world_paragraph: str = ""
    music_movement_paragraph: str = ""
    current_vs_long_term_paragraph: str = ""
    friendly_roast: str = ""
    summary: str = ""
    current_era: str = ""
    core_identity: str = ""
    listening_habits: str = ""
    comfort_artists: str = ""
    personality_tags: list[PersonalityTag] = Field(default_factory=list)
    report_sections: list[str] = Field(default_factory=list)
    recommendation_explanations: list[dict[str, str]] = Field(default_factory=list)
    mode: str = "serious"
    model: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class OllamaService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> dict[str, Any]:
        try:
            data = self._request_json("GET", "/api/tags", timeout=2.0)
        except Exception as exc:  # noqa: BLE001 - friendly local diagnostic
            return {
                "reachable": False,
                "model_installed": False,
                "model": self.settings.ollama_model,
                "message": f"Ollama is not reachable at {self.settings.ollama_base_url}: {exc}",
            }
        models = data.get("models", [])
        names = {model.get("name") for model in models if isinstance(model, dict)}
        installed = self.settings.ollama_model in names
        return {
            "reachable": True,
            "model_installed": installed,
            "model": self.settings.ollama_model,
            "message": "Ollama is reachable." if installed else f"Ollama is reachable, but {self.settings.ollama_model} is not installed.",
        }

    def generate_report(self, profile: dict[str, Any], mode: str) -> PersonaReport:
        status = self.status()
        if not status["reachable"]:
            raise RuntimeError(status["message"])
        if not status["model_installed"]:
            raise RuntimeError(status["message"])
        prompt = self._build_report_prompt(profile, mode)
        data = self._request_json(
            "POST",
            "/api/generate",
            {
                "model": self.settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.45, "top_p": 0.9, "num_predict": 900},
            },
            timeout=self.settings.ollama_generate_timeout_seconds,
        )
        raw = data.get("response", "")
        report = self.parse_report(raw, profile)
        report.mode = mode
        report.model = self.settings.ollama_model
        report.evidence = profile
        return report

    def generate_recommendation_explanations(self, profile: dict[str, Any], recommendations: list[dict[str, Any]]) -> list[dict[str, str]]:
        status = self.status()
        if not status["reachable"] or not status["model_installed"]:
            return []
        compact = [
            {
                "track_title": item["track_title"],
                "artist": item["artist"],
                "recommendation_type": item["recommendation_type"],
                "musical_connection": item.get("musical_connection"),
                "source_reason": item["source_reason"],
                "score": item["score"],
            }
            for item in recommendations[:20]
        ]
        prompt = (
            "You explain YouTube Music recommendations as a careful music-taste analyst. Use only the supplied JSON. "
            "Return JSON with key recommendation_explanations as an array of objects containing "
            "track_title, artist, why_this_fits. Mention concrete musical connections from the supplied profile. Do not invent facts.\n\n"
            f"PROFILE:\n{json.dumps(profile, ensure_ascii=True)}\n\n"
            f"RECOMMENDATIONS:\n{json.dumps(compact, ensure_ascii=True)}"
        )
        try:
            response_data = self._request_json(
                "POST",
                "/api/generate",
                {
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.4, "num_predict": 700},
                },
                timeout=self.settings.ollama_generate_timeout_seconds,
            )
            raw = response_data.get("response", "")
            data = self.extract_json(raw)
            items = data.get("recommendation_explanations", [])
            if isinstance(items, list):
                return [
                    {
                        "track_title": str(item.get("track_title", "")),
                        "artist": str(item.get("artist", "")),
                        "why_this_fits": str(item.get("why_this_fits", "")),
                    }
                    for item in items
                    if isinstance(item, dict)
                ]
        except Exception:
            return []
        return []

    def generate_character_rewrite(self, profile: dict[str, Any], mode: str = "playful") -> dict[str, Any]:
        status = self.status()
        if not status["reachable"]:
            raise RuntimeError(status["message"])
        if not status["model_installed"]:
            raise RuntimeError(status["message"])
        primary = profile.get("primary") if isinstance(profile.get("primary"), dict) else {}
        secondary = profile.get("secondary") if isinstance(profile.get("secondary"), dict) else None
        modifier = profile.get("modifier") if isinstance(profile.get("modifier"), dict) else None
        compact = {
            "period": (profile.get("period") or {}).get("label") if isinstance(profile.get("period"), dict) else None,
            "mode": mode,
            "primary_character": primary,
            "secondary_character": secondary,
            "modifier": modifier,
            "evidence_chips": profile.get("evidence_chips", [])[:8],
            "top_artists": profile.get("top_artists", [])[:5],
            "top_clusters": profile.get("top_clusters", [])[:5],
            "sonic_traits": profile.get("sonic_traits", [])[:8],
            "key_scores": profile.get("key_scores", {}),
        }
        prompt = (
            "You are a witty but careful music-profile writer. You are not calculating the profile. "
            "The character and evidence have already been selected by deterministic rules. Your job is to turn the supplied profile into a more personal, natural, music-focused paragraph.\n\n"
            "Rules:\n"
            "- Use only the supplied evidence.\n"
            "- Do not invent artists, tracks, genres, listening habits, personal facts, or emotional states.\n"
            "- Do not repeat raw statistics unless they support the joke.\n"
            "- Keep the tone playful, specific and human.\n"
            "- Avoid generic lines like 'you enjoy a diverse range of music'.\n"
            "- Avoid therapy language or serious mental-health claims.\n"
            "- Keep roasts light and music-focused.\n"
            "- No slurs, protected-characteristic insults, sexual jokes, or cruel insults.\n"
            "- The output should sound like a funny friend who actually understands music.\n\n"
            'Return strict JSON: {"headline":"","one_liner":"","profile_paragraph":"","friendly_roast":"","why_it_fits":["","",""]}.\n\n'
            f"SUPPLIED_PROFILE_JSON:\n{json.dumps(compact, ensure_ascii=True)}"
        )
        data = self._request_json(
            "POST",
            "/api/generate",
            {
                "model": self.settings.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.65, "top_p": 0.9, "num_predict": 650},
            },
            timeout=self.settings.ollama_generate_timeout_seconds,
        )
        parsed = self.extract_json(str(data.get("response", "")))
        why = parsed.get("why_it_fits") if isinstance(parsed.get("why_it_fits"), list) else []
        return {
            "headline": str(parsed.get("headline") or primary.get("name") or "Music Character"),
            "one_liner": str(parsed.get("one_liner") or primary.get("roast") or ""),
            "profile_paragraph": str(parsed.get("profile_paragraph") or primary.get("profile") or ""),
            "friendly_roast": str(parsed.get("friendly_roast") or primary.get("roast") or ""),
            "why_it_fits": [str(item) for item in why[:3] if item],
            "mode": mode,
            "model": self.settings.ollama_model,
        }

    def _build_report_prompt(self, profile: dict[str, Any], mode: str) -> str:
        mode_instruction = {
            "serious": "Write it like a polished music identity editorial.",
            "playful": "Make it witty and specific, but still grounded in the supplied evidence.",
            "roast": "Roast gently and keep it music-focused only. No slurs, protected-characteristic insults, sexual jokes, mental-health claims, or harsh insults.",
        }.get(mode, "Write it like a polished music identity editorial.")
        compact = self._report_prompt_evidence(profile, mode)
        return (
            "You are a witty but careful music-profile writer. You are not calculating the profile. "
            "The character and evidence have already been selected by deterministic rules.\n\n"
            "Your job is to interpret the listener's music identity in a way that feels insightful, human, and music-aware.\n\n"
            "Rules:\n"
            "- Use only the supplied evidence.\n"
            "- Do not invent artists, tracks, genres, behaviours, emotional problems, or personal life facts.\n"
            "- Do not simply restate the raw metrics.\n"
            "- Translate data into interpretation.\n"
            "- Explain what kind of listener this person is.\n"
            "- Keep the tone playful, smart, and specific.\n"
            "- Avoid generic language like 'you have a diverse taste'.\n"
            "- Avoid therapy language or serious mental-health claims.\n"
            "- Keep roasts light and music-focused.\n"
            "- No cruel insults, slurs, sexual jokes, or protected-characteristic jokes.\n"
            "- The output should feel like a music identity editorial, not an analytics summary.\n"
            f"{mode_instruction}\n"
            "Return strict JSON matching this schema: "
            '{"headline":"","subheadline":"","core_identity_paragraph":"","listener_type_cards":[{"title":"","body":""}],'
            '"taste_world_paragraph":"","music_movement_paragraph":"","current_vs_long_term_paragraph":"","friendly_roast":""}.\n'
            "Use 3 listener_type_cards: Primary character, Secondary character, Behaviour modifier. "
            "Do not include raw percentages or play counts unless the evidence label already makes them meaningful.\n\n"
            f"SUPPLIED_PROFILE_JSON:\n{json.dumps(compact, ensure_ascii=True)}"
        )

    def _report_prompt_evidence(self, profile: dict[str, Any], mode: str) -> dict[str, Any]:
        character = profile.get("music_character") if isinstance(profile.get("music_character"), dict) else {}
        current = profile.get("current_month_character") if isinstance(profile.get("current_month_character"), dict) else {}
        taste = profile.get("taste_interpretation") if isinstance(profile.get("taste_interpretation"), dict) else {}
        top_artists = profile.get("top_artists") if isinstance(profile.get("top_artists"), list) else []
        top_tracks = profile.get("top_tracks") if isinstance(profile.get("top_tracks"), list) else []
        return {
            "mode": mode,
            "period": (character.get("period") or {}).get("label") if isinstance(character.get("period"), dict) else None,
            "primary_character": character.get("primary"),
            "secondary_character": character.get("secondary"),
            "modifier": character.get("modifier"),
            "current_month_character": current.get("primary"),
            "current_vs_long_term": profile.get("current_vs_long_term"),
            "top_artists": [
                {"artist": item.get("artist"), "role": item.get("artist_loyalty_label")}
                for item in top_artists[:5]
                if isinstance(item, dict) and item.get("artist")
            ],
            "top_tracks": [
                {"title": item.get("title"), "artist": item.get("artist")}
                for item in top_tracks[:5]
                if isinstance(item, dict) and item.get("title")
            ],
            "top_sound_clusters": [
                {"name": item.get("name")}
                for item in taste.get("core_genre_families", [])[:5]
                if isinstance(item, dict) and item.get("name")
            ],
            "sonic_traits": list(taste.get("sonic_traits", [])[:8]) if isinstance(taste.get("sonic_traits"), list) else [],
            "plain_language_scores": profile.get("plain_language_scores", {}),
            "listener_axis": profile.get("listener_axis", {}),
            "album_or_track_behavior": profile.get("album_or_track_behavior"),
            "important_instruction": "Use the deterministic characters as the anchor. Do not choose or rename the character.",
        }

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
        host, port, prefix = self._parse_http_base_url()
        request_path = f"{prefix}{path}"
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = [
            f"{method} {request_path} HTTP/1.1",
            f"Host: {host}:{port}",
            "Accept: application/json",
            "Connection: close",
        ]
        if body is not None:
            headers.extend(["Content-Type: application/json", f"Content-Length: {len(body)}"])
        raw_request = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + (body or b"")
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.settimeout(timeout)
            conn.sendall(raw_request)
            chunks: list[bytes] = []
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
        raw_response = b"".join(chunks)
        header_bytes, _, body_bytes = raw_response.partition(b"\r\n\r\n")
        header_lines = header_bytes.decode("iso-8859-1").split("\r\n")
        status_line = header_lines[0] if header_lines else ""
        parts = status_line.split(" ", 2)
        if len(parts) < 2 or not parts[1].isdigit():
            raise RuntimeError("Ollama returned an invalid HTTP response.")
        status_code = int(parts[1])
        response_headers = {}
        for line in header_lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                response_headers[key.lower()] = value.strip().lower()
        if response_headers.get("transfer-encoding") == "chunked":
            body_bytes = self._decode_chunked_body(body_bytes)
        text = body_bytes.decode("utf-8")
        if status_code >= 400:
            raise RuntimeError(f"Ollama returned HTTP {status_code}: {text}")
        data = json.loads(text)
        return data if isinstance(data, dict) else {}

    def _parse_http_base_url(self) -> tuple[str, int, str]:
        base = self.settings.ollama_base_url.rstrip("/")
        if not base.startswith("http://"):
            raise RuntimeError("Only http:// Ollama endpoints are supported by the local socket client.")
        remainder = base[len("http://") :]
        if "/" in remainder:
            host_port, prefix = remainder.split("/", 1)
            prefix = f"/{prefix}"
        else:
            host_port, prefix = remainder, ""
        if ":" in host_port:
            host, port_text = host_port.rsplit(":", 1)
            port = int(port_text)
        else:
            host, port = host_port, 80
        return host, port, prefix

    def _decode_chunked_body(self, body: bytes) -> bytes:
        decoded = bytearray()
        cursor = 0
        while cursor < len(body):
            line_end = body.find(b"\r\n", cursor)
            if line_end == -1:
                break
            size_text = body[cursor:line_end].split(b";", 1)[0]
            size = int(size_text, 16)
            cursor = line_end + 2
            if size == 0:
                break
            decoded.extend(body[cursor : cursor + size])
            cursor += size + 2
        return bytes(decoded)

    def parse_report(self, raw: str, evidence: dict[str, Any] | None = None) -> PersonaReport:
        data = self.extract_json(raw)
        fallback = self._fallback_report_data(evidence or {})
        try:
            report = PersonaReport(**data)
            return self._fill_report_gaps(report, fallback)
        except ValidationError:
            repaired = {
                "headline": str(data.get("headline") or fallback["headline"]),
                "summary": str(data.get("summary") or fallback["summary"]),
                "current_era": str(data.get("current_era") or fallback["current_era"]),
                "core_identity": str(data.get("core_identity") or fallback["core_identity"]),
                "listening_habits": str(data.get("listening_habits") or fallback["listening_habits"]),
                "comfort_artists": str(data.get("comfort_artists") or fallback["comfort_artists"]),
                "personality_tags": data.get("personality_tags") if isinstance(data.get("personality_tags"), list) else fallback["personality_tags"],
                "report_sections": data.get("report_sections") if isinstance(data.get("report_sections"), list) else fallback["report_sections"],
                "recommendation_explanations": data.get("recommendation_explanations") if isinstance(data.get("recommendation_explanations"), list) else [],
                "subheadline": str(data.get("subheadline") or fallback["subheadline"]),
                "core_identity_paragraph": str(data.get("core_identity_paragraph") or fallback["core_identity_paragraph"]),
                "listener_type_cards": data.get("listener_type_cards") if isinstance(data.get("listener_type_cards"), list) else fallback["listener_type_cards"],
                "taste_world_paragraph": str(data.get("taste_world_paragraph") or fallback["taste_world_paragraph"]),
                "music_movement_paragraph": str(data.get("music_movement_paragraph") or fallback["music_movement_paragraph"]),
                "current_vs_long_term_paragraph": str(data.get("current_vs_long_term_paragraph") or fallback["current_vs_long_term_paragraph"]),
                "friendly_roast": str(data.get("friendly_roast") or fallback["friendly_roast"]),
            }
            return self._fill_report_gaps(PersonaReport(**repaired), fallback)

    def _fill_report_gaps(self, report: PersonaReport, fallback: dict[str, Any]) -> PersonaReport:
        report.headline = report.headline or fallback["headline"]
        report.subheadline = report.subheadline or fallback["subheadline"]
        report.core_identity_paragraph = report.core_identity_paragraph or fallback["core_identity_paragraph"]
        report.taste_world_paragraph = report.taste_world_paragraph or fallback["taste_world_paragraph"]
        report.music_movement_paragraph = report.music_movement_paragraph or fallback["music_movement_paragraph"]
        report.current_vs_long_term_paragraph = report.current_vs_long_term_paragraph or fallback["current_vs_long_term_paragraph"]
        report.friendly_roast = report.friendly_roast or fallback["friendly_roast"]
        report.summary = report.summary or fallback["summary"]
        report.current_era = report.current_era or fallback["current_era"]
        report.core_identity = report.core_identity or fallback["core_identity"]
        report.listening_habits = report.listening_habits or fallback["listening_habits"]
        report.comfort_artists = report.comfort_artists or fallback["comfort_artists"]
        if not report.listener_type_cards:
            report.listener_type_cards = [ReportCard(**item) for item in fallback["listener_type_cards"]]
        if not report.personality_tags:
            report.personality_tags = [PersonalityTag(**item) for item in fallback["personality_tags"]]
        if not report.report_sections:
            report.report_sections = list(fallback["report_sections"])
        return report

    def _fallback_report_data(self, evidence: dict[str, Any]) -> dict[str, Any]:
        coverage = evidence.get("coverage") if isinstance(evidence.get("coverage"), dict) else {}
        taste = evidence.get("taste_interpretation") if isinstance(evidence.get("taste_interpretation"), dict) else {}
        top_artists = evidence.get("top_artists") if isinstance(evidence.get("top_artists"), list) else []
        top_tracks = evidence.get("top_tracks") if isinstance(evidence.get("top_tracks"), list) else []
        scores = evidence.get("scores") if isinstance(evidence.get("scores"), list) else []
        moods = evidence.get("mood_profile") if isinstance(evidence.get("mood_profile"), list) else []
        character = evidence.get("music_character") if isinstance(evidence.get("music_character"), dict) else {}
        current_character = evidence.get("current_month_character") if isinstance(evidence.get("current_month_character"), dict) else {}
        primary = character.get("primary") if isinstance(character.get("primary"), dict) else {}
        secondary = character.get("secondary") if isinstance(character.get("secondary"), dict) else {}
        modifier = character.get("modifier") if isinstance(character.get("modifier"), dict) else {}
        artist_names = [str(item.get("artist")) for item in top_artists[:3] if isinstance(item, dict) and item.get("artist")]
        track_names = [str(item.get("title")) for item in top_tracks[:3] if isinstance(item, dict) and item.get("title")]
        day_count = coverage.get("days_represented") or 0
        play_count = evidence.get("total_detected_plays") or coverage.get("history_items_returned") or coverage.get("dated_history_items") or 0
        earliest = coverage.get("earliest_detected_play") or "the earliest detected day"
        latest = coverage.get("latest_detected_play") or "the latest detected day"
        full_year = bool(coverage.get("full_365_day_analysis"))
        max_track_plays = max((int(item.get("play_count") or 0) for item in top_tracks if isinstance(item, dict)), default=0)
        confidence = self._score_by_name(scores, "Taste confidence")
        repeat = self._score_by_name(scores, "Repeat score")
        loyalty = self._score_by_name(scores, "Artist loyalty")
        discovery = self._score_by_name(scores, "Discovery score")
        nostalgia = self._score_by_name(scores, "Nostalgia score")
        mainstream = self._score_by_name(scores, "Mainstream-Niche Estimate")
        top_artist_text = self._join_names(artist_names) or "the available top artists"
        top_track_text = self._join_names(track_names) or "the available recent tracks"
        core_families = [str(item.get("name")) for item in taste.get("core_genre_families", []) if isinstance(item, dict) and item.get("name")]
        secondary_families = [str(item.get("name")) for item in taste.get("secondary_genre_families", []) if isinstance(item, dict) and item.get("name")]
        sonic_traits = [str(item) for item in taste.get("sonic_traits", [])[:6]]
        taste_summary = str(taste.get("summary") or "")
        confidence_label = confidence.get("label") or "partial"
        coverage_text = f"{play_count} detected plays from {earliest} to {latest}"
        if day_count:
            coverage_text = f"{coverage_text}, spanning {day_count} day(s)"
        top_song_context = "Songs that survive replay matter here." if max_track_plays > 1 else "The track-level signal is still forming, so the broader character carries more weight."
        window_context = (
            "This should be read as a full-year listening profile."
            if full_year
            else "This should be read as a current snapshot rather than a full-year identity."
        )
        headline = str(primary.get("name") or evidence.get("headline_persona") or "Saville Music Persona")
        subheadline = str(primary.get("roast") or "Your listening profile has a point of view, even when the model is offline.")
        primary_profile = str(primary.get("profile") or "")
        secondary_profile = str(secondary.get("profile") or "There is not a strong secondary character yet; the main identity carries most of the signal.")
        modifier_profile = str(modifier.get("profile") or "No separate behaviour modifier is strong enough to overtake the main character.")
        sound_centre = self._join_names(core_families[:3]) or "the strongest mapped sound families"
        side_colour = self._join_names(secondary_families[:2] or sonic_traits[:2]) or "smaller side colours"
        trait_text = self._join_names(sonic_traits[:4]) or "a few recurring sonic habits"
        listener_axis = evidence.get("listener_axis") if isinstance(evidence.get("listener_axis"), dict) else {}
        artist_axis = str(listener_axis.get("artist_or_sound_led") or "")
        album_axis = str(evidence.get("album_or_track_behavior") or "")
        core_identity_paragraph = (
            f"{primary_profile} You are not just collecting disconnected songs; the profile keeps returning to {sound_centre}, "
            f"with {side_colour} adding shape around the edges."
        )
        taste_world_paragraph = (
            f"The sound-world feels {trait_text}. {taste_summary or 'The profile reads as a coherent musical weather system rather than a loose pile of categories.'} "
            f"{artist_axis or 'The bigger anchor is the musical world, not just one isolated stat.'}"
        )
        music_movement_paragraph = self._movement_paragraph(repeat, loyalty, discovery, nostalgia, mainstream, album_axis, top_song_context)
        comparison = evidence.get("current_vs_long_term") if isinstance(evidence.get("current_vs_long_term"), dict) else {}
        long_name = headline
        current_primary = current_character.get("primary") if isinstance(current_character.get("primary"), dict) else {}
        current_name = str(current_primary.get("name") or "")
        if comparison.get("has_contrast") and current_name:
            current_vs_long_term = (
                f"Long-term you read as {long_name}, while this month leans toward {current_name}. "
                f"That looks more like a current phase changing the lighting than a full identity replacement."
            )
        elif current_name:
            current_vs_long_term = (
                f"The current month and rolling-year read are broadly aligned: {current_name} still sits close to the long-term identity. "
                "This is continuity, not a sudden costume change."
            )
        else:
            current_vs_long_term = f"{window_context} Choose a monthly view after more listening data lands for a sharper phase comparison."
        summary = core_identity_paragraph
        current_era = current_vs_long_term
        core_identity = taste_world_paragraph
        listening_habits = music_movement_paragraph
        comfort_artists = (
            f"{top_artist_text} matter because they point toward a repeatable sound-world, not just a leaderboard. "
            f"{top_track_text} give the track-level surface, but the character read comes from how those signals connect."
        )
        mood_tags = [str(item.get("tag")) for item in moods[:2] if isinstance(item, dict) and item.get("tag")]
        profile_label = "Full-year taste profile" if full_year else "Current listening snapshot"
        listener_type_cards = [
            {
                "title": f"Primary: {headline}",
                "body": f"{primary_profile or core_identity_paragraph} Why it fits: {self._join_names([str(item) for item in primary.get('evidence', [])[:2]]) or 'the strongest overall character signal.'}",
            },
            {
                "title": f"Secondary: {secondary.get('name') or 'Still forming'}",
                "body": secondary_profile,
            },
            {
                "title": f"Modifier: {modifier.get('name') or 'No strong modifier'}",
                "body": modifier_profile,
            },
        ]
        personality_tags = [
            {"tag": headline, "reason": primary_profile or "Deterministic character engine selected the main identity."},
            {"tag": modifier.get("name") or profile_label, "reason": modifier_profile},
            {"tag": "Sound-world read", "reason": f"The recurring sound colours include {self._join_names(sonic_traits[:3] or mood_tags) or 'mixed listening contexts'}."},
        ]
        return {
            "headline": headline,
            "subheadline": subheadline,
            "core_identity_paragraph": core_identity_paragraph,
            "listener_type_cards": listener_type_cards,
            "taste_world_paragraph": taste_world_paragraph,
            "music_movement_paragraph": music_movement_paragraph,
            "current_vs_long_term_paragraph": current_vs_long_term,
            "friendly_roast": subheadline,
            "summary": summary,
            "current_era": current_era,
            "core_identity": core_identity,
            "listening_habits": listening_habits,
            "comfort_artists": comfort_artists,
            "personality_tags": personality_tags,
            "report_sections": [core_identity_paragraph, taste_world_paragraph, music_movement_paragraph, current_vs_long_term],
        }

    def _movement_paragraph(
        self,
        repeat: dict[str, Any],
        loyalty: dict[str, Any],
        discovery: dict[str, Any],
        nostalgia: dict[str, Any],
        mainstream: dict[str, Any],
        album_axis: str,
        top_song_context: str,
    ) -> str:
        repeat_value = float(repeat.get("value") or 0)
        loyalty_value = float(loyalty.get("value") or 0)
        discovery_value = float(discovery.get("value") or 0)
        nostalgia_value = float(nostalgia.get("value") or 0)
        mainstream_value = float(mainstream.get("value") or 0)
        repeat_line = (
            "You do not treat songs as disposable; once something lands, it tends to stay in rotation."
            if repeat_value >= 55
            else "Replay is present, but the profile is not only built from looping the same few tracks."
        )
        discovery_line = (
            "Discovery looks selective rather than chaotic: new music enters when it fits the world you already respond to."
            if discovery_value < 55
            else "There is a real exploratory streak here, but it still seems to look for music with the right emotional shape."
        )
        loyalty_line = (
            "The profile is artist-led enough that certain names act like anchors."
            if loyalty_value >= 65
            else "The profile feels more sound-led than fandom-locked: the mood and texture matter more than one artist owning everything."
        )
        niche_line = (
            "It leans toward the less-obvious side of your library without becoming obscure for the sake of it."
            if mainstream_value >= 55
            else "It keeps one foot in accessible, immediate songs, which gives the heavier or moodier edges a pop-readable centre."
        )
        nostalgia_line = "There is also an era-memory pull in the profile." if nostalgia_value >= 50 else "Nostalgia is colour, not the whole engine."
        return f"{repeat_line} {discovery_line} {loyalty_line} {niche_line} {nostalgia_line} {album_axis or top_song_context}"

    def _score_by_name(self, scores: list[Any], name: str) -> dict[str, Any]:
        for score in scores:
            if isinstance(score, dict) and score.get("name") == name:
                return score
        return {}

    def _join_names(self, names: list[str]) -> str:
        clean = [name for name in names if name]
        if not clean:
            return ""
        if len(clean) == 1:
            return clean[0]
        return f"{', '.join(clean[:-1])}, and {clean[-1]}"

    def extract_json(self, raw: str) -> dict[str, Any]:
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return {}
            try:
                data = json.loads(match.group(0))
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
