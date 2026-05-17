# Changelog

All notable changes to the Marathon Race Day Coach demo. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

The project is a three-mode ADK 2.0 education demo. Each phase below maps to a git commit (and usually a tag).

---

## [Unreleased]

### Phase 2 (in progress) — Team mode (Pillar 3: Dynamic workflows)
Adds Mode 3 — a roster of N runners (variable size) fanned out in parallel via `@node` and `asyncio.gather`. See `docs/BUILD_PLAN.md`.

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
