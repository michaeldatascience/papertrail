from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, condecimal, conint, NonNegativeInt


# --- Common Sub-models ---

class PlaybookCheckConfig(BaseModel):
    enabled: bool = False
    # Specific check parameters (e.g., threshold, max_mb, min_dpi)
    # Use Field with extra for flexible key-value pairs
    extra: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any):
        super().__init__(**data)
        # Move direct parameters into extra if they are not explicitly defined fields
        for key, value in data.items():
            if key not in self.__fields__ and key not in self.extra:
                self.extra[key] = value

class PlaybookEngineConfig(BaseModel):
    layout: Optional[str] = None
    text_extraction: Optional[str] = None
    ocr: Optional[str] = None
    ocr_fallback: Optional[str] = None
    tables: Optional[str] = None
    vision: Optional[str] = None
    always_fallback: Optional[bool] = None


# --- Section Models ---

class MetaConfig(BaseModel):
    document_type: str
    display_name: str
    description: Optional[str] = None
    engines: Optional[PlaybookEngineConfig] = None
    
    preupload: Optional[Dict[str, Dict[str, PlaybookCheckConfig]]] = None


class ClassifyCandidate(BaseModel):
    label: str
    description: str

class ClassifyConfig(BaseModel):
    prompt_template: str
    preview_chars: conint(ge=100) = 800
    hitl_threshold: condecimal(ge=0.0, le=1.0) = 0.6
    candidates: List[ClassifyCandidate] = Field(default_factory=list)


class SchemaElement(BaseModel):
    name: str
    type: Literal["string", "integer", "decimal", "date", "boolean"]
    critical: bool = False
    description: Optional[str] = None
    # Potentially add source_hint, regex, default_value, etc.

class SchemaConfig(BaseModel):
    mode: Literal["schema", "natural"]
    prompt_template: str
    vision_enabled: bool = False
    elements: List[SchemaElement] = Field(default_factory=list)


class ValidationRuleConfig(BaseModel):
    rule: str
    params: Optional[Dict[str, Any]] = None

class SoftValidationRuleConfig(BaseModel):
    prompt_template: str
    description: Optional[str] = None

class CrossFieldRuleConfig(BaseModel):
    name: str
    type: Literal["hard", "soft"]
    elements: List[str]
    prompt_template: Optional[str] = None # For soft rules
    description: Optional[str] = None
    # For hard rules, might need a handler or expression

class CorrectionConfig(BaseModel):
    enabled: bool = True
    max_attempts: NonNegativeInt = 3
    hint_template: str

class SuggestionConfig(BaseModel):
    enabled: bool = True
    template: str

class ScoringConfig(BaseModel):
    confidence_budget_start: condecimal(ge=0.0, le=1.0) = 1.0
    warning_penalty: condecimal(ge=0.0) = 0.05
    critical_weight: condecimal(ge=0.0) = 3.0

class ValidateConfig(BaseModel):
    correction: Optional[CorrectionConfig] = Field(default_factory=CorrectionConfig)
    suggestion: Optional[SuggestionConfig] = Field(default_factory=SuggestionConfig)
    scoring: Optional[ScoringConfig] = Field(default_factory=ScoringConfig)
    hard_rules: Optional[Dict[str, List[ValidationRuleConfig]]] = Field(default_factory=dict)
    soft_rules: Optional[Dict[str, List[SoftValidationRuleConfig]]] = Field(default_factory=dict)
    cross_field_rules: Optional[List[CrossFieldRuleConfig]] = Field(default_factory=list)


class ConditionConfig(BaseModel):
    name: str
    type: Literal["hard", "soft"]
    expression: Optional[str] = None # For hard conditions
    prompt_template: Optional[str] = None # For soft conditions
    action: Literal["approve", "flag", "reject", "escalate"]
    reason: Optional[str] = None

class TransformationConfig(BaseModel):
    name: str
    tool: str
    input: str # Expression for input
    output_field: str # Path to set in enriched_data
    run_on: List[Literal["approve", "flag", "reject", "escalate"]] = Field(
        default_factory=lambda: ["approve", "flag", "reject", "escalate"]
    )

class RulesConfig(BaseModel):
    conditions: List[ConditionConfig] = Field(default_factory=list)
    transformations: List[TransformationConfig] = Field(default_factory=list)
    default_action: Literal["approve", "flag", "reject", "escalate"] = "approve"


class PostprocessConfig(BaseModel):
    output_format: Literal["json", "pdf", "xml"] = "json"
    include_trace_summary: bool = True
    include_confidence_breakdown: bool = True
    export_on_approve: bool = False


# --- Merged Playbook Model ---

class MergedPlaybook(BaseModel):
    slug: str
    version: str
    extends_slug: Optional[str] = None
    is_base: bool = False

    meta: MetaConfig
    classify: ClassifyConfig
    schema_: SchemaConfig = Field(alias="schema", default_factory=SchemaConfig)
    validate_: ValidateConfig = Field(alias="validate", default_factory=ValidateConfig)
    rules_: RulesConfig = Field(alias="rules", default_factory=RulesConfig)
    postprocess: PostprocessConfig

    class Config:
        populate_by_name = True # Allows setting `schema_` and accessing as `schema`

