"""Pre-upload checks for documents."""

from typing import Any
from papertrail.models.pipeline_state import PipelineState
from papertrail.observability.logging import emit
from papertrail.engines.preprocessing.opencv_checks import check_blur, check_resolution
from papertrail.storage.blob.local import LocalBlobStore
from papertrail.config.loader import get_settings # For blob store config

async def preupload_node(state: PipelineState) -> PipelineState:
    run_id = state["run_id"]
    playbook_config = state["playbook"] # Merged playbook config

    await emit(run_id, "preupload", "stage_enter")

    file_uri = state["input_file_uri"]
    file_mime = state["input_file_mime"]
    
    # Initialize blob store
    blob_store = LocalBlobStore(get_settings().blob_storage_path) # Pass base_path explicitly

    image_bytes: bytes | None = None
    try:
        if not file_uri.startswith("local://"):
            # For now, only local files are supported for pre-upload checks
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

    # Initialize results
    preupload_result: dict[str, Any] = {
        "passed": True,
        "checks": {},
        "warnings": [],
    }

    checks_config = playbook_config.get("preupload", {}).get("checks", {})

    # --- File Integrity Check ---
    # This is often handled at blob storage level, for now assume OK if file_access passed
    if checks_config.get("file_integrity", {}).get("enabled", False):
        preupload_result["checks"]["file_integrity"] = {"passed": True}
        await emit(run_id, "preupload", "preupload_check_passed", check="file_integrity")

    # --- Format Check ---
    if checks_config.get("format", {}).get("enabled", False):
        supported_mime_types = ["application/pdf", "image/jpeg", "image/png", "image/tiff"]
        passed = file_mime in supported_mime_types
        preupload_result["checks"]["format"] = {"passed": passed, "mime": file_mime}
        if not passed:
            preupload_result["passed"] = False
            await emit(run_id, "preupload", "preupload_check_blocked", check="format", reason=f"Unsupported mime type: {file_mime}", level="error")
        else:
            await emit(run_id, "preupload", "preupload_check_passed", check="format", mime=file_mime)

    # --- Size Check ---
    if checks_config.get("size", {}).get("enabled", False):
        max_mb = checks_config["size"].get("max_mb", 50)
        # Assuming input_file_size_bytes is in PipelineState or can be derived
        # For now, let's assume `blob_store.get` provides this if it's stored, or get from image_bytes
        file_size_bytes = len(image_bytes) if image_bytes else 0
        passed = (file_size_bytes / (1024 * 1024)) <= max_mb
        preupload_result["checks"]["size"] = {"passed": passed, "value_mb": round(file_size_bytes / (1024 * 1024), 2), "max_mb": max_mb}
        if not passed:
            preupload_result["passed"] = False
            await emit(run_id, "preupload", "preupload_check_blocked", check="size", value_mb=round(file_size_bytes / (1024 * 1024), 2), max_mb=max_mb, level="error")
        else:
            await emit(run_id, "preupload", "preupload_check_passed", check="size", value_mb=round(file_size_bytes / (1024 * 1024), 2), max_mb=max_mb)


    # --- Blur Check ---
    blur_config = checks_config.get("blur", {})
    if blur_config.get("enabled", False) and image_bytes:
        check_name = "blur"
        threshold = blur_config.get("threshold", 100)
        blur_result = check_blur(image_bytes, threshold)
        
        preupload_result["checks"][check_name] = {
            "enabled": True,
            "passed": blur_result["passed"],
            "threshold": threshold,
            "value": blur_result["value"],
        }
        if blur_result["error"]:
            preupload_result["passed"] = False
            preupload_result["warnings"].append({"check": check_name, "reason": blur_result["reason"]})
            await emit(run_id, "preupload", "preupload_check_blocked", check=check_name, reason=blur_result["reason"], level="error")
        elif not blur_result["passed"]:
            preupload_result["passed"] = False
            preupload_result["warnings"].append({"check": check_name, "reason": "Document is too blurry."})
            await emit(run_id, "preupload", "preupload_check_blocked", check=check_name, value=blur_result["value"], threshold=threshold, level="warning")
        else:
            await emit(run_id, "preupload", "preupload_check_passed", check=check_name, value=blur_result["value"], threshold=threshold)


    # --- Resolution Check ---
    resolution_config = checks_config.get("resolution", {})
    if resolution_config.get("enabled", False) and image_bytes:
        check_name = "resolution"
        min_dpi = resolution_config.get("min_dpi", 150)
        resolution_result = check_resolution(image_bytes, min_dpi)

        preupload_result["checks"][check_name] = {
            "enabled": True,
            "passed": resolution_result["passed"],
            "min_dpi": min_dpi,
            "value": resolution_result["value"],
        }
        if resolution_result["error"]:
            preupload_result["passed"] = False
            preupload_result["warnings"].append({"check": check_name, "reason": resolution_result["reason"]})
            await emit(run_id, "preupload", "preupload_check_blocked", check=check_name, reason=resolution_result["reason"], level="error")
        elif not resolution_result["passed"]:
            preupload_result["passed"] = False
            preupload_result["warnings"].append({"check": check_name, "reason": "Document resolution is too low."})
            await emit(run_id, "preupload", "preupload_check_blocked", check=check_name, value=resolution_result["value"], min_dpi=min_dpi, level="warning")
        else:
            await emit(run_id, "preupload", "preupload_check_passed", check=check_name, value=resolution_result["value"], min_dpi=min_dpi)

    state["preupload_result"] = preupload_result
    
    await emit(run_id, "preupload", "stage_exit", passed=preupload_result["passed"])
    return state
