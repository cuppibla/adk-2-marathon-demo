# ADK Video Script (20 min)

**Format:** Full prose, read verbatim. Stage directions in `[brackets]`.
**Pacing assumption:** ~150 spoken words / minute conversationally.
**Pre-record checklist:**
- Open `/Users/annie/Documents/Demo/race-condition/agents/planner/agent.py` to line 47
- Open `/Users/annie/Documents/Demo/race-condition/agents/runner/agent.py` to line 155
- Open `/Users/annie/Documents/Demo/race-condition/agents/runner_autopilot/autopilot.py` to line 243
- Open `/Users/annie/Documents/Demo/marathonplanner/marathon.py` to line 187 (the `Workflow` definition)
- Have `http://127.0.0.1:8000/` open in a browser (server: `uv run python server.py`)
- Cache one HOT run in advance so Replay button is enabled if the API hiccups on stage

---

## Section 1 — What is ADK? (~2:00)

[OPEN ON: a slide or a clean editor — no code yet]

Hi everyone. In the next twenty minutes, I'm going to walk you through Google's Agent Development Kit — what it is, what's new in version 2.0, and a live demo of the new graph-based workflows.

Quick context for anyone who hasn't used ADK before. ADK is Google's framework for building production agents. If you've worked with LangChain, LangGraph, or CrewAI, ADK lives in the same neighborhood — but with a more Google-y opinion. Heavy emphasis on observability through OpenTelemetry, first-class deployment to Vertex AI's Agent Engine, and structured Pydantic schemas everywhere instead of free-form dicts.

Two ideas to keep in your head for the rest of this talk.

First: an agent, in any framework, is essentially three things — a language model, a set of tools the model can call, and a system instruction telling it how to behave.

Second — and this is the important one — the hard part isn't building one agent. The hard part is getting multiple agents and multiple steps to flow together predictably. That's the gap ADK 2.0 is targeting, and that's what we're going to spend most of our time on today.

So here's the plan. I'll show you what ADK 1.x looks like in practice using a project I have called `race-condition`. Then I'll explain what changed in 2.0 and why. Then I'll walk you through this repo — a marathon race day strategy planner I built specifically to demo the new graph workflows. And we'll end with a live run.

[TRANSITION: switch to your IDE, open race-condition project]

---

## Section 2 — ADK 1.x in Practice (~4:30)

This is a project called `race-condition`. It's a competitive marathon simulation. Three agents: a **Planner** that designs full 26.2-mile marathon routes on real Las Vegas road networks, **Runner** agents — hundreds of them running in parallel as LLM-powered NPCs that make pacing and hydration decisions every simulation tick — and a deterministic **Autopilot** variant that bypasses the LLM entirely.

This is canonical ADK 1.x. Let me open the Planner agent.

[SHOW: `race-condition/agents/planner/agent.py` lines 47–69]

```python
def get_agent():
    return LlmAgent(
        name="planner",
        model=resilient_model("gemini-3-flash-preview"),
        description="Expert GIS analyst for marathon route and event planning.",
        static_instruction=PLANNER.build(),
        generate_content_config=types.GenerateContentConfig(
            max_output_tokens=8192,
            temperature=0.1,
            thinking_config=types.ThinkingConfig(thinking_budget=1024),
        ),
        tools=get_tools(),
        before_model_callback=financial_guardrail_callback,
    )
```

This is the standard shape: an `LlmAgent` with a model, an instruction, a list of tools, and a callback. The instruction — `PLANNER.build()` — is hundreds of lines of prose. It tells the LLM things like "first load this skill, then call this tool, then synthesize a route summary." The tools are GIS functions for placing hydration stations, mapping routes, calling external Maps APIs.

The callback — `before_model_callback` — runs before every model call. In this case it's a financial guardrail. If the user asks about budgets and uses a write verb, the callback short-circuits and returns a refusal without ever hitting the model.

[SHOW: `race-condition/agents/runner/agent.py` lines 155–162]

Now look at the Runner agent. Every simulation tick — every few hundred milliseconds — fires this prompt:

```python
RUNNER_DYNAMIC_INSTRUCTION = (
    "Runner state right now -- "
    "distance: {distance} mi, "
    "water: {water}%, "
    "velocity: {velocity} mph, "
    "status: {runner_status}, "
    "target finish: {target_finish_minutes} min."
)
```

Those curly-brace placeholders get filled in by another callback — `before_agent_callback` — that pulls tick parameters out of the incoming event, mutates session state, and injects them into the instruction template. Then the LLM sees the filled-in prompt, decides whether to accelerate, brake, or hydrate, and a tool executes that decision.

