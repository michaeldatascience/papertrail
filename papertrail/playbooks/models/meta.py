"""
Meta configuration for playbooks.

This module defines:
1. PlaybookEngineConfig - Which engine to use for each stage
2. MetaConfig - Metadata about the document type
3. META_DEFAULTS - Default values from _base playbook
4. load_meta() - Merge defaults with playbook-specific config

Design Notes:
- Engines can be SELECTED, not CONFIGURED
- System defines what engines are, playbook just says which to use
- All fields are optional to allow flexible overrides
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from papertrail.playbooks.models.base import PlaybookValidationCheck, merge_dicts_recursive


class PlaybookEngineConfig(BaseModel):
    """
    Engine selection for document processing stages.
    
    This specifies WHICH engines to use, not HOW to configure them.
    Engine configuration (parameters, settings) is system-level only.
    
    Fields:
        layout: Engine for document layout extraction (e.g., "docling")
        text_extraction: Engine for text extraction (e.g., "pypdf")
        ocr: Primary OCR engine (e.g., "paddleocr")
        ocr_fallback: Fallback OCR engine (e.g., "tesseract")
        tables: Table extraction engine (e.g., "camelot")
        vision: Vision/image analysis engine (e.g., "openai")
        always_fallback: Whether to always use fallback (flag)
    """
    layout: Optional[str] = None
    text_extraction: Optional[str] = None
    ocr: Optional[str] = None
    ocr_fallback: Optional[str] = None
    tables: Optional[str] = None
    vision: Optional[str] = None
    always_fallback: Optional[bool] = None
    
    model_config = {
        "frozen": True,  # Immutable after creation
        "extra": "forbid",  # Strict - no unknown fields
    }


class MetaConfig(BaseModel):
    """
    Metadata and top-level configuration for a document type.
    
    This section defines:
    - What document type this playbook handles
    - Which engines to use for processing
    - Document-specific pre-upload checks (blur, DPI, pages, etc.)
    
    Fields:
        document_type: Type identifier (e.g., "cheque", "invoice")
        display_name: Human-readable name
        description: What this document type is
        engines: Engine selection for processing stages
        preupload: Document-specific pre-checks (configurable via playbook)
    """
    document_type: str = Field(..., description="Document type identifier")
    display_name: str = Field(..., description="Human-readable name")
    description: Optional[str] = None
    engines: Optional[PlaybookEngineConfig] = None
    preupload: Optional[Dict[str, Dict[str, PlaybookValidationCheck]]] = None
    
    model_config = {
        "frozen": True,  # Immutable after creation
        "extra": "forbid",  # Strict - no unknown fields
    }


# ============================================================================
# Loader function
# ============================================================================

def load_meta(base_config: Dict[str, Any], raw_dict: Optional[Dict[str, Any]] = None) -> MetaConfig:
    """
    Load and merge meta configuration.
    
    Strategy:
    1. Start with base_config (from _base/meta.json)
    2. Apply overrides from raw_dict (if provided)
    3. Validate with MetaConfig model
    4. Return frozen instance
    
    Args:
        base_config: Base configuration dictionary, typically from _base/meta.json
        raw_dict: Raw meta config from playbook JSON (optional)
        
    Returns:
        Validated and frozen MetaConfig instance
        
    Raises:
        ValidationError: If merged config doesn't match MetaConfig schema
    """
    # Step 1: Convert defaults to dict for merging
    merged_dict = base_config.copy()
    
    # Step 2: Apply overrides if provided
    if raw_dict:
        merged_dict = merge_dicts_recursive(merged_dict, raw_dict)
    
    # Step 3: Validate and create frozen instance
    merged_config = MetaConfig(**merged_dict)
    
    return merged_config
