# PaperTrail — Current Development

**Status:** Living engineering document  
**Last updated:** 2026-04-23

This document is the operational companion to `README.md`, `docs/PAPERTRAIL_ARCHITECTURE_V2.md`, and `docs/PLAYBOOK_DESIGN.md`.

Its purpose is to keep the team organized during development by tracking:
- completed work that is no longer actively managed
- major decisions that shape implementation
- items intentionally deferred for later
- active workstreams and their task-level progress

## Maintenance protocol
Use this document with the following rules:
1. **Do not update it for tiny edits.** Update it only after meaningful engineering progress, a real decision, a new blocker, or an important checkpoint.
2. **Completed items move upward.** When a workstream or task is stable enough, move it from the Active Development Log into Completed Tasks / Modules.
3. **Only major decisions belong in Decisions.** Small implementation choices should stay inside workstream notes, not in the Decisions section.
4. **Deferred means intentionally postponed.** It does not mean stubbed, broken, or forgotten.
5. **Active Development Log should contain only active work.** If something is finished, move it to Completed. If it is postponed, move it to Deferred.
6. **Keep status vocabulary consistent.** Use only: `completed`, `partial`, `pending`, `blocked`, `review`, `deferred`.
7. **Update this document at important checkpoints.** At each checkpoint, review all active workstreams and refresh Completed, Decisions, Deferred, and Active Development accordingly.

For project-level overview, read `README.md`.  
For architecture, read `docs/PAPERTRAIL_ARCHITECTURE_V2.md`.  
For playbook/project authoring design, read `docs/PLAYBOOK_DESIGN.md`.

---

## 1. Completed Tasks / Modules

This section is for meaningful work that is completed and no longer needs active tracking.

### Documentation
- Canonical active documentation set simplified and synced around:
  - `README.md`
  - `docs/PAPERTRAIL_ARCHITECTURE_V2.md`
  - `docs/PLAYBOOK_DESIGN.md`
  - `docs/CURRENT_DEVELOPMENT.md`
- `README.md` now serves as the main product/project overview
- `docs/PAPERTRAIL_ARCHITECTURE_V2.md` is the active architectural reference
- `docs/PLAYBOOK_DESIGN.md` now reflects the V2 project/playbook/ExecutionPlan model

### Playbooks
- V1 playbook loader/model cleanup completed enough to support the transition into V2
- Legacy duplicate playbook model file removed
- Active architectural direction now treats the V1 `_base` inheritance model as superseded by the V2 System → Project → Playbook → ExecutionPlan model
- Added the first V2 playbook definition scaffold for `projects/indian_financial/playbooks/indian_cheque/`
- Added V2 playbook loader/models separate from the legacy V1 merged-playbook path

### Execution layer
- New `papertrail/execution/` package added as the home for V2 runtime contracts
- Initial `SystemCatalog` and `ExecutionPlan` models defined
- Added a unit test that constructs representative catalog and plan objects
- Added a system catalog loader and first-pass compiler that can build an ExecutionPlan from V2 project/playbook inputs
- Added `config/catalog.json` as the canonical system capability catalog

### Project layer
- New `papertrail/projects/` package introduced for the V2 project authoring layer
- Initial `ProjectDefinition` and project loader implemented
- Added a sample `projects/indian_financial/project.json` manifest
- Added the first V2 prompt/shared-project structure for `indian_financial`

### Orchestration and state cleanup
- Stage naming cleaned up from old pass-style labels to clearer stage names
- Runtime now uses explicit canonical stage names (`layout_extract`, `text_extract`, `schema_extract`, `validate`) with the transitional `pass_*` compatibility path removed
- Runtime state field names aligned with new stage names
- Graph/node/logging labels updated to the clearer naming scheme
- Orchestration runtime now executes from a compiled `ExecutionPlan` rather than the merged V1 playbook object
- Added a lightweight internal executor to replace the LangGraph dependency during the transition

### Validation engine
- Generic hard-rule validation now executes from the compiled plan instead of hardcoded workflow functions
- `required`, `non_empty`, `regex`, `positive_decimal`, `max_value`, `min_value`, `date_format`, `date_range`, `equals`, `cross_field_sum`, and `cross_field_equals` are evaluated generically from config
- Validation rules now support explicit `stop_on_failure` behavior; blocking rules fail execution on both evaluated failures and non-evaluable outcomes
- Aggregate validation confidence now reflects only actually evaluated rules, rather than being reduced by unevaluated soft rules
- `date_range` now supports both `min: "today"` and `max: "today"`
- Validation results are stored in the canonical `validation_result` field
- The cheque playbook now includes the configured `amount_figures <= 100000` proof-point rule