And here's the autopilot variant — same agent shape, but the entire logic layer lives in a callback that returns hardcoded function calls without ever invoking a model.

[SHOW: `race-condition/agents/runner_autopilot/autopilot.py` lines 243–249]

```python
HANDLERS: dict[RunnerEventType, Callable[[StateLike, dict], LlmResponse]] = {
    RunnerEventType.START_GUN: handle_start_gun,
    RunnerEventType.CROWD_BOOST: handle_crowd_boost,
    RunnerEventType.DISTANCE_UPDATE: handle_distance_update,
    RunnerEventType.HYDRATION_STATION: handle_hydration_station,
    RunnerEventType.TICK: handle_tick,
}
```

OK. So this works. Marathons get planned, runners get simulated, hundreds of them run in parallel. But notice the friction.

The Planner's multi-step workflow lives **in the prompt**. The model has to read several hundred tokens of instructions and follow them in order. Skip a step, hallucinate a tool name, call things in the wrong sequence — the whole plan breaks. To debug, you read prompt traces, not code.

To add deterministic logic, you write callbacks. The financial guardrail is a callback. The runner state injection is a callback. The autopilot is *literally a callback masquerading as an agent.* Callbacks are powerful, but they mix policy logic, framework plumbing, and control flow in the same place. They're hard to read and harder to test in isolation.

And to mix deterministic Python with LLM reasoning in the same flow — say, "fetch weather data, then run an LLM, then save to a database" — you basically have two options. Wrap your Python in a tool and let the LLM decide when to call it. Or write a `SequentialAgent` of sub-agents and accept that every step has to be an agent. Neither is great.

This is exactly the gap ADK 2.0 is filling.

[TRANSITION: close race-condition, open marathonplanner repo or a docs slide]

---

## Section 3 — What's New in ADK 2.0 (~4:00)

ADK 2.0 introduces graph-based workflows. The shift is best stated in one sentence: instead of describing your workflow in a prompt, you express it as a graph of nodes connected by edges.

A graph workflow has a few primitive node types.

**FunctionNode** — a plain Python function that returns an Event. No LLM. Pure code. Use these for everything deterministic — API calls, data transforms, anything you'd write a regular function for.

**Agent in single-turn mode** — one LLM call with optional input and output schemas. Fire-and-forget, no chat history. Use these for the parts that genuinely need reasoning.

**JoinNode** — waits for N upstream nodes to all complete, then bundles their outputs into a typed payload for the next node.

**A router** — also just a function — returns a routing decision, a literal string like `"HOT"` or `"COLD"`, and the graph picks which branch to run next based on that string.

**RequestInput** — pauses the entire workflow waiting for human input. Human-in-the-loop as a first-class primitive, not something you bolt on with a tool.

And — importantly — **a Workflow itself can be a node** in another Workflow. So you can build reusable sub-graphs and compose them into larger flows.

The wiring lives in an `edges` array. Each row is "from this node, go to these nodes." Routers use a dictionary mapping route values to the node that should run for that route. That's the entire syntax — tuples and dicts.

What does this buy you over ADK 1.x? Four concrete things.

**First, deterministic branching on data.** In 1.x, if your flow needed to choose between three branches based on, say, the weather forecast, you'd write a coordinator agent with an instruction telling the LLM to call `transfer_to_agent` with the right name. And you'd cross your fingers. In 2.0, the router is a four-line Python `if` statement. Python decides, not the model. No prompt engineering, no hallucinations.

**Second, mixed deterministic and LLM steps in the same graph.** A graph node can be raw Python or it can be an Agent. They sit side by side in the same `edges` array. You stop having to choose between "all agents" and "all callbacks."

**Third, real parallelism with typed handoff.** Three FunctionNodes can fire from START at the same time. JoinNode waits for all three and bundles their outputs into a Pydantic-typed payload that the next node receives directly. In 1.x, ParallelAgent dumped each sub-agent's output into shared session state and you hoped the next agent's prompt remembered to read the right keys.

**Fourth — and this is the one I care about most — your prompts get smaller.** You don't need to write "first do X, then do Y, then do Z" inside a system instruction anymore, because the graph enforces ordering. Each agent's instruction shrinks down to its actual job: "given this input, produce this output." Less prompt to debug, fewer ways for the model to go off the rails.

Now let me show you what that looks like in code.

[TRANSITION: open marathonplanner/marathon.py]

---

## Section 4 — Walking Through This Repo (~3:30)

