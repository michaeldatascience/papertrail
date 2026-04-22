"""Configuration Loader (System level) for Papertrail."""

from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"       # Go three levels up then into config dir


class Settings(BaseSettings):
    # Application wide settings loaded from .env or other environment files (config/*.json)

    # Database
    ### Move this to config file with dev, staging and prod.
    database_url: str = "postgresql+asyncpg://papertrail:papertrail@localhost:5432/papertrail"

    # LLM
    openrouter_api_key: str = ""

    # Langfuse
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # App
    app_env: str = "dev"
    log_level: str = "INFO"
    blob_storage_path: str = "./data/blobs"
    playbooks_path: str = "./playbooks"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# cache setings to ensure loaidng just once
@lru_cache
def get_settings() -> Settings:
    return Settings()


def load_json_config(name: str) -> dict:
    # Load indivdiual json config
    
    path = CONFIG_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        # print or debug
        config = json.load(f)
        # print(f"Loaded config from {path}: {config}")
        return config
        