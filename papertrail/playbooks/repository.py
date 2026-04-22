from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

class PlaybookNotFoundError(Exception):
    """Raised when a playbook or playbook part is not found."""
    pass


class PlaybookRepository:
    def __init__(self, playbooks_base_path: Path):
        """
        Initializes the PlaybookRepository.
        Args:
            playbooks_base_path: The root directory where playbooks are stored (e.g., Path("./playbooks")).
        """
        self._playbooks_base_path = playbooks_base_path
        if not self._playbooks_base_path.is_dir():
            raise ValueError(f"Playbooks base path '{playbooks_base_path}' is not a valid directory.")

    def _get_playbook_dir_path(self, slug: str) -> Path:
        """Helper to get the base directory for a playbook."""
        return self._playbooks_base_path / slug

    def get_raw_section_config(self, slug: str, section_name: str) -> Dict[str, Any]:
        """
        Retrieves the raw JSON configuration for a specific section of a playbook.
        
        Args:
            slug: The playbook identifier (e.g., "indian_cheque", "_base").
            section_name: The name of the section (e.g., "meta", "classify").
            
        Returns:
            A dictionary representing the raw JSON content of the section.
            Returns an empty dictionary if the section file is not found.
            
        Raises:
            PlaybookNotFoundError: If the playbook directory itself doesn't exist
                                   or if JSON is invalid.
        """
        playbook_dir = self._get_playbook_dir_path(slug)
        if not playbook_dir.is_dir():
            raise PlaybookNotFoundError(f"Playbook directory '{slug}' not found at {playbook_dir}")
        
        section_path = playbook_dir / f"{section_name}.json"
        
        if not section_path.is_file():
            # If a section file doesn't exist, it means the playbook doesn't
            # override that section, so we return an empty dict for merging.
            return {}
            
        try:
            with open(section_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise PlaybookNotFoundError(f"Invalid JSON in {section_path}: {e}")
        except Exception as e:
            raise PlaybookNotFoundError(f"Error reading {section_path}: {e}")

