# PaperTrail — Technical Documentation

**Team Twenty** · Almichael · Anuj · Rajesh · Swati
**Version:** 1.0 · April 2026
**Purpose:** Engineering specification. Everything needed to build the system.

---

## Table of Contents

1. Overview and Scope
2. Technical Architecture
3. Dependencies and Libraries
4. Folder Structure
5. Database Design
6. Core Modules
7. Pipeline State Machine
8. LLM Layer
9. Engine Dispatcher
10. Playbook Loader and Inheritance
11. Validation Rules Engine
12. Decision Engine
13. Tool Registry
14. Observability
15. CLI Specification
16. REST API Specification
17. Prompt Templates
18. Error Handling Strategy
19. Testing Strategy
20. Development Setup
21. Milestone Plan
22. Post-Capstone Extensions

---

## 1. Overview and Scope

PaperTrail is an agentic document processing pipeline. One Playbook describes how to process one document type. The pipeline takes a document through classification, multi-pass extraction, validation, correction, decision, and post-processing. Every step is traced and queryable.

### In scope for v1

- CLI-first operation with all core commands
- PostgreSQL-backed storage, local blob storage
- 3-4 Indian financial document Playbooks (cheque, bank statement, salary slip, ITR form)
- 4-pass extraction with real engines (Docling, PaddleOCR, PyMuPDF, pdfplumber, Claude vision)
- Hard and soft validation rules per element plus cross-field checks
- Correction loop with targeted hints, up to 3 retries
- LLM diagnostic suggestion on correction exhaustion
- Decision engine with conditions and transformations
- Tool registry with 4-6 initial tools
- HITL checkpoints at classification and correction exhaustion
- Langfuse + structlog observability
- FastAPI REST endpoints
- Minimal Streamlit UI for HITL review
- Evaluation dataset of 20-30 curated documents
- 2 end-to-end demo scenarios

### Out of scope for v1

- MCP server (deferred)
- Multi-tenant isolation
- Production authentication and authorization
- S3 blob storage (abstraction in place, local used)
- Cross-document learning or RAG from past runs
- Fine-tuned models
- Automated correction suggestion application
- Horizontal scaling or Celery task queue
- Advanced UI (Streamlit stays minimal)

### Non-negotiable constraints

- Every run is immutable. Re-processing creates a new run.
- Every extracted field cites its source region.
- LLM responses must allow explicit null; never hallucinate.
- The database is the source of truth. Files are convenience.
- Every stage must be runnable in isolation for testing.

---

## 2. Technical Architecture

### 2.1 Component diagram

```
┌────────────────────────────────────────────────────────────┐
│                    User Interfaces                         │
│   CLI (Click)    REST API (FastAPI)    Streamlit UI        │
└───────────────────────┬────────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│                 Orchestration Layer                        │
│               LangGraph State Machine                      │
│   (nodes: preupload, classify, passes A-D, correction,     │
│    decide, act)  +  HITL checkpoints via MemorySaver       │
└───────────────────────┬────────────────────────────────────┘
                        │
       ┌────────────────┼────────────────┬─────────────────┐
       ▼                ▼                ▼                 ▼
┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────────┐
│  Engines   │  │    LLM     │  │ Validation │  │    Tools      │
│ Dispatcher │  │   Router   │  │   Engine   │  │   Registry    │
│            │  │            │  │            │  │               │
│ Docling    │  │ OpenRouter │  │ Hard rules │  │ ifsc_lookup   │
│ PaddleOCR  │  │ Haiku/     │  │ Soft rules │  │ currency_conv │
│ PyMuPDF    │  │  Sonnet    │  │ Cross-field│  │ date_utils    │
│ pdfplumber │  │ Fallback   │  │ Scoring    │  │ pan_validate  │
│ OpenCV     │  │  chain     │  │            │  │               │
│ Vision LLM │  │            │  │            │  │               │
└────────────┘  └────────────┘  └────────────┘  └───────────────┘
       │                │                │                 │
       └────────────────┼────────────────┴─────────────────┘
                        │
┌───────────────────────▼────────────────────────────────────┐
│                 Storage & Observability                    │
│                                                            │
│  PostgreSQL 15 (jsonb)     Blob Storage (local/S3)         │
│  playbooks · runs · passes · elements · corrections        │
│  rules · hitl · trace_events                               │
│                                                            │
│  Langfuse (LLM traces)    structlog (app logs)             │
│  OpenTelemetry (spans)                                     │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Module boundaries

The system is organized into nine modules. Each module has a single responsibility and a well-defined interface. No module imports from the others except through public interfaces.

| Module | Responsibility |
|---|---|
| `orchestration` | LangGraph state machine. Node registration and conditional routing. |
| `passes` | Pass implementations. Each pass is a pure function over state. |
| `engines` | Adapters for Docling, OCR engines, PDF parsers, vision LLM, OpenCV. |
| `llm` | OpenRouter client, per-stage routing, retry and fallback logic. |
| `validation` | Hard rule runner, soft rule runner, cross-field checks, scoring. |
| `decision` | Condition evaluator, transformation runner, precedence resolver. |
| `tools` | Tool registry. Named callables invoked from Playbook rules. |
| `playbooks` | Load from database. Merge with `_base`. Validate. |
| `storage` | SQLAlchemy models, repository pattern, blob storage adapter. |

Three support modules: `observability`, `models` (shared Pydantic types), `config` (system-level config loader).

### 2.3 Data flow

A run executes in this sequence:

1. **Upload.** File written to blob storage. SHA256 computed. `runs` row created with status `created`.
2. **Orchestrator invoked.** Playbook loaded, merged with `_base`, validated. State initialized.
3. **Pre-upload node.** Runs integrity, format, size, blur, resolution checks. Warnings added to state. Hard-block failures fail the run.
4. **Classify node.** LLM called with first 800 chars. Type and confidence returned. If below HITL threshold, state transitions to `awaiting_hitl` and the graph pauses.
5. **Pass A node.** Docling analyzes layout. Output written to `run_passes` row. Low confidence triggers fallback extraction in addition to structured output.
6. **Pass B node.** Engine dispatcher routes regions to the right engines. Per-region text and confidence collected. Fallback full-page OCR added if Pass A confidence was low.
7. **Pass C node.** LLM called with schema, Pass B output, and image (if vision enabled). Returns typed structured data.
8. **Pass D node.** Hard rules run first, soft rules second. Cross-field checks run. Validation result written to state.
9. **If validation failed and correction enabled:** Correction node generates targeted hint, calls Pass C with hint, merges corrected elements into state. Loops up to `max_attempts`.
10. **If correction exhausted:** Suggestion node runs. LLM reads trace and produces diagnostic. State transitions to `awaiting_hitl`.
11. **Decide node.** Conditions evaluated in order. Transformations run. Precedence resolver picks strongest action.
12. **Act node.** Post-processing per decision. Output serialized and written. Run row updated with final status.

Every node reads and writes the `PipelineState`. Every node writes at least one `trace_events` row.

---

## 3. Dependencies and Libraries

### 3.1 Runtime

```toml
[project]
name = "papertrail"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    # Web and API
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "click>=8.1.7",
    "streamlit>=1.40.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",

    # Database
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.29.0",
    "alembic>=1.13.3",

    # Orchestration
    "langgraph>=0.2.50",
    "langgraph-checkpoint-postgres>=1.0.0",

    # LLM
    "instructor>=1.6.0",
    "openai>=1.54.0",                     # OpenRouter-compatible
    "tenacity>=9.0.0",

    # Document processing
    "docling>=2.7.0",                     # Layout analysis
    "pymupdf>=1.24.0",                    # Digital PDF text
    "pdfplumber>=0.11.4",                 # PDF tables
    "paddleocr>=2.9.0",                   # Primary OCR
    "pytesseract>=0.3.13",                # Fallback OCR
    "opencv-python>=4.10.0",              # Image quality checks
    "pillow>=11.0.0",                     # Image manipulation
    "pdf2image>=1.17.0",                  # PDF to image conversion

    # Observability
    "langfuse>=2.54.0",
    "structlog>=24.4.0",
    "opentelemetry-api>=1.28.0",
    "opentelemetry-sdk>=1.28.0",
    "opentelemetry-instrumentation-fastapi>=0.49b0",

    # HTTP for tool calls
    "httpx>=0.27.0",
]