### Runner / CLI foundation
- `PipelineRunner` now compiles `System + Project + Playbook` into an `ExecutionPlan` before execution
- Basic preflight checks implemented:
  - file exists
  - MIME check
  - file size check
- `papertrail run` now executes the compiled V2 plan through the new orchestration boundary
- Compiled plans are persisted to `data/runs/{run_id}/plan.json`
- Final state snapshots are persisted to `data/runs/{run_id}/state.json`
- CLI output modes support:
  - summary
  - json
  - trace / verbose
- Trace output now shows stage-by-stage final pipeline state

### Demo path
- Smoke-demo path verified on cheque TIFF files using the existing CLI
- End-to-end scaffold execution confirmed through the current orchestration path

---

## 2. Major Decisions

Only major project-shaping decisions belong here.

1. **PaperTrail uses a four-document active documentation model**
   - `README.md` for product/project overview
   - `docs/PAPERTRAIL_ARCHITECTURE_V2.md` for architecture
   - `docs/PLAYBOOK_DESIGN.md` for playbook/project authoring design
   - `docs/CURRENT_DEVELOPMENT.md` for living engineering status

2. **Architecture V2 is the active architectural direction**
   - The working model is now System → Project → Playbook → ExecutionPlan
   - The orchestrator should consume only compiled execution plans

3. **Projects are now an explicit authoring concept**
   - Shared domain concerns belong at the Project level
   - Playbooks define workflow-specific behavior within a project

4. **The compiler is the boundary between authoring and execution**
   - Resolution of defaults, prompts, engines, and references belongs to compile time, not runtime

5. **CLI is the primary working interface**
   - API and UI are secondary and follow the same core, not a separate execution path

6. **Playbook/project authoring is treated as a first-class architectural concept**
   - Workflow definition is now understood in the context of Projects as well as Playbooks

7. **Documentation must stay split between target-state design and engineering truth**
   - README and architecture/playbook docs describe intended design
   - Current Development tracks actual progress, open work, and deferrals

8. **Core-first completion before external integrations**
   - LLM calls, OCR, PDF extraction, and tool integrations remain stubbed until the Core + Project + Playbook system is internally solid
   - Near-term work should prioritize compiler strictness, runtime contracts, business rules, correction semantics, and runner/orchestration consistency

---

## 3. Deferred

These are items intentionally postponed. They are not being ignored, but they are not active work right now.

### Architecture / platform direction
- Dynamic DAG or fully config-defined orchestration graph
- Multi-level or multi-parent playbook inheritance
- DB-backed playbook repository as the primary playbook source
- Richer list merge strategies for playbook sections

### Runtime / pipeline features
- Full HITL pause/resume/cancel workflow
- Mid-run tool-health-aware stage skipping
- Production-grade circuit breaker behavior
- Advanced transformation/tool execution framework

### Interface / platform expansion
- FastAPI completion as a full secondary interface
- UI workflows and HITL review interface
- Expanded evaluation workflows and broader benchmarking setup

### Broader system concerns
- Production observability stack expansion
- More ambitious storage abstractions beyond current practical needs
- Broader tool ecosystem beyond a small initial set

---

## 4. Iteration Priorities and Guardrails

This section is the standing execution guide for future iterations. Use it before starting implementation work.

### Immediate delivery order
1. **Business rules engine**
   - replace fixed decision stubs with deterministic evaluation of compiled business rules
2. **Correction contract and semantics**
   - make correction a real core-stage contract even if external retry behavior remains stubbed
3. **Compiler strictness pass**
   - continue moving authoring mistakes to compile time
   - tighten validation, business-rule, and postprocess reference checks
4. **Runtime output contracts**
   - define stable models for stage outputs so stubbed stages still obey real runtime contracts
5. **Runner lifecycle and boundary cleanup**
   - tighten failure/finalization behavior and clarify preflight vs preupload ownership
6. **External integrations later**
   - LLM calls, OCR, PDF extraction, and tool execution stay stubbed until the internal architecture is solid

### Canonical pending task list
#### Runtime stage contracts
- define stable output models for layout, text, extraction, validation, correction, decision, and postprocess stages
- keep stubbed stages deterministic and contract-accurate even before external integrations land

#### Validation
- keep validation generic and data-driven from the compiled plan
- strengthen compile-time validation for targets and parameters
- defer true soft-validation execution until the core runtime is mature

#### Business rules
- define the decision contract fully
- evaluate ordered conditions deterministically
- return structured reasons and actions from config

