# ADK 2.0 Video Script — Three Pillars in One App (20 min)

**Format:** Full prose, read verbatim. Stage directions in `[brackets]`.
**Pacing assumption:** ~150 spoken words / minute conversationally.
**Demo app:** Marathon Race Day Coach — three modes, one app. Each mode demonstrates one ADK 2.0 pillar with a feature that 1.x genuinely can't do well.

## Pre-record checklist

- [ ] `uv run python server.py` — verify the server boots cleanly
- [ ] Browse to `http://127.0.0.1:8000/` — verify all three sections render (Mode 1 graph at top, chat panel below, team panel at the bottom)
- [ ] Pre-warm Mode 1 once so the chat panel is unlocked when you start recording
- [ ] Open in IDE for the code walkthrough:
  - `workflows/strategy_graph.py:187` (Mode 1 — the `edges=[...]` Workflow)
  - `workflows/concierge.py:75` (Mode 2 — coordinator with `sub_agents=[...]`)
  - `workflows/team_planner.py:84` (Mode 3 — `@node(parallel_worker=True)`)
  - Optional ADK 1.x comparison: `race-condition/agents/planner/agent.py:47`
- [ ] If the network's flaky, cache one HOT run for the Mode 1 Replay button
- [ ] Confirm `GOOGLE_API_KEY` is set in `.env`

## Time budget

| § | Section | Time | Words |
|---|---|---:|---:|
| 1 | Intro / what's ADK 2.0 | 2:00 | 300 |
| 2 | Why marathon (bridge for non-runners) | 0:30 | 75 |
| 3 | **Mode 1 demo:** Single Runner | 4:00 | 600 |
| 4 | Pillar 1 narration | 1:00 | 150 |
| 5 | **Mode 2 demo:** Concierge | 4:00 | 600 |
| 6 | Pillar 2 narration | 1:00 | 150 |
| 7 | **Mode 3 demo:** Team | 3:00 | 450 |
| 8 | Pillar 3 narration | 1:00 | 150 |
| 9 | When to use which pillar (decision tree) | 1:30 | 225 |
| 10 | Handoff to skills/MCP | 1:00 | 150 |
| — | Buffer | 1:00 | — |
| **Total** | | **~20:00** | **~2850** |

---

# § 1 — What is ADK 2.0? (~2:00)

[OPEN ON: a slide or clean editor — no code yet]

Hi everyone. In the next twenty minutes, I'm going to walk you through Google's Agent Development Kit version 2.0. Specifically, I'll show you the **three new pillars** that make up the 2.0 release, with a live demo of each — all in one app.

Quick context for anyone who hasn't used ADK before. ADK is Google's framework for building production agents. If you've used LangChain, LangGraph, or CrewAI, ADK lives in the same neighborhood — but with a Google-y opinion: heavy emphasis on observability through OpenTelemetry, first-class deployment to Vertex AI's Agent Engine, and structured Pydantic schemas everywhere instead of free-form dicts.

ADK 2.0 introduces three new pillars. Each solves a different shape of orchestration problem.

**Pillar 1 — Graph workflows.** Declarative orchestration. You draw the diagram up front; the framework executes it. Use when the structure is known.

**Pillar 2 — Collaborative agents.** LLM-driven delegation. A coordinator agent decides at runtime which specialists to invoke in parallel. Use when an LLM should be picking who handles what.

**Pillar 3 — Dynamic workflows.** Code-driven orchestration with runtime-sized fan-out. Use when the topology depends on data you don't have until runtime.

I built one app — a marathon race day strategy planner — with three modes, each demonstrating one pillar. Same theme, three patterns. Watch them in order.

[TRANSITION: switch to browser at `http://127.0.0.1:8000/`]

---

# § 2 — Why a marathon planner? (~0:30)

Quick bridge for anyone who doesn't run. The marathon planner shape is universal. Replace *"fetch weather"* with *"fetch CRM data,"* replace *"runner's fitness pace"* with *"customer's purchase history,"* and the orchestration is identical. I picked marathons because the parallelism is concrete and visual — and because the three modes map cleanly to three real workflows: plan once, chat about it, scale to many.

---

# § 3 — Mode 1: Single Runner (Pillar 1: Graph workflows) (~4:00)

[SHOW: browser at the top of the page — the graph visualization]

This is Mode 1 — a single runner asking for a race day strategy. The graph on the left shows what'll happen: three function nodes fetch data in parallel (weather, course, fitness), a JoinNode bundles them, a router picks one of three branches based on temperature, and one of three strategy agents generates a personalized race plan.