[tool.uv.sources]
# pinned where needed

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
    "types-pyyaml>=6.0.0",
    "factory-boy>=3.3.0",                 # test fixtures
]
```

### 3.2 Environment requirements

- Python 3.11 or 3.12 (not 3.13 yet, PaddleOCR wheel support)
- PostgreSQL 15 or 16 running locally (Docker Compose for convenience)
- Tesseract binary installed if fallback OCR needed (`apt install tesseract-ocr` or `brew install tesseract`)
- At least 4 GB RAM for local development (Docling and PaddleOCR load models)
- OpenRouter API key
- Langfuse account (free tier sufficient)

### 3.3 Optional dev tooling

- `ruff` for formatting and linting
- `mypy` for type checking (strict mode on modules without external deps)
- `pre-commit` hooks for ruff + mypy on staged files
- Docker Compose for Postgres and optional Langfuse self-host

---

## 4. Folder Structure

```
papertrail/
├── pyproject.toml
├── uv.lock
├── README.md
├── .env.example
├── .gitignore
├── alembic.ini
├── compose.yaml                  # PostgreSQL for local dev
├── alembic/
│   ├── env.py
│   └── versions/                 # migration files
├── config/                       # system-level config (not Playbooks)
│   ├── llm.json
│   ├── engines.json
│   ├── system.json
│   └── prompts/
│       ├── classify_default.txt
│       ├── extract_schema.txt
│       ├── extract_natural.txt
│       ├── validate_soft_default.txt
│       ├── validate_payee_name.txt
│       ├── validate_amount_consistency.txt
│       ├── correct_hint.txt
│       └── suggest.txt
├── data/                         # gitignored
│   ├── blobs/                    # input files and large outputs
│   ├── fixtures/                 # test documents
│   └── exports/                  # exported run outputs
├── playbooks_seed/               # JSON seed for Playbooks
│   ├── _base/
│   │   ├── meta.json
│   │   ├── classify.json
│   │   ├── schema.json
│   │   ├── validate.json
│   │   ├── rules.json
│   │   └── postprocess.json
│   ├── indian_cheque/
│   ├── indian_bank_statement/
│   ├── indian_salary_slip/
│   └── indian_itr_form/
├── papertrail/
│   ├── __init__.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── app.py                # Click entry point
│   │   ├── commands/
│   │   │   ├── run.py
│   │   │   ├── playbook.py
│   │   │   ├── runs.py
│   │   │   ├── hitl.py
│   │   │   ├── db.py
│   │   │   └── eval.py
│   │   └── formatters.py         # Pretty-print output
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app
│   │   ├── dependencies.py
│   │   ├── routes/
│   │   │   ├── runs.py
│   │   │   ├── playbooks.py
│   │   │   ├── hitl.py
│   │   │   └── health.py
│   │   └── schemas.py            # Request/response Pydantic
│   ├── orchestration/
│   │   ├── __init__.py
│   │   ├── graph.py              # LangGraph state machine
│   │   ├── state.py              # PipelineState TypedDict
│   │   ├── nodes.py              # Node function registrations
│   │   ├── routing.py            # Conditional edge logic
│   │   └── runner.py             # Top-level run entry point
│   ├── passes/
│   │   ├── __init__.py
│   │   ├── preupload.py
│   │   ├── classify.py
│   │   ├── pass_a_layout.py
│   │   ├── pass_b_raw.py
│   │   ├── pass_c_schema.py
│   │   ├── pass_d_validate.py
│   │   ├── correction.py
│   │   ├── suggestion.py
│   │   ├── decide.py
│   │   └── act.py
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── base.py               # Engine Protocol
│   │   ├── dispatcher.py         # Route regions to engines
│   │   ├── layout/
│   │   │   └── docling_engine.py
│   │   ├── ocr/
│   │   │   ├── paddle_engine.py
│   │   │   └── tesseract_engine.py
│   │   ├── text/
│   │   │   ├── pymupdf_engine.py
│   │   │   └── pdfplumber_engine.py
│   │   ├── tables/
│   │   │   └── pdfplumber_tables.py
│   │   ├── vision/
│   │   │   └── claude_vision_engine.py
│   │   └── preprocessing/
│   │       └── opencv_checks.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py             # OpenRouter client
│   │   ├── router.py             # Per-stage model selection
│   │   ├── fallback.py           # Retry + provider fallback
│   │   └── prompts.py            # Prompt template loader
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── runner.py
│   │   ├── rules/
│   │   │   ├── __init__.py
│   │   │   ├── hard.py           # required, regex, valid_date, etc.
│   │   │   └── soft.py           # LLM-based rules
│   │   ├── cross_field.py
│   │   └── scoring.py
│   ├── decision/
│   │   ├── __init__.py
│   │   ├── engine.py             # Orchestrates conditions + transformations
│   │   ├── conditions.py
│   │   ├── transformations.py
│   │   ├── expressions.py        # Expression evaluator
│   │   └── precedence.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── base.py               # Tool Protocol
│   │   ├── ifsc.py
│   │   ├── currency.py
│   │   ├── date_utils.py
│   │   └── pan_validate.py
│   ├── playbooks/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── merger.py             # _base inheritance merge
│   │   ├── validator.py          # Load-time playbook validation
│   │   ├── seeder.py             # Import JSON seeds into DB
│   │   └── models.py             # Pydantic models per config section
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   ├── models.py         # SQLAlchemy ORM models
│   │   │   └── repositories/
│   │   │       ├── playbooks.py
│   │   │       ├── runs.py
│   │   │       ├── elements.py
│   │   │       ├── hitl.py
│   │   │       └── trace.py
│   │   └── blob/
│   │       ├── __init__.py
│   │       ├── base.py           # BlobStore Protocol
│   │       ├── local.py
│   │       └── s3.py             # stub for later
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── logging.py            # structlog config
│   │   ├── langfuse_client.py
│   │   └── tracing.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── pipeline_state.py
│   │   ├── extraction.py
│   │   ├── validation.py
│   │   └── decision.py
│   └── config/
│       ├── __init__.py
│       └── loader.py             # Load config/*.json into typed objects
├── ui/                           # Streamlit UI (minimal)
│   ├── app.py
│   ├── pages/
│   │   ├── 1_run_viewer.py
│   │   └── 2_hitl_queue.py
│   └── components/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_playbook_merger.py
│   │   ├── test_expression_evaluator.py
│   │   ├── test_hard_rules.py
│   │   └── test_precedence.py
│   ├── integration/
│   │   ├── test_full_pipeline.py
│   │   ├── test_correction_loop.py
│   │   └── test_hitl_checkpoints.py
│   └── evaluation/
│       ├── test_cheque_set.py
│       ├── test_bank_statement_set.py
│       └── datasets/
└── scripts/
    ├── seed_db.py                # Seed _base + starter Playbooks
    ├── run_eval.py               # Run evaluation dataset
    └── demo_setup.sh             # Reset DB + seed + sample docs
```

### 4.1 Design notes on folder layout

**Why `playbooks_seed/` separate from database.** Playbooks live in the database as rows, but seeding them requires JSON files checked into git. The seeder reads `playbooks_seed/` and imports each folder as a Playbook row set. Playbook authoring during development means editing JSON in this folder and running `papertrail db seed` to refresh.

**Why `engines/` has subfolders.** Each engine type (layout, ocr, text, tables, vision, preprocessing) may have multiple implementations. The subfolder structure keeps selection explicit. The dispatcher in `engines/dispatcher.py` picks implementations based on `engines.json` or Playbook override.

**Why `ui/` is separate from `papertrail/`.** Streamlit is a separate entry point. It reads the same database and calls into the same repositories but runs as its own process. Keeping it out of the main package avoids import cycles.

---

## 5. Database Design

### 5.1 Conventions

- All tables use `UUID` primary keys generated by PostgreSQL except `trace_events` which uses `bigserial` for insertion performance
- All timestamps use `TIMESTAMPTZ` with `NOW()` defaults and are stored in UTC
- `jsonb` is used for all structured content that does not need relational queries
- Foreign keys use `ON DELETE CASCADE` only where child rows are meaningless without parent (run_passes, run_elements, etc.)
- Indexes are named `idx_{table}_{columns}` with partial indexes where applicable

### 5.2 Schema

#### `playbooks`

```sql
CREATE TABLE playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(32) NOT NULL,
    description TEXT,
    extends_playbook_id UUID REFERENCES playbooks(id),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_base BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(slug, version)
);

CREATE INDEX idx_playbooks_slug_active
    ON playbooks(slug) WHERE is_active = TRUE;
```

A Playbook is identified by slug + version. The `_base` Playbook has `is_base = TRUE`. Each Playbook inherits from exactly one parent via `extends_playbook_id`. Inheritance is resolved at load time; the database does not materialize the merged view.

#### `playbook_configs`

```sql
CREATE TABLE playbook_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    config_type VARCHAR(32) NOT NULL
        CHECK (config_type IN ('meta','classify','schema','validate','rules','postprocess')),
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    UNIQUE(playbook_id, config_type)
);

CREATE INDEX idx_configs_playbook ON playbook_configs(playbook_id);
```

Six rows per Playbook, one per section. The `content` column holds the section JSON exactly as authored. A Playbook that inherits from `_base` may have partial content here (only the overrides); the merger combines it with `_base` at load time.

#### `tools`

```sql
CREATE TABLE tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) UNIQUE NOT NULL,
    handler VARCHAR(255) NOT NULL,
    input_schema JSONB NOT NULL,
    output_schema JSONB NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);
```

`handler` is a module path string (for example `papertrail.tools.ifsc:lookup`). The registry resolves this to a callable at startup. Input and output schemas are JSON Schema documents that the caller validates against.

#### `runs`

```sql
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_uid VARCHAR(128) UNIQUE NOT NULL,
    playbook_id UUID REFERENCES playbooks(id),
    playbook_slug VARCHAR(128) NOT NULL,
    playbook_version VARCHAR(32) NOT NULL,

    input_file_uri TEXT NOT NULL,
    input_file_hash VARCHAR(64) NOT NULL,
    input_file_name VARCHAR(512),
    input_file_size_bytes INTEGER,
    input_file_mime VARCHAR(64),

    status VARCHAR(32) NOT NULL
        CHECK (status IN ('created','running','awaiting_hitl','completed','failed','cancelled')),
    decision VARCHAR(32)
        CHECK (decision IN ('approve','flag','reject','escalate')),

    aggregate_confidence FLOAT,
    confidence_breakdown JSONB,
    warnings JSONB,

    superseded_by_run_id UUID REFERENCES runs(id),
    requested_by VARCHAR(128),

    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER
);

