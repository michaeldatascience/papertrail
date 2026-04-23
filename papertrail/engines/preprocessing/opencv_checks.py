"""Image preprocessing checks used by preupload."""

from __future__ import annotations

import io
from typing import Any

try:
    import cv2
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - environment fallback
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]


def check_blur(image_bytes: bytes, threshold: int = 100) -> dict[str, Any]:
    """Checks if an image is blurry using Laplacian variance."""
    if cv2 is None or np is None:
        return {
            "passed": True,
            "value": 0,
            "threshold": threshold,
            "error": False,
            "reason": "OpenCV unavailable; blur check skipped.",
        }

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"passed": False, "value": 0, "reason": "Could not decode image for blur check.", "error": True}

        laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
        passed = laplacian_var >= threshold
        return {"passed": passed, "value": laplacian_var, "threshold": threshold, "error": False}
    except Exception as e:
        return {"passed": False, "value": 0, "reason": f"Error during blur check: {e}", "error": True}


def check_resolution(image_bytes: bytes, min_dpi: int = 150) -> dict[str, Any]:
    """Checks the resolution (DPI) of an image."""
    try:
        from PIL import Image  # type: ignore
    except ModuleNotFoundError:
        return {
            "passed": True,
            "value": 0,
            "min_dpi": min_dpi,
            "error": False,
            "reason": "Pillow unavailable; resolution check skipped.",
        }

    try:
        img = Image.open(io.BytesIO(image_bytes))
        horizontal_dpi, vertical_dpi = img.info.get("dpi", (0, 0))
        actual_dpi = min(horizontal_dpi, vertical_dpi) if horizontal_dpi and vertical_dpi else 0
        passed = actual_dpi >= min_dpi
        return {"passed": passed, "value": actual_dpi, "min_dpi": min_dpi, "error": False}
    except Exception as e:
        return {"passed": False, "value": 0, "reason": f"Error during resolution check: {e}", "error": True}
