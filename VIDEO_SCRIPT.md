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
  - `workflows/deep_research.py:84` (Mode 3 — `@node(parallel_worker=True)` + recursive `ctx.run_node`)
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

# § 7 — Mode 3: Deep Research (Pillar 3: Dynamic workflows) (~3:00)

Mode 3. Mode 2 was for focused follow-up questions. But what if the runner asks something *open-ended* — "tell me everything I should know about racing Boston"? That's not chat. That's research.

Research that needs to break into specific sub-questions, dig into each one, possibly spawn even more questions based on what's found, then synthesize the whole thing into a briefing.

The number of sub-questions isn't predictable. The depth isn't predictable. The shape of the work is decided by the AI at runtime.

[SCROLL to research panel, SHOW the three preset buttons]

I'll click "Deep-dive: Boston Marathon."

[CLICK: Deep-dive Boston preset]

Watch the decomposer fire — that's the purple node at the top. It's deciding what sub-questions to ask.

[WAIT ~3s]

There — five top-level questions appear. Course profile, weather history, pacing, common mistakes, gear. They're all researching in parallel now.

[WAIT ~10s — narrate during]

Notice the model just decided "this finding needs deeper investigation" — and spawned children questions of its own. Those children are also researching in parallel. Some top-level questions spawned three children, some spawned two. The tree's *shape* is being decided by the LLM at runtime.

[WAIT for completion, ~15-20s more]

Briefing rendered. Headline: *"Respect the descent to survive the ascent: your Boston race is won or lost by preserving your quadriceps during the first four miles."* Sections breaking down the research themes. Key warnings the runner should not ignore.

[SCROLL to stats card]

Look at the numbers. **17 LLM calls — but only ~30 seconds of wall time.** If we ran serially, this would have been over two minutes. Tree shape: 5 top-level + 12 recursive children, *all decided at runtime by the LLMs themselves.*

[TRANSITION: switch to IDE, open workflows/deep_research.py around line 84]

Here's the recursive piece.

```python
@node(parallel_worker=True, rerun_on_resume=True)
async def research_topic(ctx, node_input):
    """One research task — parallel_worker fans this out across the question list.
    Recursive: a finding may spawn 1-3 deeper questions, which are themselves
    invoked via ctx.run_node(research_topic, [...]) — fanning out at the next depth.
    """
    question = node_input["question"]
    depth = node_input["depth"]
    finding = await ctx.run_node(research_agent, node_input=...)

    if finding.needs_deeper and depth < MAX_DEPTH:
        children = await ctx.run_node(
            research_topic,
            node_input=[{"question": dq, "depth": depth + 1, ...} for dq in finding.deeper_questions],
        )
    ...
```

The killer line: `await ctx.run_node(research_topic, ...)` — **the node calls itself recursively** with a list of deeper questions, which `parallel_worker` fans out in parallel. The depth and width of the tree are decided by the LLM, not by code.

---

# § 8 — Pillar 3 narration (~1:00)

This is the moment ADK 2.0 most diverges from 1.x.

`ParallelAgent` in 1.x has a **fixed list of sub-agents at design time.** It can't grow with data, and crucially, it can't recurse — sub-agents can't spawn more parallel work from inside themselves.

`LoopAgent` in 1.x loops a single agent **serially.** Sequential, fixed iteration.

In ADK 1.x, this deep research pattern is the boundary where you stop using framework primitives and start writing raw asyncio code outside the workflow. You lose tracing. You lose checkpointing. You lose resumability. The framework can't see what you're doing.

In ADK 2.0, the same recursive parallel pattern is native. `@node(parallel_worker=True)` plus `ctx.run_node` from inside the worker. The framework tracks every branch, every depth level, every spawn. Resumability works automatically. Tracing works automatically. You keep the infrastructure benefits while the topology adapts to data.

Same theme through all three demos: marathon planning. Same code patterns: schemas, agents, workflows, edges. But each mode demonstrates a fundamentally different orchestration capability — and Mode 3 in particular shows what dynamic workflows make possible that no prior framework primitive could.

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
3. In § 7, only run the Boston preset — skip the "let me show another preset" beat (~60s)
4. The handoff in § 10 can shrink to 30s if your collaborator goes immediately after

## Additions if running short

1. After § 4, briefly show the IDE side-by-side with `race-condition/agents/planner/agent.py` to contrast 1.x's coordinator-with-prompt pattern
2. In § 7, mention that dynamic workflows have **resumability built in** — if any branch fails mid-tree, re-running skips completed branches via per-node checkpointing
3. In § 7, run a second preset (Heat or Recovery) to show that the tree shape differs per query
4. In § 9, show two contrasting code snippets: 1.x's `ParallelAgent[a, b, c]` vs 2.0's `edges=[...]` for the same pipeline

## What to physically have on screen during the talk

- **Browser** at `http://127.0.0.1:8000/`, pre-warmed (Mode 1 has run once)
- **IDE** with these files in tabs:
  - `workflows/strategy_graph.py` open to line 187 (the Workflow definition)
  - `workflows/concierge.py` open to line 75 (the coordinator)
  - `workflows/deep_research.py` open to line 84 (the recursive parallel_worker node)
- **One slide** with the decision tree from § 9, ready to switch to for the recap
