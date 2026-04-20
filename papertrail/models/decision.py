"""Decision-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel


class ConditionResult(BaseModel):
    """Result of evaluating one decision condition."""

    rule_name: str
    fired: bool
    action: str | None = None
    reason: str | None = None
    error: str | None = None
    order_executed: int = 0


class DecisionResult(BaseModel):
    """Final decision output."""

    action: str  # approve, flag, reject, escalate
    conditions_evaluated: list[ConditionResult] = []
    transformations_applied: list[str] = []
    enriched_data: dict = {}
    reasons: list[str] = []