#### Correction
- define correction stage input/output clearly
- use compiled validation failures and correction policy to drive retry semantics
- preserve traceability across retries even while external retry execution remains stubbed

#### Compiler / authoring safety
- validate field targets, rule parameters, business-rule references, and postprocess references more strictly at compile time
- keep unresolved authoring errors out of runtime

#### Runner / lifecycle
- add DB-backed run lifecycle hooks when the supervisor contract is ready
- tighten finalization and failure consistency
- clarify preflight vs preupload boundary

#### External implementations (deferred for now)
- LLM calls
- OCR/PDF extraction
- tool execution
- real external engine dispatch

### Guardrails engineers must follow
- **One canonical name only.** Do not keep old and new names in parallel beyond a single checkpoint.
- **Core before integrations.** Finish the internal runtime/compiler/contracts before implementing LLM, OCR, PDF, or tool execution.
- **Compiler gets stricter over time.** Push authoring validation to compile time whenever practical.
- **Orchestrator stays dumb.** Nodes consume plan + state only; no raw config loading or workflow-specific hardcoding.
- **Every field has a layer owner.** New behavior must clearly belong to System, Project, Playbook, ExecutionPlan, or RunState.
- **Prefer deletion over preservation.** Remove transition-only code once the canonical path is in place.
- **Contracts before code.** Define stage I/O before expanding stage logic.
- **Runtime truth must stay explicit.** If a stage is scaffolded, keep that visible in code and in `CURRENT_DEVELOPMENT.md`.

## 5. Active Development Log

This section tracks active work only.

Work is organized as:
- **Workstream** = broader objective
- **Task** = meaningful chunk inside the workstream
- **Subtasks** = actionable progress items

Statuses used here must remain one of:
- `completed`
- `partial`
- `pending`
- `blocked`
- `review`
- `deferred`

---

### Workstream: Phase 1 — Dead Code Deletion and Repo Cleanup
**Status:** partial  
**Priority:** high  
**Objective:** remove clearly obsolete files from the v1 structure and prepare the repository for the Architecture V2 transition.

**Reference doc**
- `docs/PAPERTRAIL_ARCHITECTURE_V2.md`

**Modules / Files**
- legacy playbook model files
- legacy orchestration wrappers
- redundant LLM fallback placeholder
- obsolete fixture/script files
- documentation/readme cleanup items

#### Task 1: Safe obsolete file deletion
- [completed] remove `papertrail/playbooks/models.py`
- [completed] remove `papertrail/orchestration/state.py`
- [completed] remove `papertrail/llm/fallback.py`
- [completed] remove `scripts/generate_sample_inputs.py`
- [completed] remove `tests/fixtures/*.txt`
- [completed] remove `tests/integration/__init__.py`
- [completed] remove `tests/evaluation/__init__.py`

#### Task 2: Post-deletion review
- [pending] review remaining scaffold packages and confirm which are intentionally retained
- [pending] identify additional v1-only artifacts that should be removed during the V2 transition

#### Task 3: Documentation / repo sync
- [completed] update `README.md` to align with the active documentation set and V2 direction

**Notes / blockers**
- This workstream is the first practical phase of the Architecture V2 transition.
- Scaffold namespaces are being tolerated for now, but dead duplicate code should continue to be removed aggressively.

---

### Workstream: V2 Architecture Transition
**Status:** partial  
**Priority:** high  
**Objective:** begin moving the repository from the superseded V1 playbook/execution model to the Architecture V2 model.

**Reference doc**
- `docs/PAPERTRAIL_ARCHITECTURE_V2.md`

**Modules / Files**
- `papertrail/execution/*` (new)
- `papertrail/projects/*` (new)
- `papertrail/playbooks/*`
- `papertrail/orchestration/*`
- `config/*`
- future `projects/*` authoring tree

#### Task 1: Runtime contract definition
- [completed] define `SystemCatalog`
- [completed] define `ExecutionPlan`
- [completed] define the strict compile-time/runtime boundary

#### Task 2: Authoring model definition
- [completed] define `ProjectDefinition`
- [completed] redefine `PlaybookDefinition` around the V2 model
- [completed] separate system prompts, project prompts, and playbook prompts cleanly

#### Task 3: Compile pipeline
- [completed] design the compile flow from System + Project + Playbook to ExecutionPlan
- [partial] define compilation error hierarchy
- [partial] define prompt, engine, and rule resolution rules

**Notes / blockers**
- This is the architectural transition workstream and should guide all subsystem changes.
- Runtime work should increasingly target the ExecutionPlan model rather than the V1 merged-playbook model.

---

