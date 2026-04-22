"""
Classification configuration for playbooks.

This module defines:
1. ClassifyCandidate - A possible document classification label
2. ClassifyConfig - Configuration for classification stage
3. CLASSIFY_DEFAULTS - Defaults
4. load_classify() - Merge and validate
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, condecimal, conint

from papertrail.playbooks.models.base import merge_dicts_recursive


class ClassifyCandidate(BaseModel):
    """
    A candidate label for document classification.
    
    Fields:
        label: The classification label (e.g., "cheque", "invoice")
        description: What this label means
    """
    label: str = Field(..., description="Classification label")
    description: str = Field(..., description="What this label means")
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class ClassifyConfig(BaseModel):
    """
    Configuration for the classification stage.
    
    This stage determines what document type we're processing.
    If confidence is below threshold, triggers HITL review.
    
    Fields:
        prompt_template: Which prompt template to use for classification
        preview_chars: How many characters to preview for context
        hitl_threshold: Confidence below this triggers human review (0.0-1.0)
        candidates: List of possible classification labels
    """
    prompt_template: str = Field(..., description="Prompt template name for classification")
    preview_chars: conint(ge=100) = Field(
        default=800,
        description="Preview length in characters"
    )
    hitl_threshold: condecimal(ge=0.0, le=1.0) = Field(
        default=0.6,
        description="Confidence threshold for human review"
    )
    candidates: List[ClassifyCandidate] = Field(
        default_factory=list,
        description="Possible classification labels"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


# ============================================================================
# Loader
# ============================================================================

def load_classify(base_config: Dict[str, Any], raw_dict: Optional[Dict[str, Any]] = None) -> ClassifyConfig:
    """
    Load and merge classify configuration.
    
    Args:
        base_config: Base configuration dictionary, typically from _base/classify.json
        raw_dict: Raw config from playbook JSON
        
    Returns:
        Validated and frozen ClassifyConfig instance
    """
    merged_dict = base_config.copy()
    
    if raw_dict:
        merged_dict = merge_dicts_recursive(merged_dict, raw_dict)
    
    merged_config = ClassifyConfig(**merged_dict)
    
    return merged_config
