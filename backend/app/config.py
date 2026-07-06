from __future__ import annotations

import os
from pathlib import Path


def load_private_env(private_dir: Path) -> None:
    env_path = private_dir / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class Settings:
    """Small settings object that keeps secrets out of source control."""

    def __init__(self) -> None:
        self.backend_dir = Path(__file__).resolve().parents[1]
        self.project_root = Path(__file__).resolve().parents[2]
        self.private_dir = Path(os.getenv("SMP_PRIVATE_DIR", self.backend_dir / "private"))
        load_private_env(self.private_dir)
        self.data_dir = Path(os.getenv("SMP_DATA_DIR", self.project_root / "data"))
        self.raw_dir = self.data_dir / "raw"
        self.db_path = Path(os.getenv("SMP_DB_PATH", self.data_dir / "saville_music_persona.db"))
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "gemma3:4b")
        auth_default = self.private_dir / "oauth.json"
        self.ytmusic_auth_file = Path(os.getenv("YTMUSIC_AUTH_FILE", auth_default))
        if not self.ytmusic_auth_file.is_absolute():
            self.ytmusic_auth_file = self.project_root / self.ytmusic_auth_file
        self.ytmusic_client_id = os.getenv("YTMUSIC_OAUTH_CLIENT_ID", "")
        self.ytmusic_client_secret = os.getenv("YTMUSIC_OAUTH_CLIENT_SECRET", "")
        self.cors_origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    def ensure_local_dirs(self) -> None:
        self.private_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
