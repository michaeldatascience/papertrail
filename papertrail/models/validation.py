"""Validation-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RuleResult(BaseModel):
    """Result of evaluating one validation rule."""

    rule_name: str = ""
    passed: bool | None = None
    reason: str = ""
    confidence: float | None = None
    status: str = "evaluated"  # evaluated, unable_to_evaluate, error
    error: str | None = None


class ElementValidationResult(BaseModel):
    """Validation result for a single element."""

    element_name: str
    hard_results: list[RuleResult] = Field(default_factory=list)
    soft_results: list[RuleResult] = Field(default_factory=list)
    passed: bool = True


class ValidationResult(BaseModel):
    """Aggregate validation result from Pass D."""

    passed: bool
    element_results: list[ElementValidationResult] = Field(default_factory=list)
    cross_field_results: list[RuleResult] = Field(default_factory=list)
    aggregate_confidence: float = 1.0
    failed_elements: list[str] = Field(default_factory=list)
