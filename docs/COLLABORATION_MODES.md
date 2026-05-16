# Collaborative Agent Teams: Modes Investigation

ADK 2.0 introduces a `mode` setting for subagents under a coordinator agent. This doc covers what each mode does, when to use which, and concrete examples.

**Docs source:** [adk.dev/workflows/collaboration/](https://adk.dev/workflows/collaboration/) ([docs/workflows/collaboration.md](https://github.com/google/adk-docs/blob/main/docs/workflows/collaboration.md) in the adk-docs repo)

---

## The conceptual model

A **coordinator agent** declares `sub_agents=[...]`. Each subagent has a `mode`. The framework auto-injects tools onto the coordinator named `request_task_<subagent_name>` — one per subagent — that the coordinator can call to delegate work.

When the subagent finishes, control returns to the coordinator either automatically (for `task` and `single_turn`) or manually via `transfer_to_agent` (for `chat`).

The coordinator itself does NOT have a `mode` set. Modes are subagent-only. The docs explicitly warn: "Do not configure a root agent with the `mode` setting."

---

## The three modes

### `chat` — full conversation (default)

The subagent takes over the conversation with the user fully. It can ask questions, get answers, follow up, etc. It does NOT auto-return — the coordinator only gets control back when the subagent explicitly calls `transfer_to_agent('<coordinator_name>')`.

**This is the 1.x default behavior, preserved for back-compat.**

**Best for:** subagents that need to drive their own long-running conversation with the user — guided onboarding flows, multi-step interviews, branching dialogue trees.

**Not great for:** bounded tasks. You have to manually wire the return-to-coordinator, and the LLM might forget.

**Example:** a `runner_onboarding` chat subagent that asks 10 questions over multiple turns to set up a runner's profile (age, weekly mileage, goal race, injury history, etc.), then transfers control back to the coordinator when done.

### `task` — bounded with clarifying questions

The subagent is given a task to complete. It may ask the user clarifying questions mid-task if it needs more information. When done, it calls `complete_task` and control returns to the coordinator automatically.

**Best for:** bounded work that *might* need user clarification but otherwise runs to completion.

**Not great for:** parallel execution (not supported in task mode). Nested subagents (task mode agents must be leaf agents).

**Auto-injected on the subagent:** `complete_task` tool — call this to signal done and return control to the coordinator.

**Example:** a `flight_booker` subagent that asks "what's your preferred departure window?" and "aisle or window?" before booking, then auto-returns with the booking confirmation.

### `single_turn` — pure transform, parallel-capable

The subagent gets an input, produces a structured output, and returns immediately. No user interaction. **Multiple `single_turn` subagents can run in parallel under the same coordinator.**

**Best for:** transforms (input → output) that don't need clarification. Especially good for parallel "ask N specialists for opinions" patterns.

**Not great for:** anything needing back-and-forth with the user.

**Auto-return mechanism:** built in — the subagent returns its result automatically when the LLM call completes.

**Example:** a `pace_calculator` single-turn subagent that takes target finish time + course profile and returns a per-mile pace plan, with no user interaction.

---

## Comparison table (from docs, verbatim)

| Topic | `chat` (default) | `task` | `single_turn` |
|---|---|---|---|
| Human in the Loop | Full interaction | Clarifications only | Disallowed |
| User interaction | User chats freely with agent | Agent asks questions as needed | No user interaction |
| Control flow | Agent controls until manual handoff | Agent controls until task complete | Returns immediately after task |
| Parallel execution | Not supported | Not supported | **Multiple tasks can run in parallel** |
| Return to parent | Manual (via `transfer_to_agent`) | Automatic (via `complete_task`) | Automatic (with result) |

---

## Auto-injected tools

The framework injects tools depending on mode and context:

| Tool | Auto-injected onto | Purpose |
|---|---|---|
| `request_task_<subagent_name>` | The coordinator | Delegate work to a specific subagent |
| `complete_task` | `task`-mode subagents | Signal task done, return control to coordinator |
| `transfer_to_agent` | `chat`-mode subagents (and 1.x style agents) | Manual handoff to another named agent |

`single_turn` subagents don't get an auto-injected return mechanism — they return implicitly when their LLM call completes.

---

## Agent context isolation

Each `task` or `single_turn` subagent runs in its own **isolated session branch**. This means:

- When multiple `single_turn` subagents run in parallel, **none of them can see what their peers are doing**. Each only sees events from its own branch.
- After all branches complete, the coordinator receives the collected results and proceeds.

This is the same model as `JoinNode` in graph workflows — parallel branches don't share state during execution; they merge at the join point.

**Practical implication:** if you need parallel subagents to coordinate with each other, you can't via collaborative agents. You'd need to either:
- Run them sequentially (no parallelism)
- Use a graph workflow with explicit state passing
- Use a dynamic workflow with shared state via `Context`

---

## When to use which mode — practical guide

### Use `single_turn` when:
- The subagent is a stateless transform (input → output)
- You want to run multiple subagents in parallel
- The work is bounded and doesn't need any human input
- You want the absolute fastest path through the subagent

**Marathon-themed example:** `pace_calculator(target_finish, course)` → returns `PacePlan`. Pure math + slight LLM reasoning. No clarifications needed.

### Use `task` when:
- The subagent has a bounded task to complete
- It might need to ask the user clarifying questions to do its job
- You want automatic return-to-coordinator without manually writing the handoff
- The subagent doesn't have its own sub-sub-agents (task mode requires leaf agents)

**Marathon-themed example:** `gear_advisor` — needs to ask "what shoe brand?" and "weather sensitivity to cold?" before recommending. Returns gear list, auto-back to coordinator.

### Use `chat` when:
- The subagent is driving a multi-turn user conversation that the coordinator shouldn't see
- You're preserving 1.x behavior (chat is the legacy default)
- You explicitly want manual handoff control via `transfer_to_agent`

**Marathon-themed example:** `runner_onboarding` — asks 10+ questions over a long back-and-forth to build a complete athlete profile. Doesn't need to return to coordinator until the entire onboarding is done.

---

## Workflow node vs. transferee — control flow nuance

The same `task` or `single_turn` agent can be reused in two completely different contexts without modification:

### As a workflow graph node

When you place a task/single_turn agent inside a `Workflow(edges=[...])`, `SequentialAgent`, or `ParallelAgent`:
- The agent executes its task
- When done (via `complete_task` for task mode, or implicit for single_turn), **control automatically advances to the next node in the graph**

### As a transferee from an `LlmAgent` (the collaborative pattern)

When a parent `LlmAgent` delegates to a task agent via `request_task_*`:
- The task agent executes
- When it calls `complete_task` (or returns, for single_turn), **control automatically returns to the calling coordinator** that initiated the transfer

The runtime determines the right control flow based on how the agent was invoked. Same agent definition, different orchestrator, correct behavior in both cases.

---

## Known limitations (documented)

- **Task mode agents must be leaf agents.** They cannot have their own `sub_agents`. If you need nested delegation, use a workflow or another coordinator.
- **`chat` and `task` modes do not support parallel execution.** Only `single_turn` agents can run concurrently under a coordinator.
- **Parallel `single_turn` subagents cannot communicate during execution.** Each runs in its own isolated session branch; results merge only at the parent.

---

## Example: a coherent collaborative team

A `marathon_prep_concierge` coordinator delegates to:

- `runner_profile_builder` (`chat` mode) — drives a long onboarding conversation when a new user arrives. 10+ questions over multiple turns. Calls `transfer_to_agent('marathon_prep_concierge')` when done.
- `gear_advisor` (`task` mode) — asks the user 2-3 clarifying questions (preferred shoe brand, weather sensitivity), then auto-returns with gear recommendation.
- `nutrition_planner` (`task` mode) — asks about dietary restrictions and GI tolerance, returns fueling schedule, auto-returns.
- `pace_calculator` (`single_turn` mode) — given a target finish time and course profile, returns a structured pace plan. No user interaction. Pure transform.
- `medical_risk_screener` (`single_turn` mode) — given runner profile + planned strategy, returns a risk assessment. Pure analytical task.

The coordinator routes user requests to the right subagent based on what the user asked for. Multiple `single_turn` subagents (pace + risk) can run in parallel when the coordinator needs both at once. Long onboarding stays inside `runner_profile_builder` until complete. Bounded clarifying questions stay inside `gear_advisor` or `nutrition_planner`, automatically returning when done.

---

## How collaboration relates to graph workflows

These are not exclusive choices. A graph workflow node can be:
- A `single_turn` Agent (your current marathon planner uses this for the strategy agents)
- A whole nested `Workflow`
- An entire collaborative team — a coordinator with `sub_agents` — wrapped as a single node

Conversely, a coordinator's subagent can be a graph workflow if you want the subagent's internal logic to be structured.

The decision boils down to:
- **Graph workflow** when you can pre-determine the orchestration shape
- **Collaborative coordinator** when an LLM should decide who handles what at runtime
- **Nested combinations** when you want both — structure at the outer layer, LLM judgment at an inner layer (or vice versa)

See `ADK_2_PILLARS_DECISION_TREE.md` for the full decision tree.