CREATE INDEX idx_runs_hash ON runs(input_file_hash);
CREATE INDEX idx_runs_playbook_status ON runs(playbook_id, status);
CREATE INDEX idx_runs_created ON runs(created_at DESC);
CREATE INDEX idx_runs_status_pending
    ON runs(status) WHERE status IN ('created','running','awaiting_hitl');
```

`run_uid` format: `run_{YYYYMMDD_HHMMSS}_{playbook_slug}_{hash[:6]}` for example `run_20260420_143201_indian_cheque_abc123`. Human-readable for logs and URLs.

`aggregate_confidence` is the final confidence budget after all degradations. `confidence_breakdown` holds per-stage scores.

`superseded_by_run_id` links new runs to old ones when a document is re-processed. Older runs stay for audit but can be filtered from default views.

#### `run_passes`

```sql
CREATE TABLE run_passes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    pass_name VARCHAR(32) NOT NULL,
    pass_order INTEGER NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('pending','running','success','failed','skipped')),
    confidence FLOAT,
    output JSONB,
    output_blob_uri TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,
    error TEXT
);

CREATE INDEX idx_passes_run ON run_passes(run_id, pass_order);
```

`pass_name` values: `preupload`, `classify`, `pass_a`, `pass_b`, `pass_c`, `pass_d`, `correction_{n}`, `suggestion`, `decide`, `act`.

`output` holds small payloads inline. Large outputs (more than 100KB, typical for Pass B on multi-page documents) go to blob storage with the URI stored in `output_blob_uri` and `output` left null.

#### `run_elements`

```sql
CREATE TABLE run_elements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    element_name VARCHAR(128) NOT NULL,
    element_type VARCHAR(32),
    value JSONB,
    llm_confidence FLOAT,
    ocr_confidence FLOAT,
    source_region VARCHAR(128),
    notes TEXT,
    validation_status VARCHAR(32)
        CHECK (validation_status IN ('pending','pass','fail','unable_to_evaluate')),
    validation_details JSONB,
    is_final BOOLEAN DEFAULT FALSE NOT NULL,
    attempt_number INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_elements_run ON run_elements(run_id, element_name);
CREATE INDEX idx_elements_final ON run_elements(run_id) WHERE is_final = TRUE;
```

One row per element per correction attempt. `attempt_number = 0` is the initial extraction. Corrections increment it. `is_final = TRUE` on the row that represents the final accepted value for that element. Makes queries for final extraction trivial: `WHERE run_id = ? AND is_final = TRUE`.

#### `run_corrections`

```sql
CREATE TABLE run_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL,
    element_name VARCHAR(128) NOT NULL,
    hint_text TEXT NOT NULL,
    previous_value JSONB,
    new_value JSONB,
    succeeded BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_corrections_run ON run_corrections(run_id, attempt_number);
```

Each correction attempt on each element writes one row. Enables queries like "which elements most often need correction?" and "what is the first-try success rate by document type?"

#### `run_rule_evaluations`

```sql
CREATE TABLE run_rule_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    rule_name VARCHAR(128) NOT NULL,
    rule_type VARCHAR(32) NOT NULL
        CHECK (rule_type IN ('condition','transformation')),
    fired BOOLEAN NOT NULL,
    action VARCHAR(32),
    reason TEXT,
    evaluation_details JSONB,
    order_executed INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_rules_run ON run_rule_evaluations(run_id, order_executed);
```

One row per rule evaluation (condition or transformation). Whether it fired, what action it produced, what reason it gave. Full decision history queryable.

#### `run_hitl_events`

```sql
CREATE TABLE run_hitl_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    checkpoint_type VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('awaiting','resolved','abandoned')),
    context JSONB,
    resolution JSONB,
    resolved_by VARCHAR(128),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_hitl_awaiting ON run_hitl_events(status) WHERE status = 'awaiting';
```

`checkpoint_type` values: `classify_low_confidence`, `correction_exhausted`. Context holds data the reviewer needs; resolution holds their input. The partial index on `awaiting` makes "what's pending?" queries instant.

#### `trace_events`

```sql
CREATE TABLE trace_events (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    stage VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    level VARCHAR(16) DEFAULT 'info' NOT NULL
        CHECK (level IN ('debug','info','warning','error')),
    payload JSONB
);

CREATE INDEX idx_trace_run_ts ON trace_events(run_id, ts);
CREATE INDEX idx_trace_errors ON trace_events(level, ts)
    WHERE level IN ('warning','error');
```

Append-only. Every significant event across the pipeline. Queryable for debugging, audit, and analytics. The `bigserial` primary key preserves insertion order. Partitioning by date range is a later optimization when volume warrants.

### 5.3 Migration order

Alembic migrations should be created in this order:

1. `0001_playbooks_and_configs` — playbooks, playbook_configs, tools
2. `0002_runs_and_passes` — runs, run_passes
3. `0003_elements_and_corrections` — run_elements, run_corrections
4. `0004_decisions_and_hitl` — run_rule_evaluations, run_hitl_events
5. `0005_trace_events` — trace_events
6. `0006_indexes` — any additional indexes added later

### 5.4 Example queries

The schema is designed so typical questions are one-query:

```sql
-- Final extraction for a run
SELECT element_name, value, llm_confidence, ocr_confidence
FROM run_elements
WHERE run_id = ? AND is_final = TRUE
ORDER BY element_name;

-- Success rate by document type for last 7 days
SELECT playbook_slug,
       COUNT(*) FILTER (WHERE decision = 'approve') * 100.0 / COUNT(*) AS approval_rate,
       COUNT(*) AS total
FROM runs
WHERE created_at > NOW() - INTERVAL '7 days'
  AND status = 'completed'
GROUP BY playbook_slug;

-- Elements most often needing correction
SELECT element_name, COUNT(*) AS correction_count
FROM run_corrections
GROUP BY element_name
ORDER BY correction_count DESC
LIMIT 20;

-- HITL queue
SELECT r.run_uid, h.checkpoint_type, h.created_at, h.context
FROM run_hitl_events h
JOIN runs r ON r.id = h.run_id
WHERE h.status = 'awaiting'
ORDER BY h.created_at ASC;

-- Has this document been processed before?
SELECT id, run_uid, decision, completed_at
FROM runs
WHERE input_file_hash = ?
  AND status = 'completed'
  AND created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 1;
```

---

## 6. Core Modules

This section specifies the public interface of each module. Implementation details belong in code; this describes what each module offers to its callers.

### 6.1 `papertrail.orchestration`

Owns the LangGraph state machine. Entry point for all pipeline runs.

```python
from papertrail.models.pipeline_state import PipelineState

class PipelineRunner:
    async def run(self, run_id: str) -> PipelineState:
        """Execute the pipeline for an existing run row. Returns final state."""

    async def resume(self, run_id: str, hitl_resolution: dict) -> PipelineState:
        """Resume a paused run after HITL resolution."""

    async def cancel(self, run_id: str) -> None:
        """Cancel a running or paused run."""
```

The graph itself is built in `graph.py`:

```python
def build_graph() -> StateGraph:
    g = StateGraph(PipelineState)
    g.add_node("preupload", preupload_node)
    g.add_node("classify", classify_node)
    g.add_node("pass_a", pass_a_node)
    g.add_node("pass_b", pass_b_node)
    g.add_node("pass_c", pass_c_node)
    g.add_node("pass_d", pass_d_node)
    g.add_node("correction", correction_node)
    g.add_node("suggestion", suggestion_node)
    g.add_node("decide", decide_node)
    g.add_node("act", act_node)

    g.set_entry_point("preupload")

    g.add_edge("preupload", "classify")
    g.add_conditional_edges("classify", route_after_classify,
                            {"proceed": "pass_a", "hitl": END})
    g.add_edge("pass_a", "pass_b")
    g.add_edge("pass_b", "pass_c")
    g.add_edge("pass_c", "pass_d")
    g.add_conditional_edges("pass_d", route_after_validation,
                            {"proceed": "decide",
                             "retry": "correction",
                             "exhausted": "suggestion"})
    g.add_edge("correction", "pass_c")
    g.add_edge("suggestion", END)  # pauses for HITL
    g.add_edge("decide", "act")
    g.add_edge("act", END)

    return g.compile(checkpointer=PostgresSaver(...))
```

### 6.2 `papertrail.passes`

Each pass is a pure async function: `state -> state`. Signature:

```python
async def preupload_node(state: PipelineState) -> PipelineState:
    # read input file, run checks, update state.preupload_result
    # write run_passes row, write trace events
    return state
```

Every pass must:
- Read its inputs from state (never from the database directly)
- Write at least one `run_passes` row
- Write at least one `trace_events` row per significant event
- Return the updated state
- Never raise. Errors are represented in state as `state.error` and routing handles them.

### 6.3 `papertrail.engines`

Engine adapters implement the `Engine` protocol:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LayoutEngine(Protocol):
    async def analyze(self, file_uri: str, options: dict) -> LayoutResult: ...

@runtime_checkable
class TextExtractionEngine(Protocol):
    async def extract(self, file_uri: str, region: Region | None) -> TextResult: ...

@runtime_checkable
class OCREngine(Protocol):
    async def ocr(self, image_bytes: bytes, region: Region | None) -> OCRResult: ...

@runtime_checkable
class VisionEngine(Protocol):
    async def extract_with_vision(
        self, file_uri: str, schema: dict, prompt: str
    ) -> VisionResult: ...
```

