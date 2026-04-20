"""Extraction-related Pydantic models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Region(BaseModel):
    """A region identified during layout analysis."""

    id: str
    type: str  # text, table, image, signature, stamp
    page: int
    bbox: list[float] = Field(description="[x0, y0, x1, y1] normalized coordinates")
    confidence: float = 1.0
    label: str | None = None


class LayoutResult(BaseModel):
    """Output of Pass A layout analysis."""

    pages: int
    regions: list[Region]
    confidence: float
    raw_output: dict | None = None


class TextResult(BaseModel):
    """Output from a text extraction engine."""

    text: str
    confidence: float
    region_id: str | None = None
    engine: str = ""


class OCRResult(BaseModel):
    """Output from an OCR engine."""

    text: str
    confidence: float
    region_id: str | None = None
    engine: str = ""
    word_confidences: list[float] = Field(default_factory=list)


class VisionResult(BaseModel):
    """Output from a vision LLM engine."""

    data: dict
    confidence: float
    model: str = ""


class RegionExtractionResult(BaseModel):
    """Combined extraction result for a single region."""

    region_id: str
    text: str
    confidence: float
    engine_used: str
    fallback_used: bool = False
    fallback_text: str | None = None


class RawExtractionResult(BaseModel):
    """Output of Pass B — raw extraction across all regions."""

    regions: list[RegionExtractionResult]
    full_page_ocr: str | None = None
    full_page_ocr_confidence: float | None = None


class ExtractedElement(BaseModel):
    """A single extracted and typed field."""

    name: str
    value: object = None
    llm_confidence: float = 0.0
    ocr_confidence: float = 0.0
    source_region: str | None = None
    notes: str | None = None
    critical: bool = False


class SchemaExtractionResult(BaseModel):
    """Output of Pass C — structured extraction."""

    elements: list[ExtractedElement]
    model_used: str = ""
    attempt_number: int = 0
