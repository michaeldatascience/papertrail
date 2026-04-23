"""Load project definitions for the V2 architecture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from papertrail.projects.models import ProjectDefinition


class ProjectLoadError(Exception):
    """Raised when a project folder or project.json cannot be read."""


class ProjectValidationError(Exception):
    """Raised when a project.json file fails schema validation."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class ProjectLoader:
    """Load project authoring files from disk."""

    def __init__(self, projects_root: Path | None = None) -> None:
        self._projects_root = projects_root or Path("./projects")

    def load(self, slug: str) -> ProjectDefinition:
        project_dir = self._projects_root / slug
        if not project_dir.is_dir():
            raise ProjectLoadError(f"Project directory '{slug}' not found at {project_dir}")

        project_file = project_dir / "project.json"
        if not project_file.is_file():
            raise ProjectLoadError(f"Project manifest not found: {project_file}")

        try:
            with project_file.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError as exc:
            raise ProjectLoadError(f"Invalid JSON in {project_file}: {exc}") from exc
        except OSError as exc:
            raise ProjectLoadError(f"Error reading {project_file}: {exc}") from exc

        try:
            project = ProjectDefinition.model_validate(raw)
        except ValidationError as exc:
            raise ProjectValidationError(
                f"Failed to validate project '{slug}': {exc}",
                errors=exc.errors(),
            ) from exc

        if project.slug != slug:
            raise ProjectValidationError(
                f"Project slug mismatch: folder '{slug}' contains project slug '{project.slug}'",
            )

        return project
