"""
Validation configuration for playbooks.

This module defines:
1. ValidationRuleConfig - Hard validation rules
2. SoftValidationRuleConfig - Soft validation rules (LLM-based)
3. CrossFieldRuleConfig - Multi-field rules
4. CorrectionConfig - Correction attempt configuration
5. SuggestionConfig - Suggestion configuration
6. ScoringConfig - Confidence scoring
7. ValidateConfig - Overall validation configuration
8. Loader function
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, condecimal, NonNegativeInt

from papertrail.playbooks.models.base import merge_dicts_recursive


class ValidationRuleConfig(BaseModel):
    """
    A hard validation rule for a field.
    
    Fields:
        rule: Rule type (e.g., "regex", "format", "range")
        params: Rule-specific parameters
    """
    rule: str = Field(..., description="Rule type identifier")
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Rule-specific parameters"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class SoftValidationRuleConfig(BaseModel):
    """
    A soft validation rule using LLM.
    
    Fields:
        prompt_template: LLM prompt for validation
        description: What this validation checks
    """
    prompt_template: str = Field(..., description="Prompt template for LLM")
    description: Optional[str] = Field(
        default=None,
        description="What this validation does"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class CrossFieldRuleConfig(BaseModel):
    """
    Validation rule involving multiple fields.
    
    Fields:
        name: Rule identifier
        type: "hard" (deterministic) or "soft" (LLM-based)
        elements: Field names involved
        prompt_template: For soft rules
        description: What this rule validates
    """
    name: str = Field(..., description="Rule identifier")
    type: Literal["hard", "soft"] = Field(..., description="Rule type")
    elements: List[str] = Field(..., description="Fields involved")
    prompt_template: Optional[str] = Field(
        default=None,
        description="Prompt for soft rules"
    )
    description: Optional[str] = Field(
        default=None,
        description="Rule description"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class CorrectionConfig(BaseModel):
    """
    Configuration for correction attempts when validation fails.
    
    Fields:
        enabled: Whether correction is attempted
        max_attempts: Maximum correction tries
        hint_template: Prompt template for correction hint
    """
    enabled: bool = Field(default=True, description="Enable correction")
    max_attempts: NonNegativeInt = Field(
        default=3,
        description="Max correction attempts"
    )
    hint_template: str = Field(
        default="correct_field",
        description="Prompt template for hints"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class SuggestionConfig(BaseModel):
    """
    Configuration for suggestions when correction is exhausted.
    
    This triggers HITL pause for human review.
    
    Fields:
        enabled: Whether suggestions are provided
        template: Prompt template for suggestions
    """
    enabled: bool = Field(default=True, description="Enable suggestions")
    template: str = Field(
        default="suggest_correction",
        description="Prompt template for suggestions"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class ScoringConfig(BaseModel):
    """
    Configuration for confidence scoring.
    
    Tracks confidence throughout extraction and validation.
    
    Fields:
        confidence_budget_start: Starting confidence (1.0 = 100%)
        warning_penalty: Confidence reduction for warnings
        critical_weight: Extra importance for critical fields
    """
    confidence_budget_start: condecimal(ge=0.0, le=1.0) = Field(
        default=1.0,
        description="Starting confidence"
    )
    warning_penalty: condecimal(ge=0.0) = Field(
        default=0.05,
        description="Penalty per warning"
    )
    critical_weight: condecimal(ge=0.0) = Field(
        default=3.0,
        description="Critical field weight"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


class ValidateConfig(BaseModel):
    """
    Configuration for the validation stage.
    
    Validates extracted data against rules.
    Handles correction and suggestion flows.
    """
    correction: Optional[CorrectionConfig] = Field(
        default_factory=CorrectionConfig,
        description="Correction configuration"
    )
    suggestion: Optional[SuggestionConfig] = Field(
        default_factory=SuggestionConfig,
        description="Suggestion configuration"
    )
    scoring: Optional[ScoringConfig] = Field(
        default_factory=ScoringConfig,
        description="Scoring configuration"
    )
    hard_rules: Optional[Dict[str, List[ValidationRuleConfig]]] = Field(
        default_factory=dict,
        description="Hard rules by field"
    )
    soft_rules: Optional[Dict[str, List[SoftValidationRuleConfig]]] = Field(
        default_factory=dict,
        description="Soft rules by field"
    )
    cross_field_rules: Optional[List[CrossFieldRuleConfig]] = Field(
        default_factory=list,
        description="Rules involving multiple fields"
    )
    
    model_config = {
        "frozen": True,
        "extra": "forbid",
    }


# ============================================================================
# Loader
# ============================================================================

def load_validate(base_config: Dict[str, Any], raw_dict: Optional[Dict[str, Any]] = None) -> ValidateConfig:
    """
    Load and merge validation configuration.
    
    Args:
        base_config: Base configuration dictionary, typically from _base/validate.json
        raw_dict: Raw config from playbook JSON
        
    Returns:
        Validated and frozen ValidateConfig instance
    """
    merged_dict = base_config.copy()
    
    if raw_dict:
        merged_dict = merge_dicts_recursive(merged_dict, raw_dict)
    
    merged_config = ValidateConfig(**merged_dict)
    
    return merged_config