The dispatcher reads `engines.json` and the Playbook's `meta.engines` to decide which implementation to use for each call. Implementations are registered by name in `engines/__init__.py`.

### 6.4 `papertrail.llm`

```python
class LLMClient:
    async def call(
        self,
        stage: str,
        messages: list[dict],
        schema: type[BaseModel] | None = None,
        **kwargs
    ) -> dict:
        """Route to correct model based on stage. Handle retries and fallback.
        If schema provided, use Instructor to return typed Pydantic."""
```

Stage values map to model choices in `config/llm.json`. Instructor integration is automatic when `schema` is provided. Every call is traced to Langfuse with stage as metadata.

### 6.5 `papertrail.validation`

```python
class ValidationRunner:
    async def validate(
        self,
        elements: dict[str, ExtractedElement],
        validate_config: dict,
    ) -> ValidationResult:
        """Run hard rules, soft rules, cross-field rules. Return structured result."""
```

Hard rules are in `validation/rules/hard.py` as a name-keyed dictionary of callables. Soft rules call the LLM with the per-rule or default prompt template. The runner iterates rules per element and collects results without short-circuiting.

### 6.6 `papertrail.decision`

```python
class DecisionEngine:
    async def decide(
        self,
        state: PipelineState,
        rules_config: dict,
    ) -> DecisionResult:
        """Evaluate conditions in order. Run transformations. Resolve precedence.
        Return the final decision with all fired rules recorded."""
```

Conditions use a restricted expression language evaluated in `decision/expressions.py`. Transformations call into the tool registry. The precedence resolver picks the strongest action from `[reject, escalate, flag, approve]`.

### 6.7 `papertrail.tools`

```python
class ToolRegistry:
    def register(self, name: str, handler: Callable) -> None: ...
    def get(self, name: str) -> Callable: ...

    async def call(
        self,
        name: str,
        inputs: dict,
    ) -> dict:
        """Invoke a registered tool with validated input, return validated output."""
```

Tools are registered at application startup by reading the `tools` table and importing each handler. Input and output are validated against the stored JSON schemas before the call returns.

### 6.8 `papertrail.playbooks`

```python
class PlaybookLoader:
    async def load(self, slug: str, version: str | None = None) -> MergedPlaybook:
        """Load Playbook from DB, resolve inheritance chain, merge, validate."""

class PlaybookValidator:
    def validate(self, playbook: MergedPlaybook) -> ValidationErrors | None:
        """Check all prompt templates exist, all tool names are registered,
        all schemas are well-formed, all referenced engines are available."""
```

The loader follows `extends_playbook_id` recursively (typically one level to `_base`). The merger applies deep merge semantics: Playbook values override parent values; for lists, the Playbook's list replaces the parent's entirely (no list concat).

### 6.9 `papertrail.storage`

Repository pattern over SQLAlchemy models:

```python
class RunRepository:
    async def create(self, run: RunCreate) -> Run: ...
    async def get(self, run_id: UUID) -> Run | None: ...
    async def get_by_uid(self, run_uid: str) -> Run | None: ...
    async def get_by_hash(self, file_hash: str, within_days: int) -> Run | None: ...
    async def update_status(self, run_id: UUID, status: str) -> None: ...
    async def list(self, filter: RunFilter) -> list[Run]: ...

class TraceRepository:
    async def emit(self, event: TraceEvent) -> None: ...
    async def get_for_run(self, run_id: UUID) -> list[TraceEvent]: ...
```

Similar repositories for `PlaybookRepository`, `ElementRepository`, `HITLRepository`.

Blob storage:

```python
class BlobStore(Protocol):
    async def put(self, key: str, data: bytes) -> str: ...  # returns URI
    async def get(self, uri: str) -> bytes: ...
    async def delete(self, uri: str) -> None: ...
```

---

## 7. Pipeline State Machine

The LangGraph state is the spine of every run.

### 7.1 PipelineState definition

```python
from typing import TypedDict
from papertrail.models.extraction import (
    LayoutResult, RawExtractionResult, SchemaExtractionResult
)
from papertrail.models.validation import ValidationResult
from papertrail.models.decision import DecisionResult

class PipelineState(TypedDict, total=False):
    # Identity
    run_id: str            # UUID as string
    run_uid: str           # human-readable
    playbook_id: str

    # Playbook (merged with _base)
    playbook: dict         # MergedPlaybook serialized

    # Input
    input_file_uri: str
    input_file_hash: str
    input_file_mime: str

    # Pass results
    preupload_result: dict | None
    classification: dict | None
    pass_a_output: dict | None
    pass_b_output: dict | None
    pass_c_output: dict | None
    pass_d_output: dict | None

    # Correction loop state
    correction_attempts: int
    correction_history: list[dict]

    # Decision
    decision_result: dict | None

    # HITL
    awaiting_hitl: bool
    hitl_checkpoint_type: str | None
    hitl_context: dict | None

    # Confidence accumulator
    confidence_budget: float
    warnings: list[dict]

    # Error state
    error: str | None
    failed_stage: str | None
```

### 7.2 Conditional routing

```python
def route_after_classify(state: PipelineState) -> str:
    classification = state.get("classification")
    if not classification:
        return "error"
    if classification["confidence"] < state["playbook"]["classify"]["hitl_threshold"]:
        return "hitl"
    return "proceed"

def route_after_validation(state: PipelineState) -> str:
    result = state.get("pass_d_output")
    if not result:
        return "error"
    if result["passed"]:
        return "proceed"
    max_attempts = state["playbook"]["validate"]["correction"]["max_attempts"]
    if state.get("correction_attempts", 0) >= max_attempts:
        return "exhausted"
    return "retry"
```

### 7.3 HITL pause and resume

At HITL checkpoints, the node sets `state["awaiting_hitl"] = True` and writes a `run_hitl_events` row with status `awaiting`. The graph terminates at that point. The LangGraph `PostgresSaver` persists the state.

To resume, the caller resolves the checkpoint via CLI or API with a resolution payload, then calls `PipelineRunner.resume(run_id, resolution)`. This loads the saved state, applies the resolution to the appropriate state field, and re-enters the graph from the paused node's downstream edge.

### 7.4 Failure handling

Every node wraps its work in a try-except. On exception:
- `state["error"]` is set with the exception message
- `state["failed_stage"]` is set with the node name
- A `trace_events` row with level `error` is written
- The node returns state

A top-level handler routes states with `error` set to a terminal `failed` state. The run row is updated with status `failed`. No further passes execute.

---

## 8. LLM Layer

### 8.1 Client design

The LLM client wraps the OpenRouter API (which is OpenAI-compatible). One client, many models, routed by stage.

```python
class LLMClient:
    def __init__(self, config: LLMConfig):
        self._openrouter = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.api_key,
        )
        self._config = config
        self._langfuse = Langfuse()

    async def call(
        self,
        stage: str,
        messages: list[dict],
        schema: type[BaseModel] | None = None,
        images: list[bytes] | None = None,
        run_id: str | None = None,
        **kwargs,
    ) -> Any:
        stage_config = self._config.stages[stage]
        primary = stage_config["primary"]
        fallback = stage_config["fallback"]

        # Try primary twice, then fallback twice
        for model in (primary, fallback):
            for attempt in range(2):
                try:
                    return await self._call_model(model, messages, schema, images, run_id, stage)
                except (RateLimitError, ServiceUnavailable):
                    await asyncio.sleep(2 ** attempt)
                    continue
                except Exception as e:
                    # unrecoverable
                    raise LLMError(f"{model} failed: {e}")
        raise LLMAllProvidersFailedError()
```

### 8.2 Structured output via Instructor

When `schema` is provided, the client wraps the call with Instructor to get a typed Pydantic response with automatic retry on parse failure.

```python
import instructor

async def _call_with_schema(
    self, model: str, messages: list[dict], schema: type[BaseModel]
) -> BaseModel:
    client = instructor.from_openai(self._openrouter, mode=instructor.Mode.JSON)
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        response_model=schema,
        max_retries=2,
    )
```

### 8.3 Langfuse integration

Every call creates a Langfuse generation with:
- Input messages
- Model used
- Stage name
- Run ID as metadata
- Token counts and latency
- Output (raw or parsed)

Traces are nested under a trace per run, making run-level drill-down trivial in the Langfuse UI.

### 8.4 Configuration

`config/llm.json`:

```json
{
  "api_key_env": "OPENROUTER_API_KEY",
  "stages": {
    "classify": {
      "primary": "anthropic/claude-haiku-4.5",
      "fallback": "openai/gpt-4o-mini",
      "max_tokens": 500,
      "temperature": 0.1
    },
    "extract": {
      "primary": "anthropic/claude-sonnet-4.5",
      "fallback": "openai/gpt-4o",
      "max_tokens": 4000,
      "temperature": 0.0
    },
    "validate_soft": {
      "primary": "anthropic/claude-haiku-4.5",
      "fallback": "openai/gpt-4o-mini",
      "max_tokens": 300,
      "temperature": 0.1
    },
    "correct_suggest": {
      "primary": "anthropic/claude-sonnet-4.5",
      "fallback": "openai/gpt-4o",
      "max_tokens": 2000,
      "temperature": 0.2
    }
  },
  "retry": {
    "attempts_per_provider": 2,
    "backoff_base_seconds": 2
  }
}
```

