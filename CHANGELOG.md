# Changelog

All notable changes to the Marathon Race Day Coach demo. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

The project is a three-mode ADK 2.0 education demo. Each phase below maps to a git commit (and usually a tag).

---

## [Unreleased]

### Coming next — Phase 4: Pillar 3 rebuild

The current Mode 3 (Team Race Day Planner) demonstrates **runtime-sized parallel fan-out** but doesn't show what makes ADK 2.0's dynamic workflows uniquely powerful versus 1.x's `ParallelAgent` — namely **variable depth, recursive structure, and the ability to spawn more work from inside a parallel branch.**

Plan: replace Mode 3 with a **deep research** demo (same marathon theme — "Deep-dive: Boston Marathon"). A decomposer agent breaks the user's question into N sub-research-questions, each one researched in parallel, with some sub-questions recursively spawning their own deeper questions based on findings. A synthesizer aggregates the tree into a comprehensive briefing.

This pattern (Perplexity / ChatGPT Deep Research / Bing) is the canonical Pillar 3 use case in the wild. It's genuinely impossible to express in ADK 1.x without bypassing the framework primitives.

See `docs/BUILD_PLAN.md` (to be updated) for the phased build plan.

---

## Discoverability fix — chat + team panels findable
**Commit:** `627d819` · 2026-05-17

### Added
- Floating **"More below — Concierge (Pillar 2) + Team (Pillar 3) ▾"** pill at the bottom of the viewport when the user is at the top of Mode 1. Glass-styled, bouncing arrow, click to smooth-scroll to the chat panel. Hides automatically once the user scrolls past Mode 1.
- Auto-scroll to chat panel when Mode 1's `workflow_complete` event fires. The audience sees the natural progression instead of sitting at the stats card wondering what's next.

### Changed
- Disabled-state opacity on `.chat-section` bumped from 0.55 to 0.78 so the locked-state panel is still clearly visible on the pastel light background.
- `main` height changed from `100vh` to `calc(100vh - 24px)` to give the scroll hint room to peek above the fold.

### Why
User feedback: *"I don't see the chat panel and 6 specialist pills."* Mode 1's `height: 100vh` meant the chat and team panels were below the fold on first load, with no indicator they existed. Fix surfaces them without breaking the narrative-by-scroll layout.

---

## Phase 3 — Documentation polish
**Commit:** _next_ · 2026-05-17

### Changed
- `VIDEO_SCRIPT.md` rewritten end-to-end for the three-mode structure. Old script covered only Pillar 1 (~20 min on graph workflows alone). New script (~20 min) walks through all three modes with section-by-section prose, stage directions, code references with file paths and line numbers, and per-section pacing budgets. Includes cut and add lists for runtime flex.
- `README.md` (was empty) — proper repo overview: 3-mode summary, quickstart with uv, file structure, decision tree, "what's uniquely 2.0" per pillar, verified runtime numbers from real LLM runs.

### Decided not to add
- Mode switcher / tab bar navigation. The sequential layout (Mode 1 graph → chat panel → team panel) mirrors the video script's narrative arc, so audiences see the story by scrolling. A tab switcher would be right for a product but is over-engineering for a teaching demo.

---

## Phase 2 — Team Race Day Planner (Pillar 3: Dynamic workflows)
**Commit:** _next_ · 2026-05-17

### Added
- `workflows/team_planner.py` — `team_workflow` using `@node(parallel_worker=True, rerun_on_resume=True)` to fan out one per-runner subworkflow per roster slot. Runtime-sized parallelism via ADK 2.0's `_ParallelWorker` primitive.
- `RunnerSpec`, `RunnerPlan`, `TeamSummary` schemas in `workflows/shared/schemas.py`.
- `emit_roster` function node parses the roster from the initial user message (JSON-encoded `Content`).
- `plan_for_runner` parallel-worker node bundles per-runner data + picks the right strategy agent via temperature + invokes the agent via `ctx.run_node(agent, node_input=...)`. Reuses the strategy agents from `workflows/strategy_graph` — no per-runner duplication.
- `summarize_team` function node aggregates the parallel results into a `TeamSummary`.
- `/team?roster=alpha|omega` SSE endpoint on `server.py`. Two preset rosters: alpha (3 runners) and omega (10 runners). Stream events: `team_start`, `runner_complete`, `team_complete`.
- Team panel UI in `static/index.html`: purple "Pillar 3 · Dynamic Workflows" tag, 2 roster picker buttons, N runner rows with avatar + name + scenario + live timer + finish time. Active rows pulse cyan; complete rows go mint with the personalized target finish time displayed.
- Team stats card with runner count, total wall time, slowest runner, sum-if-serial, **parallel speedup multiplier**, and LLM call count.
- `run_team_demo.py` CLI tool for headless testing.

### Verified end-to-end in browser

| Roster | Runners | Total wall time | Sum if serial | **Speedup** |
|---|---|---|---|---|
| Team Alpha | 3 (HOT/NORMAL/COLD) | 10.82s | 27.85s | **2.6×** |
| Team Omega | 10 (mixed) | 9.24s | 78.11s | **8.4×** |