I'll pick the Hot Boston scenario — 78°F, headwind, Boston Marathon course with Heartbreak Hill at mile 20, runner has a 7:30 per mile fitness level.

[CLICK: Run]

Watch the three nodes light up at the same time. They started simultaneously. The live timer inside each one is real — pull_fitness is 1 second, fetch_weather is 1.5, analyze_course is 2 seconds. They're not happening one after another. They're truly parallel.

[WAIT ~1s while pulses are visible]

Pull_fitness completed first. Now the others. The moment all three converge, the JoinNode bundles them — that's the cyan diamond — and the router fires. The router is four lines of Python: *if temperature is above 70, route HOT.* No LLM judgment. Just an `if` statement.

[WAIT ~5s for the LLM strategy call]

Strategy returned. Look at the right panel.

**3:35** as the target finish. The pacing advice: *"Slow your typical 7:30 pace to 8:12 per mile to account for 78-degree heat and the 4.5% grade at mile 20."* Notice it referenced the actual fitness pace we passed in. The actual temperature. The actual hardest mile from the course profile. That's the `output_schema=RaceStrategy` doing real work — the model can see structured data, not just a paragraph.

[SCROLL down to stats card]

Workflow complete in seven seconds. **One LLM call.** Fetch phase ran in 2 seconds in parallel — would've taken 4.5 sequentially. Saved 2.5 seconds via fan-out.

The headline number to remember is **one LLM call.** We did not call a model to decide what data to fetch. We did not call a model to decide whether it's hot or cold. We did not call a model to merge three dicts. The model only ran for the part that genuinely needed reasoning — writing the personalized strategy.

[TRANSITION: switch to IDE, open workflows/strategy_graph.py around line 187]

Here's the entire orchestration in code.

```python
root_agent = Workflow(
    name="marathon_strategy",
    edges=[
        (START, fetch_weather, join_inputs),
        (START, analyze_course, join_inputs),
        (START, pull_fitness, join_inputs),
        (join_inputs, route_by_weather),
        (route_by_weather, {
            "HOT":    hot_strategy,
            "NORMAL": normal_strategy,
            "COLD":   cold_strategy,
        }),
    ],
)
```

Eight lines. The first three rows fan out from START into the JoinNode in parallel. The fourth runs the router after the join. The fifth picks one of three branches based on the router's `route=` value. The framework handles the rest — parallelism, scheduling, the join's typed handoff.

---

# § 4 — Pillar 1 narration (~1:00)

Three things to take away about graph workflows.

**One.** Function nodes — that's `fetch_weather`, `analyze_course`, `pull_fitness` — and Agent nodes — that's the strategy agents — coexist in the same `edges` array as peers. You don't have to wrap a function in an LLM agent just to call it. In ADK 1.x, `ParallelAgent` only orchestrates agents — fetching weather requires building a `weather_agent` with a `get_weather` tool. Three extra LLM calls just to fetch data that doesn't need any reasoning.

**Two.** The router is deterministic. The branching decision is Python — `if temp >= 70`. In 1.x, you'd write a coordinator agent with a prose instruction telling the LLM to transfer to the right handler. Sometimes right. Occasionally wrong. Here it's an `if` statement. It cannot be wrong.

**Three.** The shape of the code mirrors the shape of the diagram. Read the `edges` array and you know exactly what runs when. No prompt to grep, no transfer-to-agent logic to chase.

[TRANSITION: back to browser, scroll down to the chat panel]

---

# § 5 — Mode 2: Concierge (Pillar 2: Collaborative agents) (~4:00)

OK. Mode 1 generated a strategy. Now the runner has follow-up questions. Sometimes one quick question, sometimes a holistic review. Different questions need different specialists.

[SHOW: the chat panel with 6 specialist pills]

Six specialists are available: Medical, Weather, Pacing, Gear, Nutrition, Mental. A coordinator agent decides which ones to invoke for each question. It can fire **one specialist, three specialists, or all six — in parallel.**

I'll click *"Should I race today?"* — that's a holistic question.

[CLICK: "Should I race today?"]

Watch the row. Three specialists just lit up: Medical, Weather, Pacing. The others stayed dim. The coordinator decided those three are the relevant ones — and dispatched them all in one turn, running in parallel.

[WAIT ~10s for all three to complete]

All three returned. Notice Weather went orange — its response flagged a *serious* concern level because of the heat. The synthesized answer pulls all three responses together: *"The primary concern today is the serious risk of heat-related illness... slow your pace by at least 20 seconds per mile..."*

