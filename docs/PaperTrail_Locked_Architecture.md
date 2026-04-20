# PaperTrail — Locked Decisions, Base Playbook, and System Diagrams

**Team Twenty:** Almichael · Anuj · Rajesh · Swati
**Version:** Architecture lock · April 2026
**Purpose:** This is the reference document the team works from and the mentor reads to understand the system. It contains the final architectural decisions, the `_base` Playbook that every other Playbook extends, and the five diagrams that together tell the system story.

---

## Part 1 — Locked Decisions

These decisions are final unless the team raises a concrete objection backed by a better alternative. Raising an objection is cheap now; changing these post-code is not.

### Decision 1.1 — LLM Routing via OpenRouter

**Provider:** OpenRouter (one API key, all models behind it, swap with a string change)

**Per-stage model selection:**

| Stage | Primary | Fallback |
|---|---|---|
| Classification | `anthropic/claude-haiku-4.5` | `openai/gpt-4o-mini` |
| Soft validation | `anthropic/claude-haiku-4.5` | `openai/gpt-4o-mini` |
| LLM-backed decision conditions | `anthropic/claude-haiku-4.5` | `openai/gpt-4o-mini` |
| Schema extraction (Pass C) | `anthropic/claude-sonnet-4.5` | `openai/gpt-4o` |
| Correction retry extraction | `anthropic/claude-sonnet-4.5` | `openai/gpt-4o` |
| Correction diagnostic suggestion | `anthropic/claude-sonnet-4.5` | `openai/gpt-4o` |

**Demo mode override:** Swap Sonnet for `anthropic/claude-opus-4.7` on extraction and suggestion stages. One config change, no code edits.

**Fallback behaviour:** Two attempts on primary with exponential backoff (2s, 4s). Fall through to fallback on continued failure. Surface error to pipeline only if both providers fail on both attempts.

**Cost discipline:** Classification uses first 500-800 characters of the document, not the full text. Validation soft rules receive only the element value and its immediate context, not the whole extraction. Suggestion generation receives only the relevant portion of the trace (failed passes + validation failures + correction attempts).

**Config location:** `config/llm.json` in the repo. This is a system-level config, not a Playbook config.

### Decision 1.2 — Storage

**Primary:** PostgreSQL 15 with SQLAlchemy 2.0 async ORM and Alembic migrations. Every row uses UTC timestamps.

**Playbook configs:** Stored as `jsonb` columns in the `playbook_configs` table. One row per section per Playbook (meta, classify, schema, validate, rules, postprocess). Six rows per Playbook.

**Run outputs:** Stored as `jsonb` in `run_passes.output`. Small payloads inline. Large intermediate outputs (>100KB — mostly Pass B on long documents) written to blob storage with a URI stored in the row.

**Input documents:** Written to blob storage. Local filesystem for development (`./data/blobs/`). S3-compatible abstraction in the storage adapter so production can swap to S3 or MinIO without pipeline code changes.

**Duplicate detection:** SHA256 of input file computed at upload. Stored in `runs.input_file_hash`. Indexed column. Pre-upload stage checks for existing completed runs with matching hash within a configurable window (default 7 days). Returns cached run unless Playbook has changed since or `force_rerun` flag set.

**Immutability:** Runs are append-only. Re-processing the same file creates a new `runs` row. The `superseded_by_run_id` column links newer runs to older ones for UI purposes without destroying history.

### Decision 1.3 — Orchestration

**Framework:** LangGraph with `StateGraph` and typed state.

**State object:** A single `PipelineState` TypedDict carrying run_id, playbook reference, input file metadata, per-pass outputs, per-element extraction and validation results, correction history, decision outputs, aggregate confidence, and HITL resume tokens.

**Checkpointing:** LangGraph `MemorySaver` with PostgreSQL backing store. Enables crash recovery and HITL pause/resume.