Demo override: copy this file to `llm.demo.json` and swap Sonnet for `anthropic/claude-opus-4.7`. Runtime picks config based on `APP_ENV`.

---

## 9. Engine Dispatcher

### 9.1 Responsibility

The dispatcher routes Pass B region extractions to the right engine based on region type, file type, and Playbook configuration. It also manages fallback when an engine fails or returns low confidence.

### 9.2 Dispatch logic

```python
class EngineDispatcher:
    def __init__(self, engines: dict, default_config: dict):
        self._engines = engines
        self._default_config = default_config

    async def extract_region(
        self,
        region: Region,
        file_uri: str,
        file_mime: str,
        playbook_engines: dict,
    ) -> RegionExtractionResult:
        # Determine engine priority list for this region type
        if region.type == "text" and file_mime == "application/pdf":
            primary = playbook_engines.get("text_extraction", "pymupdf")
            fallback = "paddleocr"
        elif region.type == "table":
            primary = playbook_engines.get("tables", "pdfplumber")
            fallback = "paddleocr"
        elif region.type == "image" or file_mime.startswith("image/"):
            primary = playbook_engines.get("ocr", "paddleocr")
            fallback = "tesseract"
        # ...

        result = await self._engines[primary].extract(file_uri, region)
        if result.confidence < 0.5:
            fallback_result = await self._engines[fallback].extract(file_uri, region)
            if fallback_result.confidence > result.confidence:
                result = fallback_result

        return result
```

### 9.3 Fallback representation

Pass B always produces both structured region output AND a full-page OCR pass when any of:
- Layout confidence is below 0.75
- File mime is an image type (scans often have layout issues)
- Playbook explicitly requests `always_fallback: true` in meta.engines

The fallback is stored alongside the structured output and passed to Pass C. The LLM can reconcile them.

### 9.4 engines.json

```json
{
  "defaults": {
    "layout": "docling",
    "text_extraction": "pymupdf",
    "ocr": "paddleocr",
    "ocr_fallback": "tesseract",
    "tables": "pdfplumber",
    "vision": null
  },
  "confidence_threshold_for_fallback": 0.5,
  "layout_confidence_threshold_for_full_page_ocr": 0.75,
  "ocr_languages": ["en", "hi"]
}
```

---

## 10. Playbook Loader and Inheritance

### 10.1 Load flow

```
load(slug, version=None)
  ↓
fetch Playbook row by slug (latest active if version=None)
  ↓
fetch all 6 config rows
  ↓
if extends_playbook_id is not NULL:
    recursively load parent
  ↓
merge parent + this Playbook (deep merge)
  ↓
validate merged result
  ↓
return MergedPlaybook
```

### 10.2 Merge semantics

Deep merge with these rules:
- Objects: merged key by key; child wins on conflicts
- Arrays: child fully replaces parent (no concat)
- Primitives: child wins
- null in child: removes the key from parent (explicit deletion)

Example:

```python
# _base
{"preupload": {"checks": {"blur": {"enabled": False, "threshold": 100}}}}

# indian_cheque
{"preupload": {"checks": {"blur": {"enabled": True}}}}

# merged result
{"preupload": {"checks": {"blur": {"enabled": True, "threshold": 100}}}}
```

For arrays, the intent is that a Playbook declares its full list when it overrides. `_base.classify.candidates` is empty; each Playbook declares its own.

### 10.3 Validation at load time

The validator catches these issues:
- Referenced prompt template files do not exist
- Referenced tools are not registered
- Referenced engines are not available
- Schema mode has an empty elements list
- Correction `max_attempts` is not a positive integer
- Conditions reference elements not in the schema
- Cross-field rules reference elements not in the schema
- Expression language syntax errors in conditions

A validation failure raises `PlaybookValidationError` with a list of issues. The CLI `papertrail playbook validate <slug>` runs the validator against a Playbook for author feedback.

### 10.4 Seeder

`papertrail.playbooks.seeder`:

```python
async def seed_from_folder(folder: Path) -> SeedResult:
    """Read _base and starter Playbooks from playbooks_seed/ and upsert into DB."""
```

Run from CLI: `papertrail db seed`. Idempotent. Creates new versions if content has changed. Never deletes.

---

## 11. Validation Rules Engine

### 11.1 Hard rules

Hard rules are Python callables registered by name:

```python
HARD_RULES: dict[str, HardRule] = {
    "required": required_rule,
    "regex": regex_rule,
    "valid_date": valid_date_rule,
    "not_future": not_future_rule,
    "positive_decimal": positive_decimal_rule,
    "non_empty": non_empty_rule,
    "in_list": in_list_rule,
    "range": range_rule,
    # ...
}

class HardRule(Protocol):
    def __call__(self, value: Any, params: dict, context: dict) -> RuleResult: ...

def regex_rule(value: Any, params: dict, context: dict) -> RuleResult:
    pattern = params["pattern"]
    if value is None:
        return RuleResult(passed=False, reason="Value is null")
    if not re.fullmatch(pattern, str(value)):
        return RuleResult(passed=False, reason=f"Does not match pattern {pattern}")
    return RuleResult(passed=True)
```

Each rule is a pure function. No IO, no side effects. Testable in isolation.

### 11.2 Soft rules

Soft rules call the LLM with a prompt template:

```python
async def run_soft_rule(
    value: Any,
    prompt_template: str,
    element_name: str,
    context: dict,
    llm_client: LLMClient,
) -> RuleResult:
    template = load_prompt(prompt_template)
    rendered = template.format(value=value, element=element_name, context=context)

    class SoftRuleResponse(BaseModel):
        passed: bool
        confidence: float
        reason: str

    response = await llm_client.call(
        stage="validate_soft",
        messages=[{"role": "user", "content": rendered}],
        schema=SoftRuleResponse,
    )
    return RuleResult(passed=response.passed, reason=response.reason, confidence=response.confidence)
```

### 11.3 Cross-field rules

Cross-field rules receive multiple element values:

```python
async def run_cross_field_rule(
    rule_config: dict,
    elements: dict[str, ExtractedElement],
    llm_client: LLMClient,
) -> RuleResult:
    referenced = {name: elements[name].value for name in rule_config["elements"]}
    # Check all referenced elements are not null
    if any(v is None for v in referenced.values()):
        return RuleResult(passed=None, status="unable_to_evaluate")

    if rule_config["type"] == "hard":
        # Custom code rule
        return HARD_CROSS_FIELD_RULES[rule_config["name"]](referenced)
    else:
        # Soft rule via LLM
        return await run_soft_cross_field(rule_config, referenced, llm_client)
```

### 11.4 Scoring

After all rules run, aggregate confidence is computed:

```python
def compute_aggregate(
    elements: dict[str, ExtractedElement],
    validation_results: dict[str, RuleResult],
    scoring_config: dict,
    warnings_so_far: list[Warning],
) -> float:
    # Start with confidence budget
    score = scoring_config.get("confidence_budget_start", 1.0)

    # Penalty per warning
    warning_penalty = scoring_config.get("warning_penalty", 0.05)
    score -= len(warnings_so_far) * warning_penalty

    # Weighted per-element confidence
    total_weight = 0.0
    weighted_sum = 0.0
    for name, elem in elements.items():
        weight = scoring_config.get("critical_weight", 3.0) if elem.critical else 1.0
        per_elem_score = (elem.llm_confidence + elem.ocr_confidence) / 2
        weighted_sum += per_elem_score * weight
        total_weight += weight

    extraction_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    # Combine budget and extraction
    aggregate = min(score, extraction_score)
    return max(0.0, aggregate)
```

---

## 12. Decision Engine

### 12.1 Expression language

Conditions use a restricted expression language. Expressions are parsed and evaluated in a sandbox that only allows:

- Element references: `elements.<name>`
- Run context: `run.<attribute>` (aggregate_confidence, correction_attempts, warnings, etc.)
- Comparison operators: `<`, `<=`, `==`, `!=`, `>=`, `>`
- Logical operators: `and`, `or`, `not`
- Built-in helpers: `days_since(date)`, `days_until(date)`, `sum(list)`, `len(list)`, `abs(x)`

```python
class ExpressionEvaluator:
    def evaluate(self, expression: str, context: dict) -> Any:
        """Parse and evaluate an expression against context dict."""

context = {
    "elements": {"amount_figures": 54321, "date": date(2026, 1, 15), ...},
    "run": {"aggregate_confidence": 0.82, "correction_attempts": 1, ...}
}
```

Implementation uses Python's `ast` module with a whitelist walker to reject anything outside the allowed grammar. No `eval()`, no code execution. The evaluator throws on unsafe constructs.

### 12.2 Condition evaluation

```python
async def evaluate_conditions(
    conditions: list[dict],
    context: dict,
) -> list[ConditionResult]:
    results = []
    for order, cond in enumerate(conditions):
        try:
            if cond["type"] == "hard":
                fired = evaluator.evaluate(cond["expression"], context)
            else:  # LLM-backed condition
                fired = await run_llm_condition(cond, context)
            results.append(ConditionResult(
                rule_name=cond["name"],
                fired=bool(fired),
                action=cond["action"] if fired else None,
                reason=cond["reason"] if fired else None,
                order_executed=order,
            ))
        except Exception as e:
            results.append(ConditionResult(
                rule_name=cond["name"], fired=False,
                error=str(e), order_executed=order,
            ))
    return results
```

