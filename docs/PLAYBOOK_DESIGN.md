# Playbook Architecture & Design

**Version**: 1.1  
**Last Updated**: 2026-04-22

## Overview

A playbook defines how a specific document type is processed. It is a file-based, structured configuration made of:
- **base model contracts** (Pydantic models)
- **base JSON defaults** in `playbooks/_base/`
- **child playbook overrides** in `playbooks/<slug>/`
- **a merged runtime playbook** used by orchestration

The playbook system is intentionally simple: predictable structure, bounded flexibility, and light validation.

## Design Principles

### 1. Single-Level Inheritance
- Every child playbook extends `_base` directly
- No inheritance chains like A→B→C
- This keeps behavior predictable
- Multi-parent or sibling-style inheritance may be explored later if needed

### 2. File-First Playbooks
- Playbooks are stored as JSON files in `playbooks/`
- Base defaults live in `playbooks/_base/`
- Child playbooks live in their own folder, one JSON file per section
- No database playbook loading is used right now

### 3. Immutable After Load
- Loaded playbooks are frozen Pydantic models
- Runtime code should not mutate playbook structure
- Any runtime state belongs in pipeline state, not the playbook object

### 4. Engines: Selection, Not Configuration
- The playbook selects engines
- The system defines engine implementations and runtime parameters
- Example: playbook says `vision = "claude_vision"`, but does not define what Claude vision is

### 5. Merge Behavior
- Dict values merge recursively
- List values are replaced, not appended
- New keys are naturally added
- Validation happens after merge via Pydantic models

### 6. Light Validation
- We validate enough to catch corrupt or invalid playbook files
- We are not over-engineering a heavy authoring system
- The expectation is that developers will create playbooks carefully and use the model contracts as guardrails

## Current Structure

### Directory Layout
```text
playbooks/
├── _base/
│   ├── meta.json
│   ├── classify.json
│   ├── schema.json
│   ├── validate.json
│   ├── rules.json
│   └── postprocess.json
├── indian_cheque/
│   ├── meta.json
│   ├── classify.json
│   ├── schema.json
│   ├── validate.json
│   ├── rules.json
│   └── postprocess.json
├── indian_bank_statement/
│   └── meta.json
├── indian_itr_form/
│   └── meta.json
└── indian_salary_slip/
    └── meta.json
```

### Base Models
Current model modules live in:
```text
papertrail/playbooks/models/
├── base.py
├── meta.py
├── classify.py
├── schema.py
├── validate.py
├── rules.py
├── postprocess.py
└── merged.py
```

## Module Pattern

Each section module follows the same pattern:

1. Define the Pydantic model(s)
2. Keep a base JSON file in `playbooks/_base/`
3. Expose a loader function:
   - `load_meta(base_config, raw_dict)`
   - `load_classify(base_config, raw_dict)`
   - `load_schema(base_config, raw_dict)`
   - `load_validate(base_config, raw_dict)`
   - `load_rules(base_config, raw_dict)`
   - `load_postprocess(base_config, raw_dict)`

The loader pattern is simple:
- load `_base` JSON
- load child JSON
- merge them
- validate the result with the Pydantic model

## MergedPlaybook

`MergedPlaybook` is the final runtime object used by orchestration.

It currently contains:
- `slug`
- `version`
- `extends_slug`
- `is_base`
- `meta`
- `classify`
- `schema`
- `validate`
- `rules`
- `postprocess`

Notes:
- `schema` and `validate` are kept as field names in the runtime model
- aliases are used in the model to avoid Python/Pydantic name collisions
- this is a practical implementation detail, not a design goal

## Load Flow

Current load flow:

```text
read playbook JSON files
  ↓
read _base JSON files
  ↓
merge base + child per section
  ↓
validate each section with Pydantic
  ↓
compose MergedPlaybook
  ↓
return frozen runtime playbook
```

Important detail:
- `extends_slug` is used by the loader to decide whether to merge against `_base`
- it is treated as loader metadata, not as part of `MetaConfig`

## Merge Rules

### Dicts
Recursive merge.

### Lists
Replacement behavior.
- child list replaces base list
- no append/concat logic by default

### Scalars
Child value overrides base value.

## Playbook File Shape

### Base playbook section example
```json
{
  "document_type": "base",
  "display_name": "Base Document Type",
  "engines": {
    "ocr": "paddleocr"
  }
}
```

### Child playbook section example
```json
{
  "document_type": "indian_cheque",
  "display_name": "Indian Cheque",
  "description": "Processing pipeline for Indian bank cheques.",
  "extends_slug": "_base",
  "engines": {
    "vision": "claude_vision",
    "always_fallback": true
  }
}
```

Notes:
- `extends_slug` is stored in the child `meta.json`
- the loader reads it before validating the section model
- child playbooks only need to override what differs

## Practical Rules We Are Following

1. The playbook is hand-authored, not auto-generated.
2. Keep playbooks concise.
3. Prefer explicit base defaults over hidden behavior.
4. Keep validation light but meaningful.
5. Keep the model shape strong so children inherit safety.

## Current Status

Implemented:
- file-based playbooks in `playbooks/`
- `_base` JSON defaults
- section-based model modules
- merged runtime playbook model
- loader/repository-based merging
- frozen runtime playbooks

Still to refine later:
- versioned playbooks
- sibling/multiple inheritance
- richer merge hints for lists
- optional non-overridable fields
- future DB-backed playbook compatibility if needed

---
*This document describes the current playbook design and the implementation shape in `papertrail/playbooks/models/` and `papertrail/playbooks/`.*