**Conditional routing:**
- After classification: proceed or route to HITL checkpoint
- After validation: proceed or enter correction loop
- After correction loop exhaustion: route to HITL checkpoint with suggestion
- After decision: route to the correct post-processing branch (approve / flag / reject / escalate)

**Parallelism:** Not in v1. Sequential execution keeps the system predictable and easier to debug. Pass B region OCR can be parallelized later if latency becomes a concern.

### Decision 1.4 — Observability

**LLM traces:** Langfuse. Every LLM call is traced with prompt, response, token counts, latency, model used, stage, run_id. Langfuse is LLM-agnostic, integrates with OpenRouter, and gives a clean per-run view without dragging in the LangChain ecosystem.

**Application logging:** `structlog` with JSON output. Every stage transition, every validation result, every rule firing, every HITL pause logged as a structured event with `run_id` as the common correlation key.

**Infrastructure traces:** OpenTelemetry for cross-service spans. Useful once the system has multiple components; optional in early development.

**Trace events table:** `trace_events` in PostgreSQL is the append-only source of truth. It holds every significant event with `(run_id, ts, stage, event_type, payload_jsonb)`. Langfuse and structlog are views over this same underlying data; the database table is the canonical record.

### Decision 1.5 — Other Stack Choices

| Concern | Choice |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI with async endpoints |
| Dependency management | uv |
| LLM structured output | Instructor + Pydantic v2 |
| OCR | PaddleOCR primary, Tesseract fallback |
| Layout | Docling |
| PDF text | PyMuPDF primary, pdfplumber for tables |
| Image preprocessing | OpenCV (blur, skew, resolution checks) |
| Vision LLM | Claude Sonnet Vision (via OpenRouter) |
| CLI | Click |
| UI (later) | Streamlit minimal interface |
| Streaming to UI | Polling (simpler than SSE for v1) |
| MCP server | Deferred beyond v1 |

### Decision 1.6 — Project Structure

```
papertrail/
├── config/                      # System-level config (not Playbooks)
│   ├── llm.json
│   ├── engines.json
│   └── system.json
├── papertrail/                  # Python package
│   ├── cli/                     # CLI commands
│   ├── api/                     # FastAPI routes
│   ├── orchestration/           # LangGraph state machine
│   ├── passes/                  # Pass A, B, C, D implementations
│   ├── engines/                 # OCR, layout, table extraction adapters
│   ├── validation/              # Hard + soft rule runners
│   ├── decision/                # Conditions + transformations engine
│   ├── tools/                   # Tool registry (ifsc_api, etc.)
│   ├── playbooks/               # Playbook loader and validator
│   ├── storage/                 # DB models + blob storage adapter
│   ├── observability/           # structlog + Langfuse integration
│   └── models/                  # Pydantic models for pipeline state
├── alembic/                     # DB migrations
├── tests/
├── data/                        # Local blob storage (gitignored)
├── prompts/                     # System prompt templates
└── pyproject.toml
```

---

## Part 2 — The `_base` Playbook

Every other Playbook extends `_base`. A concrete Playbook only declares what differs. The `_base` values below are deliberately conservative: more protective rather than less, more explicit rather than implicit, more blocking rather than silent.

### `_base.meta`

```json
{
  "name": "Base",
  "slug": "_base",
  "version": "1.0",
  "description": "Root Playbook. All other Playbooks extend this one.",
  "extends": null,
  "engines": {
    "layout": "docling",
    "ocr": "paddleocr",
    "tables": "pdfplumber",
    "vision": null,
    "text_extraction": "pymupdf"
  },
  "preupload": {
    "max_file_size_mb": 10,
    "allowed_formats": ["pdf", "jpg", "jpeg", "png"],
    "checks": {
      "file_integrity": {
        "enabled": true,
        "on_fail": "block"
      },
      "format_allowed": {
        "enabled": true,
        "on_fail": "block"
      },
      "size_limit": {
        "enabled": true,
        "on_fail": "block"
      },
      "blur": {
        "enabled": false,
        "threshold": 100,
        "on_fail": "warn"
      },
      "resolution": {
        "enabled": false,
        "min_width": 1000,
        "min_height": 600,
        "on_fail": "warn"
      }
    },
    "warning_confidence_penalty": 0.1
  },
  "duplicate_detection": {
    "enabled": true,
    "lookback_days": 7,
    "on_duplicate": "return_cached"
  }
}
```

