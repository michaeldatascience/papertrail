# PaperTrail Architecture v2 — Reference Document

**Status:** Canonical architectural reference for the playbook/execution redesign
**Scope:** This document is the single source of truth for how PaperTrail is structured after the v2 redesign. It replaces ad hoc design in earlier documents for the playbook and orchestration layers. It does not replace `README.md` for project-level overview or `CURRENT_DEVELOPMENT.md` for engineering progress tracking.
**Audience:** Any engineer working on PaperTrail. Read this fully before writing code in the execution, orchestration, projects, or playbooks subsystems.

---

## 1. Why this redesign exists

The earlier design loaded a playbook, merged it with `_base` defaults, and passed the merged object into the LangGraph orchestrator. This turned out to be fragile for three reasons.

First, the orchestrator consumed whatever fell out of the merge. Its input contract was implicit and depended on merge correctness, naming conventions, and inheritance semantics all being exactly right. Small authoring mistakes surfaced as runtime errors at stage three of a live run, not at authoring time.

Second, the boundary between system capabilities, shared domain defaults, and playbook-specific behavior was unclear. Classification ended up in concrete playbooks even though it is fundamentally a domain-level decision. Preupload checks mixed system-level file sanity with playbook-specific image quality. Prompts were split between the system prompts folder and playbook folders with no clear rule for which went where.

Third, there was no concept of a Project. The `_base` folder was doing the work of a project layer but without the explicit name. This caused repeated confusion about where shared concerns belonged.

The v2 design fixes all three problems by separating **authoring** from **execution** with a hard compile boundary, and by introducing an explicit three-layer authoring model of System, Project, and Playbook.

---

## 2. The four concepts

PaperTrail v2 has four explicit concepts. Every engineer working on the project must understand the role of each.

**System** defines what is possible in the platform. It is a capability registry: what node types exist, what engines are supported, what validation rule types are allowed, what tool interfaces can be called, what file formats can be processed, what prompts are available as system-level defaults. The System is code plus a small amount of fixed configuration. It is not user-editable in normal operation. Think of it as the platform's catalog of "here is what you can do."

**Project** defines a bounded domain and what is shared across all workflows in that domain. A project picks from the System catalog. Example: "Indian Financial Documents" is a project that declares its classification universe (cheque, salary slip, bank statement, ITR form), its shared prompts, its default engine choices, and any tools common to documents in that domain. A project is user-authored but operates within System constraints. For the v1 capstone scope, there is exactly one project: `indian_financial`.

**Playbook** defines one specific workflow inside one project. A playbook picks from the Project's shared choices and adds its own specifics. Example: `indian_cheque` is a playbook inside `indian_financial` that declares the cheque extraction schema, cheque-specific validation rules, cheque-specific business rules, and any prompts that override the project defaults. A playbook never redefines classification (that lives in the project) and never declares new capabilities (those live in the system).

**ExecutionPlan** is the fully resolved runtime object that the orchestrator executes. It is produced by the compile step, which takes a project slug and a playbook slug and returns a complete, self-contained, Pydantic-validated plan. The orchestrator never reads a project file or a playbook file. It never performs merging or lookups. It only consumes an ExecutionPlan.

The rule that ties these together: **System says what is possible. Project says what is shared. Playbook says what is specific. ExecutionPlan says what will actually happen for this one run.**

---

## 3. The hard boundary between authoring and execution

The central architectural commitment of v2 is this: authoring and execution are separated by a single compile step, and the orchestrator only consumes compiled output.

```
Authoring layer                          Execution layer
───────────────                          ───────────────
System catalog (code + json)
Project definition (json files)    ──┐
Playbook definition (json files)   ──┤
                                     │
                                     ▼
                              compile(project_slug, playbook_slug)
                                     │
                                     ▼
                              ExecutionPlan (Pydantic, fully resolved)
                                     │
                                     ▼
                              LangGraph orchestrator
                                     │
                                     ▼
                              RunState (runtime, mutated by nodes)
```

Once compilation succeeds, the plan is frozen and self-contained. No external lookups happen during execution. If a prompt is needed, it is already in the plan as a fully resolved string. If an engine is selected, it is already a concrete reference with primary and fallback named. If a validation rule needs a threshold, the threshold is already filled in.

