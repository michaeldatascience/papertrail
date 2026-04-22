"""
Post-processing configuration for playbooks.

This module defines:
1. PostprocessConfig - Output formatting and delivery
2. Loader function

Design Note:
- Final stage before returning to user/system
- Handles output format, trace inclusion, exports
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

from papertrail.playbooks.models.base import merge_dicts_recursive


class PostprocessConfig(BaseModel):
    """
    Configuration for post-processing and output formatting.
    
    Fields:
        output_format: Format for results (json, pdf, xml)
        include_trace_summary: Whether to include execution trace
        include_confidence_breakdown: Whether to include confidence scores
        export_on_approve: Whether to auto-export when approved
    """
    output_format: Literal["json", "pdf", "xml"] = Field(
        default="json",
        description="Output format"
    )
    include_trace_summary: bool = Field(
        default=True,
        description="Include execution trace"
    )
    include_confidence_breakdown: bool = Field(
        default=True,
        description="Include confidence scores"
    )
    export_on_approve: bool = Field(
        default=False,
        description="Auto-export when approved"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


# ============================================================================
# Loader
# ============================================================================

def load_postprocess(base_config: Dict[str, Any], raw_dict: Optional[Dict[str, Any]] = None) -> PostprocessConfig:
    """
    Load and merge post-processing configuration.
    
    Args:
        base_config: Base configuration dictionary, typically from _base/postprocess.json
        raw_dict: Raw config from playbook JSON
        
    Returns:
        Validated and frozen PostprocessConfig instance
    """
    merged_dict = base_config.copy()
    
    if raw_dict:
        merged_dict = merge_dicts_recursive(merged_dict, raw_dict)
    
    merged_config = PostprocessConfig(**merged_dict)
    
    return merged_config
