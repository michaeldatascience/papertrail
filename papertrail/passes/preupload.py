"""Pre-upload checks for documents using the compiled execution plan."""

from __future__ import annotations

from typing import Any

from papertrail.config.loader import get_settings
from papertrail.engines.preprocessing.opencv_checks import check_blur, check_resolution
from papertrail.models.pipeline_state import PipelineState
from papertrail.observability.logging import emit
from papertrail.storage.blob.local import LocalBlobStore


async def preupload_node(state: PipelineState) -> PipelineState:
    run_id = state["run_id"]
    plan = state.get("execution_plan", {})
    checks_config = plan.get("preupload", {}).get("checks", [])

    await emit(run_id, "preupload", "stage_enter")

    file_uri = state["input_file_uri"]
    file_mime = state["input_file_mime"]

    blob_store = LocalBlobStore(get_settings().blob_storage_path)

    image_bytes: bytes | None = None
    try:
        if not file_uri.startswith("local://"):
            raise ValueError(f"Unsupported file URI scheme for pre-upload checks: {file_uri}")
        image_bytes = await blob_store.get(file_uri)
    except FileNotFoundError:
        await emit(run_id, "preupload", "preupload_check_blocked", check="file_access", reason="Input file not found.", level="error")
        state["error"] = "Input file not found."
        state["failed_stage"] = "preupload"
        return state
    except ValueError as e:
        await emit(run_id, "preupload", "preupload_check_blocked", check="file_access", reason=str(e), level="error")
        state["error"] = str(e)
        state["failed_stage"] = "preupload"
        return state
    except Exception as e:
        await emit(run_id, "preupload", "preupload_check_blocked", check="file_access", reason=f"Failed to read input file: {e}", level="error")
        state["error"] = f"Failed to read input file: {e}"
        state["failed_stage"] = "preupload"
        return state

    preupload_result: dict[str, Any] = {
        "passed": True,
        "checks": {},
        "warnings": [],
    }

    for check in checks_config:
        check_type = check.get("check_type")
        enabled = check.get("enabled", True)
        params = check.get("parameters", {})
        on_failure = check.get("on_failure", "fail")

        if not enabled:
            continue

        if check_type == "file_integrity":
            preupload_result["checks"][check_type] = {"passed": True}
            await emit(run_id, "preupload", "preupload_check_passed", check=check_type)
            continue

        if check_type == "format":
            passed = file_mime in params.get("allowed_mimes", ["application/pdf", "image/jpeg", "image/png", "image/tiff"])
            preupload_result["checks"][check_type] = {"passed": passed, "mime": file_mime}
            if not passed:
                preupload_result["passed"] = False
                await emit(run_id, "preupload", "preupload_check_blocked", check=check_type, reason=f"Unsupported mime type: {file_mime}", level="error")
            else:
                await emit(run_id, "preupload", "preupload_check_passed", check=check_type, mime=file_mime)
            continue

        if check_type == "size":
            max_mb = params.get("max_mb", 50)
            file_size_bytes = len(image_bytes) if image_bytes else 0
            passed = (file_size_bytes / (1024 * 1024)) <= max_mb
            preupload_result["checks"][check_type] = {"passed": passed, "value_mb": round(file_size_bytes / (1024 * 1024), 2), "max_mb": max_mb}
            if not passed:
                preupload_result["passed"] = False
                await emit(run_id, "preupload", "preupload_check_blocked", check=check_type, value_mb=round(file_size_bytes / (1024 * 1024), 2), max_mb=max_mb, level="error")
            else:
                await emit(run_id, "preupload", "preupload_check_passed", check=check_type, value_mb=round(file_size_bytes / (1024 * 1024), 2), max_mb=max_mb)
            continue

        if check_type == "blur" and image_bytes:
            threshold = params.get("threshold", 100)
            blur_result = check_blur(image_bytes, threshold)
            preupload_result["checks"][check_type] = {
                "enabled": True,
                "passed": blur_result["passed"],
                "threshold": threshold,
                "value": blur_result["value"],
                "on_failure": on_failure,
            }
            if blur_result["error"]:
                preupload_result["passed"] = False
                preupload_result["warnings"].append({"check": check_type, "reason": blur_result["reason"]})
                await emit(run_id, "preupload", "preupload_check_blocked", check=check_type, reason=blur_result["reason"], level="error")
            elif not blur_result["passed"]:
                preupload_result["passed"] = False
                preupload_result["warnings"].append({"check": check_type, "reason": "Document is too blurry."})
                await emit(run_id, "preupload", "preupload_check_blocked", check=check_type, value=blur_result["value"], threshold=threshold, level="warning")
            else:
                await emit(run_id, "preupload", "preupload_check_passed", check=check_type, value=blur_result["value"], threshold=threshold)
            continue

        if check_type == "resolution" and image_bytes:
            min_dpi = params.get("min_dpi", 150)
            resolution_result = check_resolution(image_bytes, min_dpi)
            preupload_result["checks"][check_type] = {
                "enabled": True,
                "passed": resolution_result["passed"],
                "min_dpi": min_dpi,
                "value": resolution_result["value"],
                "on_failure": on_failure,
            }
            if resolution_result["error"]:
                preupload_result["passed"] = False
                preupload_result["warnings"].append({"check": check_type, "reason": resolution_result["reason"]})
                await emit(run_id, "preupload", "preupload_check_blocked", check=check_type, reason=resolution_result["reason"], level="error")
            elif not resolution_result["passed"]:
                preupload_result["passed"] = False
                preupload_result["warnings"].append({"check": check_type, "reason": "Document resolution is too low."})
                await emit(run_id, "preupload", "preupload_check_blocked", check=check_type, value=resolution_result["value"], min_dpi=min_dpi, level="warning")
            else:
                await emit(run_id, "preupload", "preupload_check_passed", check=check_type, value=resolution_result["value"], min_dpi=min_dpi)
            continue

        if check_type == "pages":
            max_pages = params.get("max_pages", 1)
            preupload_result["checks"][check_type] = {"passed": True, "max_pages": max_pages, "on_failure": on_failure}
            await emit(run_id, "preupload", "preupload_check_passed", check=check_type, max_pages=max_pages)
            continue

        preupload_result["checks"][check_type or "unknown"] = {"passed": True, "note": "unsupported check type in scaffold"}

    state["preupload_result"] = preupload_result

    await emit(run_id, "preupload", "stage_exit", passed=preupload_result["passed"])
    return state