If compilation fails, it fails loudly at compile time with a specific error type and a message that points at the exact authoring problem. The orchestrator never runs on an invalid plan.

This means errors that used to surface mid-run now surface before any document processing starts. This is the main reason v2 is less fragile than v1.

---

## 4. Directory structure

The filesystem layout directly mirrors the four concepts.

```
papertrail/                                  # Python package (code)
  execution/
    plan.py                                  # ExecutionPlan model
    compiler.py                              # compile function
    catalog.py                               # SystemCatalog model
  projects/
    loader.py                                # loads project definitions
    models.py                                # ProjectDefinition model
  playbooks/
    loader.py                                # loads playbook definitions
    models/                                  # PlaybookDefinition section models
  orchestration/
    graph.py                                 # LangGraph wiring
    nodes.py                                 # node functions
    runner.py                                # top-level execution supervisor
    routing.py                               # conditional routing
  engines/                                   # engine adapters
  llm/                                       # LLM client
  validation/                                # validation rule implementations
  decision/                                  # business rule evaluator
  tools/                                     # tool implementations
  storage/
    db/                                      # SQLAlchemy models, repositories
    blob/                                    # file storage
  observability/                             # logging, tracing, langfuse
  models/                                    # runtime pydantic contracts (RunState, etc)
  config/                                    # loader for environment and config
  cli/                                       # Click commands
  api/                                       # FastAPI routes (later)

config/                                      # system-level configuration (data)
  system.json                                # system limits, file types, timeouts
  catalog.json                               # system capability catalog
  llm.json                                   # model routing by stage
  engines.json                               # engine registry and defaults
  prompts/                                   # system-level prompt templates
    classify.txt
    extract_schema.txt
    correct_hint.txt
    suggest.txt
    validate_soft_default.txt

projects/                                    # project definitions (data)
  indian_financial/
    project.json                             # project manifest
    prompts/                                 # project-shared prompts (optional)
      classify_indian_finance.txt
    playbooks/
      indian_cheque/
        meta.json
        schema.json
        validate.json
        rules.json
        postprocess.json
        prompts/                             # playbook-specific prompts (optional)
          validate_amount_consistency.txt
          validate_payee_name.txt
      indian_salary_slip/
        ...

data/                                        # runtime artifacts (gitignored)
  runs/
    {run_id}/
      plan.json                              # the compiled plan for this run
      state.json                             # final run state
      trace.jsonl                            # append-only event log
      intermediate/                          # stage outputs

samples/                                     # input documents for testing (gitignored or selective)
  cheques/
  salary_slips/

alembic/                                     # database migrations
tests/                                       # test suite
```

Two rules about this layout.

There is no `_base` folder. The concept of base defaults is absorbed into the compiler. System defaults come from the System catalog. Shared domain defaults come from the Project. Playbook-specific values come from the Playbook. The compiler layers these in a fixed order.

There is no project folder outside `projects/`. All projects live under `projects/<slug>/`. The directory slug is the project's identity. Same for playbooks: they live under `projects/<project_slug>/playbooks/<playbook_slug>/`.

---

## 5. System catalog

The System catalog declares what the platform can do. It is loaded once at startup and used by the compiler to validate that every reference in a project or playbook points at something real.

The catalog covers these areas.

**Node types.** The list of pipeline nodes the orchestrator knows how to execute. For v1: `preflight`, `preupload`, `classify`, `layout_extract`, `text_extract`, `schema_extract`, `validate`, `correct`, `decide`, `postprocess`. A playbook cannot introduce a new node type.

**Engines.** The list of engine adapters installed. Each entry has a name, a type (layout, ocr, text, table, vision), the Python class that implements it, and any default configuration. A playbook can select from this list by name; it cannot define a new engine.

**Validation rule types.** The supported validation rule types. For v1: `required`, `regex`, `max_length`, `min_length`, `positive_decimal`, `max_value`, `min_value`, `date_format`, `date_range`, `equals`, `cross_field_sum`, `cross_field_equals`, `soft_llm`. Each rule type has a declared parameter schema. The compiler validates that every rule in a playbook uses a known rule type and supplies the expected parameters.

**Business rule expression types.** The supported condition and transformation types. For v1: `expression` (simple arithmetic and comparison), `threshold`, `lookup`, `tool_call`, `llm_condition`. Similar contract to validation rule types.