**Rationale:** Engine defaults cover both digital PDFs (PyMuPDF) and scanned images (PaddleOCR). Vision LLM is off by default — Playbooks enable it explicitly for document types where it helps (cheques, handwritten slips). Image quality checks are off by default because most PDFs don't need them; Playbooks for scanned documents turn them on. File integrity and format checks are always hard blocks — we never process unverified input.

### `_base.classify`

```json
{
  "mode": "llm",
  "prompt_template": "classify_default",
  "confidence_threshold": 0.80,
  "hitl_threshold": 0.60,
  "candidates": [],
  "on_low_confidence": "hitl",
  "on_no_match": "reject",
  "input_preview_chars": 800
}
```

**Rationale:** No candidate list in `_base` — each Playbook declares its own. A Playbook may declare one candidate (its own type) or several (for routing between related types). Two thresholds: above 0.80 auto-proceeds; between 0.60 and 0.80 proceeds with a flag carried forward; below 0.60 routes to HITL for manual type selection. Below no_match threshold entirely: reject the document.

### `_base.schema`

```json
{
  "mode": "schema",
  "elements": [],
  "extraction": {
    "include_source_citation": true,
    "track_ocr_confidence": true,
    "track_llm_confidence": true,
    "allow_null_on_absent": true,
    "reject_hallucinations": true
  }
}
```

**Rationale:** No elements in `_base` — every Playbook declares its own. The extraction settings apply universally: every extracted value carries both confidences, cites its source region, and may return null when the field is genuinely absent. The `reject_hallucinations` flag tells the LLM prompt generator to include the explicit anti-hallucination instruction ("return null rather than guess").

### `_base.validate`

```json
{
  "scoring": {
    "pass_threshold": 0.85,
    "critical_weight": 3.0,
    "confidence_budget_start": 1.0,
    "warning_penalty": 0.05
  },
  "elements": {},
  "cross_field": [],
  "correction": {
    "enabled": true,
    "max_attempts": 3,
    "merge_strategy": "keep_passing",
    "hint_format": "targeted",
    "on_exhaustion": "escalate_with_suggestion",
    "on_exhaustion_timeout_seconds": 300
  },
  "suggestion": {
    "enabled": true,
    "include_trace_stages": ["preupload", "classify", "pass_a", "pass_b", "pass_c", "pass_d", "corrections"],
    "max_trace_tokens": 8000
  }
}
```

**Rationale:** `pass_threshold` at 0.85 means runs below this score come out flagged even on successful extraction. `critical_weight: 3.0` makes critical fields three times more influential in aggregate confidence. Correction loop defaults to three attempts with the merge strategy that preserves already-passing elements. On exhaustion, a suggestion is generated automatically.

### `_base.rules`

```json
{
  "conditions": [
    {
      "name": "low_aggregate_confidence",
      "type": "hard",
      "expression": "run.aggregate_confidence < 0.75",
      "action": "flag",
      "reason": "Aggregate confidence below threshold"
    },
    {
      "name": "correction_loop_exhausted",
      "type": "hard",
      "expression": "run.correction_attempts >= run.correction_max_attempts and run.validation_passed == false",
      "action": "escalate",
      "reason": "Correction loop exhausted without validation pass"
    }
  ],
  "transformations": [],
  "action_precedence": ["reject", "escalate", "flag", "approve"]
}
```

