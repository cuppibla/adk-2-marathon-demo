# Marathon Race Day Coach — Full Build Plan for ADK 2.0 Education Demo

This document is the build plan for evolving the marathon planner into a three-mode educational demo of ADK 2.0's three pillars (graph workflows, collaborative agents, dynamic workflows).

## The vision: three modes, one app, one coherent story

The marathon theme becomes a single app called **Marathon Race Day Coach** with three modes, each demonstrating one ADK 2.0 pillar. The modes tell a progressive story:

1. **Single Runner mode** — generate a strategy for one runner (Pillar 1: Graph workflows)
2. **Concierge mode** — chat with the strategy, ask follow-ups (Pillar 2: Collaborative agents)
3. **Team mode** — plan strategies for a roster of N runners (Pillar 3: Dynamic workflows)

The narrative arc: *"You can plan for one runner. You can chat about that plan. You can scale to a whole team. Each step uses the ADK 2.0 pattern that fits its shape."* The audience learns the framework by watching one app grow.

## Pedagogical map — what each mode teaches

| Mode | Pillar | Unique 2.0 feature it demos | What 1.x can't do here |
|---|---|---|---|
| **Single Runner** | Graph workflows | Function nodes + JoinNode + deterministic router in one declarative graph | Mix functions and agents without wrapping; deterministic routing without LLM judgment; typed parallel handoff |
| **Concierge** | Collaborative agents | LLM coordinator dynamically picks a *subset* of subagents to invoke in parallel based on user input | Static `ParallelAgent` always runs all sub-agents; `transfer_to_agent` is serial, one at a time |
| **Team** | Dynamic workflows | `@node` with runtime-sized parallel fan-out via `asyncio.gather` over a roster of unknown size; resumable execution | `LoopAgent` has fixed iteration count; no way to fan out over a list whose size is unknown until runtime |

Each mode demonstrates **one thing 1.x genuinely can't do well**. No filler features.

---

## Mode 1 — Single Runner (already built)

This is the current marathon planner. Kept as-is.

**Flow:** User picks Hot/Normal/Cold scenario, clicks Run. Three function nodes fetch weather + course + fitness in parallel. JoinNode bundles. Router branches on temperature. One of three strategy agents generates a personalized RaceStrategy.

**Demo time:** 4 minutes (scripted in `VIDEO_SCRIPT.md`)

**Pedagogical points:**
- Graph workflows let you draw the diagram before writing code
- Function nodes coexist with Agent nodes as peers — no wrapping
- Deterministic routing on data instead of LLM judgment
- JoinNode bundles parallel outputs into a typed payload
- ~7 seconds total, 1 LLM call

## Mode 2 — Concierge (new)

After the Mode 1 strategy is generated, switch to a chat panel. User asks free-form follow-up questions. A `race_concierge` coordinator dispatches to a dynamic subset of specialist subagents in parallel.

### Subagents (all `single_turn` mode)

- `medical_specialist` — assesses injury / health risks
- `weather_specialist` — re-checks weather, suggests adjustments
- `pacing_specialist` — re-calculates pace under different assumptions
- `gear_specialist` — recommends gear changes
- `nutrition_specialist` — adjusts fueling plan
- `mental_specialist` — addresses pre-race nerves, motivation

### What the audience sees

The chat UI lights up the relevant subagents based on the user's question:

| User question | Coordinator invokes (in parallel) |
|---|---|
| *"Should I race today?"* | medical + weather + pacing (3 nodes light up) |
| *"My left knee is twinging at mile 18"* | medical only (1 node lights up) |
| *"What about my fueling plan?"* | nutrition only (1 node) |
| *"Anything I should worry about?"* | all 6 in parallel (6 nodes) |
| *"It's raining now, should I change my plan?"* | weather + gear + pacing (3 nodes) |

The wow moment: **same UI, different inputs, different parallel patterns**. The coordinator is *reasoning about who should answer*. The audience watches dynamic delegation happen.

### Talk track

*"Notice that for 'should I race today,' three subagents fired in parallel. For 'fueling plan,' only one. With `ParallelAgent` in ADK 1.x, you'd always run all six — wasting LLM calls on irrelevant specialists. With ADK 2.0 collaborative agents, the coordinator picks the right subset every time, and runs them in parallel."*

### Demo time: 3-4 minutes

- Show the chat UI
- Type 3 different questions, watch different subsets light up
- Show the LLM-call-count delta vs. an always-fan-out approach (the stats card updates per question)

## Mode 3 — Team (new)

A toggle at the top: "Single Runner" vs "Team." In Team mode, the user uploads or selects a roster (a JSON file with N runners — could be 3, could be 12). A dynamic workflow fans out, running the full Mode 1 graph workflow for each runner in parallel. Aggregates into a team dashboard.

