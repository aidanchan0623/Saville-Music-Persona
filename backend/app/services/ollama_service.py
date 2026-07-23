
from __future__ import annotations

import json
import re
import socket
import time
from typing import Any

from pydantic import BaseModel, ValidationError

from app.config import Settings

REPORT_GENERATE_TIMEOUT_SECONDS = 240.0
OVERVIEW_GENERATE_TIMEOUT_SECONDS = 12.0


class PersonaReportLanguage(BaseModel):
    openingDescription: str
    personalityRoast: str
    musicalAgeExplanation: str
    finalRoastHeadline: str
    finalRoastBody: str
    finalLine: str
    generationSource: str = "fallback"
    fallbackReason: str | None = None
    durationMs: int | None = None


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

    def generate_overview_language(self, evidence: dict[str, Any]) -> dict[str, Any] | None:
        """Write bounded language from calculated facts without choosing any facts."""

        status = self.status()
        if not status["reachable"] or not status["model_installed"]:
            return None
        prompt = (
            "You write compact music-persona language from supplied calculated facts. "
            "The analytics already decided every number, rank, artist, song, date, period, genre and trait. "
            "Do not add or change any of them. Do not diagnose the listener or infer relationships, mental health, "
            "real-life events, physical age, or emotional maturity. Do not name any artist in this response.\n\n"
            "Return strict JSON with exactly this shape: "
            '{"identity":{"characterTitle":"","tagline":"","explanation":""},'
            '"musicalAge":{"summary":"","explanation":""}}.\n'
            "Identity characterTitle: 3-7 words, max 60 characters, starts with 'The', describes a listener character, "
            "and must not start with a genre after 'The'. Tagline max 140 characters. Identity explanation max 400 characters.\n"
            "Musical-age summary: one concise sentence. Musical-age explanation: 2-3 concise sentences, playful but grounded. "
            "Do not write digits or restate the age. Explain the supplied strongest factors without scientific certainty.\n\n"
            f"CALCULATED_FACTS_JSON:{json.dumps(evidence, ensure_ascii=True, separators=(',', ':'))}"
        )
        try:
            data = self._request_json(
                "POST",
                "/api/generate",
                {
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.2, "top_p": 0.82, "num_predict": 260},
                },
                timeout=min(float(self.settings.ollama_generate_timeout_seconds), OVERVIEW_GENERATE_TIMEOUT_SECONDS),
            )
            parsed = self.extract_json(str(data.get("response") or ""))
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def generate_persona_language(self, evidence: dict[str, Any], mode: str = "serious") -> PersonaReportLanguage:
        """Let Gemma write bounded prose while deterministic services retain every fact."""

        started = time.monotonic()
        status = self.status()
        if not status["reachable"]:
            return self.fallback_persona_language(evidence, "ollama_unavailable", started)
        if not status["model_installed"]:
            return self.fallback_persona_language(evidence, "model_not_installed", started)
        prompt = self._build_persona_language_prompt(evidence, mode)
        try:
            data = self._request_json(
                "POST",
                "/api/generate",
                {
                    "model": self.settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.15, "top_p": 0.8, "num_predict": 520},
                },
                timeout=min(float(self.settings.ollama_generate_timeout_seconds), REPORT_GENERATE_TIMEOUT_SECONDS),
            )
            parsed = self.parse_persona_language(str(data.get("response") or ""), evidence)
            parsed.durationMs = self._duration_ms(started)
            return parsed
        except TimeoutError:
            return self.fallback_persona_language(evidence, "ollama_timeout", started)
        except (ValueError, ValidationError):
            return self.fallback_persona_language(evidence, "invalid_language_json", started)
        except Exception:
            return self.fallback_persona_language(evidence, "ollama_error", started)

    def _build_persona_language_prompt(self, evidence: dict[str, Any], mode: str) -> str:
        return (
            "You write playful, respectful music-persona prose from calculated evidence. Analytics already chose every fact. "
            "Do not add or change artists, numbers, dates, ranks, genres, diagnoses, relationships, private-life claims, "
            "protected-trait insults, slurs, or scientific certainty. Do not include any digits. Only mention an artist if "
            "that exact artist appears in knownArtists. Return strict JSON with exactly one key named s, whose value is "
            "an array of exactly six strings in this order: openingDescription, personalityRoast, musicalAgeExplanation, "
            "finalRoastHeadline, finalRoastBody, finalLine. Do not use those names as keys. "
            "openingDescription is at most sixty words. personalityRoast is one short sentence. musicalAgeExplanation is "
            "two short sentences and does not restate the age. finalRoastHeadline is at most eighty characters. "
            "finalRoastBody is seventy to one hundred thirty words and interprets personality, intensity, repetition, "
            "discovery, reflective or cinematic taste, and favourite-artist patterns without listing metrics. finalLine is "
            "at most one hundred characters. Tone mode: "
            f"{mode}. CALCULATED_EVIDENCE_JSON:{json.dumps(evidence, ensure_ascii=True, separators=(',', ':'))}"
        )

    def parse_persona_language(self, raw: str, evidence: dict[str, Any]) -> PersonaReportLanguage:
        data = self.extract_json(raw)
        ordered = data.get("s") if isinstance(data.get("s"), list) and len(data["s"]) == 6 else None
        if ordered:
            data = dict(zip(
                ["openingDescription", "personalityRoast", "musicalAgeExplanation", "finalRoastHeadline", "finalRoastBody", "finalLine"],
                ordered,
                strict=True,
            ))
        fields = {
            key: self._clean_text(data.get(key), limit)
            for key, limit in {
                "openingDescription": 430,
                "personalityRoast": 260,
                "musicalAgeExplanation": 520,
                "finalRoastHeadline": 80,
                "finalRoastBody": 950,
                "finalLine": 100,
            }.items()
        }
        if not all(fields.values()):
            raise ValueError("missing report language field")
        if len(fields["openingDescription"].split()) > 60:
            raise ValueError("opening description is too long")
        body_words = len(fields["finalRoastBody"].split())
        if body_words < 70 or body_words > 130:
            raise ValueError("final roast length is outside the accepted range")
        if any(re.search(r"\d", value) for value in fields.values()):
            raise ValueError("generated language contains an invented numeric claim")
        known = [str(value).strip() for value in evidence.get("knownArtists", []) if str(value).strip()]
        for match in re.finditer(r"\b(?:by|artist|band)\s+([A-Z][\w'&.-]+(?:\s+[A-Z][\w'&.-]+){0,4})", " ".join(fields.values())):
            candidate = match.group(1).strip()
            if not any(candidate.casefold() == artist.casefold() for artist in known):
                raise ValueError("generated language contains an unknown artist")
        return PersonaReportLanguage(**fields, generationSource="gemma", fallbackReason=None)

    def fallback_persona_language(
        self,
        evidence: dict[str, Any],
        reason: str,
        started: float | None = None,
    ) -> PersonaReportLanguage:
        personality = evidence.get("personality") if isinstance(evidence.get("personality"), dict) else {}
        title = str(personality.get("title") or "your music character")
        signals = [str(value).lower() for value in evidence.get("strongestSignals", []) if value][:3]
        signal_line = ", ".join(signals) if signals else "repeat listening and a carefully guarded sonic atmosphere"
        return PersonaReportLanguage(
            openingDescription=f"{title} turns familiar songs into places worth revisiting. The clearest signals are {signal_line}.",
            personalityRoast="You do not replay songs; you renew their lease and let them rearrange the furniture.",
            musicalAgeExplanation="Familiar anchors and selective discovery share the same carefully kept rotation. Album depth and reflective listening give the estimate its shape without pretending it is a physical age.",
            finalRoastHeadline="Your soundtrack has permanent residents",
            finalRoastBody=(
                "Your music taste treats atmosphere like a basic utility and the repeat button like a trusted advisor. "
                "Intensity is welcome, but only when it arrives with melody, drama, and enough emotional architecture to hold up under another listen. "
                "Discovery gets invited in, shown around politely, and then asked whether it can match the standards set by the established favourites. "
                "There is a reflective, cinematic streak running through the whole profile, plus a suspicious talent for making an ordinary commute feel like the final scene of a film. "
                "You call it curation; your most-played songs call it a long-term tenancy agreement."
            ),
            finalLine="Keep the soundtrack dramatic and the evidence local.",
            generationSource="fallback",
            fallbackReason=reason,
            durationMs=self._duration_ms(started) if started is not None else None,
        )

    def _duration_ms(self, started: float) -> int:
        return max(0, int((time.monotonic() - started) * 1000))

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
                try:
                    chunk = conn.recv(65536)
                except socket.timeout as exc:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"Ollama did not finish within {timeout:.0f} seconds.") from exc
                    continue
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
        if host.lower() == "localhost":
            host = "127.0.0.1"
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

    def _clean_text(self, value: Any, max_chars: int = 220) -> str:
        if value is None:
            return ""
        text_value = re.sub(r"\\s+", " ", str(value)).strip()
        text_value = re.sub(r"^(?:#+\\s*|[-*]\\s+)", "", text_value)
        return text_value[:max_chars].strip()

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
