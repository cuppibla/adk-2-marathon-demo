# Rewriting the Marathon Planner in ADK 1.x — Analysis

This document analyzes how the marathon planner in this repo would look if implemented in ADK 1.x (without graph workflows), what would change, and what would break.

The current ADK 2.0 implementation is `marathon.py` (~200 lines): three parallel function nodes (`fetch_weather`, `analyze_course`, `pull_fitness`) → `JoinNode` → router → one of three `Agent` strategy nodes.

The analysis covers three viable 1.x approaches, a head-to-head scorecard, file-structure sketches, and an honest verdict.

---

## TL;DR

You can absolutely rewrite this in ADK 1.x. None of the rewrites are *good*. All three plausible approaches lose on the dimensions that matter most for this use case: speed, cost, determinism, and code clarity. The 2.0 graph wins for one structural reason: **the workflow's shape mirrors the diagram's shape**. None of the 1.x approaches give you that.

---

## The three viable 1.x approaches

### Approach A — Single LlmAgent with tools

**Architecture:** One `LlmAgent` named `marathon_planner`. Three tools attached: `get_weather`, `get_course`, `get_fitness`. Instruction tells the LLM: "Gather these three data inputs, then based on temperature, write a hot/normal/cold race strategy as JSON."

**What it gets right**
- Simplest code. ~30 lines of Python total.
- Easy to grok at a glance.
- Reuses your existing fetch functions as-is (wrap as tools).

**What it gets wrong**
- **No parallelism.** LLMs call tools serially. The 1.0s + 1.5s + 2.0s fetches run as 4.5s sequentially, not 2.0s parallel.
- **Routing lives in the prompt.** "If temperature is above 70°F, write hot-weather advice…" — and you hope the model gets the threshold right every time. Usually right, occasionally wrong on edge cases (71°F? 69°F?). You cannot *prove* it'll route correctly.
- **Multiple LLM calls per run.** Plan → tool call → tool call → tool call → synthesize. Easily 4 round trips per request. Cost and latency multiply.
- **Prompt length grows linearly with complexity.** Add humidity. Add wind direction. Add altitude. Add runner age. Each adds prompt bytes. At some point the model stops following the rules consistently.
- **Debugging is reading prompt traces.** When something goes wrong, you can't grep the code path. You read the trace and infer.

---

### Approach B — SequentialAgent + ParallelAgent composition

**Architecture:** A `SequentialAgent` runs a `ParallelAgent` first (containing three sub-agents that wrap the data fetches), then runs a `strategist` LlmAgent that reads from shared session state and writes the final strategy.

**What it gets right**
- Finally gets you parallel data fetching.
- Cleaner separation between "gather data" and "reason about data."
- Each fetch is a discrete sub-agent — modular.

**What it gets wrong**
- **Every "step" must be an agent.** To fetch weather, you need a `weather_agent` — which is an `LlmAgent` with a `get_weather` tool. The LLM has to be invoked *just to call a function*. Three useless model invocations to gather data that doesn't need any reasoning. Latency for the fetch phase becomes "max(LLM_overhead + actual_fetch)" instead of just "max(actual_fetch)."
- **Outputs flow through session state, not typed handoff.** ParallelAgent writes each sub-agent's output into a dict in session state. The strategist's prompt has to know the right keys to look for (`state["weather"]`, `state["course"]`, etc.). No validation. If a sub-agent writes the wrong key, no error — just silent wrong behavior.
- **The branching step is still LLM judgment.** The strategist agent reads state, decides hot/normal/cold in its head, and writes the appropriate strategy. You haven't eliminated the routing-via-prompt problem.
- **Composition is fragile.** SequentialAgent doesn't natively support conditional execution. To branch, you'd need to nest sub-agents or use `transfer_to_agent`, which compounds the LLM-judgment problem.

---

### Approach C — Coordinator LlmAgent with `sub_agents` + `transfer_to_agent`

**Architecture:** A coordinator `LlmAgent` declares three sub-agents (`hot_handler`, `normal_handler`, `cold_handler`) and three data-gathering tools. Its instruction tells it: "gather weather/course/fitness via your tools, then `transfer_to_agent` to the right handler based on the temperature."

**What it gets right**
- Most honest separation between data and reasoning.
- Sub-agents are scoped to one weather condition each — clean responsibility.
- Reuses the prompt-per-weather pattern that your 2.0 strategy agents already use.

**What it gets wrong**
- **Same parallelism problem as Approach A.** No native parallel tool calls.
- **Routing AND handoff are both LLM-driven.** The coordinator has to (a) classify the weather correctly, (b) call `transfer_to_agent` with the *exact string name* of the right handler. Get the name wrong — typo, hallucination — and the framework errors out.
- **Subagents must self-manage return-to-coordinator.** Each handler agent needs an instruction telling it to call `transfer_to_agent('coordinator')` after responding. Otherwise execution stalls inside the handler.
- **Mode-based auto-return doesn't exist in 1.x.** The new `mode="task"` from 2.0 (which auto-returns after `complete_task`) would solve this — but it's a 2.0 feature. In 1.x you write the handoff manually for every handler.

---

## Scorecard — 2.0 graph vs. all three 1.x approaches

For the marathon planner specifically:

