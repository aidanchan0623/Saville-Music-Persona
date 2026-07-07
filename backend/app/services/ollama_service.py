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


class PersonaReport(BaseModel):
    headline: str
    summary: str
    current_era: str
    core_identity: str
    listening_habits: str
    comfort_artists: str
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

    def _build_report_prompt(self, profile: dict[str, Any], mode: str) -> str:
        mode_instruction = {
            "serious": "Write a polished, serious music-taste profile.",
            "playful": "Make it witty and specific, but not random or insulting.",
            "roast": "Roast gently and keep it music-focused only. No slurs, protected-characteristic insults, sexuality jokes, mental-health claims, or harsh insults.",
        }.get(mode, "Write a polished, serious profile.")
        return (
            "You are a careful music critic analysing a listener's profile. Use only the supplied evidence and genre mapping. "
            "Do not invent artists, tracks, genres, personal facts, emotional problems, or listening history. "
            "Your job is to explain the listener's musical identity in concrete genre language.\n"
            "You must identify core genre families; explain how the artists combine into a coherent taste; distinguish core taste from side interests; "
            "describe sonic traits such as guitar-driven, atmospheric, melodic, heavy, cinematic, nostalgic, energetic, introspective, or experimental only when supported by evidence; "
            "state uncertainty when genre coverage is incomplete; avoid generic phrases like 'you enjoy a mix of genres'; "
            "avoid repeating raw play counts unless useful as evidence; never call a genre tag factual if it is low-confidence.\n"
            f"{mode_instruction}\n"
            "Return strict JSON matching this schema: "
            '{"headline":"","summary":"","current_era":"","core_identity":"","listening_habits":"","comfort_artists":"","personality_tags":[{"tag":"","reason":""}],"report_sections":[],"recommendation_explanations":[]}.\n'
            "The report should contain 3-5 concise paragraphs across the fields and 3 personality tags.\n\n"
            f"FACTUAL_PROFILE_JSON:\n{json.dumps(profile, ensure_ascii=True)}"
        )

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
            }
            return self._fill_report_gaps(PersonaReport(**repaired), fallback)

    def _fill_report_gaps(self, report: PersonaReport, fallback: dict[str, Any]) -> PersonaReport:
        report.headline = report.headline or fallback["headline"]
        report.summary = report.summary or fallback["summary"]
        report.current_era = report.current_era or fallback["current_era"]
        report.core_identity = report.core_identity or fallback["core_identity"]
        report.listening_habits = report.listening_habits or fallback["listening_habits"]
        report.comfort_artists = report.comfort_artists or fallback["comfort_artists"]
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
        top_artist_text = self._join_names(artist_names) or "the available top artists"
        top_track_text = self._join_names(track_names) or "the available recent tracks"
        core_families = [str(item.get("name")) for item in taste.get("core_genre_families", []) if isinstance(item, dict) and item.get("name")]
        secondary_families = [str(item.get("name")) for item in taste.get("secondary_genre_families", []) if isinstance(item, dict) and item.get("name")]
        sonic_traits = [str(item) for item in taste.get("sonic_traits", [])[:6]]
        taste_summary = str(taste.get("summary") or "")
        confidence_label = confidence.get("label") or "partial"
        repeat_label = repeat.get("label") or "unknown"
        loyalty_label = loyalty.get("label") or "unknown"
        coverage_text = f"{play_count} detected plays from {earliest} to {latest}"
        if day_count:
            coverage_text = f"{coverage_text}, spanning {day_count} day(s)"
        top_song_context = (
            "The top-song list now has repeat-count evidence, so it can be read as a real ranking."
            if max_track_plays > 1
            else "The top-song list is treated cautiously when every detected song has only one play."
        )
        window_context = (
            "This should be read as a full-year listening profile."
            if full_year
            else "This should be read as a current snapshot rather than a full-year identity."
        )
        summary = taste_summary or (
            f"This is a {confidence_label} profile based on {coverage_text}. "
            f"The clearest artist signals are {top_artist_text}. {top_song_context}"
        )
        current_era = (
            f"Right now the listening window points toward {top_artist_text}. {window_context}"
        )
        if core_families:
            current_era = f"Core taste: {self._join_names(core_families[:3])}. {window_context}"
        core_identity = (
            f"The profile reads as {evidence.get('headline_persona') or 'a private, pattern-seeking listener'}: "
            f"{self._join_names(core_families[:3]) or 'the strongest mapped genres'} form the centre, with "
            f"{self._join_names(secondary_families[:2]) or 'smaller side influences'} shaping the edges."
        )
        listening_habits = (
            f"The recent track surface includes {top_track_text}. {top_song_context}"
        )
        if sonic_traits:
            listening_habits += f" The mapped sonic traits are {self._join_names(sonic_traits[:5])}."
        comfort_artists = (
            f"{artist_names[0] if artist_names else 'The top artist'} is the strongest repeat-presence signal in the available data, "
            f"with {top_artist_text} shaping the current comfort zone."
        )
        mood_tags = [str(item.get("tag")) for item in moods[:2] if isinstance(item, dict) and item.get("tag")]
        profile_label = "Full-year taste profile" if full_year else "Current listening snapshot"
        personality_tags = [
            {"tag": profile_label, "reason": f"The report is based on {day_count or 'limited'} day(s) of detected history."},
            {"tag": "Artist-led listener", "reason": f"The strongest evidence comes from artist concentration around {top_artist_text}."},
            {"tag": "Sonic-trait profile", "reason": f"Mapped traits include {self._join_names(sonic_traits[:3] or mood_tags) or 'mixed listening contexts'}."},
        ]
        return {
            "headline": str(evidence.get("headline_persona") or "Saville Music Persona"),
            "summary": summary,
            "current_era": current_era,
            "core_identity": core_identity,
            "listening_habits": listening_habits,
            "comfort_artists": comfort_artists,
            "personality_tags": personality_tags,
            "report_sections": [summary, current_era, core_identity, listening_habits, comfort_artists],
        }

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
