from __future__ import annotations

from datetime import datetime, timezone

from papertrail.execution.catalog import (
    BusinessRuleExpressionType,
    EngineCatalogEntry,
    PromptTemplate,
    RuntimeLimits,
    SystemCatalog,
    ToolCatalogEntry,
    ValidationRuleType,
)
from papertrail.execution.plan import (
    BusinessConditionSpec,
    BusinessRulesConfig,
    BusinessTransformationSpec,
    ClassificationConfig,
    CorrectionPolicy,
    EngineBinding,
    ExecutionPlan,
    ExtractionConfig,
    ExtractionFieldSpec,
    LLMBinding,
    PostprocessConfig,
    PreflightConfig,
    PreuploadCheckSpec,
    PreuploadConfig,
    RuntimeLimits as PlanRuntimeLimits,
    ToolBinding,
    ToolCallSpec,
    ValidationConfig,
    ValidationRuleSpec,
)


def test_system_catalog_and_execution_plan_can_be_constructed() -> None:
    catalog = SystemCatalog(
        version="v2",
        compiled_at=datetime.now(timezone.utc),
        node_types=["preflight", "classify"],
        engines=[
            EngineCatalogEntry(
                name="layout-docling",
                type="layout",
                implementation="papertrail.engines.layout.docling:DoclingLayoutEngine",
            )
        ],
        validation_rule_types=[
            ValidationRuleType(name="required"),
        ],
        business_rule_expression_types=[
            BusinessRuleExpressionType(name="expression"),
        ],
        tools=[
            ToolCatalogEntry(
                name="ifsc_lookup",
                implementation="papertrail.tools.ifsc:IFSCLookupTool",
            )
        ],
        prompt_templates=[PromptTemplate(name="classify")],
        supported_mimes=["application/pdf"],
        runtime_limits=RuntimeLimits(max_file_size_bytes=10_000_000),
    )

    plan = ExecutionPlan(
        plan_id="run_123",
        project_slug="indian_financial",
        playbook_slug="indian_cheque",
        document_type="cheque",
        compiled_at=datetime.now(timezone.utc),
        compiler_version="0.1.0",
        preflight=PreflightConfig(
            allowed_mimes=["application/pdf"],
            max_file_size_bytes=10_000_000,
        ),
        preupload=PreuploadConfig(
            checks=[PreuploadCheckSpec(check_type="page_count", parameters={"max": 2})],
        ),
        classification=ClassificationConfig(
            classifier_model="gpt-4.1-mini",
            confidence_threshold=0.8,
            candidate_labels=["indian_cheque"],
            prompt_text="Classify the document.",
        ),
        extraction=ExtractionConfig(
            schema=[
                ExtractionFieldSpec(name="amount_figures", field_type="decimal", critical=True),
            ],
            primary_engine="layout-docling",
            fallback_engine=None,
            prompt_text="Extract the fields.",
        ),
        validation=ValidationConfig(
            rules=[
                ValidationRuleSpec(
                    name="amount_required",
                    rule_type="required",
                    targets=["amount_figures"],
                    stop_on_failure=True,
                )
            ],
        ),
        correction=CorrectionPolicy(
            max_retries=3,
            prompt_text="Try again using the validation failures.",
        ),
        business_rules=BusinessRulesConfig(
            conditions=[
                BusinessConditionSpec(
                    name="approve_if_valid",
                    expression_type="expression",
                    expression="validation.passed == true",
                    action="approve",
                )
            ],
            transformations=[
                BusinessTransformationSpec(
                    name="attach_reason",
                    output_binding="decision.reason",
                    expression_type="expression",
                    expression='"ok"',
                )
            ],
        ),
        postprocess=PostprocessConfig(
            output_format="json",
            fields_to_include=["amount_figures"],
            success_tool_calls=[ToolCallSpec(name="ifsc_lookup")],
        ),
        engine_routing={
            "layout": EngineBinding(
                name="layout-docling",
                type="layout",
                implementation="papertrail.engines.layout.docling:DoclingLayoutEngine",
            )
        },
        llm_routing={
            "classify": LLMBinding(
                stage="classify",
                provider="openai",
                model="gpt-4.1-mini",
            )
        },
        tools={
            "ifsc_lookup": ToolBinding(
                name="ifsc_lookup",
                implementation="papertrail.tools.ifsc:IFSCLookupTool",
            )
        },
        limits=PlanRuntimeLimits(
            max_correction_iterations=3,
            stage_timeout_seconds=600,
            overall_run_timeout_seconds=3600,
        ),
        prompts={"classify": "Classify the document."},
    )

    assert catalog.engine_names() == {"layout-docling"}
    assert plan.project_slug == "indian_financial"
    assert plan.preflight.allowed_mimes == ["application/pdf"]
    assert plan.validation.rules[0].rule_type == "required"
