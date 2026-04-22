"""
Playbook models package.

This package organizes playbook configuration into focused modules:
- base: Common types and merge utilities
- meta: Metadata and engine configuration
- classify: Document classification configuration
- schema: Schema and field extraction configuration
- validate: Data validation configuration
- rules: Business rules and post-validation actions
- postprocess: Output formatting and delivery configuration

See PLAYBOOK_DESIGN.md for architectural overview.
"""

from papertrail.playbooks.models.base import (
    PlaybookValidationCheck,
    merge_dicts_recursive,
    safe_model_dump,
)

from papertrail.playbooks.models.meta import (
    MetaConfig,
    PlaybookEngineConfig,
    load_meta,
)

from papertrail.playbooks.models.classify import (
    ClassifyConfig,
    ClassifyCandidate,
    load_classify,
)

from papertrail.playbooks.models.schema import (
    SchemaConfig,
    SchemaElement,
    load_schema,
)

from papertrail.playbooks.models.validate import (
    ValidateConfig,
    ValidationRuleConfig,
    SoftValidationRuleConfig,
    CrossFieldRuleConfig,
    CorrectionConfig,
    SuggestionConfig,
    ScoringConfig,
    load_validate,
)

from papertrail.playbooks.models.rules import (
    RulesConfig,
    ConditionConfig,
    TransformationConfig,
    load_rules,
)

from papertrail.playbooks.models.postprocess import (
    PostprocessConfig,
    load_postprocess,
)

from papertrail.playbooks.models.merged import (
    MergedPlaybook,
)

__all__ = [
    # Base utilities
    "PlaybookValidationCheck",
    "merge_dicts_recursive",
    "safe_model_dump",
    # Meta
    "MetaConfig",
    "PlaybookEngineConfig",
    "load_meta",
    # Classify
    "ClassifyConfig",
    "ClassifyCandidate",
    "load_classify",
    # Schema
    "SchemaConfig",
    "SchemaElement",
    "load_schema",
    # Validate
    "ValidateConfig",
    "ValidationRuleConfig",
    "SoftValidationRuleConfig",
    "CrossFieldRuleConfig",
    "CorrectionConfig",
    "SuggestionConfig",
    "ScoringConfig",
    "load_validate",
    # Rules
    "RulesConfig",
    "ConditionConfig",
    "TransformationConfig",
    "load_rules",
    # Postprocess
    "PostprocessConfig",
    "load_postprocess",
    # Merged
    "MergedPlaybook",
]