This is a different problem from the race simulator. Here, a runner has a marathon coming up and they want a personalized race day strategy. We need three pieces of data: the weather forecast, the course profile, and their recent training. Then we need to decide on a pacing, fueling, and gear strategy that accounts for all of it.

Let me show you the workflow definition.

[SHOW: `marathon.py` lines 187–202 — the `root_agent = Workflow(...)` block]

```python
root_agent = Workflow(
    name="marathon_strategy",
    edges=[
        (START, fetch_weather, join_inputs),
        (START, analyze_course, join_inputs),
        (START, pull_fitness, join_inputs),
        (join_inputs, route_by_weather),
        (route_by_weather, {
            "HOT": hot_strategy,
            "NORMAL": normal_strategy,
            "COLD": cold_strategy,
        }),
    ],
)
```

This is the entire orchestration layer. Read it like a diagram. START fans out to three function nodes — `fetch_weather`, `analyze_course`, `pull_fitness`. They run in parallel. JoinNode waits for all three. Then a router picks one of three strategy branches based on the weather data.

The fetch nodes are pure Python. Here's `fetch_weather`:

[SHOW: `marathon.py` `fetch_weather` function — around line 130]

```python
async def fetch_weather(node_input):
    await asyncio.sleep(1.5 * _slow_mo())
    return Event(output=_scenario()["weather"].model_dump())
```

In production this would be an actual API call. For the demo I've stubbed it with canned data so the routing is reproducible on stage. The point is — there's no LLM here. We don't need a model to fetch weather. We don't need a model to merge three dicts.

Here's the router. This is the part I'm most excited about.

[SHOW: `marathon.py` `route_by_weather` function — around line 152]

```python
def route_by_weather(node_input):
    weather = node_input["fetch_weather"]
    temp = weather["temp_f"]
    if temp >= 70:   route = "HOT"
    elif temp <= 40: route = "COLD"
    else:            route = "NORMAL"
    return Event(output=node_input, route=route)
```

Four lines. This is the entire branching logic. In ADK 1.x, this would have been a coordinator LLM with an instruction telling it to transfer to the right sub-agent based on the weather. Here it's an `if` statement.

Now the strategy agents — these are the parts that actually need reasoning.

[SHOW: `marathon.py` `hot_strategy` Agent — around line 175]

```python
hot_strategy = Agent(
    name="hot_strategy",
    model=MODEL,
    mode="single_turn",
    input_schema=BundledRunData,
    output_schema=RaceStrategy,
    instruction="""You are a marathon coach planning a race in HOT conditions.
        Heat is the primary risk — the runner needs to slow down, hydrate
        aggressively, and dress to stay cool. Their goal time should be
        adjusted SLOWER than ideal.
        ...
    """,
)
```

Three things to notice. `mode="single_turn"` — fire and forget, no chat history. `input_schema=BundledRunData` — the framework validates the input against this Pydantic model before the LLM even sees it. `output_schema=RaceStrategy` — Gemini is forced to return JSON matching this schema. Not "asked nicely" via prompt — actually constrained at the API level.

And the instruction is just the role. There's no choreography in there. No "first read the weather, then look at the course, then write your response." The graph already handled all of that.

OK. Enough code. Let me actually run it.

[TRANSITION: switch to browser]

---

## Section 5 — Live Demo (~4:00)

[SHOW: browser at `http://127.0.0.1:8000/`]

This is a small frontend I built to visualize the graph. It's not part of ADK — it's a vanilla HTML page that subscribes to a Server-Sent Events stream from a FastAPI server. Every time a node in the graph completes, an event flows through to the browser and the corresponding node lights up.

You can see the graph on the left. START at the top, three fetch nodes in parallel, the JoinNode, the router with its three branches, and the three strategy agents at the bottom. Right side has a live event log, the strategy output, and a stats panel.

I'm going to pick the **Hot Boston** scenario. That's 78 degrees, headwind, the Boston Marathon course with Heartbreak Hill at mile 20, runner has a 7:30 per mile fitness level. And I'll click Run.

[CLICK: Run]

Watch the three nodes light up at the same time. They started simultaneously. Each one shows a live timer — pull_fitness is one second, fetch_weather is one and a half, analyze_course is two seconds. They're not happening one after another. They're truly parallel.

[WAIT: ~1 second — narrate over the visual]

There — pull_fitness completed first. It's green now. fetch_weather just finished. And analyze_course at two seconds.

The moment all three completed, JoinNode bundled their outputs and handed them to the router. The router saw 78 degrees, picked the HOT branch — and now the LLM is running. That's the only LLM call in the entire workflow.

[WAIT: ~5 seconds for Gemini]

Strategy returned. Look at the right panel.

