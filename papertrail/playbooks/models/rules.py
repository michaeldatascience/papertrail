"""
Business rules configuration for playbooks.

This module defines:
1. ConditionConfig - Conditions that trigger actions
2. TransformationConfig - Data enrichment/transformation
3. RulesConfig - Overall business rules
4. Loader function

Design Note:
- Rules are applied AFTER validation
- They decide final action: approve, flag, reject, escalate
- They can trigger transformations (enrichment, tool calls)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from papertrail.playbooks.models.base import merge_dicts_recursive


class ConditionConfig(BaseModel):
    """
    A condition that triggers a business rule.
    
    Fields:
        name: Condition identifier
        type: "hard" (deterministic) or "soft" (LLM-based)
        expression: Boolean expression for hard conditions
        prompt_template: LLM prompt for soft conditions
        action: What to do if condition is true
        reason: Why this action is taken
    """
    name: str = Field(..., description="Condition identifier")
    type: Literal["hard", "soft"] = Field(..., description="Condition type")
    expression: Optional[str] = Field(
        default=None,
        description="Boolean expression for hard conditions"
    )
    prompt_template: Optional[str] = Field(
        default=None,
        description="LLM prompt for soft conditions"
    )
    action: Literal["approve", "flag", "reject", "escalate"] = Field(
        ...,
        description="Action to take"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for this action"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class TransformationConfig(BaseModel):
    """
    Transform or enrich extracted data.
    
    Fields:
        name: Transformation identifier
        tool: Tool to invoke (e.g., "enrich_ifsc", "lookup_bank")
        input: Expression for tool input
        output_field: Where to store result
        run_on: When to run (based on decision)
    """
    name: str = Field(..., description="Transformation identifier")
    tool: str = Field(..., description="Tool to invoke")
    input: str = Field(..., description="Input expression")
    output_field: str = Field(..., description="Where to store output")
    run_on: List[Literal["approve", "flag", "reject", "escalate"]] = Field(
        default_factory=lambda: ["approve", "flag", "reject", "escalate"],
        description="When to run this transformation"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class RulesConfig(BaseModel):
    """
    Business rules applied after validation.
    
    Decisions made here:
    - approve: Document is complete and valid
    - flag: Document is valid but needs review
    - reject: Document is invalid
    - escalate: Human decision needed
    
    Fields:
        conditions: List of conditions and actions
        transformations: Data enrichment steps
        default_action: What to do if no conditions match
    """
    conditions: List[ConditionConfig] = Field(
        default_factory=list,
        description="Conditions and actions"
    )
    transformations: List[TransformationConfig] = Field(
        default_factory=list,
        description="Data enrichment steps"
    )
    default_action: Literal["approve", "flag", "reject", "escalate"] = Field(
        default="approve",
        description="Default action if no conditions match"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


# ============================================================================
# Loader
# ============================================================================

def load_rules(base_config: Dict[str, Any], raw_dict: Optional[Dict[str, Any]] = None) -> RulesConfig:
    """
    Load and merge rules configuration.
    
    Args:
        base_config: Base configuration dictionary, typically from _base/rules.json
        raw_dict: Raw config from playbook JSON
        
    Returns:
        Validated and frozen RulesConfig instance
    """
    merged_dict = base_config.copy()
    
    if raw_dict:
        merged_dict = merge_dicts_recursive(merged_dict, raw_dict)
    
    merged_config = RulesConfig(**merged_dict)
    
    return merged_config
