"""Top-level pipeline runner."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime
from pathlib import Path

from papertrail.models.pipeline_state import PipelineState
from papertrail.observability.logging import emit
from papertrail.orchestration.graph import build_graph


def _generate_run_uid(playbook_slug: str, file_hash: str) -> str:
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"run_{now}_{playbook_slug}_{file_hash[:6]}"


def _compute_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class PipelineRunner:
    """Orchestrates a full pipeline run."""

    def __init__(self):
        self._graph = build_graph().compile()

    async def run(
        self,
        file_path: str,
        playbook_slug: str,
        playbook_version: str | None = None,
        force_rerun: bool = False,
    ) -> PipelineState:
        """Execute the pipeline for a file. Returns final state."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_hash = _compute_file_hash(file_path)
        run_uid = _generate_run_uid(playbook_slug, file_hash)

        # Initialize state
        initial_state: PipelineState = {
            "run_id": run_uid,  # Using run_uid as run_id for stub
            "run_uid": run_uid,
            "playbook_id": "",
            "playbook": {
                "meta": {"document_type": playbook_slug},
                "classify": {"hitl_threshold": 0.6},
                "validate": {"correction": {"max_attempts": 3}},
            },
            "input_file_uri": str(path.resolve()),
            "input_file_hash": file_hash,
            "input_file_mime": self._guess_mime(path),
            "preupload_result": None,
            "classification": None,
            "pass_a_output": None,
            "pass_b_output": None,
            "pass_c_output": None,
            "pass_d_output": None,
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

        await emit(run_uid, "orchestration", "run_started", file=file_path, playbook=playbook_slug)

        start = time.monotonic()
        final_state = await self._graph.ainvoke(initial_state)
        duration_ms = int((time.monotonic() - start) * 1000)

        await emit(
            run_uid, "orchestration", "run_completed",
            duration_ms=duration_ms,
            decision=final_state.get("decision_result", {}).get("action", "unknown"),
        )

        return final_state

    async def resume(self, run_id: str, hitl_resolution: dict) -> PipelineState:
        """Resume a paused run after HITL resolution."""
        # TODO: Load state from PostgresSaver and resume
        raise NotImplementedError("HITL resume not yet implemented")

    async def cancel(self, run_id: str) -> None:
        """Cancel a running or paused run."""
        # TODO: Implement cancellation
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
