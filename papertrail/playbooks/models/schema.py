"""
Schema configuration for playbooks.

This module defines:
1. SchemaElement - A field to extract from the document
2. SchemaConfig - Configuration for schema extraction stage
3. SCHEMA_DEFAULTS - Defaults
4. load_schema() - Merge and validate

Design Notes:
- Schema defines WHAT fields to extract
- The extraction is done via LLM (not position-based)
- Pydantic models will validate extracted data later
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from papertrail.playbooks.models.base import merge_dicts_recursive


class SchemaElement(BaseModel):
    """
    A field/element to extract from the document.
    
    Fields:
        name: Field identifier (e.g., "account_number", "total_amount")
        type: Data type for validation
        critical: Whether this field is required/critical
        description: What this field is and where to find it
    """
    name: str = Field(..., description="Field identifier")
    type: Literal["string", "integer", "decimal", "date", "boolean"] = Field(
        ...,
        description="Data type"
    )
    critical: bool = Field(
        default=False,
        description="Whether this field is required"
    )
    description: Optional[str] = Field(
        default=None,
        description="Field description and context"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class SchemaConfig(BaseModel):
    """
    Configuration for the schema extraction stage.
    
    This stage extracts structured data from the document.
    Uses LLM with the schema as guidance.
    
    Fields:
        mode: "schema" (structured) or "natural" (free-form extraction)
        prompt_template: Which prompt to use for extraction
        vision_enabled: Whether to use vision for this extraction
        elements: Fields to extract
    """
    mode: Literal["schema", "natural"] = Field(
        default="schema",
        description="Extraction mode"
    )
    prompt_template: str = Field(
        ...,
        description="Prompt template for extraction"
    )
    vision_enabled: bool = Field(
        default=False,
        description="Whether to use vision models"
    )
    elements: List[SchemaElement] = Field(
        default_factory=list,
        description="Fields to extract"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


# ============================================================================
# Loader
# ============================================================================

def load_schema(base_config: Dict[str, Any], raw_dict: Optional[Dict[str, Any]] = None) -> SchemaConfig:
    """
    Load and merge schema configuration.
    
    Args:
        base_config: Base configuration dictionary, typically from _base/schema.json
        raw_dict: Raw config from playbook JSON
        
    Returns:
        Validated and frozen SchemaConfig instance
    """
    merged_dict = base_config.copy()
    
    if raw_dict:
        merged_dict = merge_dicts_recursive(merged_dict, raw_dict)
    
    merged_config = SchemaConfig(**merged_dict)
    
    return merged_config
