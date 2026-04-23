"""Project-layer Pydantic models for the V2 architecture."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectClassificationEntry(BaseModel):
    """One document-type option in a project's classification universe."""

    label: str
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class ProjectEngineDefaults(BaseModel):
    """Default engine selections shared by a project."""

    layout: str | None = None
    text_extraction: str | None = None
    ocr: str | None = None
    ocr_fallback: str | None = None
    tables: str | None = None
    vision: str | None = None

    model_config = ConfigDict(extra="forbid")


class ProjectDefinition(BaseModel):
    """The validated project authoring contract consumed by the compiler."""

    slug: str
    name: str
    description: str | None = None
    version: str = "1.0.0"
    classification_universe: list[ProjectClassificationEntry] = Field(default_factory=list)
    shared_prompts: dict[str, str] = Field(default_factory=dict)
    engine_defaults: ProjectEngineDefaults = Field(default_factory=ProjectEngineDefaults)
    shared_tools: list[str] = Field(default_factory=list)
    schema_fragments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    playbooks: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    def classification_labels(self) -> set[str]:
        return {entry.label for entry in self.classification_universe}
