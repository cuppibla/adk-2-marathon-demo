"""Team race day planner — Pillar 3: Dynamic workflows.

A coach has a roster of N runners. Each runner needs a race day strategy.
The team can be 3 runners or 30 — size is unknown at design time.

This workflow uses ADK 2.0's `@node(parallel_worker=True)` primitive to fan
out one per-runner subworkflow per roster slot, executing them all in
parallel. The number of parallel branches is determined at runtime by the
roster size.

Topology:
    START ─► emit_roster ─► plan_for_runner (parallel × N) ─► summarize_team
                                  │  │  │
                                  │  │  └─ runner N → bundled + agent
                                  │  └─── runner 2 → bundled + agent
                                  └────── runner 1 → bundled + agent

What's uniquely ADK 2.0 about this:
- `ParallelAgent` in 1.x has a FIXED list of sub-agents at design time
- `LoopAgent` in 1.x loops one agent serially
- Only `@node(parallel_worker=True)` allows the parallel topology to be
  determined by the data shape at runtime.
"""
from __future__ import annotations

import asyncio
import json

from dotenv import load_dotenv

from google.adk import Event, Workflow
from google.adk.workflow import node, START

from workflows.shared import (
    BundledRunData,
    RaceStrategy,
    RunnerPlan,
    SCENARIOS,
    TeamSummary,
)
from workflows.strategy_graph import (
    cold_strategy,
    hot_strategy,
    normal_strategy,
    slow_mo,
)

load_dotenv()


# ─── Roster source ────────────────────────────────────────────────────────────

@node
async def emit_roster(ctx, node_input):
    """Parse the roster from the initial user message (JSON text) and emit it
    as a list so the downstream parallel_worker fans out one task per runner.

    Two input shapes are accepted:
    - state["roster"] = [...]                        — set via state_delta or pre-seeded
    - node_input is a Content with JSON-text         — passed as new_message
    """
    # Prefer state if present
    roster = ctx.state.get("roster") if hasattr(ctx, "state") else None
    if not roster:
        # Fall back to parsing the initial user message
        text = None
        if hasattr(node_input, "parts") and node_input.parts:
            text = getattr(node_input.parts[0], "text", None)
        elif isinstance(node_input, str):
            text = node_input
        if text:
            try:
                roster = json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Could not parse roster JSON from input: {e}")
    if not roster:
        raise ValueError(
            "No roster provided. Pass it as a JSON-encoded user message "
            "or pre-seed state with state['roster']."
        )
    yield Event(output=roster)


# ─── Per-runner subflow (parallel) ────────────────────────────────────────────

def _pick_strategy_agent(temp_f: float):
    """Match the temperature to the right strategy agent."""
    if temp_f >= 70:
        return hot_strategy
    if temp_f <= 40:
        return cold_strategy
    return normal_strategy


@node(parallel_worker=True, rerun_on_resume=True)
async def plan_for_runner(ctx, node_input):
    """One per-runner pipeline. ParallelWorker fans this out across the roster.

    `node_input` is ONE runner spec (dict with 'name' and 'scenario' keys).
    """
    name = node_input["name"]
    scenario_key = node_input["scenario"]

    if scenario_key not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario_key!r}")

    canned = SCENARIOS[scenario_key]

    # Simulate the data-gathering phase. For team mode we collapse the three
    # parallel fetches (weather/course/fitness) into a single synthetic
    # latency — Pillar 3's wow is the per-runner parallelism, not the
    # within-runner parallelism (that's Pillar 1's story).
    await asyncio.sleep(1.5 * slow_mo())

    bundled = BundledRunData(
        fetch_weather=canned["weather"],
        analyze_course=canned["course"],
        pull_fitness=canned["fitness"],
    )

    # Pick the right strategy agent based on weather, then invoke it
    # dynamically via ctx.run_node. The agent runs as a "child" of this
    # parallel-worker node — it's an LLM call.
    agent = _pick_strategy_agent(canned["weather"].temp_f)
    strategy_payload = await ctx.run_node(agent, node_input=bundled.model_dump())

    # ctx.run_node returns the agent's output — which for an LLM agent with
    # output_schema=RaceStrategy is the JSON string text. Parse it.
    strategy = _coerce_strategy(strategy_payload)

    plan = RunnerPlan(
        runner_name=name,
        scenario=scenario_key,
        bundled_data=bundled,
        strategy=strategy,
    )
    yield Event(output=plan.model_dump())


def _coerce_strategy(payload) -> RaceStrategy:
    """Normalize ctx.run_node's return value into a RaceStrategy.

    LLM agents return their structured output via the content channel. The
    exact shape depends on ADK's run_node wrapping. We accept either a dict
    (already JSON-decoded) or a string (JSON-encoded by the model).
    """
    if isinstance(payload, RaceStrategy):
        return payload
    if isinstance(payload, dict):
        return RaceStrategy.model_validate(payload)
    if isinstance(payload, str):
        return RaceStrategy.model_validate_json(payload)
    # Fall back: try to pull text out of a Content-like object
    if hasattr(payload, "parts") and payload.parts:
        text = getattr(payload.parts[0], "text", None)
        if text:
            return RaceStrategy.model_validate_json(text)
    raise ValueError(f"Could not coerce {type(payload).__name__} into RaceStrategy: {payload!r}")


# ─── Team summarizer ──────────────────────────────────────────────────────────

@node
async def summarize_team(node_input):
    """node_input is the list of RunnerPlan dicts from plan_for_runner."""
    plans = [RunnerPlan.model_validate(p) if isinstance(p, dict) else p for p in node_input]
    scenarios = [p.scenario for p in plans]
    unique_scenarios = sorted(set(scenarios))
    notes = (
        f"Generated {len(plans)} race day plans across the team. "
        f"Conditions span: {', '.join(unique_scenarios)}."
    )
    summary = TeamSummary(plans=plans, count=len(plans), notes=notes)
    yield Event(output=summary.model_dump())


# ─── Workflow ─────────────────────────────────────────────────────────────────

team_workflow = Workflow(
    name="team_planner",
    description="Plan race day strategies for an N-runner roster via dynamic parallel fan-out.",
    edges=[(START, emit_roster, plan_for_runner, summarize_team)],
)