### 12.3 Transformations

```python
async def run_transformations(
    transformations: list[dict],
    state: PipelineState,
    tool_registry: ToolRegistry,
    decision_so_far: str,
) -> dict:
    enriched = {}
    for t in transformations:
        # Skip if decision excludes this transformation
        run_on = t.get("run_on", ["approve", "flag", "reject", "escalate"])
        if decision_so_far not in run_on:
            continue
        input_expr = t["input"]
        input_value = evaluator.evaluate(input_expr, build_context(state))
        result = await tool_registry.call(t["tool"], {"input": input_value})
        set_nested_field(enriched, t["output_field"], result["output"])
    return enriched
```

### 12.4 Precedence resolution

```python
PRECEDENCE = ["reject", "escalate", "flag", "approve"]

def resolve_precedence(fired_conditions: list[ConditionResult]) -> str:
    if not any(c.fired for c in fired_conditions):
        return "approve"
    actions = [c.action for c in fired_conditions if c.fired]
    for action in PRECEDENCE:
        if action in actions:
            return action
    return "approve"  # fallback
```

---

## 13. Tool Registry

### 13.1 Initial tool set

Four tools ship with v1:

#### `ifsc_api`

Look up an IFSC code against a public API or a local cached lookup.

```python
async def ifsc_lookup(inputs: dict) -> dict:
    code = inputs["input"]
    # Call razorpay.com/methods/ifsc/{code} or similar
    resp = await httpx_client.get(f"https://ifsc.razorpay.com/{code}")
    if resp.status_code != 200:
        return {"output": None, "error": "IFSC not found"}
    data = resp.json()
    return {"output": {
        "bank": data["BANK"],
        "branch": data["BRANCH"],
        "city": data["CITY"],
        "state": data["STATE"],
    }}
```

#### `pan_validate`

Validate PAN format and checksum.

```python
def pan_validate(inputs: dict) -> dict:
    pan = inputs["input"]
    if not re.fullmatch(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
        return {"output": {"valid": False, "reason": "Invalid format"}}
    # Additional checksum logic if applicable
    return {"output": {"valid": True}}
```

#### `date_utils`

Parse dates in various Indian formats, compute age, etc.

```python
def date_parse(inputs: dict) -> dict:
    raw = inputs["input"]
    # Try DD/MM/YYYY, DD-MM-YYYY, "15 Jan 2026", "15-Jan-2026", ISO
    # Return ISO date string
```

#### `currency_normalize`

Round to two decimals, handle rupee-paise formats, parse Indian number format (lakhs/crores).

```python
def currency_normalize(inputs: dict) -> dict:
    raw = inputs["input"]
    # "1,23,456.78" -> 123456.78
    # "1.23 lakh" -> 123000.00
    return {"output": parsed_decimal}
```

### 13.2 Registration

At application startup, the registry loads tools from the `tools` table and imports their handlers:

```python
async def bootstrap_registry() -> ToolRegistry:
    registry = ToolRegistry()
    async with get_session() as session:
        tools = await session.execute(select(ToolModel).where(ToolModel.is_active))
        for tool in tools.scalars():
            module_path, attr = tool.handler.rsplit(":", 1)
            module = importlib.import_module(module_path)
            handler = getattr(module, attr)
            registry.register(tool.name, handler, tool.input_schema, tool.output_schema)
    return registry
```

### 13.3 Adding new tools

To add a tool:
1. Write the handler function in `papertrail/tools/your_tool.py`
2. Insert a row into the `tools` table with the handler path
3. Reference the tool name in Playbook `rules.transformations`

No core code changes. No restart required for new Playbooks using existing tools.

---

## 14. Observability

### 14.1 What gets logged

Three complementary channels:

**structlog (application events).** Every stage transition, every validation rule result, every rule firing, every HITL pause. JSON output. Fields: `run_id`, `stage`, `event`, `level`, plus event-specific fields.

**Langfuse (LLM calls).** Every LLM invocation with prompt, model, tokens, latency, stage, run_id metadata. Cross-provider (works identically for OpenRouter-routed calls).

**trace_events table (canonical record).** Database-persisted version of every significant event. Queryable with SQL. This is the append-only audit log.

### 14.2 Event types

Standardized event type strings used across all three channels:

| Event | When emitted |
|---|---|
| `stage_enter` | First action in a node |
| `stage_exit` | Last action in a node, with duration |
| `stage_failed` | Node raised an exception |
| `preupload_check_passed` | A preupload check passed |
| `preupload_check_warning` | A preupload check emitted a warning |
| `preupload_check_blocked` | A preupload check blocked processing |
| `duplicate_detected` | SHA256 match found |
| `classification_result` | Classifier returned type and confidence |
| `hitl_triggered` | HITL checkpoint created |
| `hitl_resolved` | HITL checkpoint resolved |
| `engine_dispatched` | An engine was called for a region |
| `engine_fallback_used` | Primary engine failed, fallback used |
| `fallback_ocr_added` | Full-page OCR added due to low layout confidence |
| `extraction_element_extracted` | One element extracted |
| `validation_rule_evaluated` | One rule evaluated |
| `validation_result` | Aggregate validation result computed |
| `correction_started` | Correction loop attempt begins |
| `correction_hint_generated` | Hint text produced |
| `correction_completed` | Correction attempt finished |
| `correction_exhausted` | Max attempts reached |
| `suggestion_generated` | Diagnostic suggestion produced |
| `condition_evaluated` | Decision condition evaluated |
| `condition_fired` | Condition produced an action |
| `transformation_ran` | Transformation completed |
| `decision_final` | Final action resolved |
| `run_completed` | Run reached final state |
| `run_failed` | Run ended in failure |

### 14.3 Implementation pattern

```python
# In papertrail/observability/logging.py
import structlog

logger = structlog.get_logger()

async def emit(
    run_id: str,
    stage: str,
    event: str,
    level: str = "info",
    **payload,
):
    # Write to structlog
    logger.bind(run_id=run_id, stage=stage, event=event).log(
        level.upper(), event, **payload
    )
    # Write to trace_events table
    await trace_repo.emit(TraceEvent(
        run_id=run_id,
        stage=stage,
        event_type=event,
        level=level,
        payload=payload,
    ))
```

Every node calls `emit()` at least twice: once on entry, once on exit.

---

## 15. CLI Specification

### 15.1 Command tree

```
papertrail
├── run                Run a document through the pipeline
├── playbook
│   ├── list           List available Playbooks
│   ├── show           Show a Playbook's merged config
│   ├── validate       Validate a Playbook's config
│   ├── import         Import a Playbook folder into the DB
│   └── export         Export a DB Playbook to a folder
├── runs
│   ├── list           List recent runs
│   ├── show           Show run details and final output
│   └── trace          Show the full trace log for a run
├── hitl
│   ├── list           Show pending HITL checkpoints
│   └── resolve        Resolve a checkpoint and resume the run
├── db
│   ├── migrate        Apply pending Alembic migrations
│   ├── seed           Seed Playbooks and tools into the DB
│   └── reset          Drop all tables and re-create (dev only)
└── eval
    └── run            Run the evaluation dataset
```

### 15.2 Command details

**`papertrail run <file>`**

```
papertrail run cheque_sample.jpg --playbook indian_cheque

Options:
  --playbook TEXT              Playbook slug (required)
  --version TEXT               Playbook version (default: latest active)
  --force-rerun                Skip duplicate detection
  --skip-hitl                  Fail if HITL is triggered (useful for testing)
  --output FORMAT              Output format: json, summary, verbose (default: summary)
  --save                       Save output JSON to data/exports/
```

Output format `summary` prints a compact one-screen result:

```
Run: run_20260420_143201_indian_cheque_abc123
Playbook: indian_cheque@1.0
Status: completed
Decision: flag
Confidence: 0.78
Warnings: 3

Extracted:
  payee_name: Rajesh Kumar
  amount_figures: 54321.00
  amount_words: Fifty Four Thousand Three Hundred Twenty One
  date: 2026-01-15
  account_number: 50100123456789
  ifsc_code: HDFC0000146

Enriched:
  bank_branch: HDFC Mumbai Andheri East

Reasons for flag:
  - Cheque is 95 days old (stale threshold: 90)

Duration: 12.4s
```

**`papertrail playbook list`**

```
SLUG                        VERSION  NAME                        ACTIVE
_base                       1.0      Base                        yes
indian_cheque               1.0      Indian Cheque               yes
indian_bank_statement       1.0      Indian Bank Statement       yes
indian_salary_slip          1.0      Indian Salary Slip          yes
indian_itr_form             1.0      Indian ITR Form             yes
```

**`papertrail playbook show <slug>`**

Prints the merged config (with `_base` resolved) as JSON. Useful for debugging inheritance.

**`papertrail playbook validate <slug>`**

Runs the Playbook validator. Exits with code 0 on success, non-zero with error list on failure.

**`papertrail runs list`**

```
papertrail runs list --playbook indian_cheque --decision flag --limit 10

RUN_UID                                  PLAYBOOK          STATUS     DECISION  CONF   CREATED
run_20260420_143201_cheque_abc123        indian_cheque     completed  flag      0.78   2m ago
run_20260420_141508_cheque_def456        indian_cheque     completed  approve   0.94   18m ago
...
```