The hero number is the target finish time — three thirty-five. Look at the pacing advice — *"Slow your typical 7:30 pace to 8:12 per mile to account for the 78-degree heat and the 4.5% grade at mile 20."* It referenced the actual fitness pace we passed in. The actual temperature. The actual hardest mile from the course profile. That's the input schema doing real work — the model can see the structured data, not just a paragraph of prose.

[SCROLL: down to the stats card]

Workflow complete in seven seconds. One LLM call. The fetch phase ran in two seconds in parallel — would've taken four and a half if we'd run them sequentially. Saved two and a half seconds via fan-out.

But here's the headline number I want you to remember. **One LLM call.** We did not call a model to decide what data to fetch. We did not call a model to decide whether the weather was hot or cold. We did not call a model to merge three dicts. The model only ran for the part that genuinely needed reasoning — writing a personalized strategy.

Compare that to a prompt-based agent doing the same task. You'd probably call the model three or four times: once to plan, once or twice for tool calls, once to summarize. Five seconds becomes fifteen. And every extra call is another opportunity for the model to mis-route, hallucinate a tool name, or forget context.

Let me show you the routing changing on data. I'll switch to **Cold Chicago** and run it again.

[CLICK: Cold · Chicago, then Run]

Same graph. Same parallelism. Same parallel pulse. But now — there — the router saw 35 degrees, picked the COLD branch. The cold_strategy agent fires.

[WAIT: ~5 seconds]

Different output. *"First three miles at 7:30 to warm up in the 35-degree cold... drafting strategy to hide from the 15 mph wind."* Different agent, different system prompt, different advice. The router decided which one ran — deterministically, in four lines of Python.

This is the punchline. In ADK 1.x, that branching decision would have lived inside an LLM coordinator's prompt. *"Based on the weather, transfer to the appropriate handler agent."* And we'd have hoped the model transferred correctly. Here it's an `if` statement. It cannot be wrong.

[OPTIONAL: if time permits, click Replay button to show same animation runs from cache without hitting backend — useful safety net to mention]

One last thing worth noting — see the Replay button up top? That re-plays the exact same animation timing from a client-side cache. Zero backend calls, zero LLM cost. Critical safety net for a live demo: if the API ever hiccups on stage, you can fall back to the cached run and the audience never knows.

[TRANSITION: back to a clean editor or slide]

---

## Section 6 — Handoff to Skills + MCP (~1:00)

That's ADK 2.0's graph workflows. To recap quickly.

You express your agent's structure as nodes and edges, not as a prompt. Function nodes for deterministic Python. Agent nodes for LLM reasoning. Routers branch on data, not on model judgment. JoinNodes merge parallel work with typed handoff. Workflows can nest as nodes in other workflows.

The result: shorter prompts, more predictable execution, real parallelism, and a clean separation between the parts of your agent that need a model and the parts that don't.

Now — this is half the story. Graph workflows give you the *structure*. The other half is what your agents can actually *do*. Tools, skills, MCP servers — the protocol that lets an agent reach out to external systems like Gmail, Calendar, your own internal APIs, anything.

[TEAMMATE NAME] is going to take it from here and show you how skills and MCP work — including how a single MCP tool call can become a node in a graph workflow, and how skills give your agents reusable capabilities across projects.

Over to you, [TEAMMATE NAME].

[END]

---

## Pacing notes

Approximate word counts per section (target ~150 wpm):

| Section | Words | Time |
|---|---:|---:|
| 1. What is ADK | ~290 | 2:00 |
| 2. ADK 1.x via race-condition | ~720 | 4:45 |
| 3. What's new in 2.0 | ~620 | 4:10 |
| 4. Walking through this repo | ~520 | 3:30 |
| 5. Live demo | ~620 | 4:10 |
| 6. Handoff | ~150 | 1:00 |
| **Total** | **~2920** | **~19:35** |

Buffer ~30 seconds for breath, transitions, and the live LLM call wait time. Should land at exactly 20.

## Things to cut if running long

1. The Autopilot snippet in Section 2 (saves ~30s, you still make the callback-overuse point)
2. The Replay button mention at end of Section 5 (saves ~20s — only mention if it actually saved you)
3. The "Cold Chicago" second run (saves ~60s — only do it if the routing point hasn't landed)

## Things to add if running short

1. After Section 4, briefly show the SVG visualization frontend code is ~300 lines of vanilla JS — "I built this in an afternoon, the SSE plumbing is trivial because ADK gives you the event iterator for free"
2. After Section 5 stats, mention slow-mo dropdown — change to 3× and re-run for a slower, more visible parallel pulse
