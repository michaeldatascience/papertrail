"""Validation engine for compiled execution plans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from papertrail.models.validation import ElementValidationResult, RuleResult, ValidationResult


@dataclass(slots=True)
class ValidationContext:
    plan: dict[str, Any]
    elements: dict[str, Any]


def validate_execution_plan(plan: dict[str, Any], extracted_elements: list[dict[str, Any]]) -> ValidationResult:
    """Validate extracted elements against the compiled plan."""

    context = ValidationContext(
        plan=_normalize_plan(plan),
        elements={item.get("name"): item.get("value") for item in extracted_elements if item.get("name")},
    )
    validation_rules = context.plan.get("validation", {}).get("rules", [])

    element_results: dict[str, ElementValidationResult] = {}
    cross_field_results: list[RuleResult] = []
    failed_elements: list[str] = []
    hard_failure_count = 0
    confidence_total = 0.0
    confidence_count = 0

    for rule in validation_rules:
        rule_result = _evaluate_rule(rule, context)
        if rule_result.status == "evaluated" and rule_result.confidence is not None:
            confidence_total += rule_result.confidence
            confidence_count += 1

        targets = list(rule.get("targets", []) or [])
        if len(targets) <= 1:
            target_name = targets[0] if targets else rule.get("name", "rule")
            element_result = element_results.setdefault(
                target_name,
                ElementValidationResult(element_name=target_name),
            )
            if rule.get("execution_mode", "hard") == "soft":
                element_result.soft_results.append(rule_result)
            else:
                element_result.hard_results.append(rule_result)
        else:
            cross_field_results.append(rule_result)

        if _is_blocking(rule, rule_result):
            hard_failure_count += 1
            for target in targets:
                if target not in failed_elements:
                    failed_elements.append(target)

    element_results_list: list[ElementValidationResult] = []
    for target_name, result in element_results.items():
        result.passed = all(item.passed is not False for item in result.hard_results)
        if not result.passed and target_name not in failed_elements:
            failed_elements.append(target_name)
        element_results_list.append(result)

    passed = hard_failure_count == 0
    aggregate_confidence = (confidence_total / confidence_count) if confidence_count else 1.0

    return ValidationResult(
        passed=passed,
        element_results=element_results_list,
        cross_field_results=cross_field_results,
        aggregate_confidence=aggregate_confidence,
        failed_elements=failed_elements,
    )


def _normalize_plan(plan: Any) -> dict[str, Any]:
    if hasattr(plan, "model_dump"):
        return plan.model_dump(mode="json")
    if isinstance(plan, dict):
        return plan
    raise TypeError(f"Unsupported plan type: {type(plan)!r}")


def _evaluate_rule(rule: dict[str, Any], context: ValidationContext) -> RuleResult:
    name = rule.get("name", "unknown_rule")
    rule_type = rule.get("rule_type", "")
    targets = list(rule.get("targets", []) or [])
    prompt_text = rule.get("prompt_text")
    parameters = rule.get("parameters", {}) or {}

    try:
        if rule_type == "required":
            target_value = _first_value(targets, context)
            passed = target_value is not None
            reason = "value present" if passed else f"missing required value for {targets[0] if targets else name}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "non_empty":
            target_value = _first_value(targets, context)
            passed = _is_non_empty(target_value)
            reason = "value is non-empty" if passed else f"value is empty for {targets[0] if targets else name}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "regex":
            target_value = _first_value(targets, context)
            pattern = parameters.get("pattern", "")
            passed = isinstance(target_value, str) and bool(re.fullmatch(pattern, target_value.strip()))
            reason = "regex matched" if passed else f"value did not match pattern {pattern}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "positive_decimal":
            target_value = _first_value(targets, context)
            value = _to_decimal(target_value)
            passed = value is not None and value > 0
            reason = "value is positive" if passed else f"value is not a positive decimal for {targets[0] if targets else name}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "max_value":
            target_value = _first_value(targets, context)
            maximum = _to_decimal(parameters.get("max"))
            value = _to_decimal(target_value)
            passed = value is not None and maximum is not None and value <= maximum
            reason = "within maximum" if passed else f"value exceeds max {parameters.get('max')}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "min_value":
            target_value = _first_value(targets, context)
            minimum = _to_decimal(parameters.get("min"))
            value = _to_decimal(target_value)
            passed = value is not None and minimum is not None and value >= minimum
            reason = "within minimum" if passed else f"value below min {parameters.get('min')}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "date_format":
            target_value = _first_value(targets, context)
            fmt = str(parameters.get("format", "DD/MM/YYYY"))
            passed = _matches_date_format(target_value, fmt)
            reason = "date format matched" if passed else f"value does not match date format {fmt}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "date_range":
            target_value = _first_value(targets, context)
            min_bound = parameters.get("min")
            max_bound = parameters.get("max")
            passed = _within_date_range(target_value, min_bound, max_bound)
            reason = "date within range" if passed else "date outside allowed range"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "equals":
            target_value = _first_value(targets, context)
            expected = parameters.get("value")
            passed = target_value == expected
            reason = "value matched" if passed else f"value did not match expected {expected!r}"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "cross_field_sum":
            fields = list(parameters.get("fields", targets))
            expected = _to_decimal(parameters.get("expected"))
            values = [_to_decimal(context.elements.get(field)) for field in fields]
            passed = expected is not None and all(value is not None for value in values) and sum(values) == expected
            reason = "field sum matched" if passed else "field sum did not match expected value"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "cross_field_equals":
            left = str(parameters.get("left", targets[0] if targets else ""))
            right = str(parameters.get("right", targets[1] if len(targets) > 1 else ""))
            passed = bool(left and right) and context.elements.get(left) == context.elements.get(right)
            reason = "fields matched" if passed else f"fields {left} and {right} differ"
            confidence = 1.0 if passed else 0.0
            return RuleResult(rule_name=name, passed=passed, reason=reason, confidence=confidence, status="evaluated")

        if rule_type == "soft_llm":
            return _evaluate_soft_rule(name, prompt_text)

        return RuleResult(
            rule_name=name,
            passed=None,
            reason=f"rule type '{rule_type}' is not implemented in the validation engine",
            confidence=None,
            status="unable_to_evaluate",
        )
    except Exception as exc:
        return RuleResult(
            rule_name=name,
            passed=False,
            reason=f"rule evaluation error: {exc}",
            confidence=None,
            status="error",
            error=str(exc),
        )


def _evaluate_soft_rule(name: str, prompt_text: str | None) -> RuleResult:
    # Soft rules are driven by playbook prompts and may be executed by an LLM-backed evaluator later.
    # For now we keep them non-blocking and record the prompt text so the plan remains the source of truth.
    if prompt_text:
        return RuleResult(
            rule_name=name,
            passed=None,
            reason=f"soft rule requires prompt-driven evaluation: {prompt_text.splitlines()[0][:120]}",
            confidence=None,
            status="unable_to_evaluate",
        )
    return RuleResult(
        rule_name=name,
        passed=None,
        reason="soft rule could not be evaluated because no prompt text was provided",
        confidence=None,
        status="unable_to_evaluate",
    )


def _is_blocking(rule: dict[str, Any], result: RuleResult) -> bool:
    if result.passed is True:
        return False
    if result.status in {"error", "evaluated"}:
        return bool(rule.get("stop_on_failure", False))
    if result.status == "unable_to_evaluate":
        return bool(rule.get("stop_on_failure", False))
    return False


def _first_value(targets: list[str], context: ValidationContext) -> Any:
    if not targets:
        return None
    return context.elements.get(targets[0])


def _is_non_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def _matches_date_format(value: Any, fmt: str) -> bool:
    if not isinstance(value, str):
        return False
    fmt_map = {
        "DD/MM/YYYY": "%d/%m/%Y",
        "YYYY-MM-DD": "%Y-%m-%d",
        "MM/DD/YYYY": "%m/%d/%Y",
    }
    python_fmt = fmt_map.get(fmt, fmt)
    try:
        datetime.strptime(value.strip(), python_fmt)
        return True
    except Exception:
        return False


def _within_date_range(value: Any, min_bound: Any, max_bound: Any) -> bool:
    parsed = _parse_date(value)
    if parsed is None:
        return False
    if min_bound == "today":
        if parsed < date.today():
            return False
    elif min_bound:
        min_date = _parse_date(min_bound)
        if min_date and parsed < min_date:
            return False
    if max_bound == "today":
        if parsed > date.today():
            return False
    elif max_bound:
        max_date = _parse_date(max_bound)
        if max_date and parsed > max_date:
            return False
    return True


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except Exception:
            continue
    return None
