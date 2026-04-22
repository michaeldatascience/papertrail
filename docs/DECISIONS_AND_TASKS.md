# PaperTrail Architectural Decisions & Tasks

**Last Updated**: 2026-04-22  
**Status**: Active Development

## Core Decisions

### 1. Document Processing Pipeline
- **Decision**: Multi-stage pipeline with LLM-based extraction (Option 2)
- **Stages**:
  1. `preupload_checks` - Document health (blur, DPI, pages)
  2. `classify` - Document type identification
  3. `layout_extraction` - Structure and bounding boxes
  4. `text_extraction` - All text (direct + OCR + tables)
  5. `schema_extraction` - LLM extracts structured fields
  6. `validation` - Field validation
  7. `business_rules` - Apply logic and decide action
  8. `post_processing` - Format and deliver
- **Rationale**: Flexibility + context-aware extraction like Nanonets

### 2. Playbook Architecture
- **Single-level inheritance** - All playbooks extend `_base` only
- **List merge strategy** - Replace existing list values; add new keys naturally
- **Immutable after load** - Frozen Pydantic models
- **Engines** - Can be selected, not configured (system-level config)
- **Future consideration**: sibling inheritance (A→C, B→C) may be revisited later, but not now

### 3. Configuration Hierarchy
- **`.env`** - Secrets, environment-specific values (DB URLs, API keys, paths)
- **`config/*.json`** - Operational defaults (engines, LLM routing, system limits)
- **`playbooks/*`** - Document-specific behavior

### 4. Orchestration
- **Fixed stages with skip capability** - Not a dynamic DAG
- **Supervisor layer** - Pre-flight checks, error handling, DB updates
- **Stage skipping** - Controlled by playbook config
- **Future**: dynamic composition remains a possible later exploration, but not current scope

### 5. LLM Strategy
- **Provider**: OpenRouter (OpenAI-compatible)
- **Routing**: Per-stage model selection
- **Fallback**: Keep but simplify (try primary, then fallback)
- **Implementation**: `AsyncOpenAI` + `Instructor` for structured output

### 6. Pre-upload Checks
- **System preflight** - File exists, MIME type, size limits (supervisor layer)
- **Playbook preupload** - Blur, DPI, pages, language detection, duplicate detection, etc.
- **Duplicate detection** - Playbook level

### 7. Defaults & Paths
- **Export path**: `./OUTPUT/` (configurable via Settings)
- **Playbooks path**: `playbooks_path`
- **All paths**: move from hardcoded values to Settings/config wherever practical

## Implementation Tasks

### Phase 1: Foundation — Completed
- [x] **Playbook Model Redesign**
  - [x] Create `base.py` with `PlaybookValidationCheck`
  - [x] Create section modules (`meta`, `classify`, `schema`, `validate`, `rules`, `postprocess`)
  - [x] Implement merge strategy
  - [x] Create `PLAYBOOK_DESIGN.md` documentation
  - [x] Update `merged.py`
  - [x] Load defaults from `_base/*.json`

- [x] **Configuration Cleanup**
  - [x] Rename `playbooks_seed_path` → `playbooks_path`
  - [ ] Wire up `system.json` reading
  - [ ] Wire up `engines.json` reading
  - [ ] Remove remaining config duplication

### Phase 2: Core Pipeline — In Progress
- [x] **LLM Client Implementation**
  - [x] Implement `_call_raw` with `AsyncOpenAI`
  - [x] Implement `_call_with_schema` with `Instructor`
  - [x] Wire up `router.py`
  - [ ] Add `llm.json` cleanup / final OpenRouter config review

- [ ] **Orchestration Supervisor**
  - [x] Update `PipelineRunner` to use `playbooks_path`
  - [x] Add pre-flight checks (file exists, mime, size, playbook load)
  - [x] Add basic error handling / failed-stage reporting
  - [ ] Add DB run-row lifecycle hooks
  - [ ] Add stage skipping via config
  - [ ] Simplify and align `runner.py` with final orchestration design

### Phase 3: Integration — Pending
- [ ] **Pre-upload Split**
  - [ ] Move system checks fully into supervisor
  - [ ] Keep document-specific checks in playbook nodes
  - [ ] Add stubs for language detection, hash checking, filename checks, etc.

- [ ] **Better Stage Names**
  - [ ] Rename `pass_a/pass_b/pass_c/pass_d`
  - [ ] Rename `preupload/decide/act` to clearer stage names
  - [ ] Update `graph.py`
  - [ ] Update `nodes.py`
  - [ ] Update `routing.py`

### Phase 4: Production Features — Pending
- [ ] Implement circuit breakers for LLM calls
- [ ] Add comprehensive error handling
- [ ] Wire up persistence layer
- [ ] Implement HITL pause/resume
- [ ] Add monitoring/observability

## Current Notes / Newly Observed Issues
1. `runner.py` has been updated, but it still needs a careful review and end-to-end validation.
2. `graph.py` still uses the old fixed stage names; orchestration is not yet aligned with the updated naming plan.
3. `MergedPlaybook` currently uses aliases for reserved field names (`schema`, `validate`); this avoids warnings but should be revisited if the model shape changes.
4. `system.json` and `engines.json` are present but not fully wired into the runtime yet.
5. Documentation and code are mostly aligned now, but orchestration is the main remaining gap.

## Open Questions
1. **Non-overridable fields**: Flag-based approach? (suggestion only)
2. **Orchestration decisions**: How much should LLM decide vs predefined rules?
3. **Batch processing**: Design considerations for future
4. **Tool health monitoring**: Real-time vs pre-flight only?

## Design Principles
1. **Simplicity first** - Multi-line clarity over one-line cleverness
2. **Document everything** - Especially non-obvious decisions
3. **Fail fast** - Validate early, clear error messages
4. **Extensible** - Design for future changes without over-engineering

## Progress Tracking

### Completed ✅
- Research on document pipelines (2026-04-22)
- PLAYBOOK_DESIGN.md documentation
- `papertrail/playbooks/models/*` refactor
- `papertrail/playbooks/repository.py` updated for section-based loading
- `papertrail/playbooks/loader.py` updated for new loading logic
- `papertrail/playbooks/merger.py` removed
- `playbooks/` renamed from `playbooks_seed/`
- `_base` playbook JSON files created
- Example playbooks updated to the new file-based structure
- Playbook loading and inheritance verified with concrete examples
- `papertrail/llm/client.py` implemented for OpenRouter + Instructor
- `papertrail/config/loader.py` renamed `playbooks_seed_path` → `playbooks_path`

### In Progress 🔄
- Orchestration supervisor and runner cleanup
- Stage naming and graph/routing/node cleanup
- Runtime wiring for `system.json` and `engines.json`

---
*This document is the source of truth for architectural decisions and implementation progress.*