**Tool interfaces.** The available tools with their input and output schemas. For v1: `ifsc_lookup`, `currency_convert`, `export_json`, `export_csv`, `notify`. A playbook references a tool by name; the interface is fixed by the system.

**Prompt templates.** System-level prompt templates with declared substitution variables. For v1: `classify`, `extract_schema`, `correct_hint`, `suggest`, `validate_soft_default`.

**File format support.** The MIME types the platform accepts for input documents.

**Runtime limits.** Global defaults for retry counts, timeouts, maximum file size, maximum correction iterations.

The catalog is defined as a Pydantic model in `papertrail/execution/catalog.py` and loaded from `config/catalog.json` plus code-level registration of engines, tools, and rule types. When a new engine, tool, or rule type is implemented, it must be registered in the catalog or the compiler will reject any project or playbook that references it.

---

## 6. Project definition

A project describes a bounded domain and the shared defaults for all playbooks in that domain.

The project manifest is `projects/<slug>/project.json` and contains the following sections.

**Identity.** Slug, display name, description, version.

**Classification.** The list of document types this project handles. Each entry has a label (matching a playbook slug), a display name, and optional classification hints. The project also specifies the classifier model, the classification confidence threshold, and the behavior when confidence falls below the threshold (for v1, escalate to manual review).

**Shared prompts.** Optional prompt overrides for this project. A file named `classify.txt` in `projects/<slug>/prompts/` overrides the system-level `classify.txt` for every playbook in this project. Playbooks can override further.

**Shared engine preferences.** Default engine selections for each engine slot (layout, ocr, text, table, vision). Each slot has a primary and a fallback. These defaults apply to every playbook in the project unless the playbook overrides them.

**Shared tools.** Tools that are available to every playbook in this project. A playbook references a tool by name; if the tool is not in the project's shared tools list and not registered at system level as globally available, compilation fails.

**Shared schema fragments.** Reusable field definitions. For example, `ifsc_code` can be defined once at the project level with its type, regex, and validation rules, and any playbook in the project can reference it by name rather than redefining it.

**Defaults for playbook sections.** Default values for any field in the playbook sections that is otherwise identical across playbooks. For example, the default `output_format` for postprocess might be `json` across the whole project.

A project is hand-authored JSON. The loader validates it against the `ProjectDefinition` Pydantic model and against the System catalog. Compilation of any playbook in the project requires the project to load cleanly first.

---

## 7. Playbook definition

A playbook describes one specific workflow inside one project.

The playbook folder is `projects/<project_slug>/playbooks/<playbook_slug>/` and contains these files.

**`meta.json`.** Identity, description, expected document type, document-specific preupload checks (image resolution, page count, and so on), engine overrides if any.

**`schema.json`.** The extraction schema: the list of fields to extract, their types, whether they are critical, any schema fragments pulled from the project by reference. This is what the schema extraction node targets.

**`validate.json`.** The validation rules, grouped by field or by cross-field scope. Each rule references a rule type from the System catalog and supplies the required parameters. Hard rules and soft rules are mixed in the same file but are executed differently (hard rules run in code, soft rules trigger an LLM call). Each rule may also declare `stop_on_failure`; if enabled, a failed or non-evaluable rule blocks execution and drives correction or escalation.

**`rules.json`.** The business rules. Each entry is either a Condition (evaluated for true or false) or a Transformation (computes a derived value or calls a tool). Conditions have an associated action (`approve`, `flag`, `reject`, `escalate`) and an optional reason. Transformations have an output binding.

**`postprocess.json`.** The output format, what fields to include in the final report, what tool calls to invoke at the end (notification, export), and whether to include the full trace.

**`prompts/`.** Optional playbook-specific prompt files. Any prompt file here overrides the project-level and system-level versions with the same name. For example, `validate_amount_consistency.txt` in this folder is used for soft validation of amount consistency for this playbook only.

A playbook is hand-authored JSON plus optional prompt text files. It is validated by the loader against the `PlaybookDefinition` section models, and by the compiler against both the Project it belongs to and the System catalog.

---

## 8. The ExecutionPlan