### Workstream: Convergence Cleanup
**Status:** completed  
**Priority:** high  
**Objective:** remove transitional orchestration naming and compatibility paths so the runtime uses one canonical vocabulary.

**Modules / Files**
- `papertrail/orchestration/*`
- `papertrail/models/pipeline_state.py`
- `papertrail/cli/formatters.py`
- `tests/*`

#### Task 1: Canonical stage naming
- [completed] remove `pass_a/pass_b/pass_c/pass_d` node aliases
- [completed] make graph execution use only real stage names
- [completed] keep logging and failure stages on canonical names

#### Task 2: Canonical runtime state
- [completed] remove `pass_*_output` compatibility fields from runtime state
- [completed] standardize on `layout_output`, `text_output`, `extraction_output`, and `validation_result`
- [completed] update CLI/runtime consumers to the canonical state shape

#### Task 3: Test and doc convergence
- [completed] update routing/formatter fixtures and tests to the canonical fields
- [completed] sync `CURRENT_DEVELOPMENT.md` with the convergence cleanup checkpoint

**Notes / blockers**
- This cleanup intentionally removes the transition path so future work lands only on the canonical runtime contract.

---

### Workstream: Real Extraction Path
**Status:** deferred  
**Priority:** high  
**Objective:** replace the stub extraction chain with one believable end-to-end path for the first V2-aligned document workflow, after the core runtime architecture is internally complete.

**Modules / Files**
- `papertrail/orchestration/nodes.py`
- `papertrail/engines/dispatcher.py`
- `papertrail/engines/*`
- `papertrail/models/*`
- relevant cheque playbook files under `playbooks/indian_cheque/`

#### Task 1: Layout extraction
- [pending] define the minimal real layout result shape
- [pending] choose the first practical engine path for cheque layout analysis
- [pending] return regions that are useful to downstream extraction stages

#### Task 2: Text extraction / OCR dispatch
- [pending] define the minimal real region extraction result shape
- [pending] wire at least one real engine path through the dispatcher
- [pending] produce usable text output from cheque inputs
- [pending] keep fallback behavior simple and explicit

#### Task 3: Schema extraction
- [pending] define the minimal real schema extraction I/O
- [pending] map extracted text into playbook-defined cheque fields
- [pending] replace stub schema output with real field values
- [pending] preserve traceability of the extraction output

**Notes / blockers**
- This workstream is intentionally deferred while LLM/OCR/PDF/tool integrations remain stubbed by plan.
- The first implementation pass should still prioritize one meaningful cheque path rather than broad engine coverage.
- The target is real document-derived fields, not a perfect extraction framework.

---

### Workstream: Validation Engine
**Status:** partial  
**Priority:** high  
**Objective:** make runtime validation actually enforce playbook-defined validation rules.

**Modules / Files**
- `papertrail/orchestration/nodes.py`
- `papertrail/validation/*`
- `papertrail/models/*`
- `playbooks/*/validate.json`

#### Task 1: Validation execution contract
- [completed] define runtime inputs and outputs for validation
- [completed] align validation result shape with `validation_output`
- [completed] ensure failed elements and rule results have a stable structure

#### Task 2: Hard rule implementation
- [completed] implement required-rule execution
- [completed] implement regex-rule execution
- [completed] implement positive-decimal execution
- [completed] implement max-value execution

#### Task 3: Node integration
- [completed] replace fixed pass/fail stub in validation stage
- [completed] compute actual validation output from playbook rules
- [completed] make config-only rules affect runtime behavior

**Notes / blockers**
- The `amount_figures <= 100000` rule in `indian_cheque` is now part of the playbook config and enforced by the generic validation engine.
- Soft LLM validation rules are plumbed through the compiled plan but remain a follow-up integration point.
- Extraction is still scaffolded, so real validation currently drives retry/exhaustion behavior until the extraction path becomes real or intentionally scaffolded with believable values.

---

### Workstream: Business Rules Engine
**Status:** pending  
**Priority:** highest  
**Objective:** make post-validation decisioning depend on configured rules rather than fixed approval.

**Modules / Files**
- `papertrail/orchestration/nodes.py`
- `papertrail/decision/*` or equivalent rule evaluation implementation path
- `playbooks/*/rules.json`

#### Task 1: Decision contract
- [pending] define decision engine inputs and outputs
- [pending] define how conditions_evaluated should be represented
- [pending] define minimal precedence behavior

#### Task 2: Condition evaluation
- [pending] support at least one deterministic expression path
- [pending] map fired conditions to actions
- [pending] return reasons in a structured way

#### Task 3: Runtime integration
- [pending] replace fixed `approve` decision stub
- [pending] connect decision output to `business_rules_result`
- [pending] preserve traceability of why a decision was reached

