"""Engine protocols — interfaces for all extraction engines."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from papertrail.models.extraction import (
    LayoutResult,
    OCRResult,
    Region,
    TextResult,
    VisionResult,
)


@runtime_checkable
class LayoutEngine(Protocol):
    async def analyze(self, file_uri: str, options: dict) -> LayoutResult: ...


@runtime_checkable
class TextExtractionEngine(Protocol):
    async def extract(self, file_uri: str, region: Region | None = None) -> TextResult: ...


@runtime_checkable
class OCREngine(Protocol):
    async def ocr(self, image_bytes: bytes, region: Region | None = None) -> OCRResult: ...


@runtime_checkable
class VisionEngine(Protocol):
    async def extract_with_vision(
        self, file_uri: str, schema: dict, prompt: str
    ) -> VisionResult: ...
