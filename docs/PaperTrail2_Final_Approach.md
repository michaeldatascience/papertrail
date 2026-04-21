# PaperTrail2 — Final Architecture and Delivery Plan

**Purpose:** This document freezes the important decisions we have already validated, defines the final approach for the app, records the current state of the repository, and lists the remaining items that still need discussion before we build further.

This is the working reference for the next phase of development.

---

## 1. What PaperTrail2 Is

PaperTrail2 is a **core document-processing platform** driven by **Playbooks**.

The system is not "a cheque app" or "a bank statement app." It is a reusable engine that can process many document types by swapping playbooks.

### The rule of the system

- **Core = generic, stable platform code**
- **Playbooks = data/config that define behavior**
- **No document-type logic should be hardcoded into the core**

The core pipeline should remain reusable for:
- cheques
- bank statements
- salary slips
- ITR forms
- future custom document types

---

## 2. Frozen Decisions

These are the decisions we should treat as locked unless a strong reason appears later.

### 2.1 Orchestration

- Use **LangGraph** as the orchestration backbone.
- The pipeline is a state machine with sequential stages and conditional routing.
- HITL pause/resume should be supported by the state model.
- Sequential execution is the v1 default; parallelism can come later.

### 2.2 LLM provider

- Use **OpenRouter** as the model gateway.
- Keep provider routing in config, not code.
- Maintain per-stage model selection and fallback.

### 2.3 LLM structured output

- Use **Instructor + Pydantic v2** for schema-based output.
- LLM responses must support explicit `null`.
- Never guess if the field is absent.

### 2.4 Storage

- Use **PostgreSQL** as the source of truth.
- Use **local blob storage** in development.
- Keep a blob-storage abstraction so S3/MinIO can be added later.
- Runs must be immutable.
- Re-processing a file creates a new run.

### 2.5 Observability

- Use **structlog** for application logging.
- Use **Langfuse** for LLM traces.
- Use **trace_events** in PostgreSQL as the canonical event log.

### 2.6 CLI/UI strategy

- CLI is the first working interface.
- FastAPI comes next for API support.
- Streamlit is later and minimal.
- UI should read the same storage and run the same core logic.

### 2.7 Engine stack

- Layout: Docling
- OCR: PaddleOCR primary, Tesseract fallback
- PDF text: PyMuPDF primary, pdfplumber for tables
- Image quality checks: OpenCV / Pillow
- Vision LLM: enabled per playbook, not by default

### 2.8 Playbook model

- Playbooks are config-driven.
- `_base` is the root playbook.
- All concrete playbooks extend `_base`.
- Inheritance is resolved at load time.
- Child playbooks override only what differs.

### 2.9 Core design principle

- Avoid hardcoded document-specific logic in the core.
- Prefer registries, configuration, and generic contracts.
- Use expressions/rules/config rather than special-case code.

---

## 3. Design Principles for PaperTrail2

### 3.1 Generic first

The core should never assume it is processing a cheque.
It should only know how to:
- load a playbook
- run a pipeline
- validate output
- make a decision
- record trace events

### 3.2 Playbook-driven behavior

Everything document-specific should live in playbooks:
- candidate labels
- extraction schema
- validation rules
- decision conditions
- transformations
- prompt templates
- engine preferences
- preupload thresholds

### 3.3 Pluggable modules

Anything that may vary across deployments should be pluggable:
- engines
- tools
- prompt templates
- model routing
- storage backends

### 3.4 No silent magic

If behavior changes, it should be explainable from:
- config
- playbook inheritance
- declared rules
- explicit routing

### 3.5 Pragmatic, not overengineered

We should keep the first version small and stable.
The goal is not to build every feature at once.
The goal is to build a **solid core** that can evolve.

---

## 4. Core vs Playbooks

This is the most important architectural split.

### 4.1 Core responsibilities

The core owns:
- CLI
- API entrypoints
- LangGraph pipeline orchestration
- pipeline state
- playbook loading and merge logic
- storage repositories
- tracing/logging
- validation engine
- decision engine
- tool registry
- HITL flow
- post-processing

### 4.2 Playbook responsibilities

Playbooks own:
- document type metadata
- classification candidates
- extraction schema
- validation rules
- decision rules
- transformations
- engine preferences
- preupload thresholds
- prompt/template references
- postprocessing overrides

### 4.3 What must not happen

The core must not contain logic like:
- `if playbook == 'indian_cheque'`
- special handling for a single document type
- field-specific checks that only apply to one playbook
- fixed routing outside generic config/registry rules

---

## 5. Current Status of the Repository

This section records where we are right now.

### 5.1 Working today

