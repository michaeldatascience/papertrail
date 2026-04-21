from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

class PlaybookNotFoundError(Exception):
    pass

# --- Temporary File-based Playbook Repository (to be replaced by DB repo) ---

class PlaybookRepository:
    def __init__(self, seed_path: Path):
        self._seed_path = seed_path

    async def get_playbook_config_parts(self, slug: str, version: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Loads playbook config JSON parts from the filesystem for a given slug/version.
        Returns a dict like {"meta": {...}, "classify": {...}, ...}
        """
        # For this stub, version is ignored and we just load the latest from the folder
        playbook_dir = self._seed_path / slug
        if not playbook_dir.is_dir():
            raise PlaybookNotFoundError(f"Playbook directory not found: {playbook_dir}")

        config_parts: Dict[str, Dict[str, Any]] = {}
        for config_file in playbook_dir.glob("*.json"):
            config_type = config_file.stem  # e.g., 'meta', 'classify'
            try:
                with open(config_file, "r") as f:
                    config_parts[config_type] = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {config_file}: {e}")
        
        # For testing inheritance, manually get extends_slug from meta.json if present
        # This would normally come from the DB row for the playbook.
        meta_config = config_parts.get("meta", {})
        if meta_config and "document_type" in meta_config and meta_config["document_type"] != "base":
            # This is a heuristic for our simple seed structure: if it's not base, it extends base
            # In a real DB setup, `extends_playbook_id` would determine this.
            meta_config["extends_slug"] = "_base"

        return config_parts

