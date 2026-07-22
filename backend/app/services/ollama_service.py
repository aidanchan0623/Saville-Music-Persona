from __future__ import annotations

import json
import re
import socket
import time
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.config import Settings

REPORT_GENERATE_TIMEOUT_SECONDS = 35.0


class PersonalityTag(BaseModel):
    tag: str
    reason: str


class ReportCard(BaseModel):
    title: str
    body: str


class StoryChapter(BaseModel):
    headline: str = ""
    body: str = ""
    pullQuote: str = ""


class MainCharacterStory(BaseModel):
    artistName: str = ""
    role: str = ""
    line: str = ""


class PlotTwistStory(BaseModel):
    headline: str = ""
    body: str = ""


class ClosingStory(BaseModel):
    headline: str = ""
    body: str = ""
    finalLine: str = ""


class PersonaReport(BaseModel):
    personaReportSchemaVersion: int = 2
    personaName: str = ""
    openingHook: str = ""
    coreSound: StoryChapter = Field(default_factory=StoryChapter)
    comfortLoop: StoryChapter = Field(default_factory=StoryChapter)
    mainCharacters: list[MainCharacterStory] = Field(default_factory=list)
    plotTwist: PlotTwistStory = Field(default_factory=PlotTwistStory)
    closing: ClosingStory = Field(default_factory=ClosingStory)
    fallback: bool = False
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
        if not status["reachable"] or not status["model_installed"]:
            return self.fallback_report(profile, mode)
        prompt = self._build_report_prompt(profile, mode)
        try:
            data = self._request_json(
                "POST",
                "/api/generate",
                {
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.5, "top_p": 0.9, "num_predict": 620},
                },
                timeout=min(float(self.settings.ollama_generate_timeout_seconds), REPORT_GENERATE_TIMEOUT_SECONDS),
            )
            raw = data.get("response", "")
            report = self.parse_report(raw, profile)
            report.mode = mode
            report.model = self.settings.ollama_model
            report.evidence = profile
            return report
        except Exception:
            return self.fallback_report(profile, mode)

    def fallback_report(self, profile: dict[str, Any], mode: str = "serious") -> PersonaReport:
        report = PersonaReport(**self._fallback_report_data(profile))
        report.mode = mode
        report.model = ""
        report.evidence = profile
        report.fallback = True
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
            "You are a witty but careful music-profile writer creating a cinematic music-persona story. "
            "You are not calculating metrics. Deterministic analytics have already calculated every fact.\n\n"
            "Your job is to write short, specific interpretation for a six-chapter scrolling report.\n\n"
            "Rules:\n"
            "- Use only the supplied evidence.\n"
            "- Do not calculate or invent statistics.\n"
            "- Do not invent artist facts, track facts, genres, dates, behaviours, personal details, emotional problems, or life facts.\n"
            "- mainCharacters artistName values must exactly match one of allowed_main_character_artists.\n"
            "- Mention artist names only when they appear in the supplied JSON.\n"
            "- Avoid generic lines like 'you have a diverse taste'.\n"
            "- Avoid therapy language, diagnosis language, corporate phrasing, or robotic analysis language.\n"
            "- Keep roasts light, friendly, and music-focused.\n"
            "- Do not output Markdown, HTML, reasoning, notes, alternatives, or an introduction.\n"
            "- Do not start with phrases like 'Based on your data'.\n"
            "- Do not repeat the same genre list or metric list across chapters.\n"
            "- The style should be playful, observant, slightly dramatic, and readable immediately.\n"
            f"{mode_instruction}\n"
            "Return only strict JSON matching this schema:\n"
            "{\n"
            '  "personaReportSchemaVersion": 2,\n'
            '  "personaName": "string",\n'
            '  "openingHook": "string",\n'
            '  "coreSound": {"headline": "string", "body": "string", "pullQuote": "string"},\n'
            '  "comfortLoop": {"headline": "string", "body": "string", "pullQuote": "string"},\n'
            '  "mainCharacters": [{"artistName": "string", "role": "string", "line": "string"}],\n'
            '  "plotTwist": {"headline": "string", "body": "string"},\n'
            '  "closing": {"headline": "string", "body": "string", "finalLine": "string"}\n'
            "}\n"
            "Length limits: personaName max 8 words; openingHook max 20 words; chapter headline max 12 words; "
            "chapter body 25 to 55 words; pullQuote max 14 words; artist line max 20 words; "
            "closing body max 70 words; finalLine max 18 words. Return about three mainCharacters.\n\n"
            f"SUPPLIED_PROFILE_JSON:\n{json.dumps(compact, ensure_ascii=True)}"
        )

    def _report_prompt_evidence(self, profile: dict[str, Any], mode: str) -> dict[str, Any]:
        character = profile.get("music_character") if isinstance(profile.get("music_character"), dict) else {}
        current = profile.get("current_month_character") if isinstance(profile.get("current_month_character"), dict) else {}
        taste = profile.get("taste_interpretation") if isinstance(profile.get("taste_interpretation"), dict) else {}
        top_artists = profile.get("top_artists") if isinstance(profile.get("top_artists"), list) else []
        top_tracks = profile.get("top_tracks") if isinstance(profile.get("top_tracks"), list) else []
        top_albums = profile.get("favourite_albums") if isinstance(profile.get("favourite_albums"), list) else []
        scores = profile.get("scores") if isinstance(profile.get("scores"), list) else []
        cluster_candidates = taste.get("cluster_shares") if isinstance(taste.get("cluster_shares"), list) else []
        if not cluster_candidates:
            cluster_candidates = taste.get("core_genre_families") if isinstance(taste.get("core_genre_families"), list) else []
        return {
            "mode": mode,
            "period": (character.get("period") or {}).get("label") if isinstance(character.get("period"), dict) else None,
            "primary_character": character.get("primary"),
            "secondary_character": character.get("secondary"),
            "modifier": character.get("modifier"),
            "current_month_character": current.get("primary"),
            "current_vs_long_term": profile.get("current_vs_long_term"),
            "allowed_main_character_artists": [
                str(item.get("artist"))
                for item in top_artists[:6]
                if isinstance(item, dict) and item.get("artist")
            ],
            "top_artists": [
                {
                    "artist": item.get("artist"),
                    "role": item.get("artist_loyalty_label"),
                    "play_count": item.get("play_count"),
                    "share_of_listens": item.get("share_of_listens"),
                    "unique_songs_played": item.get("unique_songs_played"),
                    "taste_role": item.get("taste_role"),
                    "why_it_matters": item.get("why_it_matters"),
                }
                for item in top_artists[:5]
                if isinstance(item, dict) and item.get("artist")
            ],
            "top_tracks": [
                {"title": item.get("title"), "artist": item.get("artist"), "play_count": item.get("play_count")}
                for item in top_tracks[:5]
                if isinstance(item, dict) and item.get("title")
            ],
            "favourite_albums": [
                {
                    "album": item.get("album"),
                    "artist": item.get("artist"),
                    "plays": item.get("plays"),
                    "unique_songs": item.get("unique_songs"),
                    "share": item.get("share"),
                    "has_album_image": bool(item.get("album_image_url")),
                }
                for item in top_albums[:8]
                if isinstance(item, dict) and item.get("album")
            ],
            "scores": [
                {
                    "key": item.get("key"),
                    "name": item.get("name"),
                    "value": item.get("value"),
                    "label": item.get("label"),
                    "plain_english": (item.get("interpretation") or {}).get("plain_english") if isinstance(item.get("interpretation"), dict) else None,
                }
                for item in scores
                if isinstance(item, dict)
            ],
            "top_sound_clusters": [
                {"name": item.get("name"), "share": item.get("share")}
                for item in cluster_candidates[:5]
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
        deadline = time.monotonic() + timeout
        headers = [
            f"{method} {request_path} HTTP/1.1",
            f"Host: {host}:{port}",
            "Accept: application/json",
            "Connection: close",
        ]
        if body is not None:
            headers.extend(["Content-Type: application/json", f"Content-Length: {len(body)}"])
        raw_request = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii") + (body or b"")
        with socket.create_connection((host, port), timeout=min(timeout, 5.0)) as conn:
            conn.sendall(raw_request)
            chunks: list[bytes] = []
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Ollama did not finish within {timeout:.0f} seconds.")
                conn.settimeout(min(max(remaining, 0.1), 5.0))
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
        repaired = dict(fallback)
        for key in [
            "headline",
            "subheadline",
            "core_identity_paragraph",
            "taste_world_paragraph",
            "music_movement_paragraph",
            "current_vs_long_term_paragraph",
            "friendly_roast",
            "summary",
            "current_era",
            "core_identity",
            "listening_habits",
            "comfort_artists",
        ]:
            value = self._clean_text(data.get(key), 180)
            if value:
                repaired[key] = value
        if isinstance(data.get("listener_type_cards"), list):
            repaired["listener_type_cards"] = self._sanitize_report_cards(data.get("listener_type_cards"), fallback["listener_type_cards"])
        if isinstance(data.get("personality_tags"), list):
            repaired["personality_tags"] = self._sanitize_personality_tags(data.get("personality_tags"), fallback["personality_tags"])
        if isinstance(data.get("report_sections"), list):
            repaired["report_sections"] = [self._clean_text(item, 80) for item in data["report_sections"] if self._clean_text(item, 80)] or fallback["report_sections"]
        if isinstance(data.get("recommendation_explanations"), list):
            repaired["recommendation_explanations"] = [item for item in data["recommendation_explanations"] if isinstance(item, dict)]

        if self._has_v2_story_data(data):
            repaired["personaReportSchemaVersion"] = 2
            repaired["personaName"] = self._limit_words(self._clean_text(data.get("personaName"), 60), 8) or fallback["personaName"]
            repaired["openingHook"] = self._limit_words(self._clean_text(data.get("openingHook"), 90), 20) or fallback["openingHook"]
            repaired["coreSound"] = self._sanitize_story_chapter(data.get("coreSound"), fallback["coreSound"])
            repaired["comfortLoop"] = self._sanitize_story_chapter(data.get("comfortLoop"), fallback["comfortLoop"])
            repaired["mainCharacters"] = self._sanitize_main_characters(data.get("mainCharacters"), fallback["mainCharacters"], evidence or {})
            repaired["plotTwist"] = self._sanitize_plot_twist(data.get("plotTwist"), fallback["plotTwist"])
            repaired["closing"] = self._sanitize_closing(data.get("closing"), fallback["closing"])
            repaired["fallback"] = False

        repaired["evidence"] = evidence or {}
        try:
            return self._fill_report_gaps(PersonaReport(**repaired), fallback)
        except ValidationError:
            return self.fallback_report(evidence or {})

    def _fill_report_gaps(self, report: PersonaReport, fallback: dict[str, Any]) -> PersonaReport:
        report.personaReportSchemaVersion = 2
        report.personaName = self._limit_words(report.personaName or fallback["personaName"], 8)
        report.openingHook = self._limit_words(report.openingHook or fallback["openingHook"], 20)
        report.coreSound = StoryChapter(**self._sanitize_story_chapter(report.coreSound.model_dump(), fallback["coreSound"]))
        report.comfortLoop = StoryChapter(**self._sanitize_story_chapter(report.comfortLoop.model_dump(), fallback["comfortLoop"]))
        report.mainCharacters = [MainCharacterStory(**item) for item in self._sanitize_main_characters([item.model_dump() for item in report.mainCharacters], fallback["mainCharacters"], report.evidence)]
        report.plotTwist = PlotTwistStory(**self._sanitize_plot_twist(report.plotTwist.model_dump(), fallback["plotTwist"]))
        report.closing = ClosingStory(**self._sanitize_closing(report.closing.model_dump(), fallback["closing"]))
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

    def _has_v2_story_data(self, data: dict[str, Any]) -> bool:
        return data.get("personaReportSchemaVersion") == 2 or any(
            key in data
            for key in ("personaName", "openingHook", "coreSound", "comfortLoop", "mainCharacters", "plotTwist", "closing")
        )

    def _sanitize_story_chapter(self, value: Any, fallback: dict[str, Any]) -> dict[str, str]:
        source = value if isinstance(value, dict) else {}
        return {
            "headline": self._limit_words(self._clean_text(source.get("headline"), 90), 12) or str(fallback.get("headline") or ""),
            "body": self._limit_words(self._clean_text(source.get("body"), 380), 55) or str(fallback.get("body") or ""),
            "pullQuote": self._limit_words(self._clean_text(source.get("pullQuote"), 90), 14) or str(fallback.get("pullQuote") or ""),
        }

    def _sanitize_plot_twist(self, value: Any, fallback: dict[str, Any]) -> dict[str, str]:
        source = value if isinstance(value, dict) else {}
        return {
            "headline": self._limit_words(self._clean_text(source.get("headline"), 90), 12) or str(fallback.get("headline") or ""),
            "body": self._limit_words(self._clean_text(source.get("body"), 380), 55) or str(fallback.get("body") or ""),
        }

    def _sanitize_closing(self, value: Any, fallback: dict[str, Any]) -> dict[str, str]:
        source = value if isinstance(value, dict) else {}
        return {
            "headline": self._limit_words(self._clean_text(source.get("headline"), 90), 12) or str(fallback.get("headline") or ""),
            "body": self._limit_words(self._clean_text(source.get("body"), 460), 70) or str(fallback.get("body") or ""),
            "finalLine": self._limit_words(self._clean_text(source.get("finalLine"), 100), 18) or str(fallback.get("finalLine") or ""),
        }

    def _sanitize_main_characters(self, value: Any, fallback: list[dict[str, str]], evidence: dict[str, Any]) -> list[dict[str, str]]:
        allowed = self._artist_name_lookup(evidence)
        fallback_by_name = {self._normalise_name(item.get("artistName")): item for item in fallback if isinstance(item, dict)}
        source = value if isinstance(value, list) else []
        result: list[dict[str, str]] = []
        used: set[str] = set()
        for item in source:
            if not isinstance(item, dict):
                continue
            requested = self._normalise_name(item.get("artistName") or item.get("artist") or item.get("name"))
            artist_name = allowed.get(requested)
            if not artist_name:
                continue
            normalized_artist = self._normalise_name(artist_name)
            if normalized_artist in used:
                continue
            fallback_item = fallback_by_name.get(normalized_artist, {})
            result.append(
                {
                    "artistName": artist_name,
                    "role": self._limit_words(self._clean_text(item.get("role"), 80), 8) or str(fallback_item.get("role") or "The anchor"),
                    "line": self._limit_words(self._clean_text(item.get("line"), 120), 20) or str(fallback_item.get("line") or "A recurring name in the story."),
                }
            )
            used.add(normalized_artist)
            if len(result) >= 3:
                break
        for item in fallback:
            if len(result) >= 3:
                break
            if not isinstance(item, dict):
                continue
            normalized_artist = self._normalise_name(item.get("artistName"))
            if normalized_artist and normalized_artist not in used:
                result.append(
                    {
                        "artistName": str(item.get("artistName") or ""),
                        "role": str(item.get("role") or "The anchor"),
                        "line": str(item.get("line") or "A recurring name in the story."),
                    }
                )
                used.add(normalized_artist)
        return result[:3]

    def _sanitize_report_cards(self, value: list[Any], fallback: list[dict[str, str]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for item in value[:3]:
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title"), 90)
            body = self._clean_text(item.get("body"), 320)
            if title and body:
                result.append({"title": title, "body": body})
        return result or fallback

    def _sanitize_personality_tags(self, value: list[Any], fallback: list[dict[str, str]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for item in value[:4]:
            if not isinstance(item, dict):
                continue
            tag = self._clean_text(item.get("tag"), 50)
            reason = self._clean_text(item.get("reason"), 180)
            if tag and reason:
                result.append({"tag": tag, "reason": reason})
        return result or fallback

    def _artist_name_lookup(self, evidence: dict[str, Any]) -> dict[str, str]:
        top_artists = evidence.get("top_artists") if isinstance(evidence.get("top_artists"), list) else []
        lookup: dict[str, str] = {}
        for item in top_artists[:8]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("artist") or "").strip()
            normalized = self._normalise_name(name)
            if name and normalized:
                lookup[normalized] = name
        return lookup

    def _normalise_name(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip()).casefold()

    def _clean_text(self, value: Any, max_chars: int = 220) -> str:
        if not isinstance(value, str):
            return ""
        clean = re.sub(r"\s+", " ", value).strip()
        return clean[:max_chars].rstrip()

    def _limit_words(self, value: str, max_words: int) -> str:
        words = re.findall(r"\S+", value)
        if len(words) <= max_words:
            return value.strip()
        return " ".join(words[:max_words]).rstrip(" ,;:") + "."

    def _fallback_report_data(self, evidence: dict[str, Any]) -> dict[str, Any]:
        coverage = evidence.get("coverage") if isinstance(evidence.get("coverage"), dict) else {}
        taste = evidence.get("taste_interpretation") if isinstance(evidence.get("taste_interpretation"), dict) else {}
        top_artists = evidence.get("top_artists") if isinstance(evidence.get("top_artists"), list) else []
        top_tracks = evidence.get("top_tracks") if isinstance(evidence.get("top_tracks"), list) else []
        top_albums = evidence.get("favourite_albums") if isinstance(evidence.get("favourite_albums"), list) else []
        scores = evidence.get("scores") if isinstance(evidence.get("scores"), list) else []
        moods = evidence.get("mood_profile") if isinstance(evidence.get("mood_profile"), list) else []
        character = evidence.get("music_character") if isinstance(evidence.get("music_character"), dict) else {}
        current_character = evidence.get("current_month_character") if isinstance(evidence.get("current_month_character"), dict) else {}
        primary = character.get("primary") if isinstance(character.get("primary"), dict) else {}
        secondary = character.get("secondary") if isinstance(character.get("secondary"), dict) else {}
        modifier = character.get("modifier") if isinstance(character.get("modifier"), dict) else {}
        artist_names = [str(item.get("artist")) for item in top_artists[:3] if isinstance(item, dict) and item.get("artist")]
        track_names = [str(item.get("title")) for item in top_tracks[:3] if isinstance(item, dict) and item.get("title")]
        album_names = [str(item.get("album")) for item in top_albums[:3] if isinstance(item, dict) and item.get("album")]
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
        top_album = top_albums[0] if top_albums and isinstance(top_albums[0], dict) else {}
        top_album_text = str(top_album.get("album") or (album_names[0] if album_names else "the most revisited album"))
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
        main_characters = self._fallback_main_characters(top_artists)
        repeat_value = float(repeat.get("value") or 0)
        discovery_value = float(discovery.get("value") or 0)
        core_sound_body = (
            f"The centre of the report lives around {sound_centre}. "
            f"{trait_text.capitalize()} keep showing up as the texture, while {top_artist_text} give that world a recognizable cast."
        )
        comfort_body = (
            f"Repeat score {repeat_value:.0f} and discovery score {discovery_value:.0f} suggest a listener who "
            f"{'returns hard once a song earns trust' if repeat_value >= discovery_value else 'keeps one hand on novelty without losing the thread'}. "
            f"{top_album_text} is the clearest album-shaped signal in the current data."
        )
        plot_headline = "Consistency Is The Twist"
        plot_body = (
            f"The profile does not need a fake surprise: {sound_centre} remains the main character. "
            f"{side_colour.capitalize()} still add enough side-light to keep the report from feeling flat."
        )
        if comparison.get("has_contrast") and current_name:
            plot_headline = "This Month Changes The Lighting"
            plot_body = (
                f"Long-term you read as {long_name}, while this month leans toward {current_name}. "
                "That contrast is supported by the current period, so the story feels like a phase shift rather than a rewrite."
            )
        elif secondary_families:
            plot_headline = "The Side Quest Has Receipts"
            plot_body = (
                f"The main centre stays close to {sound_centre}, but {self._join_names(secondary_families[:2])} keep appearing as secondary colour. "
                "It is not random wandering; it is a smaller lane orbiting the same identity."
            )
        closing_body = (
            f"{headline} is a listener built around {sound_centre}, with {top_artist_text} acting as anchors and "
            f"{trait_text} shaping the atmosphere. The strongest read is not a leaderboard; it is a pattern of returns, side quests, and recognizable musical weather."
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
            "personaReportSchemaVersion": 2,
            "personaName": self._limit_words(headline, 8),
            "openingHook": self._limit_words(f"Your headphones keep choosing {sound_centre}, then adding just enough drama around the edges.", 20),
            "coreSound": {
                "headline": self._limit_words(f"{sound_centre} Holds The Centre", 12),
                "body": self._limit_words(core_sound_body, 55),
                "pullQuote": self._limit_words(trait_text.capitalize(), 14),
            },
            "comfortLoop": {
                "headline": "The Songs Earn Their Return",
                "body": self._limit_words(comfort_body, 55),
                "pullQuote": "Comfort, but with standards.",
            },
            "mainCharacters": main_characters,
            "plotTwist": {
                "headline": self._limit_words(plot_headline, 12),
                "body": self._limit_words(plot_body, 55),
            },
            "closing": {
                "headline": self._limit_words(f"{headline}, In The Credits", 12),
                "body": self._limit_words(closing_body, 70),
                "finalLine": "Roll the next song with intent.",
            },
            "fallback": True,
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

    def _fallback_main_characters(self, top_artists: list[Any]) -> list[dict[str, str]]:
        roles = ["The emotional anchor", "The recurring atmosphere", "The reliable wildcard"]
        result: list[dict[str, str]] = []
        for index, item in enumerate(top_artists[:3]):
            if not isinstance(item, dict) or not item.get("artist"):
                continue
            artist = str(item.get("artist"))
            play_count = int(item.get("play_count") or 0)
            unique_songs = int(item.get("unique_songs_played") or 0)
            role = roles[index] if index < len(roles) else "The anchor"
            metric_text = (
                f"{play_count} detected plays across {unique_songs} songs."
                if play_count and unique_songs
                else "A recurring name in the listening pattern."
            )
            result.append({"artistName": artist, "role": role, "line": self._limit_words(metric_text, 20)})
        return result

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
        raw = str(raw or "").strip()
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
        if fence:
            raw = fence.group(1).strip()
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            for match in re.finditer(r"\{", raw):
                try:
                    data, _ = decoder.raw_decode(raw[match.start() :])
                    return data if isinstance(data, dict) else {}
                except json.JSONDecodeError:
                    continue
            return {}
