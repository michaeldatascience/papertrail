# PaperTrail — Session Log (2026-04-20)

This log captures what was implemented and executed during the setup/foundation session.

## Summary

Goal: bootstrap **Week 1 foundation** from the technical spec, get the repo into a collaborative (GitHub) state, stand up the database schema via Alembic, and confirm the pipeline skeleton runs end-to-end.

Status: ✅ Repo scaffolding complete, ✅ migrations applied, ✅ CLI runnable, ✅ sample fixtures added, ✅ pushed to GitHub.

---

## Tasks completed

### 1) Git + GitHub setup
- Initialized git repository locally.
- Added remote and pushed to GitHub:
  - `origin`: https://github.com/michaeldatascience/papertrail.git
- Confirmed branch sync: local `master` tracks `origin/master` with clean working tree.

### 2) Project scaffolding (folders + packaging)
- Created full folder structure matching the technical documentation (Section 4), including:
  - `papertrail/` package modules
  - `config/` with prompts
  - `playbooks_seed/`
  - `tests/`, `scripts/`, `ui/`
- Added `pyproject.toml` with dependencies and a console script entrypoint:
  - `papertrail = papertrail.cli.app:cli`

### 3) Configuration + prompt templates
- Added system configuration files:
  - `config/llm.json`
  - `config/engines.json`
  - `config/system.json`
- Added prompt templates under `config/prompts/`:
  - `classify_default.txt`
  - `extract_schema.txt`, `extract_natural.txt`
  - `validate_soft_default.txt`
  - `correct_hint.txt`
  - `suggest.txt`
  - cheque-specific templates: `validate_payee_name.txt`, `validate_amount_consistency.txt`

### 4) Core models (Pydantic + typed state)
- Implemented shared Pydantic models:
  - `papertrail/models/pipeline_state.py`
  - `papertrail/models/extraction.py`
  - `papertrail/models/validation.py`
  - `papertrail/models/decision.py`

### 5) Orchestration skeleton (LangGraph)
- Implemented the LangGraph state machine skeleton:
  - `papertrail/orchestration/graph.py`
  - `papertrail/orchestration/nodes.py` (stubbed nodes)
  - `papertrail/orchestration/routing.py` (conditional edges)
  - `papertrail/orchestration/runner.py` (PipelineRunner)
- Nodes included (stubbed outputs):
  - `preupload`, `classify`, `pass_a`, `pass_b`, `pass_c`, `pass_d`, `correction`, `suggestion`, `decide`, `act`
- Conditional routing implemented:
  - classify → proceed vs HITL vs error
  - validate → proceed vs retry vs exhausted vs error

### 6) CLI scaffold (Click)
- Implemented CLI with command tree:
  - `papertrail run`
  - `papertrail playbook ...`
  - `papertrail runs ...`
  - `papertrail hitl ...`
  - `papertrail db ...`
  - `papertrail eval ...`
- Implemented output formatters:
  - summary view, json pretty printer, simple table output.

### 7) Observability base
- Added structlog JSON logging configuration + a shared `emit()` helper:
  - `papertrail/observability/logging.py`
- Added Langfuse client wrapper:
  - `papertrail/observability/langfuse_client.py`
- Added placeholder for OpenTelemetry:
  - `papertrail/observability/tracing.py`

### 8) Storage layer
- Implemented async SQLAlchemy session management:
  - `papertrail/storage/db/session.py`
- Implemented ORM models for all tables from the spec:
  - `papertrail/storage/db/models.py`
- Implemented repository layer:
  - `runs`, `playbooks`, `elements`, `hitl`, `trace`
- Implemented blob storage interface + local implementation:
  - `papertrail/storage/blob/base.py`
  - `papertrail/storage/blob/local.py`
  - `papertrail/storage/blob/s3.py` (stub)

### 9) Alembic setup + initial migration
- Added Alembic configuration:
  - `alembic.ini`, `alembic/env.py`
- Generated and applied initial migration:
  - `alembic/versions/f419b339e175_initial_schema.py`