The ExecutionPlan is the runtime contract. It is a Pydantic model, fully validated, fully resolved, and self-contained. The orchestrator reads from it and nothing else.

The plan has these top-level fields.

**Identity.** `plan_id` (uuid, matches the run id), `project_slug`, `playbook_slug`, `document_type`, `compiled_at` (timestamp), `compiler_version`.

**Preflight.** System-level file checks that must pass before the pipeline starts. Max file size, allowed MIME types, page count limits. These values are copied from the System catalog at compile time so the plan is self-contained.

**Preupload.** Playbook-specific document checks. Image quality, resolution, page-count constraints for this document type. Each check is a fully specified entry with a type, parameters, and the action to take on failure.

**Classification.** The classifier model reference, the threshold, the list of candidate labels, the resolved classification prompt text. Even if classification is governed by the project, the compiled plan contains the full resolved configuration for this one playbook.

**Extraction.** The schema (list of field specifications with types and criticality), the extraction engine reference (primary and fallback), the resolved extraction prompt text with the schema already formatted into it, and any field-level extraction hints.

**Validation.** The list of validation rules, each one fully specified with its rule type, target field or fields, parameters, `stop_on_failure` behavior, and the resolved prompt text if it is a soft rule. No rule references an external prompt file. No rule relies on a default that lives elsewhere.

**Correction.** The correction policy: max retries (typically three), the resolved correction prompt, which validation failures trigger correction versus which escalate immediately.

**Business rules.** The ordered list of conditions with their associated actions and reasons, and the ordered list of transformations with their output bindings. Each entry is fully specified with its expression or tool reference.

**Postprocess.** The output format, the fields to include, the tool calls to execute on success and on failure, and trace-inclusion settings.

**Engine routing.** A map from engine slot (layout, ocr, text, table, vision) to a concrete engine reference (primary + fallback + configuration).

**LLM routing.** A map from pipeline stage to a concrete model reference (model name + provider + parameters).

**Tools.** A map from tool name to a concrete tool binding (which tool implementation, with what configuration, and what input and output schema it accepts).

**Limits.** Runtime limits for this plan: max correction iterations, per-stage timeouts, overall run timeout.

**Prompts.** A map from prompt name to resolved prompt text. Every prompt the plan needs is already present here. Nodes read prompts from this dictionary.

Every field in the plan is required. There are no optional lookups. There are no references to external files. The plan can be serialized to JSON, and the serialized form is written to `data/runs/{run_id}/plan.json` at the start of every run. If something goes wrong, you can read this file and see exactly what was being executed.

---

## 9. The compile step

The compile step is a single function. Its signature is:

```
compile(project_slug: str, playbook_slug: str, run_id: str) -> ExecutionPlan
```

It is deterministic given the same inputs and the same on-disk authoring files. It runs on every document execution. The expected runtime is milliseconds.

The compilation procedure is a fixed sequence of steps. Each step can fail with a specific error type.

**Step 1: Load the System catalog.** Parse `config/catalog.json` plus code-registered capabilities. Validate the catalog. If this fails, the platform is misconfigured and no compilation can succeed.

**Step 2: Load the Project definition.** Read `projects/<project_slug>/project.json`. Parse it as a `ProjectDefinition`. Validate every reference in it against the System catalog (engines referenced must exist, tools referenced must exist, prompt templates referenced must exist). If a reference is invalid, raise `ProjectValidationError`.

**Step 3: Load the Playbook definition.** Read `projects/<project_slug>/playbooks/<playbook_slug>/*.json` and any prompt files under `prompts/`. Parse them as `PlaybookDefinition`. Validate every reference against both the Project and the System catalog. If a reference is invalid, raise `PlaybookValidationError`.

**Step 4: Assemble each section of the ExecutionPlan.** For every field in the plan, the compiler applies this resolution order: System default, then Project override, then Playbook override. The override rules are recursive merge for objects, replace for scalars, and replace for lists. This matches the authoring merge rules you already decided on. Lists never append; the last writer wins.

**Step 5: Resolve prompts.** For each prompt name the plan needs, the compiler looks up the prompt text in this order: playbook `prompts/` folder, project `prompts/` folder, system `config/prompts/` folder. The first hit wins. The resolved text is inserted into the plan's `prompts` dictionary.

