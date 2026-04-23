# PaperTrail — Playbook Design

**Status:** Canonical playbook and project authoring design  
**Last updated:** 2026-04-23

This document explains how workflow authoring works in PaperTrail under the V2 architecture.

It focuses on:
- the relationship between System, Project, Playbook, and ExecutionPlan
- what belongs in a Project
- what belongs in a Playbook
- how prompts, engines, and rules are resolved
- how authoring is separated from runtime execution

For the overall architecture, see `docs/PAPERTRAIL_ARCHITECTURE_V2.md`.  
For engineering progress and workstreams, see `docs/CURRENT_DEVELOPMENT.md`.

---

## 1. Design goal

The purpose of the authoring model is to make workflow definition explicit, validated, and safe.

PaperTrail should not execute loosely merged config fragments directly. Instead, the system should:
1. define platform capabilities at the **System** layer
2. define shared domain defaults at the **Project** layer
3. define workflow-specific behavior at the **Playbook** layer
4. compile those into a strict **ExecutionPlan** for runtime

This gives a clean separation between:
- authoring
- validation
- execution

---

## 2. The four-concept model

## 2.1 System
The System defines what is possible in the platform.

It includes:
- supported node types
- supported engine types and registered engines
- supported validation rule types
- supported business-rule expression types
- supported tools
- supported prompt templates at the system level
- file support and runtime limits

The System is a capability catalog.

## 2.2 Project
A Project defines what is shared across a bounded domain.

Examples:
- Indian Financial Documents
- KYC
- Lending Documents

A Project selects from the System catalog and defines:
- classification universe
- shared prompts
- shared engine defaults
- shared schema fragments
- shared tools
- shared defaults for all playbooks in that project

## 2.3 Playbook
A Playbook defines one specific workflow inside one Project.

Examples within an Indian financial documents project:
- cheque validation
- bank statement processing
- salary slip verification
- ITR form verification

A Playbook defines:
- extraction schema
- validation rules
- business rules
- postprocessing behavior
- document-specific preprocessing
- prompt overrides when needed

## 2.4 ExecutionPlan
The ExecutionPlan is the fully resolved runtime contract.

The orchestrator executes the ExecutionPlan directly.

It should already contain:
- resolved prompts
- resolved engine selections
- resolved validation rules
- resolved business rules
- resolved limits and stage configuration

The runtime should never need to interpret raw project or playbook authoring files.

---

## 3. Authoring vs execution boundary

The authoring model exists upstream of execution.

### Authoring inputs
- System catalog
- Project definition
- Playbook definition

### Compile step
These are loaded, validated, resolved, and compiled.

### Runtime input
- ExecutionPlan

This means:
- Projects and Playbooks are not runtime objects for the orchestrator
- merge/default resolution belongs to the compiler
- the orchestrator should consume only a strict compiled plan

This is the central rule of the V2 architecture.

---

## 4. Directory structure

The authoring structure should follow this pattern:

```text
config/
  system.json
  catalog.json
  llm.json
  engines.json
  prompts/
    classify.txt
    extract_schema.txt
    correct_hint.txt
    suggest.txt
    validate_soft_default.txt

projects/
  indian_financial/
    project.json
    prompts/
      classify_indian_finance.txt
    playbooks/
      indian_cheque/
        meta.json
        schema.json
        validate.json
        rules.json
        postprocess.json
        prompts/
          validate_amount_consistency.txt
          validate_payee_name.txt
      indian_salary_slip/
      indian_bank_statement/
      indian_itr_form/
```

This layout has three important properties:
1. system-level config is separate from project/playbook authoring
2. projects contain their own playbooks
3. playbooks are always understood in the context of a project

---

## 5. What belongs in the System layer

The System layer should contain only platform-level capabilities and defaults.

Examples:
- node type registry
- engine registry
- tool registry
- validation rule type registry
- expression type registry
- runtime limits
- file format support
- generic prompt templates

A Project or Playbook may reference these capabilities, but should not create new platform capabilities on its own.

---

## 6. What belongs in the Project layer

A Project should contain everything shared across its playbooks.

Typical project responsibilities:
- project identity and description
- classification universe for that domain
- shared prompts
- shared engine preferences
- shared tools
- shared schema fragments
- shared defaults for postprocessing or validation behavior

A Project is the place for domain-level concerns.

For example, in an Indian financial documents project, classification belongs at the project level because the classifier needs to choose among the different document families inside that project.

---

## 7. What belongs in the Playbook layer

A Playbook should contain only workflow-specific behavior.

Typical playbook responsibilities:
- workflow identity and metadata
- extraction schema for this workflow
- validation rules for this workflow
- business rules for this workflow
- postprocessing behavior for this workflow
- document-specific preprocessing
- prompt overrides for workflow-specific tasks

A Playbook should not redefine project-wide classification or invent new platform capabilities.

---

## 8. Playbook files

Each Playbook is represented as a folder containing section files.

## 8.1 `meta.json`
Contains:
- playbook identity
- description
- expected document type
- document-specific preprocessing / preupload checks
- engine overrides if needed