Now I'll ask something narrower. *"What about my fueling plan?"*

[CLICK: "About fueling"]

Only Nutrition lights up. One specialist. The other five sit out. The coordinator made a precise judgment about what's relevant.

[WAIT ~8s]

Response back: *"Maintain your electrolyte schedule strictly every 2 miles... extra salt at mile 13 is crucial..."*

One more — *"Anything I should worry about overall?"*

[CLICK: "Full review"]

All six light up at once. Holistic question, holistic dispatch. They all run in parallel.

[WAIT ~14s for all 6 to complete]

[TRANSITION: switch to IDE, open workflows/concierge.py around line 75]

The coordinator definition is shorter than you'd think.

```python
race_concierge = Agent(
    name="race_concierge",
    model=MODEL,
    sub_agents=[
        medical_specialist,
        weather_specialist,
        pacing_specialist,
        gear_specialist,
        nutrition_specialist,
        mental_specialist,
    ],
    instruction="""You are a marathon race day concierge...
        1. DECIDE which specialists are genuinely relevant. Be precise.
        2. Call the relevant specialist tools IN PARALLEL by emitting
           multiple function calls in one turn.
        3. SYNTHESIZE their responses into one cohesive answer...""",
)
```

When you declare `sub_agents`, ADK auto-injects a tool per subagent — `request_task_medical_specialist`, `request_task_weather_specialist`, and so on. The coordinator's LLM picks which ones to call. Multiple calls in one turn = parallel execution.

---

# § 6 — Pillar 2 narration (~1:00)

This is the one ADK 2.0 collab feature that's genuinely new.

In 1.x, `ParallelAgent` runs a **fixed** list of sub-agents — always all of them. For our concierge, that'd mean 6 LLM calls per question even when 5 are irrelevant. `transfer_to_agent` is serial — one subagent at a time. There's no way to express *"LLM, pick a subset of these specialists and run them in parallel."*

In 2.0 collab, the coordinator does exactly that. Same input shape — a question — different outputs depending on which specialists fire. *Different inputs, different parallel patterns.* The math: 6× fewer LLM calls for narrow questions, same execution time for broad ones because of parallelism.

If you don't need this — if your routing is deterministic — use a graph workflow with a router function. Collab is for when an LLM should be making the routing call.

[TRANSITION: back to browser, scroll down to the team panel]

---

# § 7 — Mode 3: Team Planner (Pillar 3: Dynamic workflows) (~3:00)

Mode 3. A coach has a roster of N runners. Could be 3 today, could be 30 tomorrow. The team size is unknown at design time.

[SHOW: the team panel with two roster buttons]

I'll start with Team Alpha — three runners across three different conditions.

[CLICK: Team Alpha]

Watch all three rows light up at the same time. Three independent per-runner subworkflows fired in parallel. Each one will pick its own strategy agent based on its scenario, run that agent, return a personalized plan.

[WAIT ~10s]

All three complete. Alice — hot Boston — 3:35. Bob — normal Berlin — 3:03. Carol — cold Chicago — 3:12. **Stats card shows 2.6× parallel speedup** — 27 seconds of work in 10 seconds wall time.

Here's the moment. Same UI, ten runners.

[CLICK: Team Omega]

Ten rows. Ten pulses. Ten independent LLM calls running concurrently.

[WAIT ~10s]

Ten plans, ten target finish times. **Total wall time: 9 seconds. Sum if serial: 78 seconds. Parallel speedup: 8.4×.**

[TRANSITION: switch to IDE, open workflows/team_planner.py around line 84]

Here's the dynamic node.

```python
@node(parallel_worker=True, rerun_on_resume=True)
async def plan_for_runner(ctx, node_input):
    """Per-runner pipeline. ParallelWorker fans this out across the roster."""
    name = node_input["name"]
    scenario_key = node_input["scenario"]
    canned = SCENARIOS[scenario_key]
    bundled = BundledRunData(...)
    agent = _pick_strategy_agent(canned["weather"].temp_f)
    strategy_payload = await ctx.run_node(agent, node_input=bundled.model_dump())
    ...
```

The decorator does the work. `parallel_worker=True` wraps this in ADK's `_ParallelWorker` — when the upstream node emits a list, ParallelWorker spawns one task per item. The number of branches is determined by the list length at runtime.

---

# § 8 — Pillar 3 narration (~1:00)

What's uniquely 2.0 here.

