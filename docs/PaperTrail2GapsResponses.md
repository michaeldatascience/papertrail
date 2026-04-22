I've read docs/PaperTrail2Gaps.md carefully. Let me walk through your points section by section and share thoughts, pushback, and open questions. No code changes — just discussion.

1. compose.yaml and DB configuration
Your point: Maybe remove compose.yaml if we're not using Docker; where else is Postgres configured?

My analysis:

`compose.yaml` only spins up Postgres for local dev. It doesn't *define* the DB the code talks to.
The actual connection string comes from `Settings.database_url` in `papertrail/config/loader.py`, which reads from `.env` (key `DATABASE_URL`).
So the real source of truth is `.env` + `Settings`, not `compose.yaml`.
Recommendation: Keep compose.yaml as an optional convenience (it's small, zero harm). Add a clear note in README that the canonical DB config is .env / DATABASE_URL, and Docker is just one way to stand up Postgres locally.

Question back: Is your team standardizing on WSL-native Postgres going forward? If yes, I'd keep compose but mark it "optional."

2. pyproject.toml, uv, CLI wiring
Your point: Can we use pip + requirements.txt instead of uv? How does the CLI actually work?

My analysis:

**uv vs pip:** Yes, fully replaceable. `uv sync` just resolves and installs from `pyproject.toml` + `uv.lock`. Equivalents:
`pip install -e .` → installs the package in editable mode (same as uv sync for this project).
Generate `requirements.txt` via `uv export --format requirements-txt > requirements.txt` or `pip-compile`.
You lose the fast resolver + lockfile guarantees but gain ubiquity.
**CLI wiring:** The magic is this in `pyproject.toml`:
[project.scripts]
papertrail = "papertrail.cli.app:cli"
When you `pip install -e .` (or `uv sync`), setuptools/hatchling writes a tiny shim into `.venv/bin/papertrail` that calls `papertrail.cli.app:cli`. That `cli` is a `click.Group` defined in `cli/app.py`. Subcommands are attached via `cli.add_command(run_cmd, "run")`, etc. Each subcommand is itself a `@click.command` or `@click.group` decorated function that parses args and calls into the rest of the codebase.
Recommendation: Stay on uv — your team is already working, and mixing tools mid-project adds friction. But document the "pip fallback path" for anyone who can't use uv.

3. config/*.json documentation & centralization
Your point: Document them; move hardcoded things (like default data/output paths) here.

Strong agreement. Right now the config has drift:

`system.json` has `max_file_size_mb`, `supported_mimes`, `preupload.blur_threshold`, etc. — but **none of these are actually read by the code**. `preupload.py` reads these values from the **playbook** instead.
`engines.json` defaults aren't read anywhere either — the playbook's `meta.engines` is used directly.
`llm.json` *is* used (by `LLMClient`).
So we have three levels of config and they aren't clearly separated:

`config/*.json` — system-wide, environment-independent defaults (read once at startup).
`.env` / `Settings` — environment-specific (DB URL, API keys, paths).
`playbooks/*` — document-type behavior.
Candidate items to centralize:

Default data/blob path (currently `.env`).
Default output/exports path (currently hardcoded `data/exports/` in `cli/commands/run.py`).
Supported mime types (currently duplicated between `preupload.py`, `runner.py._guess_mime`, `system.json`).
Default correction max_attempts, HITL thresholds (could be playbook-only though).
Retry/backoff parameters.
Open question: What's the rule you want for deciding where a setting lives? I'd propose:

**`.env`:** anything secret or environment-varying (keys, URLs, filesystem paths).
**`config/*.json`:** operational defaults that rarely change and aren't document-specific.
**Playbook:** anything document-specific.
If we agree on that rule, the cleanup is mechanical.

4. config/loader.py — Langfuse, app vars, playbooks_seed_path
My analysis:

`Settings` currently holds Langfuse keys, `app_env`, `log_level`, `blob_storage_path`, `playbooks_seed_path`. All read from `.env`.
**`playbooks_seed_path` is misnamed.** It's being used by `PlaybookRepository` as *the* playbook source, not a seed. If we're keeping file-based playbooks (your decision), this should become `playbooks_path` or `playbooks_dir`.
**Langfuse:** Fine to leave in Settings. It's optional (short-circuits if key missing).
**`app_env`:** Currently only used to toggle SQLAlchemy `echo=True`. That's fine, but we could also use it to select `config/llm.dev.json` vs `config/llm.prod.json` as the docs suggest.
Recommendation:

Rename `playbooks_seed_path` → `playbooks_path`.
Once we settle the config rule in point 3, move operational defaults out of `Settings`.
5. papertrail/playbooks/* — the big one
This is the heart of your feedback. Let me restate what I hear you saying:

Playbooks stay file-based for now, but the format must remain DB-portable (= JSON blobs).
The loader/merger shouldn't try to be clever about where playbooks come from — treat them as if they might come from DB.
Validation can be loose/optional at load time; strict validation is really just a failsafe against a corrupt file.
**The Pydantic base models should be the contract.** Children inherit from base; if base is right, children are automatically right.
Playbook authoring is a human activity, not a system feature. So: strong base + good samples > complex validators.
Engines are **system-level**, not playbook-level. A playbook can *select* an engine but not *configure* it.
Different sections (meta, classify, schema, validate, cross_validate, rules, postprocess) probably deserve their own classes, each with a clear base.
I strongly agree with most of this. Some thoughts and pushback:

Current code problems I see
`models.py` has a weird `PlaybookCheckConfig.__init__` that hacks extras into `self.extra` — brittle and fights Pydantic v2 design. Pydantic v2 has `model_config = {"extra": "allow"}` which handles this cleanly.
`MergedPlaybook` uses `schema_` / `validate_` / `rules_` aliases because `schema` / `validate` are reserved. The loader `pop()`s them and renames — works but fragile.
`loader.py` has "heuristic for file-based stub" — setting `extends_slug = "_base"` if `document_type != "base"`. This is exactly the kind of patchwork you're calling out.
`repository.py` injects `extends_slug` into `meta` — same problem.
Inheritance in config sections is **shallow**: `deep_merge` merges dicts recursively, but since the Pydantic models have strict types, merged dicts get re-validated *as a whole*. So if `_base.validate` has full structure and `indian_cheque.validate` only has a partial override, the merged dict is still a *complete* `ValidateConfig`. That's OK — it works — but it's not obvious from the code.
Lists are fully replaced on merge. That's documented, but **it means a child can't add a single validation rule without re-declaring all base rules.** Is that what you want? Trade-off: list-replacement = predictable but verbose; list-append = ergonomic but ambiguous. Worth discussing.
Your "engines can be selected not configured" point
I agree but want to sharpen it:

**System defines:** which engine implementations exist, how to instantiate them, what params they take.
**Playbook says:** "use `paddleocr` for OCR," optionally "with language=hi."
The playbook should **never** define what "paddleocr" *is*.
Currently meta.engines in the playbook holds just names ("layout": "docling"), which is correct. But config/engines.json has the actual engine defaults — and as noted, it's not being read. So the structure is right, but wiring is missing.

Proposed structure (for discussion)
Each config section as its own module with three things:

`BaseXxxConfig` (Pydantic) — required fields & types.
`XxxDefaults` — the `_base` values, also validated against the base model.
`load_xxx(raw_dict) -> XxxConfig` — merges defaults + raw, returns a validated instance.
Then MergedPlaybook is just a composition of these. No aliases, no extends_slug hackery. Inheritance = "apply child overrides to base defaults."

Question back to you:

Do you want **single-level inheritance** (every playbook extends `_base` directly, no chains)? I'd recommend yes — simpler to reason about, covers every real use case.
For list fields: **replace** or **merge-by-key**? (e.g., if child says `hard_rules.payee_name = [{"rule": "regex"}]`, does it replace base rules for payee_name or add to them?)
Do you want section classes to be **frozen/immutable** after load? (Safer, but means correction attempts etc. must live in pipeline state only, not in the playbook object — which is already the case.)
6. Orchestration — graph.py, nodes.py
Your biggest concern: the graph is fixed and hardcoded. Steps/nodes are embedded in code. You want the graph to come from playbook config, and you want an orchestration layer that sits above the graph and can handle system-level failures (bad config, missing tools, unhealthy file).

This is a significant architectural direction. Let me split it into two separate questions:

Question A: Should stages themselves be playbook-configurable?
Right now stages are fixed: preupload → classify → pass_a → pass_b → pass_c → pass_d → correction? → decide → act.

Options:

**Keep stages fixed, make them skippable via config.** A playbook can say `"classify": {"enabled": false}` and the graph skips it. Minimal code change; nodes just early-return.
**Make stages composable.** Playbook declares a `"pipeline": ["preupload", "classify", "extract", "validate", "decide"]` list; the graph is built at runtime from that.
**Full DAG from playbook.** Playbook fully describes nodes and edges.
My view:

Option 3 is **overkill** for this project. DAGs-from-config are hard to reason about, hard to test, hard to debug, and introduce bugs that mimic bad config.
Option 1 gives you 80% of the flexibility with 5% of the complexity.
Option 2 is a reasonable middle ground *if* we genuinely need different pipelines for different document families. Do we? I haven't seen a concrete example yet — every document type in scope follows the same stage order.
Strong recommendation: Option 1 (skippable stages + runtime-tunable parameters) unless you can point to a concrete document type that needs a different shape of pipeline, not just different settings.

Question B: Should there be a supervisor layer above the graph?
Yes, absolutely. I fully agree. The current code is missing:

Pre-flight checks: does the playbook load? Are referenced engines available? Are referenced tools registered? Are prompt templates present? Are API keys set?
A runtime error policy: what does a node failure mean? Currently nothing — the next node runs anyway.
Cleanup on abort: DB status update, trace flush, partial run marking.
Proposed shape:

PipelineRunner.run(file, playbook_slug):
    1. Load + validate playbook (fail fast)
    2. Preflight: engines, tools, templates, credentials
    3. Create run row in DB (status=created)
    4. Invoke graph.ainvoke(state)
       - each node wraps its work in try/except
       - on error: state.error set, routing sends to terminal failure node
    5. Finalize: DB status update, trace flush, blob cleanup
The graph itself stays minimal. The supervisor wraps it.

Question back: When you say "orchestration engine can decide to skip execution based on tool health" — do you mean at run start (pre-flight) or mid-run (e.g., IFSC API is down, skip enrichment but keep the run going)? They're different problems.

7. routing.py, runner.py
You said "mostly ok for fixed logic." I agree for now. Once we settle on playbook-driven stages (point 6A), routing needs to change too — but if we stick with Option 1 (skippable stages), routing changes are small.

8. papertrail/passes/* — pre-upload placement
Your point: pre-upload is currently executed at system level but configured at playbook level. You want to move it fully into playbook+orchestration.

I agree — but with nuance. Some pre-upload checks are inherently system-level:

Is the file accessible?
Is the mime type in our *global* allowlist?
Is the file under the *global* max size?
These are gate-keepers — they protect the system regardless of playbook.

Other checks are document-specific:

Blur threshold
Resolution DPI
Page count limits
These belong to the playbook.

Recommended split:

**System preflight** (in orchestration supervisor): file exists, mime in global allowlist, size within absolute max, not a duplicate. No playbook needed.
**Playbook preupload node** (in graph): blur, resolution, page count, document-specific format filters. Config from `playbook.preupload.checks`.
This matches your instinct (push to playbook) while keeping the system safe against bad inputs before any playbook logic runs.

Question back: Do you see duplicate detection as system-level or playbook-level? Docs say system-level (global hash check); playbook could override the lookback window. Agree?

9. papertrail/llm/*
You want:

Real OpenRouter client (`_call_raw`, `_call_with_schema`).
Real router.
Decide whether fallback is needed.
My analysis:

**OpenRouter client** is straightforward. OpenRouter is OpenAI-API-compatible. With the `openai` package, `AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)` and you're in. Instructor integration for structured output via `instructor.from_openai(...)`.
**Router** is already half there in `llm/router.py` (stage → primary/fallback names). It just needs to actually be used by `LLMClient.call`.
**Fallback:** I'd argue **keep it but simplify.** The current design (retry primary N times, then fallback N times) is fine. But:
If you're cost-sensitive and trust Anthropic, maybe just use primary with 2 retries and surface errors. That's simpler.
If you want reliability (capstone demo), keep fallback — it costs nothing when primary works.
**My recommendation:** keep fallback, drop the per-provider retry count to 1 (so: try primary once, try fallback once, done). Simpler to reason about, 2 API calls max.
Open question: Do you want streaming? Instructor supports it but it complicates everything. For this project I'd skip it.

10. papertrail/cli/*
You want to keep extending it in sync with functionality. Agreed. Small point: the --save flag in cli/commands/run.py hardcodes data/exports/ — that should come from settings once we finalize the config rule.

11. playbooks_seed/*
Your decision: scrap the seed concept; just use real data + real playbooks.

I agree. The seed concept only made sense if we were DB-first. Since you're committing to file-based playbooks, playbooks_seed/ is the playbooks directory — just rename it to playbooks/ and be done.

12. tests/*, scripts/*, docs
**tests:** Agree — delete, rewrite after architecture settles. But keep `conftest.py` structure as reference.
**scripts:** Agree — `generate_sample_inputs.py` is obsolete.
**docs:** Agree — archive outdated ones. Candidates for archive: `Session_Log_2026-04-20.md` (historical only), possibly parts of `PaperTrail_Locked_Architecture.md` if the playbook structure changes significantly.
13. Gaps list
Your restated gaps are accurate. Priority order (my proposal, for discussion):

#	Gap	Why this priority
1	Playbook model rewrite	Everything downstream depends on this
2	Supervisor/preflight layer	Safety net before we wire real engines
3	LLM client real implementation	Needed for classify + extract
4	Engine dispatcher real implementation	Needed for pass_b
5	Validation + decision engines	Needed to close the loop
6	Persistence wiring	Can be done in parallel with 3-5
7	HITL resume	After core pipeline works
8	API package	After CLI path is solid
9	Schema drift cleanup	Concurrent with #1
Overall bottom line + my counter-questions for you
Where I strongly agree:

Playbook model is too hacky — base models should be the contract.
Engines are system-level; playbooks only select.
Supervisor layer above the graph is needed.
Scrap seeds, scrap obsolete tests/scripts.
Config-rule clarity (`.env` vs `config/*.json` vs playbook) is overdue.
Where I'd push back / want clarification:

**"Graph should be fully config-driven"** — I think this goes too far. Suggest Option 1 (skippable stages) unless you have a concrete doc type that needs a different pipeline shape.
**"Pre-upload moves fully into playbook"** — I'd keep a thin system-level preflight and push doc-specific checks into playbook. Do you agree with the split?
**"Validation can be loose"** — I'd argue strictly validate at load time but only against the Pydantic base models, not against custom rules. Loose = confusing bugs later.
**Lists on merge: replace vs append?** Need a decision.
**Inheritance: single level only?** Recommend yes.
**LLM fallback: keep or drop?** Recommend keep-but-simplify.
**When does the orchestrator decide to skip?** Preflight only, or also mid-run?
If you give me your position on those 7 questions, I think we'll have enough alignment to start proposing concrete redesigns (still without touching code until you say go).