## 8.2 `schema.json`
Contains:
- field definitions
- field types
- critical vs non-critical fields
- any schema-fragment references to project-level reusable definitions

## 8.3 `validate.json`
Contains:
- field-level validation rules
- cross-field validation rules
- soft and hard validation behavior
- correction configuration if this workflow needs it

## 8.4 `rules.json`
Contains:
- business-rule conditions
- actions triggered by conditions
- transformations or enrichment steps
- rule ordering where needed

## 8.5 `postprocess.json`
Contains:
- output format
- trace inclusion policy
- export behavior
- final-output shaping configuration

## 8.6 `prompts/`
Contains optional playbook-specific prompt overrides.

These prompts override project and system prompts by name.

---

## 9. Project file

Each Project is represented by a `project.json` file plus optional prompt files.

The Project should define:
- identity
- classification universe
- shared prompts
- shared engine defaults
- shared tools
- shared schema fragments
- shared defaults for playbooks

This file is the domain-level authoring contract.

---

## 10. Prompt ownership and resolution

Prompt ownership is split across three layers.

## 10.1 System prompts
These are generic reusable prompt templates.

Examples:
- classify
- extract_schema
- correct_hint
- suggest
- generic soft validation fallback prompt

These live under:
- `config/prompts/`

## 10.2 Project prompts
These are shared prompts for a whole domain/project.

Examples:
- domain-specific classification prompt
- domain-specific shared extraction phrasing
- shared validation prompt wording for the project

These live under:
- `projects/<project_slug>/prompts/`

## 10.3 Playbook prompts
These are workflow-specific prompt overrides.

Examples:
- cheque amount consistency validation
- cheque payee-name plausibility
- workflow-specific extraction hints

These live under:
- `projects/<project_slug>/playbooks/<playbook_slug>/prompts/`

## 10.4 Resolution rule
Prompt resolution should follow this order:
1. playbook prompt
2. project prompt
3. system prompt

The compile step should resolve the final prompt text and place it in the ExecutionPlan.

---

## 11. Engines and authoring

Engine behavior should be split cleanly.

### System level
The System defines:
- what engines exist
- what type they are
- what implementation they map to
- system-level defaults and runtime behavior

### Project level
The Project defines:
- default engine choices for the domain

### Playbook level
The Playbook defines:
- workflow-specific engine overrides if needed

The authoring model should express **engine selection**, not raw engine implementation details.

---

## 12. Validation authoring model

The authoring model should define **what validation should happen**.

Validation rules should be declared using rule types already known to the System catalog.

This means:
- Project or Playbook authoring references rule types
- the compiler validates rule types and parameters
- unsupported rule types are authoring errors, not runtime warnings
- the runtime validation engine executes the resolved rule list from the ExecutionPlan
- if a rule is marked `stop_on_failure`, a failure or non-evaluable result blocks forward progress

Validation authoring may include:
- required fields
- regex checks
- numeric/date constraints
- cross-field checks
- soft validation prompts
- per-rule `stop_on_failure` behavior
- correction policy

---

## 13. Business-rule authoring model

Business rules should be declared, not hardcoded.

A Playbook should define:
- ordered conditions
- associated actions
- optional reasons
- optional transformations or tool calls

The compiler should ensure that:
- referenced tools exist
- referenced expression or condition types are supported
- all rule data is fully resolved into the ExecutionPlan

---

## 14. Schema fragments and reuse

Projects may define shared schema fragments.

Examples:
- IFSC field specification
- account number field specification
- PAN field specification

Playbooks may reference these fragments rather than redefining them.

This allows:
- reuse across workflows
- consistency across related document workflows
- less duplication in playbook authoring

---

## 15. Merge and resolution philosophy

The V2 model still uses layered resolution, but only inside the compiler.

Resolution order is:
1. System defaults
2. Project overrides
3. Playbook overrides

This should produce one final compiled result.

Important rules:
- object-like structures merge recursively
- scalar values override directly
- list values replace rather than append
- prompt references are resolved by tiered lookup
- no unresolved references remain after compilation

The runtime never performs these merges.

---

## 16. ExecutionPlan as the runtime contract

The most important rule in this design is:

> The orchestrator executes only the ExecutionPlan.

This means:
- no raw authoring files are read during execution
- no defaults are guessed at runtime
- no prompt is resolved from disk during execution
- no engine is looked up dynamically from authoring files during execution

The compiler is the place where all that work happens.

---

## 17. Authoring principles

The authoring system should remain:
- explicit
- readable
- easy to review in version control
- strongly validated
- bounded by platform capabilities

It should avoid:
- hidden inheritance behavior
- playbooks redefining project concerns
- project files redefining system capabilities
- runtime dependency on raw config resolution

---

## 18. Summary

Under Architecture V2, the playbook system is no longer just a file-based inheritance model.

It is part of a broader authoring model:
- **System** defines what the platform can do
- **Project** defines what is shared across a domain
- **Playbook** defines one workflow in that domain
- **ExecutionPlan** is the compiled runtime object that the orchestrator executes

This gives PaperTrail a cleaner and safer foundation for configurable document workflows without exposing the runtime to fragile authoring semantics.