- Python environment is available in WSL
- `uv sync` works
- PostgreSQL works directly in WSL
- `papertrail db migrate` works
- `papertrail run` executes end-to-end
- the `indian_cheque` playbook loads successfully
- the pipeline state machine runs through all stages
- logs and final output are produced

### 5.2 Partially working

- playbook loading now works, but the loader/repository layer is still a temporary file-based implementation
- preupload stage is wired, but the check config path still needs cleanup
- the pipeline currently runs with many stubbed stage outputs
- validation, correction, decision, and transformations are still placeholders in most places

### 5.3 Still stubbed or incomplete

- Pass A layout engine
- Pass B OCR/text engine routing
- Pass C schema extraction with LLM
- Pass D validation engine
- correction loop
- suggestion generation
- decision engine logic
- tool execution and enrichment
- database-backed playbook repository/seeder
- HITL persistence/resume
- full run repository integration
- REST API
- Streamlit UI

---

## 6. What We Learned So Far

### 6.1 The playbook loading direction is correct

We verified that:
- `_base` and `indian_cheque` merge correctly
- the loaded playbook is structurally correct
- `meta`, `schema`, `validate`, `rules`, and `postprocess` are all present after merge

This means the **playbook inheritance model is viable**.

### 6.2 The core pipeline shape is correct

We have already proven that the core can:
- initialize state
- load a playbook
- move through the graph
- return a final result

So the orchestration skeleton is usable.

### 6.3 The current issue is not "does the pipeline run"

The real issue is:
- how much of the pipeline is still stubbed
- whether the core abstractions are generic enough
- whether config access is aligned with the final playbook schema

---

## 7. Data and Playbook Plan

We should select datasets and playbooks together, because the dataset determines what the playbook must prove.

### 7.1 Selection goals

We want the chosen data to demonstrate:
- classification
- structured extraction
- validation
- correction/HITL
- decisions
- multi-page handling
- table extraction
- noisy OCR handling
- generic behavior across document families

### 7.2 Recommended data families

| Priority | Data family | Purpose | Suggested playbook |
|---|---|---|---|
| 1 | Existing cheque TIFFs already in `data/` | Fastest end-to-end demo | `indian_cheque` |
| 2 | Indian bank statement samples | Multi-page + tables + balance logic | `indian_bank_statement` |
| 3 | Salary slip samples | Payroll-style structured extraction | `indian_salary_slip` |
| 4 | ITR / tax form samples | Complex form extraction | `indian_itr_form` |
| 5 | FUNSD | Generic form understanding benchmark | `generic_form_extraction` |
| 6 | CORD / SROIE | OCR-heavy receipt/invoice style benchmark | `receipt_invoice` |
| 7 | RVL-CDIP | Classification / routing benchmark | `generic_document_router` |

### 7.3 Suggested public benchmark search targets

Because Kaggle search results can vary, we should look for the following dataset families:
- `Indian cheque OCR dataset`
- `Indian bank statement OCR dataset`
- `salary slip OCR dataset`
- `ITR form OCR dataset`
- `FUNSD`
- `CORD`
- `SROIE`
- `RVL-CDIP`

### 7.4 Recommended playbook sequence

Start with the smallest set that proves the platform:
1. `indian_cheque`
2. `indian_bank_statement`
3. `generic_form_extraction`
4. `receipt_invoice`
5. `generic_document_router`
6. `indian_salary_slip`
7. `indian_itr_form`

### 7.5 What each playbook should demonstrate

- `indian_cheque`: signature/stale-date/amount consistency/IFSC lookup/HITL
- `indian_bank_statement`: transaction table extraction, totals, running balance checks
- `generic_form_extraction`: field/value extraction from forms with variable layout
- `receipt_invoice`: OCR-heavy extraction with totals and line items
- `generic_document_router`: classification accuracy and routing only
- `indian_salary_slip`: pay period, earnings, deductions, net pay validation
- `indian_itr_form`: higher-complexity structured extraction and cross-field checks

### 7.6 Data curation rule

For each selected dataset, create a small evaluation set containing:
- clean examples
- noisy examples
- edge cases
- failure cases
- at least a few documents that should trigger HITL or correction

This ensures the demo shows the core platform behavior, not just the happy path.

---

## 8. Open Questions Still to Discuss

These are not final decisions yet.

### 7.1 LangChain vs LangGraph vs LangFlow

Recommended direction:
- **LangGraph** = core orchestration
- **LangChain** = optional helper utilities only if needed
- **LangFlow** = not part of the core architecture

Still to confirm:
- do we use any LangChain abstractions at all, or keep LLM calls fully custom?

### 7.2 Playbook storage source

Current work used a temporary file-based repository.
Still to decide/finalize:
- exact DB-backed playbook repository API
- how seeding syncs JSON to DB
- how versioning and inheritance are materialized in storage

