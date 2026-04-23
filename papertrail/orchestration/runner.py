from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from papertrail.execution import compile as compile_execution_plan
from papertrail.execution.catalog import load_system_catalog
from papertrail.models.pipeline_state import PipelineState
from papertrail.observability.logging import emit
from papertrail.orchestration.graph import build_graph


DEFAULT_PROJECT_SLUG = "indian_financial"


def _generate_run_uid(project_slug: str, playbook_slug: str, file_hash: str) -> str:
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"run_{now}_{project_slug}_{playbook_slug}_{file_hash[:6]}"


def _compute_file_hash(file_path: Path) -> str:
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class PipelineRunner:
    """Orchestrates a full pipeline run using a compiled ExecutionPlan."""

    def __init__(self) -> None:
        self._graph = build_graph().compile()
        self._system_catalog = load_system_catalog()

    async def _run_preflight_checks(self, file_path: Path) -> tuple[str, str]:
        """Perform file-only preflight checks before compilation."""
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        file_hash = _compute_file_hash(file_path)
        file_mime = self._guess_mime(file_path)

        if file_mime not in self._system_catalog.supported_mimes:
            raise ValueError(
                f"Unsupported file type: {file_mime}. Supported types are: {', '.join(self._system_catalog.supported_mimes)}"
            )

        max_file_size_bytes = self._system_catalog.runtime_limits.max_file_size_bytes
        if max_file_size_bytes is not None and file_path.stat().st_size > max_file_size_bytes:
            raise ValueError(
                f"File size exceeds limit: {file_path.stat().st_size / (1024 * 1024):.2f}MB. Max allowed: {max_file_size_bytes / (1024 * 1024):.2f}MB"
            )

        return file_hash, file_mime

    async def run(
        self,
        file_path: str,
        playbook_slug: str,
        project_slug: str = DEFAULT_PROJECT_SLUG,
        playbook_version: str | None = None,
        force_rerun: bool = False,
    ) -> PipelineState:
        """Execute the pipeline for a file and return the final state."""
        path = Path(file_path)
        run_uid = ""

        final_state: PipelineState = {
            "run_id": "",
            "run_uid": "",
            "project_id": project_slug,
            "playbook_id": playbook_slug,
            "execution_plan": None,
            "playbook": None,
            "input_file_uri": f"local://{path.resolve()}",
            "input_file_hash": "",
            "input_file_mime": "",
            "preupload_result": None,
            "classification": None,
            "layout_output": None,
            "text_output": None,
            "extraction_output": None,
            "validation_result": None,
            "postprocess_result": None,
            "correction_attempts": 0,
            "correction_history": [],
            "decision_result": None,
            "awaiting_hitl": False,
            "hitl_checkpoint_type": None,
            "hitl_context": None,
            "confidence_budget": 1.0,
            "warnings": [],
            "error": None,
            "failed_stage": None,
        }

        try:
            file_hash, file_mime = await self._run_preflight_checks(path)
            run_uid = _generate_run_uid(project_slug, playbook_slug, file_hash)

            run_dir = Path("data/runs") / run_uid
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "intermediate").mkdir(parents=True, exist_ok=True)

            plan = compile_execution_plan(project_slug, playbook_slug, run_uid)
            (run_dir / "plan.json").write_text(json.dumps(plan.model_dump(mode="json"), indent=2, default=str), encoding="utf-8")

            initial_state: PipelineState = {
                "run_id": run_uid,
                "run_uid": run_uid,
                "project_id": project_slug,
                "playbook_id": playbook_slug,
                "execution_plan": plan.model_dump(mode="json"),
                "playbook": {"project_slug": project_slug, "slug": playbook_slug},
                "input_file_uri": f"local://{path.resolve()}",
                "input_file_hash": file_hash,
                "input_file_mime": file_mime,
                "preupload_result": None,
                "classification": None,
                "layout_output": None,
                "text_output": None,
                "extraction_output": None,
                "validation_result": None,
                "postprocess_result": None,
                "correction_attempts": 0,
                "correction_history": [],
                "decision_result": None,
                "awaiting_hitl": False,
                "hitl_checkpoint_type": None,
                "hitl_context": None,
                "confidence_budget": 1.0,
                "warnings": [],
                "error": None,
                "failed_stage": None,
            }

            await emit(run_uid, "orchestration", "run_started", file=file_path, project=project_slug, playbook=playbook_slug)

            start = time.monotonic()
            final_state = await self._graph.ainvoke(initial_state)
            duration_ms = int((time.monotonic() - start) * 1000)

            (run_dir / "state.json").write_text(json.dumps(dict(final_state), indent=2, default=str), encoding="utf-8")

            decision_result = final_state.get("decision_result") or {}
            await emit(
                run_uid,
                "orchestration",
                "run_completed",
                duration_ms=duration_ms,
                decision=decision_result.get("action", "unknown"),
                error=final_state.get("error"),
            )
            return final_state

        except (FileNotFoundError, ValueError) as e:
            final_state["error"] = str(e)
            final_state["failed_stage"] = "preflight"
            if run_uid:
                await emit(run_uid, "orchestration", "run_failed", error=str(e), stage="preflight")
            else:
                await emit("unknown_run", "orchestration", "run_failed_pre_uid", error=str(e), file=str(path), playbook=playbook_slug)
            return final_state
        except Exception as e:
            final_state["error"] = f"An unexpected error occurred: {e}"
            final_state["failed_stage"] = final_state.get("failed_stage") or "unknown"
            if run_uid:
                await emit(run_uid, "orchestration", "run_failed", error=str(e), failed_stage=final_state["failed_stage"])
            else:
                await emit("unknown_run", "orchestration", "run_failed_pre_uid", error=str(e), file=str(path), playbook=playbook_slug)
            return final_state

    async def resume(self, run_id: str, hitl_resolution: dict) -> PipelineState:
        raise NotImplementedError("HITL resume not yet implemented")

    async def cancel(self, run_id: str) -> None:
        raise NotImplementedError("Run cancellation not yet implemented")

    @staticmethod
    def _guess_mime(path: Path) -> str:
        suffix = path.suffix.lower()
        return {
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".tiff": "image/tiff",
            ".tif": "image/tiff",
        }.get(suffix, "application/octet-stream")