| Concern | 1.x — Approach A | 1.x — Approach B | 1.x — Approach C | **ADK 2.0 graph** |
|---|---|---|---|---|
| LLM calls per run | 4–5 | 4–5 (one per sub-agent + final) | 3–4 | **1** |
| Parallelism | None | Yes (only across agents) | None | **Yes (across functions)** |
| Total latency (no slow-mo) | ~15–20s | ~10–12s | ~12–15s | **~7s** |
| Routing correctness | LLM-judged, ~95–98% | LLM-judged, ~95–98% | LLM-judged, ~95–98% | **100% — Python `if`** |
| Prompt size per agent | Long (full workflow) | Medium (per sub-agent) | Long (coordinator) | **Short (role only)** |
| Debug "why did it do that?" | Read trace | Read trace + state | Read trace + handoffs | **Read `edges` array** |
| Total Python LOC | ~30 | ~80 | ~100 | ~200 (mostly Pydantic + canned data) |
| Adding a new branch (e.g., HUMID) | Edit prompt, retest | New sub-agent + edit prompt | New sub-agent + handoff instruction | **Add one route + agent** |
| Mixing pure-Python steps in flow | Wrap as tools (extra LLM calls) | Wrap as agents (extra LLM calls) | Wrap as tools (extra LLM calls) | **Drop function in `edges`** |

The line-count comparison is a trap. ADK 2.0 has *more* lines because of Pydantic schemas and explicit canned data. Those extra lines are *types*, which buy runtime guarantees. The 1.x line counts are smaller because they're more permissive — and more failure-prone.

---

## File structure walkthrough — what an Approach B rewrite would look like

For the curious. This is what `marathonplanner/` would look like if rewritten under Approach B.

```
marathonplanner/
├── pyproject.toml          # google-adk==1.x instead of 2.0.0b1
├── .env                    # same
├── main.py                 # entry point — creates Runner, invokes root_agent
├── agents/
│   ├── __init__.py
│   ├── root.py             # SequentialAgent[gather, strategist]
│   ├── gather/
│   │   ├── __init__.py
│   │   ├── parallel.py     # ParallelAgent[weather_agent, course_agent, fitness_agent]
│   │   ├── weather_agent.py    # LlmAgent + get_weather tool + output_key="weather"
│   │   ├── course_agent.py     # LlmAgent + get_course tool + output_key="course"
│   │   └── fitness_agent.py    # LlmAgent + get_fitness tool + output_key="fitness"
│   └── strategist/
│       ├── __init__.py
│       └── agent.py        # LlmAgent — reads state, decides hot/normal/cold, writes strategy
├── tools/
│   ├── __init__.py
│   ├── weather.py          # get_weather() → canned scenario data
│   ├── course.py           # get_course() → canned scenario data
│   └── fitness.py          # get_fitness() → canned scenario data
├── schemas/
│   ├── __init__.py
│   ├── data.py             # WeatherData, CourseData, FitnessData
│   └── strategy.py         # RaceStrategy
└── server.py               # FastAPI — but the SSE story is harder (see below)
```

A few things worth noting about what changes:

**Each fetch becomes a folder of three things:** the tool function (1 file), the wrapping agent (1 file), and registration in the parallel container (1 line). What was a single function in 2.0 is now ~30 lines of agent boilerplate per fetch.

**The strategist agent absorbs all branching logic.** Its instruction grows to encompass all three strategies. Either:
- One mega-prompt with `if hot: do this, if cold: do that` — long, hard to maintain, prone to mode confusion.
- OR add three sub-agents under the strategist + `transfer_to_agent` — which brings back Approach C's pain.

**The SSE visualization is harder.** The custom visualization in this repo subscribes to `runner.run_async()` events from the workflow. In 1.x, the equivalent is also `runner.run_async()` — but events come from agents, not nodes. You'd see one event per sub-agent invocation, which means you'd see "weather_agent started" and "weather_agent completed" but no obvious bundling into a JoinNode-equivalent payload. The visualization wouldn't animate as cleanly because there's no "join" moment to highlight.

**Adding a new branch (e.g., a HUMID strategy) requires:**
- A new `humid_strategy.py` agent file under strategist's sub-agents
- Updating the strategist's instruction to add the HUMID classification logic
- Updating the strategist's `sub_agents=` list
- Updating the visualization (if you keep it) to know about a new branch

In 2.0, the same change is: add one Agent definition, add one entry in the router's dict, add one node in the SVG. Three lines.

---

## Where ADK 1.x is actually fine

Three honest situations where 1.x wins or ties:

- **The workflow is genuinely conversational.** A user-facing chatbot where the structure is "user types, agent responds, repeat." The LLM *is* the workflow. Graph workflows don't add value.
- **The workflow is one step.** A single LlmAgent with a few tools is the lightest possible setup. Graphs would be over-engineering.
- **You're already invested.** A team with a working ADK 1.x codebase shouldn't migrate just because 2.0 exists. The 2.0 gains compound with workflow complexity. Simple flows don't benefit enough to justify migration risk.

For *this* use case (structured upfront planning + parallel data + data-driven branching + final reasoning), none of those apply. 2.0 is the right tool.

---

## The honest verdict

ADK 2.0 graph workflows are straightforwardly better for this specific use case on every dimension that matters: speed, cost, determinism, code clarity, and debuggability.

The line-count comparison favors 1.x but the comparison is misleading — the extra lines in 2.0 are mostly *types* (Pydantic models) and *data* (canned scenarios), which give you runtime guarantees the 1.x approach can't match.

The structural argument is the strongest: **in 2.0, the code shape mirrors the diagram shape.** Reading `marathon.py` tells you what executes when, in what order, with what dependencies — directly from the `edges` array. No 1.x approach gives you that. They all encode the structure in prose (prompts) and dispatch logic (transfer calls) — both of which decay as the project grows.

If you ever want to add a fourth branch, change the routing thresholds, or insert a new step between two existing ones, the 2.0 version is a 2-line edit. The 1.x versions are a multi-file refactor plus prompt re-tuning. That's the compounding gap that justifies the framework choice.