### What the audience sees

User clicks "Load Team A" (3 runners). Three full graph workflows execute in parallel — visualized as three columns running simultaneously. Each runner's parallel pulse → router → strategy plays out. After all complete, a team dashboard summarizes:

- Three strategies side-by-side
- Common themes ("all three need to manage 78°F heat")
- Outliers ("Bob's pace target is unusual for his fitness")

Then: user clicks "Load Team B" (10 runners). Same UI, ten columns. The audience SEES that the topology is determined at runtime by the roster size.

### The hero moment

Show two scenarios:
1. **Static graph would require:** "redefine the workflow's edges every time team size changes" — not possible
2. **`LoopAgent` would require:** "fixed iteration count, can't fan out in parallel" — also not possible
3. **Dynamic `@node` does:** "given a runtime list, fan out in parallel via `asyncio.gather`" — works for 3 or 30 runners

### Bonus: resumability

After Team B runs (10 runners), simulate a crash. Re-trigger the workflow. The dynamic workflow's checkpointing means already-completed runners are skipped — only the unfinished ones re-execute. *This is genuinely impossible in 1.x without manual session management.*

### Talk track

*"For the single runner, we drew the graph. For the team, we don't know the team size at design time — could be 3 runners, could be 30. Dynamic workflows let us fan out at runtime over a list of any size. And because dynamic workflows checkpoint each node, if anything fails, we can resume and skip what's already done."*

### Demo time: 3 minutes

---

## Architecture / file layout

The repo grows but stays organized:

```
marathonplanner/
├── pyproject.toml
├── .env, .env.example, .gitignore
├── README.md                       (NEW — getting started)
├── docs/
│   ├── ADK_1X_REWRITE_ANALYSIS.md
│   ├── ADK_2_PILLARS_DECISION_TREE.md
│   ├── COLLABORATION_MODES.md
│   └── BUILD_PLAN.md
├── VIDEO_SCRIPT.md                (updated for 3 modes)
├── workflows/                     (NEW package)
│   ├── __init__.py
│   ├── shared/
│   │   ├── schemas.py             (WeatherData, CourseData, FitnessData, RaceStrategy, etc.)
│   │   └── scenarios.py           (canned HOT/NORMAL/COLD data)
│   ├── strategy_graph.py          (Mode 1 — existing marathon.py logic, refactored)
│   ├── concierge.py               (Mode 2 — collab coordinator + 6 specialists)
│   └── team_planner.py            (Mode 3 — dynamic @node + roster loader)
├── server.py                      (extended — endpoints per mode)
├── run_demo.py                    (CLI, supports --mode flag)
├── smoke_test.py
└── static/
    ├── index.html                 (becomes a mode-switcher shell)
    ├── modes/
    │   ├── single.html            (the existing Mode 1 UI)
    │   ├── concierge.html         (Mode 2 chat UI)
    │   └── team.html              (Mode 3 team dashboard)
    └── shared/
        ├── styles.css             (Liquid Glass shared)
        └── client.js              (SSE consumer, shared)
```

The current `marathon.py` file gets split into `workflows/shared/` and `workflows/strategy_graph.py`. The frontend gains mode-switching but keeps the Liquid Glass styling.

---

## Build plan — phased

### Phase 0 — Refactor (~3 hrs)

Move existing `marathon.py` into the new structure. No behavior change. Verify `run_demo.py` still works. This sets up the codebase for Phases 1 and 2 without contaminating them.

**Done when:** existing demo runs identically after refactor.

### Phase 1 — Concierge mode (~1 day)

Backend (`workflows/concierge.py`):
- Define 6 single_turn subagents (medical, weather, pacing, gear, nutrition, mental)
- Each takes the current strategy + bundled data + user question as input
- Build the `race_concierge` coordinator with `sub_agents=[...]`
- Coordinator's instruction tells it: "given a user question and the runner's strategy, decide which specialists to invoke in parallel via `request_task_*` and synthesize their responses"

Server (`server.py`):
- New endpoint `POST /chat?strategy_id=...` accepting a user question
- Returns SSE stream with events: `subagent_dispatched`, `subagent_result`, `synthesized_response`

Frontend (`static/modes/concierge.html`):
- Chat input at the top
- The 6 specialist nodes as a horizontal row in the visualization
- Active subset pulses; inactive ones stay dim
- Response card below shows the synthesized answer

**Done when:** typing three different questions causes three different subsets of specialists to light up.

### Phase 2 — Team mode (~1 day)

