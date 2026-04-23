# Config loader. Loads settings from env, and JSON configs from disk.
# Default values can be set in the dataclass (overriden by .env etc)


from __future__ import annotations
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


@dataclass(slots=True)
class Settings:
    """Application-wide settings loaded from environment or .env."""

    database_url: str = "postgresql+asyncpg://papertrail:papertrail@localhost:5432/papertrail"
    openrouter_api_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    app_env: str = "dev"
    log_level: str = "INFO"
    blob_storage_path: str = "./data/blobs"
    projects_path: str = "./projects"
    playbooks_path: str = "./playbooks"

    @classmethod
    def from_env(cls) -> "Settings":
        values = _load_env_file(ENV_FILE)
        values.update(os.environ)
        defaults = cls()
        return cls(
            database_url=values.get("DATABASE_URL", defaults.database_url),
            openrouter_api_key=values.get("OPENROUTER_API_KEY", defaults.openrouter_api_key),
            langfuse_secret_key=values.get("LANGFUSE_SECRET_KEY", defaults.langfuse_secret_key),
            langfuse_public_key=values.get("LANGFUSE_PUBLIC_KEY", defaults.langfuse_public_key),
            langfuse_host=values.get("LANGFUSE_HOST", defaults.langfuse_host),
            app_env=values.get("APP_ENV", defaults.app_env),
            log_level=values.get("LOG_LEVEL", defaults.log_level),
            blob_storage_path=values.get("BLOB_STORAGE_PATH", defaults.blob_storage_path),
            projects_path=values.get("PROJECTS_PATH", defaults.projects_path),
            playbooks_path=values.get("PLAYBOOKS_PATH", defaults.playbooks_path),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def load_json_config(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
