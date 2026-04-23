"""V2 playbook authoring models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PreuploadCheckSpec(BaseModel):
    """A playbook-specific preupload check."""

    check_type: str
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)
    on_failure: Literal["fail", "warn", "escalate"] = "fail"

    model_config = ConfigDict(extra="forbid")


class PlaybookMeta(BaseModel):
    """Playbook metadata and document-specific configuration."""

    document_type: str
    display_name: str
    description: str | None = None
    preupload_checks: list[PreuploadCheckSpec] = Field(default_factory=list)
    engine_overrides: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PlaybookSchemaField(BaseModel):
    """One extraction field defined by a playbook."""

    name: str
    field_type: str
    critical: bool = False
    description: str | None = None
    source_hint: str | None = None
    fragment_ref: str | None = None
    extraction_hint: str | None = None

    model_config = ConfigDict(extra="forbid")


class PlaybookValidationRule(BaseModel):
    """One resolved validation rule from a playbook authoring file."""

    name: str
    rule_type: str
    targets: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    execution_mode: Literal["hard", "soft"] = "hard"
    prompt_template: str | None = None
    severity: Literal["error", "warning"] = "error"
    stop_on_failure: bool | None = None
    message: str | None = None

    model_config = ConfigDict(extra="forbid")


class PlaybookBusinessCondition(BaseModel):
    """A decisioning condition declared by a playbook."""

    name: str
    expression_type: str
    expression: str
    action: Literal["approve", "flag", "reject", "escalate"]
    reason: str | None = None
    order: int = 0
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PlaybookBusinessTransformation(BaseModel):
    """A post-validation transformation declared by a playbook."""

    name: str
    output_binding: str
    expression_type: str | None = None
    expression: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, Any] = Field(default_factory=dict)
    order: int = 0
    enabled: bool = True

    model_config = ConfigDict(extra="forbid")


class PlaybookPostprocess(BaseModel):
    """Final output shaping and delivery behavior."""

    output_format: str
    fields_to_include: list[str] = Field(default_factory=list)
    include_trace: bool = False
    success_tool_calls: list[str] = Field(default_factory=list)
    failure_tool_calls: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PlaybookDefinition(BaseModel):
    """The fully loaded playbook authoring contract."""

    project_slug: str
    slug: str
    meta: PlaybookMeta
    schema: list[PlaybookSchemaField] = Field(default_factory=list)
    validation_rules: list[PlaybookValidationRule] = Field(default_factory=list)
    conditions: list[PlaybookBusinessCondition] = Field(default_factory=list)
    transformations: list[PlaybookBusinessTransformation] = Field(default_factory=list)
    postprocess: PlaybookPostprocess
    prompts: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
