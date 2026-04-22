from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from papertrail.playbooks.repository import PlaybookRepository, PlaybookNotFoundError
from papertrail.playbooks.models import (
    MergedPlaybook,
    load_meta, load_classify, load_schema, load_validate, load_rules, load_postprocess
)


class PlaybookValidationError(Exception):
    """Raised when a loaded playbook fails validation."""
    def __init__(self, message: str, errors: list[Dict[str, Any]] | None = None):
        super().__init__(message)
        self.errors = errors if errors is not None else []


class PlaybookLoader:
    _BASE_PLAYBOOK_SLUG = "_base" # Constant for the base playbook identifier

    def __init__(self, repository: PlaybookRepository):
        self._repository = repository
        # Removed _cache as it will be handled higher up or not needed in this simplified loader

    async def load(self, slug: str, version: Optional[str] = None) -> MergedPlaybook:
        """
        Loads a playbook by slug and version, resolving single-level inheritance and merging.
        
        Args:
            slug: The identifier of the playbook to load.
            version: The specific version of the playbook (currently not used for file-based).
            
        Returns:
            A fully merged and validated MergedPlaybook instance.
            
        Raises:
            PlaybookNotFoundError: If the playbook or its base is not found.
            PlaybookValidationError: If the merged playbook fails Pydantic validation.
        """
        # Determine if the current playbook is the base playbook itself
        is_base = (slug == self._BASE_PLAYBOOK_SLUG)

        # 1. Fetch raw meta config for the specific playbook to determine inheritance
        # This raw_meta will contain the 'extends_slug' if declared by the playbook.
        raw_meta_current = self._repository.get_raw_section_config(slug, "meta")
        extends_slug: Optional[str] = raw_meta_current.get("extends_slug") 
        
        # If it's the base playbook, it doesn't extend anything.
        if is_base:
            extends_slug = None 
        
        # 2. Prepare base configurations by section.
        #    For single-level inheritance, the parent is always '_base' if 'extends_slug' is present.
        base_configs_by_section: Dict[str, Dict[str, Any]] = {}
        
        if extends_slug == self._BASE_PLAYBOOK_SLUG:
            # Load _base configs if the playbook explicitly extends _base
            for section_name in ["meta", "classify", "schema", "validate", "rules", "postprocess"]:
                base_configs_by_section[section_name] = self._repository.get_raw_section_config(self._BASE_PLAYBOOK_SLUG, section_name)
        elif extends_slug and extends_slug != self._BASE_PLAYBOOK_SLUG:
            # Enforce single-level inheritance: only _base can be extended.
            raise PlaybookNotFoundError(
                f"Multi-level inheritance from '{extends_slug}' is not supported. "
                f"Playbooks must extend '{self._BASE_PLAYBOOK_SLUG}' or not specify 'extends_slug'."
            )
            # If a playbook doesn't specify extends_slug, it implicitly extends an empty configuration
            # which is handled by load_xxx defaulting to base_configs_by_section.get(section_name, {})

        # 3. Load specific section configurations for the current playbook from the repository.
        #    These are the "actual playbook instances" or "overrides."
        current_configs_by_section: Dict[str, Dict[str, Any]] = {}
        for section_name in ["meta", "classify", "schema", "validate", "rules", "postprocess"]:
            current_configs_by_section[section_name] = self._repository.get_raw_section_config(slug, section_name)

        # 4. Use the section-specific loaders to merge and validate.
        #    Each load_xxx function implements the "apply child overrides to base" logic.
        raw_meta_current_for_meta_config = current_configs_by_section.get("meta", {}).copy()
        if "extends_slug" in raw_meta_current_for_meta_config:
            del raw_meta_current_for_meta_config["extends_slug"]
        
        meta_config = load_meta(base_configs_by_section.get("meta", {}), raw_meta_current_for_meta_config)
        classify_config = load_classify(base_configs_by_section.get("classify", {}), current_configs_by_section.get("classify", {}))
        schema_config = load_schema(base_configs_by_section.get("schema", {}), current_configs_by_section.get("schema", {}))
        validate_config = load_validate(base_configs_by_section.get("validate", {}), current_configs_by_section.get("validate", {}))
        rules_config = load_rules(base_configs_by_section.get("rules", {}), current_configs_by_section.get("rules", {}))
        postprocess_config = load_postprocess(base_configs_by_section.get("postprocess", {}), current_configs_by_section.get("postprocess", {}))

        # 5. Assemble the MergedPlaybook (the "final playbook: structure + data").
        try:
            # Version handling: For flat files, version might be part of the slug/folder name,
            # or a field within meta.json. For now, defaulting to "latest".
            playbook_instance = MergedPlaybook(
                slug=slug,
                version=version or "latest", 
                extends_slug=extends_slug,
                is_base=is_base,
                meta=meta_config,
                classify=classify_config,
                schema=schema_config,
                validate=validate_config,
                rules=rules_config,
                postprocess=postprocess_config,
            )
            return playbook_instance
        except Exception as e:
            # Catch and re-raise Pydantic ValidationErrors for better debugging.
            # In a real scenario, this would be PlaybookValidationError with Pydantic errors.
            raise PlaybookValidationError(f"Failed to validate playbook '{slug}': {e}") from e