**`papertrail runs show <run-uid>`**

Full run details. Extracted fields, rules fired, warnings, trace summary.

**`papertrail runs trace <run-uid>`**

Full trace log. One line per event:

```
14:32:01.234  preupload       stage_enter
14:32:01.245  preupload       check_passed        check=file_integrity
14:32:01.267  preupload       check_warning       check=blur value=72 threshold=100
14:32:01.278  preupload       stage_exit          duration_ms=44
14:32:01.290  classify        stage_enter
14:32:02.801  classify        classification_result  type=indian_cheque confidence=0.94
14:32:02.815  classify        stage_exit          duration_ms=1525
...
```

**`papertrail hitl list`**

```
RUN_UID                                  CHECKPOINT             WAITING
run_20260420_143201_cheque_abc123        classify_low_confidence  5m
```

**`papertrail hitl resolve <run-uid>`**

Interactive: prompts for the resolution based on checkpoint type. For classification, shows candidate types and asks the user to pick. For correction exhausted, shows the suggestion and asks for override/reject.

**`papertrail db migrate`**

Applies pending Alembic migrations.

**`papertrail db seed`**

Seeds `_base` and starter Playbooks from `playbooks_seed/`.

**`papertrail eval run`**

Runs the evaluation dataset and reports accuracy metrics.

### 15.3 Implementation notes

- Click as the framework. One command = one function in `cli/commands/`.
- Click groups match the tree structure above.
- All commands are async-friendly via `asyncio.run()` wrapper.
- `papertrail` command is installed as a console script via pyproject.toml.

---

## 16. REST API Specification

### 16.1 Endpoints

```
POST   /api/v1/runs
         Body: multipart (file + playbook_slug)
         Returns: {run_uid, status: "running" | "awaiting_hitl"}

GET    /api/v1/runs/{run_uid}
         Returns: full run details including extracted fields

GET    /api/v1/runs/{run_uid}/trace
         Returns: list of trace events

GET    /api/v1/runs
         Query: ?playbook=&decision=&status=&limit=
         Returns: paginated list

POST   /api/v1/runs/{run_uid}/cancel
         Cancels a running or paused run

GET    /api/v1/playbooks
         Returns: list

GET    /api/v1/playbooks/{slug}
         Returns: merged Playbook config

GET    /api/v1/hitl/pending
         Returns: list of pending HITL checkpoints

POST   /api/v1/hitl/{run_uid}/resolve
         Body: {checkpoint_type, resolution: {...}}
         Resumes the run

GET    /health
         Returns: {status: "ok", db: "connected", llm: "reachable"}

GET    /metrics
         Returns: Prometheus-format metrics (later)
```

### 16.2 Async upload handling

Uploading a document is a long operation. Two modes:

- **Polling.** `POST /runs` returns immediately with run_uid and status. Client polls `GET /runs/{run_uid}` until status is `completed`, `failed`, or `awaiting_hitl`.
- **Synchronous (for testing).** `POST /runs?wait=true` blocks until the run completes or pauses. Not for production.

We ship with polling. Streamlit UI polls every 2 seconds while a run is active.

### 16.3 Authentication

Out of scope for v1. The API runs without authentication. For the demo, the API is bound to localhost only.

---

## 17. Prompt Templates

System-level prompts live in `config/prompts/`. Playbooks can reference these or provide their own overrides.

### 17.1 Classification prompt (`classify_default.txt`)

```
You are a document classifier for Indian financial documents.

Here is the first {preview_chars} characters of a document:

---
{document_preview}
---

Classify this document as one of the following types:

{candidates_formatted}

If none of the candidates match, return type: "unknown".

Respond with a JSON object matching this schema:
{
  "type": "<label from candidates, or 'unknown'>",
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining the classification>"
}

Be strict about confidence. If you are uncertain, return a lower confidence
rather than picking a weak match.
```

### 17.2 Schema extraction prompt (`extract_schema.txt`)

```
You are extracting structured data from a document.

Document type: {document_type}

Here is the raw text extracted from the document, by region:
{region_text_formatted}

{full_page_fallback_section}

Your task is to extract the following elements. For each element, return:
- the extracted value (or null if genuinely not present)
- your confidence that the value is correct (0.0 to 1.0)
- which region you extracted it from
- any notes if you inferred, corrected, or had to resolve ambiguity

IMPORTANT:
- If a field is not present in the document, return null. Do NOT guess.
- If you had to correct obvious OCR errors (like O->0 or l->1), note this.
- The OCR confidence for each region is shown. Be more skeptical of
  values from regions with low OCR confidence.

Elements to extract:
{elements_formatted}

Return a JSON object matching the schema provided.
```

### 17.3 Natural extraction prompt (`extract_natural.txt`)

```
You are extracting information from a document.

Document type: {document_type}

Here is the raw text extracted from the document:
{region_text_formatted}

Based on the following natural-language description, extract what you can:

{natural_description}

Return a JSON object with whatever fields you can extract. For each field:
- value: the extracted value
- confidence: 0.0 to 1.0
- source: where in the document you found it

Do your best. Null is acceptable if you cannot find something.
```

### 17.4 Soft validation prompt (`validate_soft_default.txt`)

```
You are validating an extracted field.

Element: {element_name}
Value: {value}
Additional context: {context}

Question: {validation_question}

Respond with:
{
  "passed": true | false,
  "confidence": <0.0 to 1.0>,
  "reason": "<brief explanation>"
}
```

### 17.5 Correction hint prompt (`correct_hint.txt`)

```
You are correcting a failed extraction.

Document type: {document_type}

Extraction attempt {attempt_number} failed on: {element_name}

Current value: {current_value}
Validation issue: {failure_reason}

Other elements (for context):
{other_elements_formatted}

Cross-field constraints that might help:
{cross_field_hints}

Original region text:
{region_text}

Please re-extract {element_name}. Use the context above to resolve ambiguity.
If you still cannot determine the value, return null.

Return JSON:
{
  "value": <extracted value or null>,
  "confidence": <0.0 to 1.0>,
  "notes": "<brief note on reasoning or corrections made>"
}
```

### 17.6 Suggestion prompt (`suggest.txt`)

```
You are a diagnostic assistant. A document processing pipeline has exhausted
its correction retries on a document. Your job is to produce a summary and
suggestions for a human reviewer.

Document type: {document_type}
Final status: extraction failed after {max_attempts} attempts

Pipeline trace (relevant stages only):
{trace_formatted}

Failed elements after all attempts:
{failed_elements_formatted}

Produce a JSON response with:
{
  "summary": "<2-3 sentences describing what went wrong>",
  "suggestions": [
    {
      "type": "extraction_region" | "validation_rule" | "image_quality" | "playbook_config",
      "element": "<element name if relevant, null otherwise>",
      "detail": "<specific suggestion>"
    }
  ],
  "escalation_reason": "<why this needs a human>"
}

Be specific. Don't say "improve extraction" — say exactly which region
looks problematic and why.
```

---

## 18. Error Handling Strategy

### 18.1 Error categories

Errors fall into four categories with different handling:

| Category | Example | Handling |
|---|---|---|
| Configuration errors | Playbook validation failed | Fail fast at load time. Never start the run. |
| Input errors | Corrupt file, unsupported format | Pre-upload blocks. Run fails with clear reason. |
| Transient errors | LLM rate limit, network timeout | Retry with backoff. Fall back to alternative provider. |
| Logic errors | Impossible state, assertion failure | Emit error trace event. Fail the run. Alert dev. |

### 18.2 Where errors are raised vs recorded

**Never raise:**
- From inside a pass node. Errors go into state and routing handles them.
- From within a rule (hard or soft). Rule returns `RuleResult` with error fields set.
- From a tool call. Tool returns `{output: null, error: "..."}`.

**Always raise:**
- From the Playbook loader/validator if config is invalid.
- From the orchestration layer on impossible state.
- From the LLM client when all fallbacks are exhausted.

### 18.3 Retry discipline

- LLM calls: 2 attempts on primary, 2 on fallback, exponential backoff.
- Tool HTTP calls: 1 attempt, timeout 10s, no retry (tools should be fast).
- Database operations: SQLAlchemy handles connection retry at the pool level.
- Blob storage writes: 1 attempt. Failures bubble up.

### 18.4 Partial failure behaviour

- If Pass B fails on one region but others succeed, Pass C receives what was extracted with `extraction_status: partial` in the state.
- If one soft validation rule times out, the rule is marked `unable_to_evaluate` and validation continues.
- If a transformation tool fails, the transformation is skipped and logged; the decision proceeds on what was extracted.

The pipeline is designed to produce some output whenever possible. Full failure is reserved for cases where no meaningful output can be produced.

---

## 19. Testing Strategy

### 19.1 Test pyramid

**Unit tests** (fast, many):
- Hard rule implementations: each rule with 5-10 cases
- Expression evaluator: comparison, boolean, helpers, edge cases, malicious input
- Playbook merger: deep merge scenarios, list replacement, null deletion
- Precedence resolver: all 16 combinations of 4 actions
- Scoring function: critical weight, warning penalties
- Tool implementations: each tool with valid and invalid inputs

**Integration tests** (medium speed, moderate count):
- Full pipeline on a known-good document (happy path)
- Full pipeline with forced correction retry
- Full pipeline with HITL pause and resume
- Playbook loading with `_base` inheritance
- Pass B engine dispatcher with fallback

