"""Compile System + Project + Playbook authoring into an ExecutionPlan."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from papertrail.execution.catalog import EngineCatalogEntry, SystemCatalog, load_system_catalog
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
from papertrail.playbooks.v2_loader import V2PlaybookLoader, V2PlaybookLoadError, V2PlaybookValidationError
from papertrail.projects.loader import ProjectLoader, ProjectLoadError, ProjectValidationError


class CompilationError(Exception):
    """Base compilation error."""

    def __init__(self, message: str, path: str | None = None, field: str | None = None) -> None:
        super().__init__(message)
        self.path = path
        self.field = field


class SystemCatalogError(CompilationError):
    """Base catalog error."""


class CatalogLoadError(SystemCatalogError):
    """Raised when the system catalog cannot be loaded."""


class CatalogValidationError(SystemCatalogError):
    """Raised when the system catalog fails validation."""


class ProjectError(CompilationError):
    """Base project error."""


class ProjectReferenceError(ProjectError):
    """Raised when a project references unsupported system capabilities."""


class PlaybookError(CompilationError):
    """Base playbook error."""


class PlaybookReferenceError(PlaybookError):
    """Raised when a playbook references unsupported project/system capabilities."""


class PlanValidationError(CompilationError):
    """Raised when the final ExecutionPlan fails Pydantic validation."""


def compile(project_slug: str, playbook_slug: str, run_id: str) -> ExecutionPlan:
    catalog = load_system_catalog()
    project = ProjectLoader().load(project_slug)
    playbook = V2PlaybookLoader().load(project_slug, playbook_slug)

    _validate_project_against_catalog(project, catalog)
    _validate_playbook_against_project_and_catalog(playbook, project, catalog)

    project_dir = Path("./projects") / project_slug

    preflight = PreflightConfig(
        allowed_mimes=list(catalog.supported_mimes),
        max_file_size_bytes=catalog.runtime_limits.max_file_size_bytes,
    )

    preupload = PreuploadConfig(
        checks=[_normalize_preupload_check(item) for item in playbook.meta.preupload_checks]
    )

    classification_prompt = _resolve_prompt(
        name="classify",
        project=project,
        playbook_prompts=playbook.prompts,
        project_dir=project_dir,
        system_catalog=catalog,
    )

    extraction_prompt = _resolve_prompt(
        name="extract_schema",
        project=project,
        playbook_prompts=playbook.prompts,
        project_dir=project_dir,
        system_catalog=catalog,
    )

    correction_prompt = _resolve_prompt(
        name="correct_hint",
        project=project,
        playbook_prompts=playbook.prompts,
        project_dir=project_dir,
        system_catalog=catalog,
    )

    suggest_prompt = _resolve_prompt(
        name="suggest",
        project=project,
        playbook_prompts=playbook.prompts,
        project_dir=project_dir,
        system_catalog=catalog,
    )

    validation_default_prompt = _resolve_prompt(
        name="validate_soft_default",
        project=project,
        playbook_prompts=playbook.prompts,
        project_dir=project_dir,
        system_catalog=catalog,
    )

    plan_validation_rules: list[ValidationRuleSpec] = []
    for rule in playbook.validation_rules:
        prompt_text = None
        if rule.execution_mode == "soft":
            prompt_name = rule.prompt_template or "validate_soft_default"
            prompt_text = _resolve_prompt(
                name=prompt_name,
                project=project,
                playbook_prompts=playbook.prompts,
                project_dir=project_dir,
                system_catalog=catalog,
            )
            if prompt_name == "validate_soft_default" and not rule.prompt_template:
                prompt_text = validation_default_prompt
        plan_validation_rules.append(
            ValidationRuleSpec(
                name=rule.name,
                rule_type=rule.rule_type,
                targets=rule.targets,
                parameters=rule.parameters,
                execution_mode=rule.execution_mode,
                prompt_text=prompt_text,
                severity=rule.severity,
                stop_on_failure=(
                    rule.stop_on_failure
                    if rule.stop_on_failure is not None
                    else (rule.execution_mode == "hard" and rule.severity == "error")
                ),
                message=rule.message,
            )
        )

    prompt_map: dict[str, str] = {
        "classify": classification_prompt,
        "extract_schema": extraction_prompt,
        "correct_hint": correction_prompt,
        "suggest": suggest_prompt,
        "validate_soft_default": validation_default_prompt,
    }
    prompt_map.update(playbook.prompts)

    plan = ExecutionPlan(
        plan_id=run_id,
        project_slug=project_slug,
        playbook_slug=playbook_slug,
        document_type=playbook.meta.document_type,
        compiled_at=datetime.now(timezone.utc),
        compiler_version="0.1.0",
        preflight=preflight,
        preupload=preupload,
        classification=ClassificationConfig(
            classifier_model="gpt-4.1-mini",
            confidence_threshold=0.8,
            candidate_labels=sorted(project.classification_labels()),
            prompt_text=classification_prompt,
            low_confidence_action="hitl",
        ),
        extraction=ExtractionConfig(
            schema=[
                ExtractionFieldSpec(
                    name=field.name,
                    field_type=field.field_type,
                    critical=field.critical,
                    description=field.description,
                    source_hint=field.source_hint,
                    fragment_ref=field.fragment_ref,
                    extraction_hint=field.extraction_hint,
                )
                for field in playbook.schema
            ],
            primary_engine=_resolve_engine_name(project, playbook, "layout") or "docling",
            fallback_engine=_resolve_engine_name(project, playbook, "ocr"),
            prompt_text=extraction_prompt,
            field_hints={
                field.name: field.extraction_hint or field.description or ""
                for field in playbook.schema
                if field.extraction_hint or field.description
            },
        ),
        validation=ValidationConfig(rules=plan_validation_rules),
        correction=CorrectionPolicy(
            max_retries=catalog.runtime_limits.max_correction_iterations,
            prompt_text=correction_prompt,
            retry_on_failures=["validation_failed", "extraction_missing"],
        ),
        business_rules=BusinessRulesConfig(
            conditions=[
                BusinessConditionSpec(
                    name=condition.name,
                    expression_type=condition.expression_type,
                    expression=condition.expression,
                    action=condition.action,
                    reason=condition.reason,
                    order=condition.order,
                    enabled=condition.enabled,
                    parameters=condition.parameters,
                )
                for condition in playbook.conditions
            ],
            transformations=[
                BusinessTransformationSpec(
                    name=transform.name,
                    output_binding=transform.output_binding,
                    expression_type=transform.expression_type,
                    expression=transform.expression,
                    tool_name=transform.tool_name,
                    tool_arguments=transform.tool_arguments,
                    order=transform.order,
                    enabled=transform.enabled,
                )
                for transform in playbook.transformations
            ],
        ),
        postprocess=PostprocessConfig(
            output_format=playbook.postprocess.output_format,
            fields_to_include=playbook.postprocess.fields_to_include,
            include_trace=playbook.postprocess.include_trace,
            success_tool_calls=[ToolCallSpec(name=name) for name in playbook.postprocess.success_tool_calls],
            failure_tool_calls=[ToolCallSpec(name=name) for name in playbook.postprocess.failure_tool_calls],
        ),
        engine_routing=_resolve_engine_bindings(project, playbook, catalog),
        llm_routing=_resolve_llm_bindings(catalog),
        tools=_resolve_tool_bindings(catalog),
        limits=PlanRuntimeLimits(
            max_correction_iterations=catalog.runtime_limits.max_correction_iterations,
            stage_timeout_seconds=catalog.runtime_limits.stage_timeout_seconds,
            overall_run_timeout_seconds=catalog.runtime_limits.overall_run_timeout_seconds,
        ),
        prompts=prompt_map,
    )

    try:
        return ExecutionPlan.model_validate(plan.model_dump())
    except ValidationError as exc:
        raise PlanValidationError(
            f"Compiled plan for {project_slug}/{playbook_slug} failed validation: {exc}",
        ) from exc


def _normalize_preupload_check(check: Any) -> PreuploadCheckSpec:
    if hasattr(check, "model_dump"):
        return PreuploadCheckSpec.model_validate(check.model_dump())
    return PreuploadCheckSpec.model_validate(check)


def _validate_project_against_catalog(project: Any, catalog: SystemCatalog) -> None:
    for engine_name in [
        project.engine_defaults.layout,
        project.engine_defaults.text_extraction,
        project.engine_defaults.ocr,
        project.engine_defaults.ocr_fallback,
        project.engine_defaults.tables,
        project.engine_defaults.vision,
    ]:
        if engine_name and engine_name not in catalog.engine_names():
            raise ProjectReferenceError(f"Project '{project.slug}' references unknown engine '{engine_name}'")
    for tool_name in project.shared_tools:
        if tool_name not in catalog.tool_names():
            raise ProjectReferenceError(f"Project '{project.slug}' references unknown tool '{tool_name}'")
    for prompt_name, prompt_file in project.shared_prompts.items():
        if prompt_name not in catalog.prompt_names():
            raise ProjectReferenceError(
                f"Project '{project.slug}' references unknown prompt '{prompt_name}' mapped to '{prompt_file}'",
            )


def _validate_playbook_against_project_and_catalog(playbook: Any, project: Any, catalog: SystemCatalog) -> None:
    if playbook.meta.document_type not in project.classification_labels():
        raise PlaybookReferenceError(
            f"Playbook '{playbook.slug}' document type '{playbook.meta.document_type}' is not in project '{project.slug}' classification universe",
        )
    for slot, engine_name in playbook.meta.engine_overrides.items():
        if engine_name not in catalog.engine_names():
            raise PlaybookReferenceError(
                f"Playbook '{playbook.slug}' references unknown engine '{engine_name}' for slot '{slot}'",
            )
    for rule in playbook.validation_rules:
        if rule.rule_type not in catalog.validation_rule_type_names():
            raise PlaybookReferenceError(
                f"Playbook '{playbook.slug}' validation rule '{rule.name}' uses unknown rule type '{rule.rule_type}'",
            )
        if rule.execution_mode == "soft":
            prompt_name = rule.prompt_template or "validate_soft_default"
            if not _prompt_is_resolvable(prompt_name, playbook.prompts, project.shared_prompts, catalog):
                raise PlaybookReferenceError(
                    f"Playbook '{playbook.slug}' soft validation rule '{rule.name}' references missing prompt '{prompt_name}'",
                )
    for condition in playbook.conditions:
        if condition.expression_type not in catalog.expression_type_names():
            raise PlaybookReferenceError(
                f"Playbook '{playbook.slug}' condition '{condition.name}' uses unknown expression type '{condition.expression_type}'",
            )
    for transform in playbook.transformations:
        if transform.expression_type and transform.expression_type not in catalog.expression_type_names():
            raise PlaybookReferenceError(
                f"Playbook '{playbook.slug}' transformation '{transform.name}' uses unknown expression type '{transform.expression_type}'",
            )
        if transform.tool_name and transform.tool_name not in catalog.tool_names():
            raise PlaybookReferenceError(
                f"Playbook '{playbook.slug}' transformation '{transform.name}' references unknown tool '{transform.tool_name}'",
            )


def _resolve_engine_name(project: Any, playbook: Any, slot: str) -> str | None:
    return playbook.meta.engine_overrides.get(slot) or getattr(project.engine_defaults, slot)


def _resolve_engine_bindings(project: Any, playbook: Any, catalog: SystemCatalog) -> dict[str, EngineBinding]:
    bindings: dict[str, EngineBinding] = {}
    for slot in ["layout", "text_extraction", "ocr", "ocr_fallback", "tables", "vision"]:
        engine_name = _resolve_engine_name(project, playbook, slot)
        if not engine_name:
            continue
        engine = _engine_entry_by_name(catalog, engine_name)
        bindings[slot] = EngineBinding(
            name=engine.name,
            type=engine.type,
            implementation=engine.implementation,
            config=engine.config,
        )
    return bindings


def _resolve_llm_bindings(catalog: SystemCatalog) -> dict[str, LLMBinding]:
    llm_path = Path("./config/llm.json")
    with llm_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    bindings: dict[str, LLMBinding] = {}
    for stage, cfg in raw.get("stages", {}).items():
        bindings[stage] = LLMBinding(
            stage=stage,
            provider="openrouter",
            model=cfg["primary"],
            parameters={k: v for k, v in cfg.items() if k not in {"primary", "fallback"}},
        )
    return bindings


def _resolve_tool_bindings(catalog: SystemCatalog) -> dict[str, ToolBinding]:
    bindings: dict[str, ToolBinding] = {}
    for tool in catalog.tools:
        bindings[tool.name] = ToolBinding(
            name=tool.name,
            implementation=tool.implementation,
            input_schema=tool.input_schema,
            output_schema=tool.output_schema,
            config=tool.config,
        )
    return bindings


def _engine_entry_by_name(catalog: SystemCatalog, name: str) -> EngineCatalogEntry:
    for entry in catalog.engines:
        if entry.name == name:
            return entry
    raise CatalogValidationError(f"Engine '{name}' was not found in the system catalog")


def _prompt_is_resolvable(
    name: str,
    playbook_prompts: dict[str, str],
    project_prompts: dict[str, str],
    system_catalog: SystemCatalog,
) -> bool:
    if name in playbook_prompts or (name.endswith(".txt") and name[:-4] in playbook_prompts):
        return True
    if name in project_prompts:
        return True
    if name in system_catalog.prompt_names():
        return True
    if name.endswith(".txt") and name[:-4] in system_catalog.prompt_names():
        return True
    return False


def _resolve_prompt(
    name: str,
    project: Any,
    playbook_prompts: dict[str, str],
    project_dir: Path,
    system_catalog: SystemCatalog,
) -> str:
    if name in playbook_prompts:
        return playbook_prompts[name]
    if name.endswith(".txt") and name[:-4] in playbook_prompts:
        return playbook_prompts[name[:-4]]

    project_prompt_file = project.shared_prompts.get(name)
    if project_prompt_file:
        project_prompt_path = project_dir / "prompts" / project_prompt_file
        if project_prompt_path.is_file():
            return project_prompt_path.read_text(encoding="utf-8")
        raise ProjectReferenceError(
            f"Project '{project.slug}' references missing prompt file '{project_prompt_file}' for prompt '{name}'",
        )

    system_prompt_path = Path("./config/prompts") / f"{name}.txt"
    if system_prompt_path.is_file():
        return system_prompt_path.read_text(encoding="utf-8")
    if name.endswith(".txt"):
        alt_system_prompt_path = Path("./config/prompts") / name
        if alt_system_prompt_path.is_file():
            return alt_system_prompt_path.read_text(encoding="utf-8")

    if name in system_catalog.prompt_names():
        raise CatalogValidationError(f"Prompt '{name}' is listed in catalog but no file was found")

    raise PlaybookReferenceError(
        f"Unable to resolve prompt '{name}' from playbook, project, or system tiers",
    )