`ParallelAgent` in 1.x has a **fixed list of sub-agents at design time.** You can't grow it with the roster.

`LoopAgent` in 1.x loops a single agent **serially.** No parallelism.

Only `@node(parallel_worker=True)` lets the **parallel topology be determined by data at runtime.** Roster of 3? Three parallel branches. Roster of 30? Thirty. Same code.

Also: dynamic workflows checkpoint per node. If a runner's plan fails mid-flight, you can resume and skip the runners that already completed. That's free with `parallel_worker` — you don't write the resume logic.

[TRANSITION: back to a slide or clean editor]

---

# § 9 — When to use which pillar (~1:30)

Let me leave you with the decision tree.

[SHOW: the decision tree as a slide if you have one — otherwise narrate]

**Free-form conversation? Use a single LlmAgent** — or a chat-mode coordinator with collaborative subagents if you want specialists.

**Structure known up front?** Graph workflow. Draw the diagram, write the `edges` array.

**Loops or runtime-sized fan-out?** Dynamic workflow with `@node` and `parallel_worker`.

**LLM should pick which specialist?** Collaborative agents.

**Otherwise?** Single LlmAgent with tools. Don't over-engineer.

These mix. A graph workflow node can be a whole nested workflow. A dynamic node can invoke an agent via `ctx.run_node`. The marathon app we just saw uses all three pillars in one repo — each pillar where it fits. None of these are mutually exclusive.

For the marathon planner specifically, the three pillars map directly to three real product needs: *plan once* (graph), *chat about the plan* (collab), *scale to many* (dynamic). That progression is the same path most production agent apps take. Pick the right pillar for each stage.

---

# § 10 — Handoff to skills + MCP (~1:00)

That's ADK 2.0's three pillars. Quick recap.

- **Graph workflows** for declarative orchestration with deterministic routing
- **Collaborative agents** for LLM-driven dynamic delegation
- **Dynamic workflows** for runtime-sized parallel topologies

Each pillar fits a specific shape of problem. The marathon app shows all three in one repo to make the comparison concrete.

This is half the story. The other half is what your agents can actually *do* — tools, skills, MCP servers, the protocols that let agents reach Gmail, Calendar, your internal APIs, anything outside the model's own knowledge.

[TEAMMATE NAME] is going to take it from here and show you how skills and MCP integration work.

Over to you, [TEAMMATE NAME].

[END]

---

## Pacing notes by section

| Section | Words | Time @ 150 wpm |
|---|---:|---:|
| § 1 Intro | ~300 | 2:00 |
| § 2 Why marathon | ~75 | 0:30 |
| § 3 Mode 1 demo | ~600 | 4:00 |
| § 4 Pillar 1 narration | ~150 | 1:00 |
| § 5 Mode 2 demo | ~600 | 4:00 |
| § 6 Pillar 2 narration | ~150 | 1:00 |
| § 7 Mode 3 demo | ~450 | 3:00 |
| § 8 Pillar 3 narration | ~150 | 1:00 |
| § 9 Decision tree | ~225 | 1:30 |
| § 10 Handoff | ~150 | 1:00 |
| **Total** | **~2850** | **~19:00** |

Plus ~1 minute of buffer for breath, transitions, and LLM call waits. Should land at 20.

## Cuts if running long

1. The "third question — Anything I should worry about overall?" in § 5 (~45s — the first two questions already make the dispatch-pattern point)
2. The code snippet from § 7 if you've burned time on the demo (~30s — the visual demo is enough)
3. The handoff in § 10 can shrink to 30s if your collaborator goes immediately after

## Additions if running short

1. After § 4, briefly show the IDE side-by-side with `race-condition/agents/planner/agent.py` to contrast 1.x's coordinator-with-prompt pattern
2. In § 7, mention that Team mode supports **resumability** — if a runner fails mid-flight, re-running skips completed runners (the `@node` checkpoint feature)
3. In § 9, show two contrasting code snippets: 1.x's `ParallelAgent[a, b, c]` vs 2.0's `edges=[...]` for the same pipeline

## What to physically have on screen during the talk

- **Browser** at `http://127.0.0.1:8000/`, pre-warmed (Mode 1 has run once)
- **IDE** with these files in tabs:
  - `workflows/strategy_graph.py` open to line 187 (the Workflow definition)
  - `workflows/concierge.py` open to line 75 (the coordinator)
  - `workflows/team_planner.py` open to line 84 (the parallel_worker node)
- **One slide** with the decision tree from § 9, ready to switch to for the recap