- Verified tables created in Postgres:
  - `playbooks`, `playbook_configs`, `tools`, `runs`, `run_passes`, `run_elements`, `run_corrections`, `run_rule_evaluations`, `run_hitl_events`, `trace_events`
  - plus `alembic_version`

### 10) Playbook seeds
- Added `_base` Playbook seed (6 sections).
- Added `indian_cheque` Playbook seed (6 sections) with initial schema + validation/rules placeholders.

### 11) Sample data / fixtures
- Added lightweight text fixtures (not OCR/PDF) so the stub pipeline can be exercised immediately:
  - `tests/fixtures/cheque_sample.txt`
  - `tests/fixtures/bank_statement_sample.txt`
  - `tests/fixtures/salary_slip_sample.txt`
  - `tests/fixtures/itr_form_sample.txt`
- Added generator script to create the same fixtures under `data/fixtures/`:
  - `scripts/generate_sample_inputs.py`

### 12) Environment + runtime verification
- Created `.venv` using **Python 3.11** (Python 3.13 was detected initially and corrected).
- Installed dependencies and verified imports:
  - FastAPI, SQLAlchemy, LangGraph, structlog, Docling, PaddleOCR, etc.

### 13) Ran the pipeline end-to-end
- Successfully executed:
  - `papertrail run tests/fixtures/cheque_sample.txt --playbook indian_cheque`
  - `papertrail run ... --output json`
- Confirmed stage-by-stage logs and final state output.

### 14) Issues encountered + fixes
- Docker engine not available on the machine; switched to local Postgres 16 service.
- Git add failed due to an invalid path `nul` (Windows reserved device name). Fix applied:
  - Added `nul` to `.gitignore`
  - Re-attempted commit successfully.

---

## Commands used (high-signal)

### Run the pipeline (stub)
```bash
papertrail run tests/fixtures/cheque_sample.txt --playbook indian_cheque
papertrail run tests/fixtures/cheque_sample.txt --playbook indian_cheque --output json
```

### Generate local sample fixtures
```bash
python scripts/generate_sample_inputs.py
papertrail run data/fixtures/cheque_sample.txt --playbook indian_cheque
```

### Database
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
psql -h localhost -U papertrail -d papertrail -c "\\dt"
```

---

## Next tasks (recommended order)

### A) Make runs persistent in Postgres (highest immediate value)
Right now the pipeline runs in-memory only.
Implement DB persistence so these work end-to-end:
- Create `runs` row at start.
- For each node, write a `run_passes` row.
- Write all `emit()` events to `trace_events` via `TraceRepository`.
- Update final run status/decision/confidence.

This unlocks:
- `papertrail runs list/show/trace` to show real executions.

### B) Implement Playbook loading/merging/validation
- Implement `papertrail.playbooks` module:
  - loader from DB
  - deep merge semantics (`_base` inheritance)
  - validator checks prompt existence, engine/tool references, schema correctness
- Implement `papertrail db seed` to import `playbooks_seed/` + tools into DB.

### C) Add FastAPI + REST endpoints
- Implement `papertrail/api/main.py` and core routes:
  - `/api/v1/runs` upload + start
  - `/api/v1/runs/{run_uid}`
  - `/api/v1/runs/{run_uid}/trace`
  - HITL endpoints

### D) Build the real pipeline passes incrementally
- Preupload checks (OpenCV blur/resolution, file constraints)
- Pass A: Docling layout
- Pass B: dispatcher routes PyMuPDF/pdfplumber/PaddleOCR
- Pass C: LLM schema extraction via Instructor
- Pass D: validation runner (hard + soft + cross-field)

### E) Decision engine + expression evaluator
- Implement AST-based safe evaluator.
- Implement conditions + precedence resolver.
- Implement transformations via tool registry.

### F) Tools registry + initial tools
- Implement tool registry bootstrapping from DB.
- Implement tools:
  - IFSC lookup
  - PAN validate
  - date utils
  - currency normalize

### G) HITL persistence + resume
- Implement HITL events table writes.
- Implement `PipelineRunner.resume()` (LangGraph checkpointing via PostgresSaver).

---

## Repo state at end of session
- GitHub synced: ✅ local `master` == `origin/master`
- Latest commit: `f969141` (fixtures + generator)