**Step 6: Resolve engines and tools.** Each engine slot and each tool reference is turned into a concrete binding by looking up the referenced name in the System catalog and applying any project or playbook configuration overrides.

**Step 7: Validate the final plan.** The assembled ExecutionPlan is passed through Pydantic validation. Every required field must be present. Every rule type must match the System catalog. Every prompt reference must resolve. If anything is malformed, raise `PlanValidationError` with a message that points at the exact field.

**Step 8: Return the plan.** The plan is returned and written to `data/runs/{run_id}/plan.json` before the orchestrator starts.

The compiler never silently fills in defaults. If a required value is not found in System, Project, or Playbook, compilation fails with an error that names the missing value.

---

## 10. Compilation errors

Compilation errors are first-class typed errors, not plain strings. When authoring fails, the CLI and (later) the API should be able to present a clear, structured message.

The error hierarchy is:

```
CompilationError (base)
├── SystemCatalogError
│   ├── CatalogLoadError
│   └── CatalogValidationError
├── ProjectError
│   ├── ProjectLoadError
│   ├── ProjectValidationError
│   └── ProjectReferenceError      # project references something not in System
├── PlaybookError
│   ├── PlaybookLoadError
│   ├── PlaybookValidationError
│   └── PlaybookReferenceError     # playbook references something not in Project or System
└── PlanValidationError             # final assembled plan failed Pydantic validation
```

Every error instance carries: the error type, a human-readable message, the file path that is the source of the problem, the field or section name, and optionally a suggested fix. The CLI renders these consistently.

Sample error messages:

`PlaybookReferenceError: playbook 'indian_cheque' validation rule for field 'amount_figures' references rule type 'fuzzy_match' which is not in the System catalog. Supported rule types: required, regex, max_length, ...`

`ProjectReferenceError: project 'indian_financial' references classifier prompt 'classify_domain.txt' which was not found in project prompts or system prompts.`

`PlanValidationError: compiled plan for project='indian_financial' playbook='indian_cheque' is missing required field 'extraction.primary_engine'. This usually means neither the project nor the playbook specified an OCR engine and the System has no default.`

---

## 11. Database and filesystem split

The database is a registry and index. The filesystem holds the content.

The database answers queries like "list all runs," "show me all failed runs in the last week," "what playbooks exist," "which runs used which playbook." It is small, queryable, and stable.

The filesystem holds the actual content: the compiled plan for each run, the final run state, the trace log, any intermediate stage outputs. These files are large, sequential, and often written once and read rarely.

For v1 use SQLite. The schema has four tables.

**`projects` table.** Columns: `id` (uuid primary key), `slug` (unique), `name`, `path` (relative path to project folder), `created_at`, `updated_at`. One row per project. For v1 there is one row.

**`playbooks` table.** Columns: `id` (uuid primary key), `project_id` (foreign key to projects), `slug` (unique within project), `name`, `path` (relative path to playbook folder), `created_at`, `updated_at`. One row per playbook. The combination of `project_id` and `slug` is unique.

**`runs` table.** Columns: `id` (uuid primary key), `playbook_id` (foreign key to playbooks), `document_path` (input document location), `status` (enum: pending, running, completed, failed, escalated), `decision` (enum: approve, flag, reject, null when not yet decided), `plan_path` (path to compiled `plan.json`), `state_path` (path to final `state.json`), `trace_path` (path to `trace.jsonl`), `started_at`, `completed_at`, `error_summary` (short string, null on success), `created_at`, `updated_at`. One row per document execution.

**`run_events` table (optional, defer if not needed for v1).** Columns: `id` (uuid primary key), `run_id` (foreign key to runs), `stage`, `event_type`, `timestamp`, `payload_path` (path to detail file, or null). One row per significant pipeline event. If you defer this, the trace file on disk remains the authoritative log; this table is only for queryable events.

Row lifecycle for a run:

1. When a user invokes `papertrail run <document> --project P --playbook K`, the runner creates a row in `runs` with status `pending`.
2. Compilation runs. On success, `plan_path` is set and status transitions to `running`. On failure, status transitions to `failed` and `error_summary` is populated with the compilation error message.
3. The orchestrator executes the plan. Every event is appended to `trace.jsonl`. Intermediate outputs are written to `data/runs/{run_id}/intermediate/`.
4. On completion, `decision`, `state_path`, and `completed_at` are populated and status transitions to `completed` or `escalated` depending on the outcome.
5. On unrecoverable failure, status transitions to `failed` and `error_summary` describes the failure.

