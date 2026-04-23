from __future__ import annotations

from datetime import date

from papertrail.execution.compiler import compile
from papertrail.validation import validate_execution_plan


def test_validation_engine_enforces_hard_rules_for_indian_cheque() -> None:
    plan = compile("indian_financial", "indian_cheque", "run_validation_001")

    extracted_elements = [
        {"name": "payee_name", "value": "Test User"},
        {"name": "amount_figures", "value": "123.45"},
        {"name": "amount_words", "value": "One Hundred Twenty Three Rupees Only"},
        {"name": "date", "value": "20/04/2026"},
        {"name": "ifsc_code", "value": "ABCD0123456"},
        {"name": "has_signature", "value": True},
    ]

    result = validate_execution_plan(plan.model_dump(mode="json"), extracted_elements)

    assert result.passed is True
    assert result.failed_elements == []
    assert result.aggregate_confidence > 0.0


def test_validation_engine_reports_missing_required_fields() -> None:
    plan = compile("indian_financial", "indian_cheque", "run_validation_002")

    extracted_elements = [
        {"name": "payee_name", "value": ""},
        {"name": "amount_figures", "value": None},
        {"name": "amount_words", "value": None},
        {"name": "date", "value": None},
        {"name": "ifsc_code", "value": None},
        {"name": "has_signature", "value": None},
    ]

    result = validate_execution_plan(plan.model_dump(mode="json"), extracted_elements)

    assert result.passed is False
    assert "payee_name" in result.failed_elements
    assert "amount_figures" in result.failed_elements
    assert "date" in result.failed_elements


def test_validation_engine_enforces_max_value_rule_from_playbook_config() -> None:
    plan = compile("indian_financial", "indian_cheque", "run_validation_003")

    extracted_elements = [
        {"name": "payee_name", "value": "Test User"},
        {"name": "amount_figures", "value": "100001"},
        {"name": "amount_words", "value": "One Hundred Thousand One Rupees Only"},
        {"name": "date", "value": "20/04/2026"},
        {"name": "ifsc_code", "value": "ABCD0123456"},
        {"name": "has_signature", "value": True},
    ]

    result = validate_execution_plan(plan.model_dump(mode="json"), extracted_elements)

    assert result.passed is False
    assert "amount_figures" in result.failed_elements


def test_validation_engine_blocks_on_non_evaluable_rule_when_stop_on_failure_enabled() -> None:
    plan = {
        "validation": {
            "rules": [
                {
                    "name": "unknown_rule",
                    "rule_type": "not_implemented_here",
                    "targets": ["field_a"],
                    "execution_mode": "hard",
                    "severity": "error",
                    "stop_on_failure": True,
                }
            ]
        }
    }

    result = validate_execution_plan(plan, [{"name": "field_a", "value": "x"}])

    assert result.passed is False
    assert "field_a" in result.failed_elements


def test_validation_engine_does_not_penalize_confidence_for_unevaluated_soft_rules() -> None:
    plan = {
        "validation": {
            "rules": [
                {
                    "name": "field_required",
                    "rule_type": "required",
                    "targets": ["field_a"],
                    "execution_mode": "hard",
                    "severity": "error",
                    "stop_on_failure": True,
                },
                {
                    "name": "field_soft",
                    "rule_type": "soft_llm",
                    "targets": ["field_a"],
                    "execution_mode": "soft",
                    "severity": "warning",
                    "stop_on_failure": False,
                    "prompt_text": "Check whether this looks plausible.",
                },
            ]
        }
    }

    result = validate_execution_plan(plan, [{"name": "field_a", "value": "x"}])

    assert result.passed is True
    assert result.aggregate_confidence == 1.0


def test_validation_engine_supports_date_range_min_today() -> None:
    today = date.today().strftime("%d/%m/%Y")
    plan = {
        "validation": {
            "rules": [
                {
                    "name": "date_today_or_future",
                    "rule_type": "date_range",
                    "targets": ["date_field"],
                    "parameters": {"min": "today"},
                    "execution_mode": "hard",
                    "severity": "error",
                    "stop_on_failure": True,
                }
            ]
        }
    }

    result = validate_execution_plan(plan, [{"name": "date_field", "value": today}])

    assert result.passed is True
    assert result.failed_elements == []
