"""ExecutionPlan models for the V2 architecture."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PreflightConfig(BaseModel):
    """System-level checks copied into the execution plan."""

    allowed_mimes: list[str] = Field(default_factory=list)
    max_file_size_bytes: int | None = Field(default=None, ge=1)
    max_page_count: int | None = Field(default=None, ge=1)

    model_config = ConfigDict(extra="forbid")


class PreuploadCheckSpec(BaseModel):
    """A playbook-specific document check executed before orchestration starts."""

    check_type: str
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    on_failure: Literal["fail", "warn", "escalate"] = "fail"

    model_config = ConfigDict(extra="forbid")


class PreuploadConfig(BaseModel):
    """Playbook-specific preupload checks."""

    checks: list[PreuploadCheckSpec] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ClassificationConfig(BaseModel):
    """Resolved classification settings."""

    classifier_model: str
    confidence_threshold: float = Field(ge=0.0, le=1.0)
    candidate_labels: list[str] = Field(default_factory=list)
    prompt_text: str
    low_confidence_action: Literal["hitl", "fail", "proceed"] = "hitl"

    model_config = ConfigDict(extra="forbid")


class ExtractionFieldSpec(BaseModel):
    """A resolved field specification for extraction."""

    name: str
    field_type: str
    critical: bool = False
    description: str | None = None
    source_hint: str | None = None
    fragment_ref: str | None = None
    extraction_hint: str | None = None

    model_config = ConfigDict(extra="forbid")


class ExtractionConfig(BaseModel):
    """Resolved extraction behavior."""

    schema: list[ExtractionFieldSpec] = Field(default_factory=list)
    primary_engine: str
    fallback_engine: str | None = None
    prompt_text: str
    field_hints: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ValidationRuleSpec(BaseModel):
    """A fully resolved validation rule."""

    name: str
    rule_type: str
    targets: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    execution_mode: Literal["hard", "soft"] = "hard"
    prompt_text: str | None = None
    severity: Literal["error", "warning"] = "error"
    stop_on_failure: bool = False
    message: str | None = None

    model_config = ConfigDict(extra="forbid")


class ValidationConfig(BaseModel):
    """Resolved validation behavior."""

    rules: list[ValidationRuleSpec] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CorrectionPolicy(BaseModel):
    """Correction-loop settings."""

    max_retries: int = Field(default=3, ge=0)
    prompt_text: str
    retry_on_failures: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class BusinessConditionSpec(BaseModel):
    """A resolved business-rule condition."""

    name: str
    expression_type: str
    expression: str
    action: Literal["approve", "flag", "reject", "escalate"]
    reason: str | None = None
    order: int = 0
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class BusinessTransformationSpec(BaseModel):
    """A resolved business-rule transformation."""

    name: str
    output_binding: str
    expression_type: str | None = None
    expression: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    order: int = 0
    enabled: bool = True

    model_config = ConfigDict(extra="forbid")


class BusinessRulesConfig(BaseModel):
    """Resolved business rule behavior."""

    conditions: list[BusinessConditionSpec] = Field(default_factory=list)
    transformations: list[BusinessTransformationSpec] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ToolCallSpec(BaseModel):
    """A resolved tool invocation used in post-processing."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PostprocessConfig(BaseModel):
    """Resolved output and post-processing behavior."""

    output_format: str
    fields_to_include: list[str] = Field(default_factory=list)
    include_trace: bool = False
    success_tool_calls: list[ToolCallSpec] = Field(default_factory=list)
    failure_tool_calls: list[ToolCallSpec] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class EngineBinding(BaseModel):
    """A concrete engine binding resolved for runtime."""

    name: str
    type: str
    implementation: str
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class LLMBinding(BaseModel):
    """A concrete LLM binding resolved for runtime."""

    stage: str
    provider: str
    model: str
    parameters: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ToolBinding(BaseModel):
    """A concrete tool binding resolved for runtime."""

    name: str
    implementation: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class RuntimeLimits(BaseModel):
    """Run-specific runtime limits copied into the plan."""

    max_correction_iterations: int = Field(default=3, ge=0)
    stage_timeout_seconds: int = Field(default=600, ge=1)
    overall_run_timeout_seconds: int = Field(default=3600, ge=1)

    model_config = ConfigDict(extra="forbid")


class ExecutionPlan(BaseModel):
    """The fully resolved runtime contract executed by the orchestrator."""

    plan_id: str
    project_slug: str
    playbook_slug: str
    document_type: str
    compiled_at: datetime
    compiler_version: str
    preflight: PreflightConfig
    preupload: PreuploadConfig
    classification: ClassificationConfig
    extraction: ExtractionConfig
    validation: ValidationConfig
    correction: CorrectionPolicy
    business_rules: BusinessRulesConfig
    postprocess: PostprocessConfig
    engine_routing: dict[str, EngineBinding]
    llm_routing: dict[str, LLMBinding]
    tools: dict[str, ToolBinding]
    limits: RuntimeLimits
    prompts: dict[str, str]

    model_config = ConfigDict(extra="forbid")