If the database is wiped, the files survive and can be re-indexed. If a file is missing or corrupt, the database row points at what was supposed to be there. This makes recovery and debugging straightforward.

For migrations use Alembic, which is already set up in the repo. The initial migration for v2 creates these four tables.

---

## 12. Orchestrator boundary

The orchestrator is a LangGraph state machine. After v2 it has exactly one input contract: it receives an ExecutionPlan and a RunState. It produces a final RunState.

The orchestrator must not:

- Load a project file.
- Load a playbook file.
- Merge anything.
- Resolve a prompt by name from disk.
- Look up an engine by name from a config file.
- Tolerate missing fields on the plan by substituting defaults at runtime.
- Apply inheritance or override logic.

Every node in the orchestrator reads configuration from the plan and state from the RunState. Nodes write to the RunState. That is the entire contract.

If a node needs a prompt, it reads it from `plan.prompts[name]`. If a node needs an engine, it reads it from `plan.engine_routing[slot]`. If a node needs a validation rule, it reads it from `plan.validation.rules`. There is no fallback path to config files.

This is what makes the v2 orchestrator predictable. The same plan always produces the same execution path. Errors in authoring cannot surface at stage three; they either failed compilation or they will produce a specific, attributable runtime error like "extraction engine returned no result" that is not about configuration shape.

---

## 13. Execution flow end to end

A single invocation of `papertrail run <document> --project indian_financial --playbook indian_cheque` runs the following steps.

**Step 1: CLI argument parsing.** Click parses arguments into a typed request object. No business logic.

**Step 2: System preflight.** The runner checks that the input file exists, is readable, has an accepted MIME type, and is under the maximum file size. These checks use values from the System catalog. No project or playbook is loaded yet.

**Step 3: Create run row.** A new row is inserted into the `runs` table with status `pending` and a generated `run_id`. The run directory `data/runs/{run_id}/` is created.

**Step 4: Compile.** The compiler is invoked with `(project_slug, playbook_slug, run_id)`. It produces an ExecutionPlan or raises a compilation error. On success, the plan is serialized and written to `data/runs/{run_id}/plan.json`. The runs row is updated with `plan_path` and status transitions to `running`. On failure, the runs row transitions to `failed` with the error message, and the run ends here.

**Step 5: Initialize RunState.** A fresh RunState is created. It contains the run id, the plan reference, the document path, and empty slots for each stage's output.

**Step 6: Orchestrator execution.** LangGraph takes over. It runs the stages defined by the plan, in order: preupload, classify (verify the document matches the expected type), layout extraction, text extraction, schema extraction, validation, correction loop if needed, business rules, postprocess. Each stage reads from the plan, reads from and writes to the RunState, and emits trace events.

**Step 7: Trace logging.** Every significant event (stage started, stage completed, correction attempted, rule evaluated, decision reached) is appended as a JSON line to `data/runs/{run_id}/trace.jsonl`. The trace is an append-only log.

**Step 8: Finalization.** When the orchestrator exits, the final RunState is serialized to `data/runs/{run_id}/state.json`. The runs row is updated with `state_path`, `decision`, `completed_at`, and a final status.

**Step 9: Output to user.** The CLI formats the final result for the user (summary, json, or trace output mode).

Throughout this flow, each subsystem has one job. CLI parses. Runner supervises. Compiler produces plans. Orchestrator executes plans. Nodes do work. Storage persists. No subsystem reaches across boundaries.

---

## 14. Where code lives

This section maps concepts to specific files. Anyone implementing v2 should follow this layout.

`papertrail/execution/catalog.py` contains the `SystemCatalog` Pydantic model and a function `load_system_catalog()` that reads `config/catalog.json` and assembles the runtime catalog from code-registered engines, tools, and rule types.

`papertrail/execution/plan.py` contains the `ExecutionPlan` model and all its sub-models (`PreflightSpec`, `PreuploadSpec`, `ClassificationSpec`, `ExtractionSpec`, `FieldSpec`, `ValidationSpec`, `ValidationRule`, `BusinessRulesSpec`, `Condition`, `Transformation`, `PostProcessSpec`, `EngineRef`, `ModelRef`, `ToolRef`, `RuntimeLimits`). Every sub-model is strict, with required fields and no optional fallback behavior.

