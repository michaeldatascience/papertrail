"""Load V2 playbook authoring files from the projects tree."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from papertrail.playbooks.v2_models import (
    PlaybookBusinessCondition,
    PlaybookBusinessTransformation,
    PlaybookDefinition,
    PlaybookMeta,
    PlaybookPostprocess,
    PlaybookSchemaField,
    PlaybookValidationRule,
    PreuploadCheckSpec,
)


class V2PlaybookLoadError(Exception):
    """Raised when a V2 playbook cannot be loaded."""


class V2PlaybookValidationError(Exception):
    """Raised when a V2 playbook fails schema validation."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


class V2PlaybookLoader:
    """Load playbook sections from projects/<project>/playbooks/<playbook>."""

    def __init__(self, projects_root: Path | None = None) -> None:
        self._projects_root = projects_root or Path("./projects")

    def load(self, project_slug: str, playbook_slug: str) -> PlaybookDefinition:
        playbook_dir = self._projects_root / project_slug / "playbooks" / playbook_slug
        if not playbook_dir.is_dir():
            raise V2PlaybookLoadError(f"Playbook directory not found: {playbook_dir}")

        meta = self._load_meta(playbook_dir / "meta.json")
        schema = self._load_schema(playbook_dir / "schema.json")
        validation_rules = self._load_validation(playbook_dir / "validate.json")
        conditions, transformations = self._load_rules(playbook_dir / "rules.json")
        postprocess = self._load_postprocess(playbook_dir / "postprocess.json")
        prompts = self._load_prompts(playbook_dir / "prompts")

        try:
            return PlaybookDefinition(
                project_slug=project_slug,
                slug=playbook_slug,
                meta=meta,
                schema=schema,
                validation_rules=validation_rules,
                conditions=conditions,
                transformations=transformations,
                postprocess=postprocess,
                prompts=prompts,
            )
        except ValidationError as exc:
            raise V2PlaybookValidationError(
                f"Failed to validate playbook '{project_slug}/{playbook_slug}': {exc}",
                errors=exc.errors(),
            ) from exc

    def _read_json(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise V2PlaybookLoadError(f"Required playbook file not found: {path}")
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise V2PlaybookLoadError(f"Invalid JSON in {path}: {exc}") from exc
        except OSError as exc:
            raise V2PlaybookLoadError(f"Error reading {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise V2PlaybookLoadError(f"Expected JSON object in {path}")
        return data

    def _load_meta(self, path: Path) -> PlaybookMeta:
        raw = self._read_json(path)
        raw_checks = raw.pop("preupload_checks", [])
        meta = PlaybookMeta.model_validate({**raw, "preupload_checks": raw_checks})
        return meta

    def _load_schema(self, path: Path) -> list[PlaybookSchemaField]:
        raw = self._read_json(path)
        elements = raw.get("elements", [])
        return [PlaybookSchemaField.model_validate(item) for item in elements]

    def _load_validation(self, path: Path) -> list[PlaybookValidationRule]:
        raw = self._read_json(path)
        rules: list[PlaybookValidationRule] = []
        for item in raw.get("rules", []):
            rules.append(PlaybookValidationRule.model_validate(item))
        return rules

    def _load_rules(self, path: Path) -> tuple[list[PlaybookBusinessCondition], list[PlaybookBusinessTransformation]]:
        raw = self._read_json(path)
        conditions = [PlaybookBusinessCondition.model_validate(item) for item in raw.get("conditions", [])]
        transformations = [
            PlaybookBusinessTransformation.model_validate(item)
            for item in raw.get("transformations", [])
        ]
        return conditions, transformations

    def _load_postprocess(self, path: Path) -> PlaybookPostprocess:
        raw = self._read_json(path)
        return PlaybookPostprocess.model_validate(raw)

    def _load_prompts(self, prompts_dir: Path) -> dict[str, str]:
        if not prompts_dir.is_dir():
            return {}
        prompts: dict[str, str] = {}
        for path in sorted(prompts_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8")
            prompts[path.stem] = text
            prompts[path.name] = text
        return prompts
