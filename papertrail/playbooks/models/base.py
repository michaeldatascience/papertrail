"""
Base types and models for playbooks.

This module contains:
1. PlaybookValidationCheck - Common validation check type (no __init__ hack)
2. Common types used across all playbook sections
3. Helper functions for merging playbook configs

Design Note:
- PlaybookValidationCheck uses Pydantic v2's model_config for flexibility
- No custom __init__ hackery - clean and maintainable
- Frozen after initialization to prevent accidental changes
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class PlaybookValidationCheck(BaseModel):
    """
    A validation check definition for a playbook.
    
    Fields:
        enabled (bool): Whether this check is active
        Additional fields allowed via extra="allow" for check-specific params
        
    Example:
        {
            "enabled": true,
            "blur_threshold": 100,
            "min_dpi": 150,
            "max_pages": 50
        }
    """
    enabled: bool = False
    
    model_config = {
        "extra": "allow",  # Allow arbitrary fields for check-specific parameters
        "frozen": True,    # Immutable after creation
    }


def merge_dicts_recursive(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge overrides into base dictionary.
    
    Strategy:
    - For dict values: Recursively merge
    - For list values: Replace (not append)
    - For scalar values: Replace with override value
    
    Args:
        base: The base configuration dictionary
        overrides: The overriding configuration dictionary
        
    Returns:
        Merged dictionary (new object, doesn't modify inputs)
        
    Example:
        base = {"a": 1, "b": {"c": 2, "d": [1, 2]}}
        overrides = {"b": {"c": 3}, "b": {"d": [4, 5]}}
        result = {"a": 1, "b": {"c": 3, "d": [4, 5]}}
    """
    merged = base.copy()
    
    if not overrides:
        return merged
    
    for key, override_value in overrides.items():
        base_value = merged.get(key)
        
        # Case 1: Base doesn't have this key - add it
        if key not in merged:
            merged[key] = override_value
        
        # Case 2: Both are dicts - recurse
        elif isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = merge_dicts_recursive(base_value, override_value)
        
        # Case 3: Lists or other types - replace (not append)
        else:
            merged[key] = override_value
    
    return merged


def safe_model_dump(model: BaseModel) -> Dict[str, Any]:
    """
    Safely dump a Pydantic model to dict.
    
    Uses by_alias=True to handle renamed fields.
    
    Args:
        model: Pydantic model instance
        
    Returns:
        Dictionary representation
    """
    return model.model_dump(by_alias=True, exclude_none=False)