`papertrail/execution/compiler.py` contains the `compile()` function and the supporting private functions for each resolution step (`_resolve_section`, `_resolve_prompts`, `_resolve_engines`, and so on). It also contains the compilation error hierarchy.

`papertrail/projects/models.py` contains the `ProjectDefinition` Pydantic model and its section sub-models.

`papertrail/projects/loader.py` contains the function that reads a project folder from disk and returns a validated `ProjectDefinition`.

`papertrail/playbooks/models/` (a package, not a file) contains one file per playbook section: `meta.py`, `schema.py`, `validate.py`, `rules.py`, `postprocess.py`, and a top-level `definition.py` that assembles them into `PlaybookDefinition`.

`papertrail/playbooks/loader.py` contains the function that reads a playbook folder from disk and returns a validated `PlaybookDefinition`.

`papertrail/orchestration/runner.py` is the top-level supervisor. It accepts the CLI request, does system preflight, creates the run row, invokes the compiler, initializes RunState, starts the orchestrator, and finalizes the run row. It is the one place that stitches these subsystems together.

`papertrail/orchestration/graph.py` contains the LangGraph wiring: nodes, edges, conditional routing. It does not load any config; it receives a plan and a state.

`papertrail/orchestration/nodes.py` contains the node functions. Each node is a pure function of plan and state, returning an updated state.

`papertrail/models/` contains the runtime Pydantic contracts that are not part of the ExecutionPlan: `RunState`, `ExtractionOutput`, `ValidationOutput`, `DecisionOutput`, `TraceEvent`.

`papertrail/storage/db/` contains the SQLAlchemy models for the four tables, repository classes for each, and the session helper.

`papertrail/cli/commands/run.py` is a thin wrapper that calls `runner.run(request)` and formats the output. Nothing else.

---

## 15. Implementation plan

This is the order in which v2 should be built. Follow it. Do not skip ahead. The goal is to have a working end-to-end path for one document before elaborating anything.

**Phase 1: Delete dead code. Half a day.** Remove `papertrail/playbooks/models.py` (legacy duplicate), `papertrail/orchestration/state.py` (unused re-export), `papertrail/llm/fallback.py` (redundant placeholder), `scripts/generate_sample_inputs.py`, `tests/fixtures/*.txt`, the empty `tests/integration/__init__.py` and `tests/evaluation/__init__.py`. Remove the entire `_base` folder concept. Update the README to reflect the new architecture.

**Phase 2: Define the runtime contract. One day.** Write `papertrail/execution/catalog.py` with the `SystemCatalog` model. Write `papertrail/execution/plan.py` with the full `ExecutionPlan` model and all sub-models. Do not write the compiler yet. Review the models. Adjust until they feel right. At this stage you should be able to hand-construct an ExecutionPlan in Python for the indian_cheque case and see that it type-checks.

**Phase 3: Write the system catalog content. Half a day.** Create `config/catalog.json` and register engines, tools, rule types, and node types in code. For v1 register: node types from section 5; a minimal set of engines (one layout engine based on PyMuPDF or Docling, one OCR engine); basic validation rule types; IFSC lookup tool; system prompts.

**Phase 4: Create the project and playbook models. One day.** Write `papertrail/projects/models.py` with `ProjectDefinition`. Write `papertrail/playbooks/models/*.py` with the section models. Write the loaders. They should read from disk and validate, but not compile yet.

**Phase 5: Migrate `indian_cheque` into the new structure. Half a day.** Create `projects/indian_financial/project.json` with the classification universe, shared prompts list, engine defaults, shared tools. Move the cheque playbook into `projects/indian_financial/playbooks/indian_cheque/`. Write its five JSON files. Ensure the loader can read both cleanly.

**Phase 6: Write the compiler. One to two days.** Write `compile()` step by step following section 9. Start by producing a partial plan that covers only classification and extraction, hand-verify, then add validation, business rules, postprocess. Write the compilation error hierarchy. Write a CLI command `papertrail compile <project> <playbook>` that compiles and prints the plan for inspection.