### 7.3 Validation DSL

We need to finalize:
- how hard rules are represented
- how soft rules are represented
- whether expression-based rules cover enough cases
- whether we need a stricter schema for rule configs

### 7.4 Decision engine details

Still to settle:
- exact precedence behavior for multiple fired conditions
- how transformations are executed and validated
- whether transformations can be skipped per decision outcome

### 7.5 Tool registry scope

We need to finalize the first v1 tool set.
Likely candidates:
- IFSC lookup
- PAN validation
- date utilities
- currency normalization

Still to decide:
- exact tool schemas
- whether tools are synchronous, async, or mixed
- how tools are versioned

### 7.6 Preupload model

The locked architecture and technical documentation disagree slightly on the exact shape of the preupload section.
We need to finalize one canonical schema for v1.

### 7.7 Pipeline state shape

The current `PipelineState` should be reviewed and possibly tightened so it matches the final playbook/output model.

### 7.8 DB integration for runs

We need to confirm:
- which parts of run state are persisted in DB rows
- which parts stay only in graph state
- how run replay/resume will work

---

## 9. Recommended Final Architecture

This is the final approach I recommend we build toward.

### 8.1 Execution model

1. CLI receives file + playbook slug
2. Runner computes file hash and initializes run
3. Playbook loader loads merged playbook
4. Preupload checks run
5. Classification runs
6. Pass A/B/C run
7. Validation runs
8. Correction loop runs if needed
9. Decision engine resolves final outcome
10. Postprocessing runs
11. Run is stored and traced

### 8.2 Data-driven behavior

The runner should only ask:
- what does the playbook say?
- which engine is configured?
- which rules are active?
- what should happen on failure?

The runner should not embed document-specific decisions.

### 8.3 Generic contracts

We should keep these contracts stable:
- `PipelineState`
- `PlaybookLoader`
- `EngineDispatcher`
- `ValidationRunner`
- `DecisionEngine`
- `ToolRegistry`
- `BlobStore`
- repository interfaces

### 8.4 Incremental implementation strategy

Build in this order:
1. stabilize core models and config shapes
2. finalize playbook loading and merge rules
3. implement preupload correctly
4. implement one real extraction path end-to-end
5. implement validation and decision execution
6. add correction and HITL
7. add more playbooks

---

## 10. What We Should Focus On Next

The best next focus is to **stabilize the core abstractions and remove remaining architectural ambiguity**.

### Immediate focus area 1 — Canonical playbook schema

We should decide the final schema for:
- `meta`
- `classify`
- `schema`
- `validate`
- `rules`
- `postprocess`

This must match the frozen architecture and be implemented consistently.

### Immediate focus area 2 — Core config access

We need to align the runtime code with the playbook structure so the core always reads configuration from the correct place.

### Immediate focus area 3 — Minimal real pipeline contract

We should define the smallest useful real pipeline:
- load playbook
- run preupload
- classify
- extract stub output
- validate stub output
- decide stub output
- store trace

Then each stub can be replaced one by one.

### Immediate focus area 4 — DB-backed playbook repository

The temporary file-based loader should be replaced with the real storage-backed loader and seeder.

### Immediate focus area 5 — Validation and decision framework

These are the core behaviors that make the system useful beyond a demo.

---

## 11. Suggested Milestone Plan

### Milestone 1 — Core foundation
- playbook loading works
- pipeline runs
- logs persist
- stubs are stable
- CLI is usable

### Milestone 2 — Core abstractions
- final playbook schema
- validation runner
- decision runner
- engine dispatcher
- tool registry
- blob adapter

### Milestone 3 — Real processing
- preupload checks
- extraction engines
- schema extraction
- validation rules
- decision logic
- correction loop

### Milestone 4 — Multi-playbook support
- add more playbooks
- verify no core code changes are needed
- keep behavior config-driven

---

## 12. Final Recommendation

PaperTrail2 should be built as a **generic, playbook-driven document platform** with:
- LangGraph orchestration
- OpenRouter-based LLM routing
- PostgreSQL source of truth
- local blob storage in dev
- structured playbooks with inheritance
- generic registries for engines/tools/rules
- minimal hardcoded logic in the core

The next thing to do is not to add more document-specific logic.
The next thing to do is to **freeze the canonical core interfaces and align the codebase to them**.

---

## 13. Working Summary

**We started with:**
- a locked architecture
- a strong playbook-driven vision
- a generic pipeline spec

**We have reached:**
- a runnable CLI
- a working PostgreSQL setup
- a working playbook load path
- a stubbed end-to-end pipeline

**We should go next to:**
- stabilize the core architecture
- finalize the canonical playbook schema
- replace stubs in a disciplined order
- keep the system fully generic

---

*End of PaperTrail2 draft.*
