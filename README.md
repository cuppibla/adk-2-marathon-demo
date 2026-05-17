# Marathon Race Day Coach

> An education demo for **Google ADK 2.0** — three modes, three pillars, one app.

This repo is a working, end-to-end demonstration of all three orchestration patterns introduced in ADK 2.0 (the v2.0.0b1 Beta of `google-adk`). Each mode tells one part of a coherent story: plan a single runner's race day, chat about the plan, then scale to a whole team.

| Mode | Pillar | What you'll see |
|---|---|---|
| **1. Single Runner** | Graph workflows | Three parallel data fetches converge in a `JoinNode`, a deterministic Python router branches on temperature, one of three LLM strategy agents generates a structured `RaceStrategy`. ~7s, **1 LLM call**. |
| **2. Concierge** | Collaborative agents | An LLM coordinator dispatches a *dynamic subset* of 6 specialist subagents in parallel based on what the user asks. Same UI, different inputs, different dispatch patterns. |
| **3. Team Planner** | Dynamic workflows | A roster of N runners (3 or 10) fans out into N parallel per-runner subworkflows via `@node(parallel_worker=True)`. **8.4× parallel speedup** with 10 runners. |

---

## Quickstart

Requires Python 3.11+, [uv](https://github.com/astral-sh/uv), and a Gemini API key in `.env`.

```bash
# Install dependencies
uv sync

# Set up API key
cp .env.example .env
# Then edit .env and put your key in GOOGLE_API_KEY=...

# Run the server
uv run python server.py
```

Browse to **http://127.0.0.1:8000/**.

### CLI runners (no browser needed)

```bash
uv run python run_demo.py HOT           # Mode 1 — single runner, HOT scenario
uv run python run_concierge_demo.py     # Mode 2 — concierge with 4 sample questions
uv run python run_team_demo.py          # Mode 3 — team with 3-runner and 10-runner rosters
uv run python smoke_test.py             # Minimal ADK 2.0 Workflow sanity check
```

---

## What's in this repo

```
marathonplanner/
├── workflows/                  # ADK 2.0 workflows — the heart of the demo
│   ├── shared/
│   │   ├── schemas.py          # Pydantic models (WeatherData, RaceStrategy, etc.)
│   │   └── scenarios.py        # Canned HOT/NORMAL/COLD scenario data
│   ├── strategy_graph.py       # Pillar 1 — graph workflow with parallel fetches + router + agents
│   ├── concierge.py            # Pillar 2 — coordinator with 6 single_turn specialist subagents
│   └── team_planner.py         # Pillar 3 — @node(parallel_worker=True) for runtime fan-out
├── server.py                   # FastAPI + SSE bridge (no ADK knowledge — just plumbing)
├── static/index.html           # Liquid Glass visualization (vanilla HTML/CSS/JS)
├── run_demo.py, run_*_demo.py  # Headless CLI runners per mode
├── docs/
│   ├── BUILD_PLAN.md           # The plan that produced this repo
│   ├── ADK_1X_REWRITE_ANALYSIS.md  # How this would look in ADK 1.x (and why it'd be worse)
│   ├── ADK_2_PILLARS_DECISION_TREE.md  # Which pillar to use when
│   └── COLLABORATION_MODES.md  # chat/task/single_turn deep dive
├── VIDEO_SCRIPT.md             # 20-min talk script for recording the demo
└── CHANGELOG.md
```

The repo grew in phases. Each phase is its own git commit, and `v1-graph-workflow-stable` is a tag pointing to the working single-mode version before Phase 1 + Phase 2 were added.

---

## Why three pillars, not one?

ADK 2.0's headline features are three distinct orchestration patterns. They overlap but each shines in a different shape of problem.

```
                            ┌──────────────────────────────────┐
                            │  Is the structure known up front │
                            │  and expressible as a diagram?   │
                            └────────────┬──────────────┬──────┘
                                  yes    │              │   no
                                         ▼              ▼
                          ┌──────────────┐    ┌─────────────────────────┐
                          │  Pillar 1    │    │  Loops, recursion, or   │
                          │  Graph WF    │    │  runtime-sized fan-out? │
                          └──────────────┘    └────┬──────────────┬─────┘
                                                  yes             │  no
                                                   ▼              ▼
                                       ┌──────────────┐  ┌──────────────────────┐
                                       │  Pillar 3    │  │  LLM should decide   │
                                       │  Dynamic WF  │  │  who handles it?     │
                                       └──────────────┘  └─────┬────────────┬───┘
                                                              yes           │ no
                                                               ▼            ▼
                                                  ┌──────────────┐  ┌─────────────────┐
                                                  │  Pillar 2    │  │  Single LlmAgent│
                                                  │  Collab agents│ │  with tools     │
                                                  └──────────────┘  └─────────────────┘
```

The marathon planner uses all three because the problem has all three shapes: structured planning (graph), conversational follow-up (collab), variable team scale (dynamic). See [docs/ADK_2_PILLARS_DECISION_TREE.md](docs/ADK_2_PILLARS_DECISION_TREE.md) for the full decision tree with worked examples.

---

## What's *uniquely* ADK 2.0 about this demo

For each pillar, here's the thing 1.x genuinely can't do as cleanly:

**Pillar 1 (Graph):** Mixing function nodes and agent nodes as peers in the same `edges=[...]` array. In 1.x, every "node" must be an agent — so fetching weather requires building a `weather_agent` with a `get_weather` tool, adding an LLM call per fetch.

**Pillar 2 (Collab):** LLM-driven *dynamic subset* selection with parallel execution. 1.x's `ParallelAgent` is static (always all sub-agents); `transfer_to_agent` is serial. Only 2.0 collab lets the coordinator pick which specialists to invoke per request and run them concurrently.

**Pillar 3 (Dynamic):** Runtime-sized parallel fan-out. 1.x's `ParallelAgent` has a fixed sub-agent list; `LoopAgent` is serial. Only `@node(parallel_worker=True)` lets the parallel topology be determined by data shape at runtime.

See [docs/ADK_1X_REWRITE_ANALYSIS.md](docs/ADK_1X_REWRITE_ANALYSIS.md) for the full side-by-side comparison.

---

## Verified numbers (from real LLM runs)

| Mode | Scenario | Wall time | LLM calls | Notes |
|---|---|---|---|---|
| 1 | Single Runner, HOT | ~7s | 1 | Fetch phase saved 2.5s via parallel fan-in |
| 2 | "Should I race today?" | ~13s | 4 | Coordinator + 3 parallel specialists |
| 2 | "What about fueling?" | ~10s | 2 | Coordinator + 1 specialist (5 sat out) |
| 2 | "Full review" | ~16s | 7 | Coordinator + 6 specialists in parallel |
| 3 | Team Alpha (3 runners) | ~10s | 3 | **2.6× parallel speedup** vs serial |
| 3 | Team Omega (10 runners) | ~9s | 10 | **8.4× parallel speedup** vs serial |

---

## Tech stack

- **ADK 2.0:** `google-adk==2.0.0b1` (Beta — install with `uv add "google-adk==2.0.0b1" --prerelease=allow`)
- **Model:** `gemini-flash-latest` (resolves to `gemini-3-flash-preview`)
- **Server:** FastAPI + `sse-starlette` (both come transitively from ADK)
- **Frontend:** Vanilla HTML/CSS/JS + SVG. No framework, no build step. Liquid Glass aesthetic.

---

## Recording the demo

The full 20-minute talk script is in [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md). It includes:
- Pre-record checklist (what to open, what to pre-warm)
- Section-by-section prose with stage directions
- Pacing budget per section
- Cut list (if running long) and addition list (if running short)

---

## Status

This is a **demo / education repo**, not production code:
- Module-level state on the server (single-user assumption)
- Canned scenario data (no real API calls)
- No tests beyond the smoke test
- ADK 2.0 itself is Beta — APIs may break between releases

The current state is stable and works end-to-end. Use it as a reference for what ADK 2.0 looks like when each pillar is applied correctly.

---

## License

MIT.

---

*Built as a teaching artifact. If you spot something that could be a clearer example, open a PR.*