**Phase 7: Rewrite orchestrator nodes to consume the plan. One to two days.** Update `papertrail/orchestration/nodes.py` so each node reads from the plan and state only. Remove any direct config or playbook access. Update `graph.py` and `routing.py` to match. The orchestrator should now execute a compiled plan end-to-end on one real cheque document, even if some stages are still stubs.

**Phase 8: Wire up the database. Half a day.** Write the Alembic migration for the four tables. Update `runner.py` to insert a run row, update status transitions, and set paths. Verify the row lifecycle with a test run.

**Phase 9: Make one stage actually real. Two to three days.** Pick either text extraction or validation and make it real end-to-end. Text extraction means real OCR on a real cheque document producing real fields. Validation means actually enforcing the rules in `validate.json` with hard-coded rule execution. Either one is acceptable; both is better. Do one first.

**Phase 10: Verify the full loop. One day.** Run a real cheque, get a real decision. Run a cheque with a deliberate error (for example, amount_figures not matching amount_words), see validation fail, see the correction loop trigger, see the final escalation if correction fails. This is the demo of the self-correcting agent described in the proposal.

After phase 10 you have a working v1. Everything after is elaboration: a second playbook, more tool calls, the frontend, MCP exposure.

---

## 16. Rules engineers must follow

These are not suggestions. They are the rules that make the v2 design hold up over time.

The orchestrator consumes only ExecutionPlan. If a node needs information, it must be on the plan. If a node needs to load something from disk during execution, that is a bug.

The compiler is the only place that resolves inheritance and defaults. No runtime code applies "if missing use default" logic. The default is already on the plan.

System, Project, Playbook are the only authoring concepts. Do not introduce new authoring layers without redesigning this document. Do not let `_base` creep back in.

Every reference must resolve at compile time. If a playbook references a rule type, it must be in the System catalog. If it references a tool, it must be available. If it references a prompt, it must exist in the prompts folders. Compilation must catch every unresolved reference. At runtime, if a rule marked `stop_on_failure` cannot be evaluated or evaluates to failure, execution must not silently continue.

Database tracks identity and status. Filesystem holds content. Do not store large blobs in the database. Do not invent runtime-only state in the database.

One project for v1. One. Do not build for multiple projects before one works end-to-end. The directory structure already supports multi-project; that is sufficient preparation.

Do not add fields to the ExecutionPlan for features that are not being built. If HITL workflows are deferred, there is no `hitl_config` on the plan. Add fields when the feature lands, not before.

CLI and API share the same service layer. The CLI command is a thin wrapper around a function in `papertrail/orchestration/runner.py`. The future API will be another thin wrapper around the same function. No business logic lives in Click callbacks or FastAPI route handlers.

Prompts live in three tiers: system, project, playbook. Playbook overrides project. Project overrides system. Resolution is by filename. There is no other prompt resolution mechanism.

Simplicity wins. If a choice is between two designs and one is simpler, pick the simpler one. If a feature is not on the phase list, do not build it. If a layer of abstraction is not needed for the v1 demo, do not add it.

---

## 17. What this document does not cover

This document covers the authoring-to-execution architecture and the four concepts. It does not cover:

- Specific OCR engine choice and configuration.
- Prompt engineering details for each stage.
- The exact correction-hint format.
- Frontend design.
- MCP server exposure details.
- Deployment and packaging.

Those belong in separate docs or in `CURRENT_DEVELOPMENT.md` as they are worked on. Keep this document focused on the v2 architecture.

---

## 18. Summary in one paragraph

PaperTrail v2 separates authoring from execution with a compile step. There are four concepts: System (what is possible, platform catalog), Project (what is shared across a domain), Playbook (what is specific to one workflow), and ExecutionPlan (the fully resolved runtime object the orchestrator executes). Authoring files live on disk under `config/`, `projects/<project>/`, and `projects/<project>/playbooks/<playbook>/`. The compiler takes a project slug and a playbook slug and produces a validated ExecutionPlan. The orchestrator executes the plan. A small database holds projects, playbooks, and runs as identity and status records; the filesystem holds plan content, trace logs, and run state. The self-correcting intra-run loop and the eventual demo rest on this foundation. Build the foundation first, then make one real extraction path work end-to-end, then add breadth.
