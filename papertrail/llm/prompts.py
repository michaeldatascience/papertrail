"""Prompt template loader."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "prompts"


def load_prompt(template_name: str) -> str:
    """Load a prompt template by name from config/prompts/."""
    path = PROMPTS_DIR / template_name
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_name}")
    return path.read_text(encoding="utf-8")


def render_prompt(template_name: str, **kwargs) -> str:
    """Load and render a prompt template with variables."""
    template = load_prompt(template_name)
    return template.format(**kwargs)
