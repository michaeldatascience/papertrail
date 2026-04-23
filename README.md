# PaperTrail

PaperTrail is a document-processing platform for structured, traceable workflows over financial and related documents.

Its purpose is to provide a reusable core engine that can:
- ingest documents
- identify or confirm their type
- extract structured information
- validate extracted values
- apply business rules
- support correction and escalation
- produce auditable outputs and execution traces

PaperTrail is designed as a **generic platform**, not a one-off document parser. The system should support multiple workflows by configuration and compiled execution plans rather than by hardcoded document-specific branches.

---

## What PaperTrail is trying to achieve

PaperTrail aims to separate document processing into clear architectural layers:
- a fixed **system capability layer**
- a **project** layer that defines a bounded domain
- a **playbook** layer that defines one specific workflow
- a compiled **execution plan** that the runtime executes

This allows the platform to remain stable while different domains and workflows are defined above it.

Examples of intended domains and workflows include:
- Indian financial documents
  - cheque validation
  - bank statement processing
  - salary slip verification
  - ITR form verification
- KYC
  - ID verification
  - KYC validation

---

## Core concepts

PaperTrail uses four key concepts.

### 1. System
The system defines what is possible in the platform:
- supported node types
- supported engines
- supported validation rule types
- supported tool interfaces
- supported prompt types
- supported file formats
- runtime limits and platform capabilities

### 2. Project
A project defines what is shared across a bounded domain:
- classification universe
- shared prompts
- shared engine defaults
- shared schema fragments
- shared tools
- defaults used by all playbooks in that project

### 3. Playbook
A playbook defines one specific workflow inside one project:
- extraction schema
- validation rules
- business rules
- postprocessing behavior
- document-specific preupload behavior
- playbook-specific prompt overrides

### 4. ExecutionPlan
The ExecutionPlan is the final runtime object produced by compilation.

The orchestrator executes the ExecutionPlan directly. It does not load raw project or playbook files at runtime.

---

## High-level workflow

A typical PaperTrail run follows this shape:

1. system preflight checks
2. compilation of project + playbook into an ExecutionPlan
3. orchestrated execution of the plan
4. document preprocessing / preupload
5. classification
6. layout extraction
7. text extraction / OCR
8. schema extraction
9. validation
10. correction loop if needed
11. business-rule evaluation
12. post-processing and output generation

The output of a run should include:
- run identity
- input metadata
- stage outputs
- extracted values
- validation results
- decision result
- warnings/errors
- traceable execution events

---

## Main platform features

### Playbook-driven workflows
Document-specific behavior should be expressed through playbooks rather than embedded directly in the core runtime.

### Compile boundary between authoring and execution
Projects and playbooks are authoring inputs. The runtime consumes only the compiled ExecutionPlan.

### Structured extraction
The system is intended to support extraction through OCR, parsing, and LLM-assisted schema extraction.

### Validation and correction
The system should support both hard and soft validation, with optional correction attempts before escalation.

### Business rules and decisioning
The system should support configurable conditions, transformations, and final actions such as:
- approve
- flag
- reject
- escalate

### Traceability
Each run should be observable through logs, trace events, stage outputs, and final state artifacts.

### Human-in-the-loop (HITL)
The platform should support controlled pause/review/resume points for ambiguous or failed cases.

---

## Intended architecture

At a high level, PaperTrail is organized into these layers:

- **Interfaces**
  - CLI
  - API
  - future UI

- **Execution / orchestration**
  - runner
  - compiler
  - LangGraph orchestration
  - runtime state handling

- **Processing subsystems**
  - engines
  - LLM client
  - validation engine
  - decision engine
  - tools

- **Persistence and observability**
  - database registry and run tracking
  - filesystem/blobs for plan, state, and traces
  - structured logs and tracing

---

## Technology direction

PaperTrail is designed around a Python stack with:
- typed models
- async-capable execution paths
- modular engine adapters
- configurable LLM usage
- structured logging and traces
- relational storage for identity and status
- filesystem/blob storage for larger execution artifacts

The exact implementation details may evolve, but the design intent remains:
- modular
- auditable
- configurable
- reusable

---

## Documentation

The project should be read through these documents:

- `README.md` — product/project overview
- `docs/PAPERTRAIL_ARCHITECTURE_V2.md` — the active architectural reference for the redesigned execution/playbook model
- `docs/PLAYBOOK_DESIGN.md` — playbook and project authoring model
- `docs/CURRENT_DEVELOPMENT.md` — engineering progress, workstreams, completed work, and deferred items

If there is any conflict between older implementation ideas and the V2 document, the V2 architecture should be treated as the active architectural direction.

---

## Development status note

PaperTrail is under active development. The implementation may temporarily lag the intended architecture, but development should move toward the Architecture V2 model rather than silently drifting from it.

---

## Team

PaperTrail is being developed as a collaborative engineering project. Team and role details can be expanded here as needed.
