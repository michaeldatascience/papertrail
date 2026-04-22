from __future__ import annotations

import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from papertrail.models.pipeline_state import PipelineState
from papertrail.observability.logging import emit
from papertrail.orchestration.graph import build_graph
from papertrail.playbooks.loader import PlaybookLoader, PlaybookValidationError
from papertrail.playbooks.repository import PlaybookRepository, PlaybookNotFoundError
from papertrail.config.loader import get_settings, load_json_config


def _generate_run_uid(playbook_slug: str, file_hash: str) -> str:
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"run_{now}_{playbook_slug}_{file_hash[:6]}"


def _compute_file_hash(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class PipelineRunner:
    """Orchestrates a full pipeline run, including pre-flight checks and error handling."""

    def __init__(self):
        self._settings = get_settings()
        self._system_config = load_json_config("system.json")
        self._graph = build_graph().compile()
        self._playbook_repository = PlaybookRepository(Path(self._settings.playbooks_path))
        self._playbook_loader = PlaybookLoader(self._playbook_repository)

    async def _run_preflight_checks(self, file_path: Path, playbook_slug: str) -> tuple[str, str, dict]:
        """
        Performs initial sanity checks before invoking the pipeline graph.
        
        Returns:
            tuple[file_hash, file_mime, loaded_playbook_dict]
        
        Raises:
            FileNotFoundError: If the input file does not exist.
            ValueError: For invalid file type, size, or playbook issues.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")

        file_hash = _compute_file_hash(file_path)
        file_mime = self._guess_mime(file_path)
        
        # 1. MIME type check
        supported_mimes = self._system_config.get("supported_mimes", [])
        if file_mime not in supported_mimes:
            raise ValueError(f"Unsupported file type: {file_mime}. Supported types are: {', '.join(supported_mimes)}")

        # 2. File size check
        max_file_size_mb = self._system_config.get("max_file_size_mb", 50) # Default to 50MB
        if file_path.stat().st_size > max_file_size_mb * 1024 * 1024:
            raise ValueError(f"File size exceeds limit: {file_path.stat().st_size / (1024 * 1024):.2f}MB. Max allowed: {max_file_size_mb}MB")

        # 3. Playbook availability check
        try:
            loaded_playbook = await self._playbook_loader.load(playbook_slug)
        except (PlaybookNotFoundError, PlaybookValidationError) as e:
            raise ValueError(f"Playbook '{playbook_slug}' validation/load failed: {e}")

        # TODO: Stub for checking engine availability (e.g., ensure vision engine configured in playbook exists)
        # TODO: Stub for checking credentials (e.g., LLM API key)

        return file_hash, file_mime, loaded_playbook

    async def run(
        self,
        file_path: str,
        playbook_slug: str,
        playbook_version: str | None = None, # Future: use for versioned playbooks from repository
        force_rerun: bool = False, # Future: Use to ignore cache/deduplication
    ) -> PipelineState:
        """Execute the pipeline for a file. Returns final state."""
        path = Path(file_path)
        run_uid: str = "" # Initialize for finally block

        # Initial state to track overall run status and errors
        final_state: PipelineState = {
            "run_id": "",
            "run_uid": "",
            "playbook_id": playbook_slug,
            "playbook": None, # Will be filled after loading
            "input_file_uri": f"local://{path.resolve()}",
            "input_file_hash": "",
            "input_file_mime": "",
            "preupload_result": None,
            "classification": None,
            "pass_a_output": None, # Should be renamed later
            "pass_b_output": None, # Should be renamed later
            "pass_c_output": None, # Should be renamed later
            "pass_d_output": None, # Should be renamed later
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
            # --- Pre-flight Checks ---
            file_hash, file_mime, loaded_playbook = await self._run_preflight_checks(path, playbook_slug)
            run_uid = _generate_run_uid(playbook_slug, file_hash)

            # --- Initialize State with loaded playbook and pre-flight data ---
            initial_state: PipelineState = {
                "run_id": run_uid,
                "run_uid": run_uid,
                "playbook_id": loaded_playbook.slug,
                "playbook": loaded_playbook.model_dump(),
                "input_file_uri": f"local://{path.resolve()}",
                "input_file_hash": file_hash,
                "input_file_mime": file_mime,
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

            # TODO: DB STUB - Create initial run record in database with status 'RUNNING'
            # For now, just emit start event
            await emit(run_uid, "orchestration", "run_started", file=file_path, playbook=playbook_slug)

            start = time.monotonic()
            final_state = await self._graph.ainvoke(initial_state)
            duration_ms = int((time.monotonic() - start) * 1000)

            # TODO: DB STUB - Update run record in database with final status and output
            await emit(
                run_uid, "orchestration", "run_completed",
                duration_ms=duration_ms,
                decision=final_state.get("decision_result", {}).get("action", "unknown"),
                error=final_state.get("error"),
            )
            return final_state

        except (FileNotFoundError, ValueError, PlaybookNotFoundError, PlaybookValidationError) as e:
            # Pre-flight or Playbook loading errors
            final_state["error"] = str(e)
            final_state["failed_stage"] = "preflight"
            if run_uid: # Only emit if run_uid was generated
                await emit(run_uid, "orchestration", "run_failed", error=str(e), stage="preflight")
            else: # If run_uid couldn't be generated (e.g., file hash failed early)
                await emit("unknown_run", "orchestration", "run_failed_pre_uid", error=str(e), file=str(path), playbook=playbook_slug)
            return final_state
        except Exception as e:
            # Catch all other unexpected errors during graph execution
            final_state["error"] = f"An unexpected error occurred: {e}"
            final_state["failed_stage"] = final_state.get("failed_stage", "unknown") # Keep existing failed_stage if set by graph, else "unknown"
            if run_uid:
                await emit(run_uid, "orchestration", "run_failed", error=str(e), stage=final_state["failed_stage"])
            else:
                 await emit("unknown_run", "orchestration", "run_failed_pre_uid", error=str(e), file=str(path), playbook=playbook_slug)
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
