from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from papertrail.playbooks.models import MergedPlaybook, MetaConfig, ClassifyConfig, SchemaConfig, ValidateConfig, RulesConfig, PostprocessConfig
from papertrail.playbooks.merger import deep_merge
from papertrail.playbooks.repository import PlaybookRepository, PlaybookNotFoundError

class PlaybookValidationError(Exception):
    """Raised when a loaded playbook fails validation."""
    def __init__(self, message: str, errors: list[Dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors if errors is not None else []


class PlaybookLoader:
    def __init__(self, repository: PlaybookRepository, base_playbook_slug: str = "_base"):
        self._repository = repository
        self._base_playbook_slug = base_playbook_slug
        self._cache: Dict[str, MergedPlaybook] = {}

    async def load(self, slug: str, version: Optional[str] = None) -> MergedPlaybook:
        """Loads a playbook by slug and version, resolving inheritance and merging.
        Caches loaded playbooks for performance.
        """
        cache_key = f"{slug}:{version or 'latest'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Fetch current playbook's parts
        try:
            current_playbook_parts = await self._repository.get_playbook_config_parts(slug, version)
        except PlaybookNotFoundError as e:
            raise PlaybookNotFoundError(f"Playbook '{slug}' not found: {e}")

        # Determine if it extends a base playbook (heuristic for file-based stub)
        # In a real DB scenario, this would come from a `extends_playbook_id` field on the Playbook DB model
        meta_config_dict = current_playbook_parts.get("meta", {})
        extends_slug = meta_config_dict.get("extends_slug") # Injected by stub repository

        merged_config: Dict[str, Any] = {}

        if extends_slug and slug != self._base_playbook_slug:
            # Recursively load and merge base playbook first
            base_playbook = await self.load(extends_slug) # base_playbook should be fully merged
            merged_config = deep_merge(base_playbook.model_dump(by_alias=True), current_playbook_parts)
        else:
            merged_config = current_playbook_parts

        # Ensure required top-level sections are present for Pydantic validation
        # This handles cases where _base has a section, but an inheriting playbook omits it
        # (though deep_merge should handle this for objects, lists are replaced)
        # For our P6-Pydantic models, we rely on default_factory for optional fields.

        # Special handling for 'schema' key due to Python keyword collision
        if "schema" in merged_config:
            merged_config["schema_"] = merged_config.pop("schema")

        if "slug" in merged_config:
            merged_config.pop("slug")

        if "version" in merged_config:
            merged_config.pop("version")

        try:
            # Validate against the MergedPlaybook Pydantic model
            playbook_instance = MergedPlaybook(slug=slug, version=version or "latest", **merged_config)
            if extends_slug and slug != self._base_playbook_slug:
                playbook_instance.extends_slug = extends_slug

            self._cache[cache_key] = playbook_instance
            return playbook_instance
        except Exception as e:
            # In a real scenario, we'd capture Pydantic ValidationError details
            raise PlaybookValidationError(f"Failed to validate playbook '{slug}': {e}") from e

