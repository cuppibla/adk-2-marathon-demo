# ADK 2.0: Three Pillars + Decision Tree

ADK 2.0 introduces three distinct ways to orchestrate agents. They overlap, but each is the right tool for a different shape of problem. This doc covers all three, gives a reference for every node type, and provides a decision tree the audience can take home.

---

## The three pillars at a glance

| Pillar | Best for | Shape of problem |
|---|---|---|
| **Graph workflows** | Structured, declarative orchestration with known steps | "I can draw the diagram up front" |
| **Collaborative agents** | LLM-driven delegation between specialized agents | "I want the coordinator to *decide* who handles it" |
| **Dynamic workflows** | Code-driven workflows with loops, recursion, or runtime-sized fan-out | "The structure depends on data I don't have yet" |

You can mix and match. A graph workflow can include a node that internally uses collaborative agents. A dynamic workflow can call out to other graph workflows. They are layers, not exclusive choices.

---

## Pillar 1 — Graph workflows

Declarative orchestration. You define nodes and edges; the framework executes the graph.

### `Workflow` — the graph container

The thing you build. Takes a name and an `edges` array. The grammar of the edges array is the entire API surface for assembling graphs:

- **Sequence:** `(START, node_a, node_b)` — run a, then b
- **Fan-out (parallel):** a nested tuple inside a sequence — `(START, (node_a, node_b, node_c), join_node, next_node)` — runs the inner three in parallel before continuing
- **Conditional routing:** `(router_fn, {"X": node_x, "Y": node_y})` — branches based on router's emitted `route=` value

**Workflows can be nodes in other workflows.** Use them to compose. A sub-workflow used as a node runs its own internal graph, emits its final output, and the parent's next node receives it.

**When to reach for it:** the structure of the work is known up front. You can draw the diagram. Routing decisions can be expressed as code or as deterministic rules.

**Limitations:** Doesn't support Live Streaming or some third-party integrations in 2.0 beta.

### `FunctionNode` — raw Python as a node

A regular Python function (sync or async) that takes a `node_input` and returns or yields `Event(output=...)`. Two ways to wire it:

- **Implicit** — drop the bare function into the `edges` array; the framework auto-wraps it
- **Explicit** — wrap it as `FunctionNode(my_fn, name="...", rerun_on_resume=True)` if you want to override the name or opt into resume behavior

**When to reach for it:** the step doesn't need a language model. API calls, deterministic math, data transforms, side effects (database writes, calendar inserts), validation, routing decisions, scheduling, sending notifications.

**Critical rule:** each node may emit only **one** `Event(output=...)` per execution. Multiple `output` yields will error at runtime. You CAN yield multiple `message` or `state` events.

**Examples:**
- `fetch_strava_history(athlete_id)` — REST call, returns recent runs
- `compute_taper_schedule(race_date, weekly_mileage)` — math only
- `parse_gpx_course(file)` — file parsing
- `notify_coach(strategy)` — fires a Slack message, returns confirmation
- `validate_runner_age(profile)` — boolean check, raises if outside 18–80

### `JoinNode` — parallel fan-in

Built-in node that waits for all its upstream nodes to complete, then emits their outputs as a **dict keyed by upstream node names**.

If upstream nodes are `fetch_weather`, `analyze_course`, `pull_fitness`, the next node receives `{"fetch_weather": {...}, "analyze_course": {...}, "pull_fitness": {...}}`.

**When to reach for it:** you fan out N independent tasks and need to gather them before the next step. The downstream node typically expects the bundle as a typed payload (use `input_schema` on the next Agent).

**Limitation:** if any upstream branch fails to emit an Event, the join blocks indefinitely. Always ensure upstream nodes emit *something*, even in error paths.

**Examples:**
- Three weather provider APIs in parallel → join → pick the freshest
- Five "what could go wrong" critic agents in parallel → join → summarize
- Six athlete history queries (Strava, Garmin, Apple Health, coach notes, manual log, race history) → join → synthesize

### `Agent` — the LLM node (also the coordinator)

The same `Agent` class plays two roles in 2.0:

**Role 1: Leaf node in a graph workflow.** Configure with `mode="single_turn"`, `input_schema`, `output_schema`, and an instruction. Fires once, returns structured output, control advances to the next edge.