Backend (`workflows/team_planner.py`):
- Define a sample roster format (JSON: `[{"name": "Alice", "scenario": "HOT"}, ...]`)
- Build the `@node` dynamic function: given a roster, `asyncio.gather` over per-runner strategy workflows
- Each per-runner sub-workflow reuses `strategy_graph.py` from Mode 1
- Aggregate into a team summary (one more single_turn agent or a function node)

Server:
- New endpoint `POST /team?roster=...` accepting a roster
- SSE stream emits events per runner: `runner_started`, `runner_node_complete`, `runner_finished`

Frontend (`static/modes/team.html`):
- Roster preview at the top (avatars + names)
- One graph-workflow visualization per runner, arranged in columns
- All columns animate simultaneously
- Team dashboard below shows aggregated results

**Done when:** loading a 3-runner roster animates 3 columns; loading a 10-runner roster animates 10 columns; the topology is data-driven.

### Phase 3 — Frontend integration + polish (~half day)

- Mode switcher at the top of `index.html`
- Shared Liquid Glass styles across all three modes
- Unified header (brand, mode tabs, run button)
- Replay button works per mode
- Stats card unified across modes

### Phase 4 — Stretch: resumability demo (~half day, optional)

- Simulate a deliberate failure in Team mode (one runner's workflow throws)
- Show that re-running picks up where it left off, skipping completed runners
- This is the strongest argument for dynamic workflows over `LoopAgent`

### Total effort estimate

**~3 days of focused work** for Phases 0-3. **~3.5 days** if you do Phase 4.

---

## Demo flow for the 20-min video

Updated script outline:

| Section | Time | Content |
|---|---|---|
| 1. Intro / context | 2:00 | What's ADK, what's new in 2.0, three pillars |
| 2. Why marathon | 0:30 | The "you don't run? doesn't matter, replace 'fetch weather' with 'fetch CRM data'" bridge |
| 3. Mode 1: Single Runner | 4:00 | Live demo + code walkthrough of graph workflow |
| 4. Pillar 1 narration | 1:00 | Recap what graph workflows give you |
| 5. Mode 2: Concierge | 4:00 | Live demo: 3 different questions cause 3 different parallel patterns |
| 6. Pillar 2 narration | 1:00 | LLM-driven dynamic delegation, the one thing collab does that 1.x can't |
| 7. Mode 3: Team | 3:00 | Live demo: load Team A (3), then Team B (10), watch topology adapt to data |
| 8. Pillar 3 narration | 1:00 | Runtime-sized fan-out + resumability — when graphs are too rigid |
| 9. When-to-use-which recap | 1:30 | The decision tree as a slide |
| 10. Handoff to skills/MCP | 1:30 | What the next presenter covers |
| **Buffer** | 0:30 | |
| **Total** | **~20:00** | |

The three demos are roughly equal time. The narration after each one cements the pedagogical message.

---

## Why this works pedagogically

Three reasons.

### 1. Each mode demonstrates ONE thing 1.x can't do

If a viewer can recreate your demo in 1.x, you've taught them nothing. By picking the unique feature of each pillar — typed parallel fan-out (graph), LLM-driven subset selection (collab), runtime fan-out (dynamic) — every section has a clear "this is genuinely new" argument.

### 2. The same theme threads through

Audience cognitive load is the enemy of education. By keeping the marathon theme constant and varying the orchestration pattern, viewers only have to learn one new thing per section (the pattern), not two (pattern + domain). Compare: "here's a marathon planner. Now here's a customer support chatbot. Now here's a deployment pipeline." Viewers reset mentally each time.

### 3. The progression mirrors how teams actually grow apps

The story arc — one user → conversational follow-up → team scaling — is the same path most production apps take. Viewers can map it onto their own work. *"We have a single-user feature. We want to add chat follow-up. Eventually we want to scale to teams."* Each pattern fits a stage they'll recognize.

---

## What to avoid

- **Don't try to stack all three pillars in one demo.** Each pillar has its own demo. They share a theme, not a single execution path. Trying to nest dynamic-inside-collab-inside-graph in one app makes each pillar feel weak.
- **Don't add features that don't demonstrate the pillar's unique value.** A refiner+critic loop in Mode 3 doesn't show dynamic workflows' unique value — `LoopAgent` does the same. Stick to runtime-sized fan-out.
- **Don't skip the "what 1.x can't do" line.** The audience will keep asking that question. Answer it explicitly in each section.

---

## Safety: preserving the working v1 (graph workflow only)

Before starting Phase 0, the current state of the repo (polished graph workflow + Liquid Glass UI + working demo) is committed and tagged as `v1-graph-workflow-stable`. This is the fallback if anything in Phases 0-3 breaks irrecoverably.

To restore v1 from any later state:
```
git checkout v1-graph-workflow-stable
```

Or to view what v1 looked like without affecting your current branch:
```
git show v1-graph-workflow-stable -- marathon.py
```