**Rationale:** `_base` provides two universal conditions. The first translates accumulated warnings into a flag via aggregate confidence. The second ensures exhausted correction loops always escalate, regardless of other rules. Both are hard (deterministic) conditions. Playbooks add their own domain-specific rules on top.

### `_base.postprocess`

```json
{
  "output": {
    "format": "json",
    "include_extracted": true,
    "include_enriched": true,
    "include_warnings": true,
    "include_confidence_breakdown": true,
    "include_trace_id": true
  },
  "on_approve": {
    "export": ["json"],
    "notify": false,
    "archive": true
  },
  "on_flag": {
    "export": ["json"],
    "notify": false,
    "archive": true,
    "include_warnings_prominently": true
  },
  "on_reject": {
    "export": ["json"],
    "notify": false,
    "archive": true,
    "generate_reason_summary": true
  },
  "on_escalate": {
    "export": ["json"],
    "notify": false,
    "archive": true,
    "include_full_trace": true,
    "include_suggestion": true
  }
}
```

**Rationale:** All four outcomes archive the run. All four export JSON. Rejected and escalated runs include additional context (reason summary, full trace, suggestion). No notification channel is enabled in `_base` — Playbooks configure this per their operational needs.

---

## Part 3 — Inheritance Example

Here is what an actual Playbook looks like when it extends `_base`. This is the full `indian_cheque` Playbook — notice how short it is.

### `indian_cheque.meta`

```json
{
  "name": "Indian Cheque",
  "slug": "indian_cheque",
  "version": "1.0",
  "description": "CTS-2010 compliant Indian bank cheque",
  "extends": "_base",
  "engines": {
    "vision": "claude-sonnet-vision"
  },
  "preupload": {
    "checks": {
      "blur": {"enabled": true, "threshold": 100, "on_fail": "warn"},
      "resolution": {"enabled": true, "min_width": 1000, "min_height": 600, "on_fail": "warn"}
    }
  }
}
```

Only the vision engine and the two image quality checks are overridden. Everything else comes from `_base`.

### `indian_cheque.classify`

```json
{
  "candidates": [
    {
      "label": "indian_cheque",
      "description": "A CTS-compliant Indian bank cheque with payee, amount in figures and words, date, IFSC, account number, and drawer signature"
    }
  ]
}
```

One field overridden. Everything else inherited.

### `indian_cheque.schema`

```json
{
  "elements": [
    {"name": "payee_name", "type": "string", "required": true, "critical": true, "description": "Full name of the payee", "region_hint": "payee_region"},
    {"name": "amount_figures", "type": "decimal", "required": true, "critical": true, "description": "Numeric amount in the figures box", "region_hint": "figures_region"},
    {"name": "amount_words", "type": "string", "required": true, "critical": true, "description": "Amount spelled out in words", "region_hint": "words_region"},
    {"name": "date", "type": "date", "required": true, "critical": false, "description": "Date on the cheque", "region_hint": "date_region"},
    {"name": "account_number", "type": "string", "required": true, "critical": false, "description": "Account number at bottom", "region_hint": "bottom_region"},
    {"name": "ifsc_code", "type": "string", "required": true, "critical": false, "description": "11-character IFSC code", "region_hint": "bottom_region"}
  ]
}
```

### `indian_cheque.validate`

```json
{
  "elements": {
    "ifsc_code": {"type": "hard", "rules": [{"name": "required"}, {"name": "regex", "params": {"pattern": "^[A-Z]{4}0[A-Z0-9]{6}$"}}]},
    "date": {"type": "hard", "rules": [{"name": "required"}, {"name": "valid_date"}, {"name": "not_future"}]},
    "amount_figures": {"type": "hard", "rules": [{"name": "required"}, {"name": "positive_decimal"}]},
    "amount_words": {"type": "hard", "rules": [{"name": "required"}]},
    "account_number": {"type": "hard", "rules": [{"name": "required"}, {"name": "regex", "params": {"pattern": "^[0-9]{9,18}$"}}]},
    "payee_name": {"type": "soft", "prompt_template": "validate_payee_name"}
  },
  "cross_field": [
    {"name": "amount_consistency", "type": "soft", "elements": ["amount_figures", "amount_words"], "prompt_template": "validate_amount_consistency"}
  ]
}
```