**Evaluation tests** (slow, run on-demand):
- 20-30 curated documents, 5-10 per Playbook
- Expected outputs for each
- Metrics: exact match on extracted fields, confidence calibration, decision match

### 19.2 Running tests

```bash
# All unit tests, fast
pytest tests/unit/

# Integration tests (requires Postgres running)
pytest tests/integration/

# Evaluation (requires OpenRouter API key and network)
papertrail eval run --dataset cheques
```

### 19.3 Test fixtures

- Sample documents in `tests/fixtures/` with known-expected outputs
- Mock LLM client for unit tests (no network calls)
- Factory-boy for database fixtures
- pytest fixtures for Playbook loading, test database session

### 19.4 CI pipeline

GitHub Actions workflow:
- Run unit tests on every PR
- Run integration tests on merge to main (requires Postgres service)
- Evaluation tests run manually via workflow_dispatch

---

## 20. Development Setup

### 20.1 First-time setup

```bash
# Clone
git clone <repo>
cd papertrail

# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up Python env
source .venv/bin/activate

# Copy env template
cp .env.example .env
# Edit .env with OpenRouter API key, Langfuse keys, DB URL

# Start PostgreSQL via Docker Compose
docker compose up -d postgres

# Apply migrations
papertrail db migrate

# Seed Playbooks and tools
papertrail db seed

# Verify
papertrail playbook list
# Should show _base and 4 starter Playbooks

# Run a sample
papertrail run tests/fixtures/cheque_clean.jpg --playbook indian_cheque
```

### 20.2 `compose.yaml` for local dev

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: papertrail
      POSTGRES_PASSWORD: papertrail
      POSTGRES_DB: papertrail
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### 20.3 `.env.example`

```
# Database
DATABASE_URL=postgresql+asyncpg://papertrail:papertrail@localhost:5432/papertrail

# LLM
OPENROUTER_API_KEY=sk-or-v1-...

# Langfuse
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# App
APP_ENV=dev
LOG_LEVEL=INFO
BLOB_STORAGE_PATH=./data/blobs
```

### 20.4 IDE setup

Recommended VS Code extensions: Python, Pylance, Ruff. Settings:

```json
{
  "python.analysis.typeCheckingMode": "strict",
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "charliermarsh.ruff"
}
```

---

## 21. Milestone Plan

Four weeks, four people. The plan below assumes Monday-Friday work with Saturday for review and documentation.

### Week 1: Foundation and Skeleton

**Goal:** A runnable end-to-end pipeline with stubbed passes. CLI works. Database is seeded. Team confirms the shape of everything.

**Deliverables by end of week:**
- Postgres running, all migrations applied, schema matches Section 5
- `_base` Playbook plus 1 starter Playbook (indian_cheque) seeded
- `papertrail run` command executes end-to-end with stub passes that return canned data
- `papertrail playbook list/show/validate` work
- LangGraph skeleton compiles and runs
- Observability (structlog + Langfuse) emits events

**Task allocation:**

Person 1 (Database & Models):
- Day 1-2: Alembic setup, migrations 0001-0005
- Day 3: SQLAlchemy models and session management
- Day 4-5: Repository layer (runs, playbooks, elements, trace, hitl)

Person 2 (Playbooks):
- Day 1-2: Playbook Pydantic models for all 6 sections
- Day 3: Loader, merger, validator
- Day 4: Seeder + `_base` JSON files + indian_cheque JSON
- Day 5: Playbook CLI commands

Person 3 (Orchestration & CLI):
- Day 1: Click CLI scaffolding, command structure
- Day 2-3: LangGraph graph with stub nodes
- Day 4: State management, PipelineRunner
- Day 5: `papertrail run` command end-to-end with stubs

Person 4 (Engines & LLM & Observability):
- Day 1: Engine protocol and dispatcher scaffolding
- Day 2: LLM client with OpenRouter
- Day 3: Prompt loader, stage routing
- Day 4: structlog + Langfuse setup, emit() helper
- Day 5: Integration, fix issues

**End of Week 1 demo:** Team runs `papertrail run cheque.jpg --playbook indian_cheque` and sees a run completed row in the database with stub outputs at each stage. Trace events visible in Langfuse and `papertrail runs trace`.

### Week 2: Extraction Core

**Goal:** Real extraction on cheques and bank statements. Classification works. Pre-upload works. Schema extraction returns typed output.

**Deliverables by end of week:**
- Pre-upload checks (file integrity, format, size, blur, resolution) implemented
- Classification LLM call with decision-tree prompt
- Pass A: Docling integration, layout output with page abstraction
- Pass B: engine dispatcher routing PyMuPDF, PaddleOCR, pdfplumber
- Pass B: fallback full-page OCR when layout confidence low
- Pass C: schema extraction with Instructor + Pydantic
- All 4 passes produce correct output for the happy-path cheque

**Task allocation:**

Person 1: Pass A + Pass B engine adapters (Docling, PyMuPDF, pdfplumber)
Person 2: Pass C with prompts, Instructor wiring, schema → Pydantic model generator
Person 3: Pre-upload checks + classification + OpenCV preprocessing
Person 4: PaddleOCR engine + vision engine + engine fallback logic

**End of Week 2 demo:** Run a clean digital-PDF bank statement end-to-end; see extracted fields with per-field confidence. Run a scanned cheque; see OCR working and fields extracted correctly.

### Week 3: Validation, Correction, Decision

**Goal:** Pass D validation works with hard and soft rules. Correction loop fires and succeeds on synthetic damaged documents. Decision engine routes to correct outcomes. Tools integrate.

**Deliverables by end of week:**
- Pass D: hard rule runner with 8-10 built-in rules
- Pass D: soft rule runner using LLM
- Cross-field validation runner
- Correction loop with targeted hints, up to 3 retries
- Suggestion generation on exhaustion
- Decision engine with expression evaluator
- Tool registry with 4 tools (ifsc_api, pan_validate, date_utils, currency_normalize)
- HITL checkpoints at classification and correction exhaustion
- HITL CLI commands (list, resolve)

**Task allocation:**

Person 1: Validation rules (hard + soft + cross-field), scoring function
Person 2: Correction loop + suggestion generation + hint prompts
Person 3: Decision engine + expression evaluator + precedence
Person 4: Tool registry + 4 tools + HITL checkpoints + CLI

**End of Week 3 demo:** Walk through the two dry-run scenarios from the Project Description for real. Clean bank statement → approve. Damaged salary slip → correction loop fires, succeeds, decision flags due to warnings.

### Week 4: Multi-Document, UI, Evaluation, Polish

**Goal:** All 4 document types work. Minimal Streamlit UI for HITL review. Evaluation dataset exercises the system. Demo is rehearsed.

**Deliverables by end of week:**
- 4 Playbooks: indian_cheque, indian_bank_statement, indian_salary_slip, indian_itr_form
- Streamlit UI with 2 pages: run viewer and HITL queue
- Evaluation dataset of 20-30 documents with expected outputs
- Evaluation CLI (`papertrail eval run`) with accuracy reporting
- Demo script prepared, rehearsed
- Documentation updated (README, architecture doc, Playbook authoring guide)
- Bug fixes and polish

**Task allocation:**

Person 1: indian_cheque + indian_bank_statement Playbooks + test fixtures
Person 2: indian_salary_slip + indian_itr_form Playbooks + test fixtures
Person 3: Streamlit UI (run viewer + HITL queue)
Person 4: Evaluation framework + dataset curation + demo prep

**End of Week 4 deliverable:** Demo-ready system. All 4 document types process correctly. UI shows run details and HITL queue. Evaluation report shows accuracy metrics. Mentor meeting materials prepared.

### Weekly rhythm

- Monday morning: sync on the week's plan, adjust task allocation if needed
- Wednesday midday: standup on blockers, re-slice work if someone is ahead or behind
- Friday afternoon: integration session, team tests end-to-end, fixes urgent issues
- Saturday: review what shipped, update docs, prep for next week

### Risk management

**Risk: Docling or PaddleOCR has unexpected issues on Indian documents.**
Mitigation: Week 2 has buffer; both Person 1 and Person 4 work on engine adapters; we can fall back to Tesseract + PyMuPDF only if needed.

**Risk: Correction loop does not converge on realistic documents.**
Mitigation: Week 3 keeps the loop simple (max 3 attempts, targeted hints). If not working, fall back to manual HITL as the default path.

**Risk: Tool implementations (especially IFSC API) are flaky.**
Mitigation: Cache IFSC responses locally. Handle tool errors gracefully (transformation fails, decision still proceeds).

**Risk: Evaluation shows poor accuracy.**
Mitigation: Narrow the demo to the document types where accuracy is best. The pipeline's value is in the architecture and auditability, not raw accuracy.

---

## 22. Post-Capstone Extensions

Items deliberately deferred that would be natural next steps:

- MCP server exposure via FastMCP
- Chat-based Playbook creation (the original motivation for config files)
- Cross-document learning from run history
- Fine-tuned extraction models on domain-specific data
- S3 blob storage activation
- Multi-tenant isolation
- Production authentication (OAuth, API keys with scopes)
- Celery task queue for horizontal scaling
- Visual Playbook editor (React-based)
- Automated correction application based on LLM suggestions
- Comparison UI to see how two Playbook versions perform on the same documents
- Feedback-driven rule learning (rules authored automatically from flagged examples)

---

*Document complete. Engineering specification ready for implementation.*
