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
                "options": {"temperature": 0.45, "top_p": 0.9},
            },
            timeout=90.0,
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
                "source_reason": item["source_reason"],
                "score": item["score"],
            }
            for item in recommendations[:20]
        ]
        prompt = (
            "You explain YouTube Music recommendations. Use only the supplied JSON. "
            "Return JSON with key recommendation_explanations as an array of objects containing "
            "track_title, artist, why_this_fits. Do not invent facts.\n\n"
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
                    "options": {"temperature": 0.4},
                },
                timeout=90.0,
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
            "serious": "Write a polished, serious profile.",
            "playful": "Write a playful but still evidence-led profile.",
            "roast": "Roast gently. Keep it affectionate and non-hateful. No slurs, sexual content, protected-characteristic insults, or genuinely demeaning language.",
        }.get(mode, "Write a polished, serious profile.")
        return (
            "You write the Saville Music Persona report for a local private music dashboard.\n"
            "Use only the facts in the supplied JSON. Never invent artists, tracks, genres, dates, play counts, or personal life details. "
            "Do not claim causation. Where data confidence is low, explicitly state uncertainty. "
            "Write in clear English, polished but not overly dramatic.\n"
            f"{mode_instruction}\n"
            "Return strict JSON matching this schema: "
            '{"headline":"","summary":"","current_era":"","core_identity":"","listening_habits":"","comfort_artists":"","personality_tags":[{"tag":"","reason":""}],"report_sections":[],"recommendation_explanations":[]}.\n'
            "The report should contain 4-6 substantial paragraphs across the fields and 3 personality tags.\n\n"
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
        try:
            return PersonaReport(**data)
        except ValidationError:
            repaired = {
                "headline": str(data.get("headline") or (evidence or {}).get("headline_persona") or "Saville Music Persona"),
                "summary": str(data.get("summary") or "The local model returned a partial report, so this summary was repaired from available fields."),
                "current_era": str(data.get("current_era") or ""),
                "core_identity": str(data.get("core_identity") or ""),
                "listening_habits": str(data.get("listening_habits") or ""),
                "comfort_artists": str(data.get("comfort_artists") or ""),
                "personality_tags": data.get("personality_tags") if isinstance(data.get("personality_tags"), list) else [],
                "report_sections": data.get("report_sections") if isinstance(data.get("report_sections"), list) else [],
                "recommendation_explanations": data.get("recommendation_explanations") if isinstance(data.get("recommendation_explanations"), list) else [],
            }
            return PersonaReport(**repaired)

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
