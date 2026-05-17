# ADK 2.0: A Complete Guide

A teaching document covering what ADK 2.0 is, how it differs from ADK 1.x, when to use each of its three pillars, how to build with it, and how to use this marathon demo to explain it to others.

If you're teaching ADK 2.0 to a video audience or new teammate, this is the doc to read first.

---

## Table of contents

1. [What is ADK?](#1-what-is-adk)
2. [ADK 1.x — the baseline](#2-adk-1x--the-baseline)
3. [What ADK 2.0 adds (the three pillars)](#3-what-adk-20-adds-the-three-pillars)
4. [Pillar 1 — Graph workflows (deep dive)](#4-pillar-1--graph-workflows-deep-dive)
5. [Pillar 2 — Collaborative agents (deep dive)](#5-pillar-2--collaborative-agents-deep-dive)
6. [Pillar 3 — Dynamic workflows (deep dive)](#6-pillar-3--dynamic-workflows-deep-dive)
7. [Decision tree — which pillar do I use?](#7-decision-tree--which-pillar-do-i-use)
8. [How to build with ADK 2.0](#8-how-to-build-with-adk-20)
9. [Component reference](#9-component-reference)
10. [Using this demo to teach others](#10-using-this-demo-to-teach-others)
11. [Common mistakes (gotchas)](#11-common-mistakes-gotchas)

---

## 1. What is ADK?

ADK is Google's **Agent Development Kit** — a Python framework for building production AI agents.

If you've used LangChain, LangGraph, or CrewAI, ADK lives in the same neighborhood. It's a Google-y opinion: heavy emphasis on observability (OpenTelemetry), first-class deployment to Vertex AI's Agent Engine, structured Pydantic schemas everywhere instead of free-form dicts.

### What's an "agent"?

An ADK agent is **one LLM with a job and some tools.** Three ingredients:

- **A language model** — the brain (e.g., Gemini Flash)
- **An instruction** — the job description
- **Tools** — things the brain can call (Python functions, APIs, databases)

That's it for one agent. The hard part — and the part this guide is mostly about — is what happens when you need **multiple agents and multiple steps to flow together reliably.** That's called **orchestration**, and it's where ADK 2.0 introduces three new patterns.

---

## 2. ADK 1.x — the baseline

ADK 1.x gave you a small set of orchestration patterns:

| 1.x primitive | What it does |
|---|---|
| `LlmAgent` | One LLM with tools and instructions |
| `LlmAgent` with `sub_agents=[...]` | Coordinator that uses `transfer_to_agent` to hand off via prompts |
| `SequentialAgent` | Run a list of agents in order |
| `ParallelAgent` | Run a list of agents at the same time (fixed list at construction) |
| `LoopAgent` | Repeat one agent until a condition |
| Callbacks (`before_model_callback`, `before_agent_callback`, etc.) | Hook into execution lifecycle |

### Where 1.x works well

- Conversational agents (single LlmAgent with tools)
- Linear pipelines (SequentialAgent)
- Always-fan-out patterns (ParallelAgent with a known set)

### Where 1.x gets brittle

- **Routing decisions inside prompts.** Telling an LLM "if X transfer to Y agent, if Z transfer to W agent" mostly works, occasionally fails. You can't *prove* the routing is correct.
- **Multi-step workflows in prose.** A 400-token instruction "first do X, then if Y, do Z, otherwise W" is hard to debug. The LLM might skip a step or call tools in the wrong order.
- **Mixing pure-Python steps with LLM steps.** ParallelAgent only orchestrates agents. To run a function in parallel with agents, you wrap the function in a tool inside an agent — adding an unnecessary LLM call per function.
- **Runtime-sized work.** ParallelAgent's sub-agent list is fixed at construction. If your fan-out count depends on user input, you can construct it dynamically but lose graph-level guarantees.
- **Callbacks for non-trivial logic.** Custom orchestration ends up in `before_model_callback` functions that mix policy logic with framework plumbing.

These pain points motivated ADK 2.0.

---

## 3. What ADK 2.0 adds (the three pillars)

ADK 2.0 introduces three new orchestration patterns. Each addresses one shape of problem 1.x handled poorly.

| Pillar | One-word reminder | When to reach for it |
|---|---|---|
| **1. Graph workflows** | **diagram** | The structure is known up front; you can draw it before writing code |
| **2. Collaborative agents** | **delegation** | An LLM should be picking which sub-agent handles each request |
| **3. Dynamic workflows** | **scale** | The topology depends on data unknown until runtime (loops, recursion, runtime fan-out) |

These overlap — you can mix them. A graph workflow can include a node that's itself a collaborative coordinator. A dynamic workflow can invoke other workflows. They're layers, not exclusive choices.

The rest of this guide goes deep on each.

---

## 4. Pillar 1 — Graph workflows (deep dive)

### What it is

You **declare** a graph of nodes connected by edges. Nodes can be plain Python functions or LLM agents. The framework executes the graph.

```python
from google.adk import Workflow
from google.adk.workflow import START

root_agent = Workflow(
    name="marathon_strategy",
    edges=[
        (START, fetch_weather, join_inputs),         # parallel branch
        (START, analyze_course, join_inputs),        # parallel branch
        (START, pull_fitness, join_inputs),          # parallel branch
        (join_inputs, route_by_weather),             # converge + route
        (route_by_weather, {                          # branch on route
            "HOT":    hot_strategy_agent,
            "NORMAL": normal_strategy_agent,
            "COLD":   cold_strategy_agent,
        }),
    ],
)
```

Read it like a diagram. Three rows starting with `START` fan out in parallel. The `(join_inputs, route_by_weather)` row runs after the join. The `route_by_weather, {...}` row picks one of three branches based on the router function's emitted `route=` value.

### What's uniquely 2.0

| Feature | 1.x | 2.0 graph |
|---|---|---|
| Mix function nodes + agent nodes in same flow | Functions must be wrapped as tools inside agents | Functions and agents coexist as peers |
| Deterministic routing on data | LLM coordinator with `transfer_to_agent` (prompt-driven) | Router function returns `Event(route="...")`, framework picks branch |
| Typed parallel handoff | ParallelAgent dumps outputs to session state (untyped) | `JoinNode` bundles outputs into a typed payload for the next node |

### Concrete in our demo: Mode 1

`workflows/strategy_graph.py` is the canonical example. Three function nodes (no LLM) fetch weather, course, fitness in parallel. `JoinNode` bundles them. A 4-line Python `route_by_weather` function picks one of three branches based on temperature. The chosen strategy agent (LLM, single_turn) generates the final `RaceStrategy`.

**Total LLM calls: 1.** Everything else is pure Python. In 1.x's `SequentialAgent + ParallelAgent` equivalent, this would be 4-5 LLM calls (one per fetch-agent + one per strategy + one for routing).

### When to reach for it

- The work has a fixed, drawable shape
- Routing decisions can be expressed as rules (not LLM judgment)
- You want deterministic execution
- Performance matters (graph minimizes LLM calls)

### When NOT to use it

- Free-form conversation (no fixed shape)
- The structure changes based on user input (use Pillar 3)
- An LLM should be making the routing call (use Pillar 2)

---

## 5. Pillar 2 — Collaborative agents (deep dive)

### What it is

A **coordinator** agent declares `sub_agents=[...]`. The framework auto-injects "delegation tools" the coordinator can call to invoke any subagent. The coordinator's LLM picks which subagents to invoke per request — **and can invoke multiple in parallel** in one turn.

```python
race_concierge = Agent(
    name="race_concierge",
    model="gemini-flash-latest",
    sub_agents=[
        medical_specialist,
        weather_specialist,
        pacing_specialist,
        gear_specialist,
        nutrition_specialist,
        mental_specialist,
    ],
    instruction="""You are a race day concierge. Six specialists are available...
    Decide which are relevant. Call multiple in parallel in one turn when appropriate.""",
)
```

Each subagent has a `mode`:

| Mode | Use when |
|---|---|
| `chat` (default) | Subagent drives its own multi-turn conversation with user |
| `task` | Bounded task that may ask clarifying questions; auto-returns when done |
| `single_turn` | Pure transform; **multiple can run in parallel** under a coordinator |

The killer mode for orchestration is `single_turn` — it's the only mode that supports parallel execution under one coordinator.

### What's uniquely 2.0

| Feature | 1.x | 2.0 collab |
|---|---|---|
| Coordinator picks **which** subagents to invoke | Yes (via `transfer_to_agent`) | Yes (via auto-injected `request_task_*` tools) |
| Coordinator picks a **subset** dynamically per request | Sort of (one at a time) | Yes — can call multiple in one turn |
| Subagents run **in parallel** under one coordinator | No (transfer_to_agent is serial) | **Yes** — multi-call function_call parts execute concurrently |
| Auto-return without explicit handoff | No (subagent must `transfer_to_agent` back) | Yes (`task` mode: auto-return via `complete_task`; `single_turn`: implicit return) |

The unique 2.0 thing is **LLM-driven dynamic subset selection with parallel execution.** Static `ParallelAgent` always runs every sub-agent. Collab agents let the coordinator pick 1, 3, or all 6 in parallel based on the request.

### Concrete in our demo: Mode 2

`workflows/concierge.py` has a coordinator with 6 single_turn specialists. Examples:

- "My knee hurts" → coordinator invokes **medical only** (1 LLM call)
- "Should I race today?" → coordinator invokes **medical + weather + pacing in parallel** (3 LLM calls in parallel)
- "Anything I should worry about overall?" → coordinator invokes **all 6 in parallel** (6 LLM calls in parallel)

Same UI, different inputs, different subsets. The coordinator's LLM is reasoning about who should answer.

### When to reach for it

- The routing decision itself benefits from LLM reasoning (not deterministic rules)
- Multiple specialists may be relevant per request
- You want parallel execution AND dynamic subset selection
- Subagents have clearly different domains

### When NOT to use it

- The routing is deterministic (use Pillar 1 graph with a router)
- The orchestration is always-fan-out (use ParallelAgent — simpler)
- Just one subagent per request (use sequential delegation in 1.x or a graph branch)

---

## 6. Pillar 3 — Dynamic workflows (deep dive)

### What it is

**The topology of parallel work is determined by data at runtime.** Not just the count of parallel branches, but the *shape* of the work — including recursive structures where a node spawns more parallel work from inside itself.

Two key primitives:

```python
from google.adk.workflow import node

@node  # @node turns a function into a workflow node
async def emit_topics(ctx, node_input):
    yield Event(output=["topic_a", "topic_b", "topic_c"])

@node(parallel_worker=True, rerun_on_resume=True)
async def research_topic(ctx, node_input):
    # parallel_worker=True: when upstream emits a LIST, this fans out
    # one task per item. Topology is data-driven.
    question = node_input

    finding = await some_agent.run(question)

    # Recursive spawning — call ctx.run_node(self, list) to fan out more
    if finding.needs_deeper:
        children = await ctx.run_node(
            research_topic,
            node_input=finding.deeper_questions,  # another list → another fan-out
        )
        finding.children = children

    yield Event(output=finding)
```

When `emit_topics` emits a list of 3 items, `research_topic` (wrapped in `_ParallelWorker`) spawns 3 parallel tasks — one per item. If `emit_topics` had emitted 30 items, it would spawn 30. The count came from data.

### What's uniquely 2.0

| Feature | 1.x | 2.0 dynamic |
|---|---|---|
| Parallel execution of N tasks | Yes (ParallelAgent) | Yes |
| Count of parallel tasks determined at construction | Yes (fixed) | Yes |
| Count determined at runtime | Awkward (construct ParallelAgent in handler) | Native (`parallel_worker=True` + list input) |
| Recursive spawning (a parallel branch spawns more parallel work) | **Impossible** with framework primitives — must drop to raw asyncio | **Native** via recursive `ctx.run_node(self, list)` |
| Variable depth per item | **Impossible** declaratively | Native — each item can branch differently |
| Resumability (skip completed branches on retry) | No | Yes (per-node checkpointing) |

The unique 2.0 thing isn't just "parallel" (ParallelAgent does that). It's **recursive, runtime-shaped parallelism with framework-level tracing and resumability.**

### Concrete in our demo: Mode 3

`workflows/deep_research.py` is a deep research workflow:

1. `decompose` (function node) — runs an LLM to decompose the user query into 3-7 sub-questions
2. `research_topic` (`@node(parallel_worker=True)`) — runs in parallel across the sub-questions; each instance may flag `needs_deeper=True` and recursively spawn 1-3 child questions
3. `synthesize` (function node) — runs an LLM to aggregate the nested findings tree into a briefing

Result for a Boston Marathon deep-dive: 5 top-level questions + ~12 recursive children = **17 LLM calls in 30 seconds** (vs ~136s if serial). The tree's width AND depth are decided by the LLMs at runtime.

In ADK 1.x, you cannot express the recursive part with framework primitives. You'd write raw `asyncio.gather` outside the workflow, losing tracing, checkpointing, and resumability.

### When to reach for it

- The number of parallel tasks isn't known until runtime
- A task may spawn more sub-tasks based on its findings
- Long-running, failure-prone workflows that need resumability
- Batch/operational pipelines (process every file, every customer, every PR)

### When NOT to use it

- The structure is known up front (use Pillar 1 graph)
- The fan-out is always the same size (ParallelAgent is fine)
- One-step transforms (single agent is fine)

### A common confusion to head off

**Pillar 3 is NOT about running multiple users in parallel** (that's infrastructure scaling). It's about parallel work *inside* one workflow run, where the number of branches comes from the data.

---

## 7. Decision tree — which pillar do I use?

First "yes" wins:

```
Is the work a free-form conversation?
  YES → Single LlmAgent
        (or chat-mode coordinator + collaborative subagents
         if you have specialized roles)

Is the structure known up front and expressible as a diagram?
  YES → Pillar 1 — Graph workflow

Does it need loops, recursion, or runtime-sized fan-out?
  YES → Pillar 3 — Dynamic workflow

Should an LLM be the one picking which specialist invokes per request?
  YES → Pillar 2 — Collaborative agents

Otherwise → Single LlmAgent with tools (don't over-engineer)
```

Common mistakes:

- Reaching for graphs when the structure isn't known (forces fragile `if/else` in nodes)
- Reaching for collab when routing is deterministic (use a graph router — 10× cheaper)
- Reaching for dynamic when the structure is static (just use graph)
- Reaching for any pillar when one LlmAgent would do (don't over-engineer)

See [docs/ADK_2_PILLARS_DECISION_TREE.md](ADK_2_PILLARS_DECISION_TREE.md) for the worked examples.

---

## 8. How to build with ADK 2.0

### Setup

```bash
# Python 3.11+ required
uv init my-agent-app
cd my-agent-app
uv add "google-adk==2.0.0b1" --prerelease=allow
```

Add `GOOGLE_API_KEY` to a `.env` file.

### Build order (recommended)

1. **Schemas first.** Pydantic `BaseModel` for every typed payload — input, output, intermediate. Get these right before writing code; they're load-bearing.

2. **Function nodes.** Pure Python — API calls, transforms, anything that doesn't need an LLM. Just async functions that return `Event(output=...)`.

3. **Agent nodes.** LLM with `output_schema` for structured output. Single-turn for one-shot, task for clarification, chat for full conversation.

4. **Compose.** Wire them with `Workflow(edges=[...])` for graphs, `sub_agents=[...]` for collab, `@node(parallel_worker=True)` for dynamic.

5. **Test in CLI first.** Use `Runner` + `runner.run_async()` in a script before building any UI. CLI feedback is faster than browser.

6. **Add observability.** SSE bridge to a frontend if you want a visual demo. Otherwise rely on OpenTelemetry tracing.

### Key patterns

**Function node** (zero LLM calls):
```python
async def fetch_weather(node_input):
    data = await weather_api.fetch()
    return Event(output=data)
```

**Agent node** (one LLM call, structured output):
```python
strategy_agent = Agent(
    name="hot_strategy",
    model="gemini-flash-latest",
    mode="single_turn",
    input_schema=BundledRunData,
    output_schema=RaceStrategy,
    instruction="You are a marathon coach for hot conditions...",
)
```

**Graph workflow** (declarative orchestration):
```python
Workflow(
    name="my_flow",
    edges=[
        (START, fetch_a, join),
        (START, fetch_b, join),
        (join, router),
        (router, {"X": agent_x, "Y": agent_y}),
    ],
)
```

**Collaborative coordinator**:
```python
Agent(
    name="coordinator",
    sub_agents=[specialist_a, specialist_b, specialist_c],
    instruction="Pick the right specialist(s) and invoke in parallel...",
)
```

**Dynamic recursive workflow**:
```python
@node(parallel_worker=True, rerun_on_resume=True)
async def process_item(ctx, node_input):
    item = node_input
    result = await some_processing(item)
    if result.needs_deeper:
        children = await ctx.run_node(process_item, result.sub_items)
        result.children = children
    yield Event(output=result)
```

### Running

```python
from google.adk import Runner
from google.adk.sessions import InMemorySessionService

runner = Runner(
    node=my_workflow,
    app_name="my_app",
    session_service=InMemorySessionService(),
    auto_create_session=True,
)
async for event in runner.run_async(user_id="u", session_id="s", new_message=msg):
    ...
```

---

## 9. Component reference

The APIs you'll actually use, with import paths:

| Import | What it is | When you use it |
|---|---|---|
| `from google.adk import Agent` | An LLM with instructions + tools (and optionally sub_agents) | Any agent |
| `from google.adk import Workflow` | The graph container with `edges=[...]` | Pillars 1, 3 |
| `from google.adk import Event` | The thing nodes yield (carries `output`, `route`, `message`) | Every node |
| `from google.adk import Runner` | Executes a workflow or agent | Top-level driver |
| `from google.adk.workflow import START` | Sentinel for graph entry point | Inside `edges` |
| `from google.adk.workflow import JoinNode` | Waits for N upstream branches, bundles into a dict | Parallel fan-in |
| `from google.adk.workflow import node` | Decorator that wraps a function as a node | Function nodes (esp. `parallel_worker=True`) |
| `from google.adk.workflow import FunctionNode` | Explicit function wrapping (rarely needed) | Custom name/config |
| `from google.adk.events import RequestInput` | HITL pause primitive | Human-in-the-loop |
| `from google.adk.sessions import InMemorySessionService` | Demo-grade session service | Local dev |
| `from google.genai import types as gtypes` | Content/Part for messages | Passing user messages |

**Critical methods:**

- `Workflow(name=..., edges=[...])` — build a graph workflow
- `Agent(name=, model=, instruction=, sub_agents=, output_schema=, mode=...)` — build an agent
- `@node` or `@node(parallel_worker=True, rerun_on_resume=True)` — decorate a function as a node
- `await ctx.run_node(node_or_list, node_input=...)` — invoke another node from inside a function node
- `runner.run_async(user_id=, session_id=, new_message=...)` — run the workflow, returns async iterator of events

---

## 10. Using this demo to teach others

This repo IS a teaching tool. Here's how to use it.

### For a 20-min video / talk

Follow [VIDEO_SCRIPT.md](../VIDEO_SCRIPT.md). It's a verbatim prose script with timing, stage directions, and IDE file/line references.

Sections:
1. Intro / what ADK 2.0 is (2 min)
2. Bridge for non-runners (30s)
3. Mode 1 demo + Pillar 1 narration (5 min)
4. Mode 2 demo + Pillar 2 narration (5 min)
5. Mode 3 demo + Pillar 3 narration (4 min)
6. Decision tree recap (1.5 min)
7. Handoff to skills/MCP (1 min)

### For a 5-min lightning demo

Use only Mode 1 (graph). Click "Hot · Boston" → Run. Narrate the parallel pulse and the 1-LLM-call payoff. Don't try to cover all three pillars in 5 min.

### For a coding workshop

1. Open `workflows/strategy_graph.py` — the `edges=[...]` block is the canonical Pillar 1 demo. ~200 lines including schemas.
2. Open `workflows/concierge.py` — coordinator + sub_agents. ~150 lines.
3. Open `workflows/deep_research.py` — `@node(parallel_worker=True)` with recursive `ctx.run_node`. ~200 lines.

Walk through each in sequence (~10 min each), pausing to point at the unique-to-2.0 line:

- Graph: the `(route_by_weather, {"HOT": ..., "NORMAL": ..., "COLD": ...})` row — deterministic branching
- Collab: the `sub_agents=[...]` parameter — auto-delegation infrastructure
- Dynamic: the `await ctx.run_node(research_topic, deeper_questions)` line — recursive parallel fan-out

### Talking points to memorize

When someone asks the inevitable question for each pillar:

| Question | One-line answer |
|---|---|
| *"Couldn't I do graph workflows with SequentialAgent + ParallelAgent in 1.x?"* | You'd pay three ways: more LLM calls (every node must be an agent), serial fetches (ParallelAgent only orchestrates agents), and shared-state handoff (no typed payload). |
| *"Couldn't I do collab with sub_agents + transfer_to_agent in 1.x?"* | transfer_to_agent is serial. 2.0 collab lets the coordinator invoke multiple subagents in **one turn**, running in parallel. |
| *"Couldn't I do dynamic with LoopAgent or constructed ParallelAgent in 1.x?"* | LoopAgent is serial. ParallelAgent's sub-agent list is fixed at construction. Neither can express *recursive* parallel work (a parallel branch spawning more parallel branches). |

---

## 11. Common mistakes (gotchas)

I hit all of these building this demo. Now you don't have to.

### Schema mistakes

- **Forgetting `output_schema` on an Agent.** Then the model returns free-form text and you can't parse it reliably. Always pass `output_schema` for non-conversational agents.
- **Forgetting `Field(description=...)`.** The description ends up in the JSON schema sent to Gemini — it's load-bearing for output quality. *"target_finish"* with no description produces *"3:35:00 with 5 min buffer for headwind"*. With `description="Clean time only, format H:MM:SS"`, it produces *"3:35:00"*.

### Workflow mistakes

- **Routing in LLM prompts.** "If temp > 70, transfer to hot_handler" works most of the time. Use a function-node router instead — Python `if/elif`, deterministic, free.
- **Wrapping pure Python in an agent.** If your fetch doesn't need reasoning, don't make it an `LlmAgent` with a tool. Just use a function node. Saves an LLM call.

### Collab mistakes

- **Mode confusion.** `mode="chat"` doesn't auto-return. Use `mode="task"` for bounded work or `mode="single_turn"` for transforms. Only `single_turn` supports parallel execution under a coordinator.
- **Coordinator with `mode=` set.** The docs explicitly warn: *"Do not configure a root agent with the `mode` setting."* Mode is for subagents.

### Dynamic mistakes

- **Missing `rerun_on_resume=True`.** `ctx.run_node` requires the calling node to have it. `parallel_worker=True` does NOT auto-set this. Must pass both: `@node(parallel_worker=True, rerun_on_resume=True)`.
- **Function parameter naming.** Default `parameter_binding='state'` looks up params from `ctx.state`. If your function takes `runner_spec` as a param, the framework will try to find `ctx.state["runner_spec"]` (not what you want). Name your param `node_input` to get the actual input.
- **No depth guard on recursion.** A `@node(parallel_worker=True)` that recursively spawns can explode if the LLM always says `needs_deeper=True`. Pass a `depth` field through node_input and check `depth < MAX_DEPTH` before spawning.

### General mistakes

- **`state_delta` not reaching the first node.** Passing initial state via `runner.run_async(state_delta={"k": "v"})` doesn't reliably populate `ctx.state` for the first node. Pass data via `new_message` (JSON-encoded Content) instead.
- **Forgetting to restart the server after code changes.** ADK doesn't hot-reload. Stop and restart your server (or `uv run python server.py`) after Python edits.

### Demo / observability mistakes

- **No tracing during development.** If your workflow does anything unexpected, look at the raw `runner.run_async` event stream. The path `event.node_info.path` tells you which node fired, and `event.content.parts` shows function calls and text outputs.
- **Mixing function-node `event.output` with agent `event.content`.** Function nodes put structured data in `event.output`. LLM agents put it in `event.content.parts[0].text` (as JSON string). When building SSE bridges, you need a helper that handles both — see `_event_output()` in `server.py`.

---

## Where to go from here

- **Run the demo** — `uv run python server.py` then play with all three modes (see [README](../README.md))
- **Read the source** — `workflows/strategy_graph.py` is ~200 lines and covers everything new in Pillar 1
- **Try modifying** — change a strategy agent's instruction; add a 4th weather scenario; swap models; whatever
- **Build your own** — pick a problem in your work that matches one of the pillar shapes
- **Reference docs** — official ADK 2.0 docs at <https://adk.dev/2.0/> + source at <https://github.com/google/adk-python>

For more depth on specific topics in this repo:

- [docs/ADK_2_PILLARS_DECISION_TREE.md](ADK_2_PILLARS_DECISION_TREE.md) — when-to-use-which with worked examples
- [docs/COLLABORATION_MODES.md](COLLABORATION_MODES.md) — chat/task/single_turn deep dive
- [docs/ADK_1X_REWRITE_ANALYSIS.md](ADK_1X_REWRITE_ANALYSIS.md) — head-to-head: this demo in 1.x vs 2.0
- [docs/BUILD_PLAN.md](BUILD_PLAN.md) — the original plan that produced this repo
- [VIDEO_SCRIPT.md](../VIDEO_SCRIPT.md) — verbatim 20-min talk script
- [CHANGELOG.md](../CHANGELOG.md) — what changed when, with WHY notes