**Notes / blockers**
- The first version should stay deterministic and small.
- Transformation/tool execution can remain bounded after the base decision path works.

---

### Workstream: Preupload and Config Boundary Cleanup
**Status:** partial  
**Priority:** medium  
**Objective:** clearly separate supervisor-level preflight from playbook-driven preupload checks and tighten config ownership.

**Modules / Files**
- `papertrail/orchestration/runner.py`
- `papertrail/passes/preupload.py`
- `papertrail/config/loader.py`
- `config/system.json`
- `config/engines.json`
- playbook `meta` / preupload-related config

#### Task 1: Preflight ownership
- [completed] basic supervisor preflight for file existence, MIME, size, and playbook loading
- [pending] define the final boundary between system-level and playbook-level checks
- [pending] ensure document-specific checks are executed from the correct config path

#### Task 2: Config alignment
- [partial] `system.json` is partly used by preflight
- [pending] make `engines.json` meaningfully influence runtime behavior
- [pending] remove or reduce duplicated config logic across runner/code/playbook layers

#### Task 3: Documentation and clarity
- [pending] ensure this boundary remains consistent across docs and implementation

**Notes / blockers**
- This workstream is partly underway, but the semantics are not yet clean enough to call finished.

---

### Workstream: Runner Lifecycle and Execution Hygiene
**Status:** partial  
**Priority:** medium  
**Objective:** make the runner a cleaner supervisor for execution, failure handling, and future persistence.

**Modules / Files**
- `papertrail/orchestration/runner.py`
- `papertrail/orchestration/graph.py`
- `papertrail/orchestration/routing.py`

#### Task 1: Supervisor cleanup
- [completed] basic preflight path
- [completed] basic failure reporting and final-state return path
- [pending] simplify and review runner design as a coherent supervisor layer

#### Task 2: Lifecycle hooks
- [pending] add DB run-row lifecycle hooks
- [pending] define finalization responsibilities clearly
- [pending] improve failure-state consistency across runner and nodes

#### Task 3: Optional control hooks
- [pending] evaluate whether stage skipping is still required
- [deferred] mid-run or advanced orchestration policy hooks

**Notes / blockers**
- The runner is useful now, but still more like a practical scaffold than a fully shaped supervisor.

---

### Workstream: Runtime Truth and Demo Clarity
**Status:** partial  
**Priority:** medium  
**Objective:** keep the demo path useful while ensuring the team and reviewers can clearly distinguish real functionality from scaffolding.

**Modules / Files**
- `papertrail/cli/*`
- `docs/CURRENT_DEVELOPMENT.md`
- demo-related commands / output paths

#### Task 1: CLI visibility
- [completed] summary output
- [completed] JSON output
- [completed] trace/verbose output for stage-by-stage final state

#### Task 2: Demo framing
- [partial] smoke-demo path established
- [pending] keep demo guidance aligned with what is actually real
- [pending] ensure important checkpoints move into Completed section after stabilization

#### Task 3: Ongoing document hygiene
- [partial] canonical documentation set established
- [pending] maintain consistent updates across future sessions

**Notes / blockers**
- This workstream is about discipline and communication, not just code.

---

## 5. Checkpoint Update Rules

At each important checkpoint, review this document in the following order:

1. **Review every active workstream.**
   - If a workstream is substantially stable, move completed parts to **Completed Tasks / Modules**.
   - If it is no longer active, remove it from the Active Development Log.

2. **Update Major Decisions only if a real project-shaping decision was taken.**
   - Do not add small code choices here.

3. **Move intentionally postponed items into Deferred.**
   - Do not leave postponed work cluttering the Active Development Log.

4. **Refresh statuses consistently.**
   - Use only the approved statuses:
     `completed`, `partial`, `pending`, `blocked`, `review`, `deferred`.

5. **Keep Completed stable.**
   - Once something is truly completed and moved there, it should not return to active tracking unless a new workstream is opened.

6. **Keep this document useful, not exhaustive.**
   - It should track engineering direction and execution cleanly, not mirror every commit.

---

## 6. Quick Usage Reminder

Use this document as follows:
- planning starts from the **Active Development Log**
- checkpoint reviews update **Completed**, **Decisions**, and **Deferred**
- project/product intent stays in `README.md`
- architecture stays in `docs/PAPERTRAIL_ARCHITECTURE_V2.md`
- playbook/project authoring design stays in `docs/PLAYBOOK_DESIGN.md`

This separation should be preserved across future sessions so the project remains organized and the documents do not drift into overlapping roles.