**Role 2: Coordinator with subagents.** Configure with `sub_agents=[...]`, no `mode` on the coordinator itself. The framework auto-injects `request_task_<subagent_name>` tools that the coordinator can call to delegate. (See `COLLABORATION_MODES.md` for full coverage.)

**When to reach for it:** the step needs actual language reasoning — writing, classifying nuance, summarizing, multi-step planning.

**Critical rule (graph node use):** don't set `mode="chat"` on a node in a workflow. The chat mode is meant for coordinator-attached subagents. The docs explicitly say "do not configure a root agent with the `mode` setting."

### `RequestInput` — human-in-the-loop pause

Yield it from inside any node. The workflow pauses until the system provides a response from the user. Supports `message` (prompt the user sees), `payload` (structured data alongside), `response_schema` (validates the user's response).

**When to reach for it:** approval gates. Missing data. Decision confirmations.

**Critical limitation:** `response_schema` does NOT automatically coerce free-text input into the schema. The user must submit data in the right shape, or you need a downstream `Agent` to coerce free text.

**Examples:**
- "Approve this strategy?" — gates calendar export
- "Tell me about your recent injuries (free text)" — then an LLM-coercing Agent normalizes it
- "Pick your shoe model" — payload contains a list of detected shoes from a previous Garmin query

### Router (a pattern, not a class)

A regular function node that yields `Event(output=data, route="LABEL")`. The label matches against the dict in the next edge: `(router_fn, {"LABEL_A": node_a, "LABEL_B": node_b})`.

A router can yield **multiple** route Events to trigger multiple downstream branches simultaneously — useful when conditions overlap (e.g., a strategy that's both hot AND humid).

**When to reach for it:** branching is a function of data, not LLM judgment. The marathon planner uses this for temperature buckets.

**Examples:**
- `route_by_injury_status` → `INJURED` / `RECOVERING` / `HEALTHY`
- `route_by_race_distance` → `5K` / `HALF` / `MARATHON` / `ULTRA`
- `route_by_terrain` → `ROAD` / `TRAIL` / `MIXED`

### Things in the workflow API that aren't worth using directly

- `Node` / `BaseNode` (parent class) — internal. Don't subclass directly. Use `FunctionNode` or `@node`.
- `Edge` — there isn't actually a user-facing `Edge` class. Edges are tuples in `Workflow(edges=...)`.

---

## Pillar 2 — Collaborative agents

LLM-driven delegation. A coordinator agent has `sub_agents=[...]` and decides at runtime which subagent should handle the user's input.

Covered in depth in `COLLABORATION_MODES.md`. Summary here:

- A coordinator `Agent` declares `sub_agents=[...]`
- Each subagent has a `mode`: `chat` (default), `task`, or `single_turn`
- The framework auto-injects `request_task_<subagent_name>` tools on the coordinator
- The coordinator's job is to read user input, decide which subagent should handle it, and call the appropriate `request_task_*` tool
- Control returns to the coordinator automatically for `task` and `single_turn`, manually for `chat` (via `transfer_to_agent`)

**When to reach for it:** the routing decision is itself something the LLM should reason about (not a simple `if/else`), and you want clean separation between specialists.

---

## Pillar 3 — Dynamic workflows

Code-driven orchestration. Use when the graph topology isn't known up front.

### `@node` decorator

Marks an async function as a node. Inside the body you can:
- `await ctx.run_node(other_node, input)` to invoke other nodes by reference
- Use `asyncio.gather(...)` to fan out
- Use `while` / `for` over runtime-sized lists
- Recursively call nodes

**When to reach for it:**
- The graph topology depends on data: "fan out one task per uploaded training file, but I don't know how many files there'll be"
- Recursive workflows: "keep refining the strategy until the critic agent approves"
- Conditional loops that can't be expressed as a static graph

**Bonus:** dynamic workflows get automatic per-node checkpointing. They're **resumable** — restart skips already-completed nodes.

**Examples:**
- "Analyze every PR comment on this branch in parallel, then summarize" (count of PRs is unknown)
- "Generate draft strategy, run it past N reviewers (configurable), gather feedback, regenerate, repeat until all approve"
- "Process each row in this CSV with this pipeline, gather errors, retry failures with backoff"

---

## Decision tree — which pillar do I use?

Ask these questions, top to bottom. First "yes" wins.

```
Is the user-facing interaction a free-form conversation?
  └─> YES → Single LlmAgent (or chat-mode coordinator + collaborative agents
            if you have specialized subagents you want to delegate to)
  └─> NO ↓

Is the structure of the workflow known up front and expressible as a static diagram?
  └─> YES → Graph workflow
  └─> NO ↓

Does the orchestration need loops, recursion, or runtime-sized fan-out?
  └─> YES → Dynamic workflow (@node)
  └─> NO ↓

Should an LLM coordinator decide which specialist to invoke (not deterministic routing)?
  └─> YES → Collaborative agents (coordinator + sub_agents with modes)
  └─> NO  → Single LlmAgent with tools (you're over-engineering)
```

### Worked examples — applying the tree

**"Build me a marathon race day strategy from weather + course + fitness"**
- Free-form chat? No.
- Static structure? Yes — three fetches, a router, three strategies.
- → **Graph workflow.** This is your current marathon planner.

**"Help me chat about my training plan"**
- Free-form chat? Yes.
- → **Single LlmAgent** with a coaching system prompt and a few tools. Or, if you want specialists (gear, nutrition, pacing), a **chat-mode coordinator with collaborative subagents.**

**"Critique my strategy from 5 different angles (medical, gear, weather, pacing, logistics) and summarize concerns"**
- Free-form chat? No.
- Static structure? Yes — 5 critics, then a summarizer.
- → **Graph workflow** with 5 parallel single-turn agents → JoinNode → summarizer agent. OR — equally valid — **collaborative coordinator** with 5 single-turn subagents. The graph is more visual; the collab is more "agent feels."

**"Process every training file in this folder and find the runner's optimal pace"**
- Free-form chat? No.
- Static structure? No — folder size is unknown.
- Loops / runtime fan-out? Yes.
- → **Dynamic workflow** with `@node` and `asyncio.gather` over the file list.

**"Iteratively improve a draft strategy until a critic agent approves"**
- Free-form chat? No.
- Static structure? No — loop count is unknown.
- Loops? Yes.
- → **Dynamic workflow** with a `while` loop and recursive node calls.

**"Triage a customer support ticket — figure out if it's billing, technical, or shipping, then escalate to the right human team"**
- Free-form chat? Partial — could be a back-and-forth.
- Could the routing be deterministic? Maybe, with keyword rules, but LLM classification is more robust.
- → **Collaborative agents** with a coordinator that delegates to billing/technical/shipping specialists. Or — if classification is reliable enough — a graph workflow with a classifier-router node and three downstream agents.

**"Run a chatbot for my product, with the ability to call any of 50 APIs"**
- Free-form chat? Yes.
- → **Single LlmAgent with tools** for the chat. If you want specialists per API category, layer a collaborative coordinator on top.

---

## Decision-tree wall-poster version (one-liner each)

- **Free-form chat?** → Single LlmAgent (or chat coordinator + collab subagents)
- **Known structure?** → Graph workflow
- **Loops / runtime fan-out?** → Dynamic workflow
- **LLM should route?** → Collaborative agents
- **Otherwise?** → Single LlmAgent — don't over-engineer

---

## Common pitfalls

- **Reaching for graph workflows when the structure isn't actually known.** If you find yourself adding `if/else` inside function nodes to handle "what if the user said X instead of Y" — that's a sign the workflow is really conversational, not structured. Switch to a collaborative or single LlmAgent.
- **Reaching for collaborative agents when routing is deterministic.** If your coordinator's job is "check the temperature and pick a handler," that's a router, not a coordinator. Use a graph workflow with a router function — it's 10x cheaper and 100% reliable.
- **Reaching for dynamic workflows for static problems.** If you can write the graph as `edges=[...]` without any runtime info, do that. `@node` is for when you genuinely can't.
- **Mixing modes recklessly.** A `chat`-mode subagent under a coordinator never auto-returns — only `task` and `single_turn` do. If the user is "stuck" in a subagent, you probably wanted `task` mode, not `chat`.
