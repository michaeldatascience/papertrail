# Catalog of system capabilities, loaded from config/catalog.json and validated with Pydantic.
# System capabilities are the fundamental building blocks of the execution engine and include evertyhing from availab
# tools, llm providers, enginers, validation rules etc



from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class EngineCatalogEntry(BaseModel):
# Engines are the LLM providers + embedding providers
# E.g. "gpt-4" from "openai", or "text-embedding-3-small" from "cohere"

    name: str
    type: str
    implementation: str
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class ValidationRuleType(BaseModel):
    """A validation rule type supported by the system."""

    name: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class BusinessRuleExpressionType(BaseModel):
    """A supported business-rule expression type."""

    name: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class ToolCatalogEntry(BaseModel):
    """A system-registered tool interface."""

    name: str
    implementation: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class PromptTemplate(BaseModel):
    """A named prompt template known to the system."""

    name: str
    variables: list[str] = Field(default_factory=list)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class RuntimeLimits(BaseModel):
    """Global runtime limits declared by the system."""

    max_file_size_bytes: int | None = Field(default=None, ge=1)
    max_correction_iterations: int = Field(default=3, ge=0)
    stage_timeout_seconds: int = Field(default=600, ge=1)
    overall_run_timeout_seconds: int = Field(default=3600, ge=1)

    model_config = ConfigDict(extra="forbid")


class SystemCatalog(BaseModel):
    """The validated system capability catalog consumed by the compiler."""

    version: str = "v2"
    compiled_at: datetime | None = None
    node_types: list[str] = Field(default_factory=list)
    engines: list[EngineCatalogEntry] = Field(default_factory=list)
    validation_rule_types: list[ValidationRuleType] = Field(default_factory=list)
    business_rule_expression_types: list[BusinessRuleExpressionType] = Field(default_factory=list)
    tools: list[ToolCatalogEntry] = Field(default_factory=list)
    prompt_templates: list[PromptTemplate] = Field(default_factory=list)
    supported_mimes: list[str] = Field(default_factory=list)
    runtime_limits: RuntimeLimits = Field(default_factory=RuntimeLimits)

    model_config = ConfigDict(extra="forbid")

    def engine_names(self) -> set[str]:
        return {entry.name for entry in self.engines}

    def tool_names(self) -> set[str]:
        return {entry.name for entry in self.tools}

    def validation_rule_type_names(self) -> set[str]:
        return {entry.name for entry in self.validation_rule_types}

    def expression_type_names(self) -> set[str]:
        return {entry.name for entry in self.business_rule_expression_types}

    def prompt_names(self) -> set[str]:
        return {entry.name for entry in self.prompt_templates}


def load_system_catalog(config_path: Path | None = None) -> SystemCatalog:
    """Load the system catalog from config/catalog.json with Pydantic validation."""

    path = config_path or Path("./config/catalog.json")
    if not path.is_file():
        raise FileNotFoundError(f"System catalog not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    try:
        return SystemCatalog.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid system catalog at {path}: {exc}") from exc