Correction settings come from `_base`. Playbook only declares per-element rules and cross-field checks.

### `indian_cheque.rules`

```json
{
  "conditions": [
    {"name": "high_value_flag", "type": "hard", "expression": "elements.amount_figures > 100000", "action": "flag", "reason": "High-value cheque"},
    {"name": "stale_cheque", "type": "hard", "expression": "days_since(elements.date) > 90", "action": "reject", "reason": "Cheque is stale (older than 90 days)"},
    {"name": "post_dated_cheque", "type": "hard", "expression": "days_until(elements.date) > 0", "action": "flag", "reason": "Post-dated cheque"}
  ],
  "transformations": [
    {"name": "ifsc_lookup", "type": "tool_call", "tool": "ifsc_api", "input": "elements.ifsc_code", "output_field": "enriched.bank_branch"}
  ]
}
```

The two universal conditions from `_base` (low_aggregate_confidence and correction_loop_exhausted) stack with these domain conditions. Total: five conditions evaluated in declared order, with precedence applied at the end.

### `indian_cheque.postprocess`

```json
{}
```

Fully inherited. No overrides needed. The base behaviour is correct for this document type.

**Result:** The full `indian_cheque` Playbook is six small JSON objects. Everything in `_base` applies except where explicitly overridden. This is the pattern every Playbook follows.

---

## Part 4 — System Diagrams

Five diagrams are provided with this document. Each one explains a different aspect of the system at a different zoom level.

### Diagram 01 — Architecture One-Pager

The high-level view. Five layers stacked vertically, foundation panel on the right. This is the diagram a mentor reads in two minutes. It answers the question "what is PaperTrail made of?"

**File:** `01_architecture.svg`

### Diagram 02 — End-to-End Flow

A horizontal flow following a single document through every stage. Shows the six sequential stages (upload, pre-upload, classify, extract, decide, act), the HITL checkpoints, the correction loop, and the final output. Answers the question "what happens when I feed a document in?"

**File:** `02_end_to_end_flow.svg`

### Diagram 03 — Extraction Detail

Zooms into the Extract layer. Four passes laid out side by side with their engines, outputs, and latency. The correction loop is shown as a separate panel looping back into Pass C. Answers the question "how does the extraction actually work?"

**File:** `03_extraction_detail.svg`

### Diagram 04 — Decision Routing

Shows how validated extractions flow through the Decision Layer and get routed to one of four outcomes (approve, flag, escalate, reject). Includes the action precedence resolver and typical firing conditions for each outcome. Answers the question "how does the system decide what to do with a document?"

**File:** `04_decision_tree.svg`

### Diagram 05 — Playbook Anatomy

Shows the six sections of a Playbook, which pipeline stage each section governs, and the inheritance model. Answers the question "what do I write when I want to add a new document type?"

**File:** `05_playbook_anatomy.svg`

---

## Part 5 — How to Use This Document

**Team members** read Parts 1 and 2 carefully. The locked decisions tell you what to use when you're implementing a module. The `_base` Playbook tells you the shape of every config your code will load.

**Mentors** read Diagram 01 first (two minutes), then Diagram 02 if they want the flow, then skim Part 1 for stack choices. Parts 2 and 3 are for when they have deeper questions.

**When writing a new Playbook:** Diagram 05 shows the shape. Part 3 shows the pattern of overriding `_base`. Keep overrides minimal.

**When something doesn't work:** The trace events table is the first place to look. Every significant event has a `run_id` for correlation. Langfuse shows the LLM calls; structlog shows everything else.

---

*Document complete. Ready for team review and mentor meeting.*
