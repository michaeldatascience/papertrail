from __future__ import annotations

from papertrail.execution.compiler import compile


def test_compile_builds_execution_plan_for_indian_cheque() -> None:
    plan = compile("indian_financial", "indian_cheque", "run_test_001")

    assert plan.project_slug == "indian_financial"
    assert plan.playbook_slug == "indian_cheque"
    assert plan.document_type == "indian_cheque"
    assert plan.classification.candidate_labels == [
        "indian_bank_statement",
        "indian_cheque",
        "indian_itr_form",
        "indian_salary_slip",
    ]
    assert "classify" in plan.prompts
    assert "extract_schema" in plan.prompts
    assert plan.validation.rules[0].name == "payee_name_required"
    assert plan.validation.rules[0].stop_on_failure is True
    assert "vision" in plan.engine_routing
