"""
Merged playbook model.

This module defines:
1. MergedPlaybook - The complete playbook after merging with _base
2. Helper to create MergedPlaybook from sections

Design Note:
- No aliases, no hacks - clean composition
- All sections are loaded via their respective loaders
- Frozen after creation
- This is what orchestration works with
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from papertrail.playbooks.models.meta import MetaConfig
from papertrail.playbooks.models.classify import ClassifyConfig
from papertrail.playbooks.models.schema import SchemaConfig
from papertrail.playbooks.models.validate import ValidateConfig
from papertrail.playbooks.models.rules import RulesConfig
from papertrail.playbooks.models.postprocess import PostprocessConfig


class MergedPlaybook(BaseModel):
    """
    Complete playbook after merging with _base.
    
    This is what the orchestration engine works with.
    It contains all sections fully merged and validated.
    
    Fields:
        slug: Playbook identifier (e.g., "indian_cheque")
        version: Playbook version
        extends_slug: Which base it extends from
        is_base: Whether this is the base playbook
        meta: Metadata and engine config
        classify: Classification config
        schema: Schema extraction config
        validate: Validation config
        rules: Business rules config
        postprocess: Output formatting config
    """
    
    # Identity
    slug: str = Field(..., description="Playbook identifier")
    version: str = Field(..., description="Playbook version")
    extends_slug: Optional[str] = Field(
        default=None,
        description="Base playbook being extended"
    )
    is_base: bool = Field(
        default=False,
        description="Whether this is the base playbook"
    )
    
    # Sections
    meta: MetaConfig = Field(..., description="Metadata")
    classify: ClassifyConfig = Field(..., description="Classification")
    schema: SchemaConfig = Field(..., description="Schema extraction", alias="schema")
    validate: ValidateConfig = Field(..., description="Validation", alias="validate")
    rules: RulesConfig = Field(..., description="Business rules")
    postprocess: PostprocessConfig = Field(..., description="Post-processing")
    
    model_config = {
        "frozen": True,  # Immutable after creation
        "extra": "forbid",  # No unknown fields
    }
    
    def get_document_type(self) -> str:
        """Get the document type this playbook handles."""
        return self.meta.document_type
    
    def get_engine(self, stage: str) -> Optional[str]:
        """
        Get the engine configured for a processing stage.
        
        Args:
            stage: Stage name (e.g., "ocr", "layout", "text_extraction")
            
        Returns:
            Engine name or None if not configured
        """
        if not self.meta.engines:
            return None
        
        # Map stage names to engine config fields
        engine_map = {
            "layout": self.meta.engines.layout,
            "text_extraction": self.meta.engines.text_extraction,
            "ocr": self.meta.engines.ocr,
            "ocr_fallback": self.meta.engines.ocr_fallback,
            "tables": self.meta.engines.tables,
            "vision": self.meta.engines.vision,
        }
        
        return engine_map.get(stage)
    
    def is_stage_enabled(self, stage: str) -> bool:
        """
        Check if a processing stage is enabled.
        
        Currently all stages default to enabled.
        Future: Use stage.enabled field.
        
        Args:
            stage: Stage name
            
        Returns:
            True if stage is enabled
        """
        # TODO: Implement via playbook config when stages become configurable
        return True