The 10-runner case is the killer pitch: 10 LLM calls completing in the same wall time as ~3, because they're all running in parallel under one `_ParallelWorker`. Each runner gets a personalized RaceStrategy with the right target finish time per their scenario (HOT runners cluster ~3:35, NORMAL ~3:03, COLD ~3:12).

### Why this is uniquely ADK 2.0
- `ParallelAgent` (1.x): static list of sub-agents at design time. Can't grow with roster size.
- `LoopAgent` (1.x): serial only.
- `@node(parallel_worker=True)`: takes a runtime list, spawns one task per item, gathers via `asyncio.wait`. Topology determined by data, not code.

### Notes on what tripped me up
- `state_delta` on `runner.run_async()` doesn't reach the first node's `ctx.state` (the dict is unpopulated when `emit_roster` runs). Worked around by passing the roster as a JSON-encoded `Content` user message and parsing in `emit_roster`.
- `ctx.run_node(other_node, ...)` requires the CALLING node to have `rerun_on_resume=True`. The `parallel_worker=True` decorator does NOT auto-set this. Must pass explicitly: `@node(parallel_worker=True, rerun_on_resume=True)`.
- `@node(parallel_worker=True)` functions must use parameter name `node_input` (not a domain-specific name) because default `parameter_binding='state'` looks up non-special-named params from `ctx.state`.

---

## Phase 1 — Race Day Concierge (Pillar 2: Collaborative agents)
**Commit:** `0c39ce2` · 2026-05-17

### Added
- `workflows/concierge.py` — `race_concierge` coordinator with 6 single_turn specialist subagents (medical, weather, pacing, gear, nutrition, mental).
- `SpecialistInput` + `SpecialistResponse` schemas (with `concern_level`, `recommendation`, `reasoning`).
- `/chat?question=...` SSE endpoint on `server.py` — streams `dispatched`, `specialist_done`, `synthesized`, `chat_complete` events. Parses parallel `function_call` parts so the UI lights up subagents individually.
- Chat panel UI in `static/index.html` (Liquid Glass styled, mint accents): 6 specialist pills with idle/active/complete/concern-serious states, 5 suggestion pills, chat history bubbles tagged with "Concierge · N specialists in parallel".
- `run_concierge_demo.py` — CLI tool for testing 4 question types.

### Changed
- `server.py`: module-level `_latest` cache for the most recent strategy + bundled data (so `/chat` can reference them).
- `static/index.html`: body `overflow-y: auto` to allow scrolling below the Mode 1 main grid into the chat panel.

### Verified
| Question | Dispatched subset | Pattern |
|---|---|---|
| "Should I race today?" | medical + weather + pacing | 3-of-6 in parallel |
| "What about my fueling plan?" | nutrition | 1-of-6 |
| "Anything I should worry about overall?" | all 6 | 6-in-parallel |

Different inputs → different parallel subsets, the unique ADK 2.0 collab feature that 1.x `ParallelAgent` (static) cannot do.

---

## Phase 0 — Refactor to workflows/ package
**Commit:** `c7af894` · 2026-05-17

### Changed
- Split the monolithic `marathon.py` into:
  - `workflows/shared/schemas.py` — Pydantic models (WeatherData, CourseData, FitnessData, RaceStrategy, BundledRunData).
  - `workflows/shared/scenarios.py` — canned HOT/NORMAL/COLD data + `scenario()` and `slow_mo()` helpers (renamed from private `_scenario`/`_slow_mo` to public module-level).
  - `workflows/strategy_graph.py` — function nodes, JoinNode, router, three strategy agents, root `Workflow`.
- Updated imports in `run_demo.py` and `server.py`.

### Removed
- `marathon.py` (replaced by `workflows/strategy_graph.py`).

### Why
Phase 1 (concierge) and Phase 2 (team) need their own workflow modules. Splitting before adding them keeps the package layout clean.

---

## v1 — Graph workflow stable
**Commit:** `4729d8a` · 2026-05-16 · **Tag:** `v1-graph-workflow-stable`

### Added
- ADK 2.0 `Workflow` with 3 parallel function nodes (`fetch_weather`, `analyze_course`, `pull_fitness`) → `JoinNode` → router → one of three single_turn strategy `Agent`s (hot/normal/cold).
- Real LLM agents using `gemini-flash-latest` with structured `RaceStrategy` outputs.
- FastAPI + SSE server (`server.py`) streaming node lifecycle to the browser.
- Vanilla JS + SVG Liquid Glass visualization (`static/index.html`): live pulse animation, per-node timers, replay button, slow-mo dropdown.
- CLI runner (`run_demo.py`) and minimal smoke test (`smoke_test.py`).
- `VIDEO_SCRIPT.md` — 20-minute talk script.
- `docs/`:
  - `ADK_1X_REWRITE_ANALYSIS.md`
  - `ADK_2_PILLARS_DECISION_TREE.md`
  - `COLLABORATION_MODES.md`
  - `BUILD_PLAN.md`

### Fallback
Tagged for safety so any future state can `git checkout v1-graph-workflow-stable` to return to this working version.
