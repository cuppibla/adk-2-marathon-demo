"""ADK 1.x equivalent of Mode 1 (Graph Workflow — single runner race strategy).

This file shows what the 2.0 graph workflow in `workflows/strategy_graph.py` would
look like if built with ADK 1.x primitives (`LlmAgent`, `SequentialAgent`,
`ParallelAgent`).

NOT RUNNABLE in this project — this project depends on google-adk 2.0.0b1.
This file imports 1.x APIs for reference / video comparison only.
See ../README.md for context.

==============================================================================
2.0 EQUIVALENT: ../../workflows/strategy_graph.py
PROBLEM:        Three parallel data fetches → bundle → route on temperature → 1 strategy LLM call
==============================================================================
"""
from __future__ import annotations

# NOTE: These imports require ADK 1.x — they will fail in this 2.0 project.
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.tools import FunctionTool
from pydantic import BaseModel, Field


# ─── Pretend shared schemas (would normally import from workflows/shared) ─────

class WeatherData(BaseModel):
    temp_f: float
    wind_mph: float
    wind_direction: str
    humidity_pct: int
    conditions: str


class CourseData(BaseModel):
    name: str
    distance_mi: float
    total_elevation_gain_ft: int
    hardest_mile: int
    hardest_mile_grade_pct: float


class FitnessData(BaseModel):
    avg_pace_per_mile_sec: int
    longest_recent_run_mi: float
    weekly_mileage_mi: int


class RaceStrategy(BaseModel):
    target_finish: str = Field(description="Clean finish time only, H:MM:SS.")
    pacing_advice: str
    fueling_plan: str
    gear: str
    key_warning: str


# ─── Fetch functions (the same canned data as 2.0) ───────────────────────────

def get_weather() -> dict:
    """Pretend weather API call. Returns canned data."""
    return WeatherData(
        temp_f=78, wind_mph=12, wind_direction="headwind",
        humidity_pct=70, conditions="sunny",
    ).model_dump()


def get_course() -> dict:
    """Pretend course profile API call."""
    return CourseData(
        name="Boston Marathon", distance_mi=26.2,
        total_elevation_gain_ft=815, hardest_mile=20,
        hardest_mile_grade_pct=4.5,
    ).model_dump()


def get_fitness() -> dict:
    """Pretend Strava API call."""
    return FitnessData(
        avg_pace_per_mile_sec=450,
        longest_recent_run_mi=22, weekly_mileage_mi=55,
    ).model_dump()


# ─── PAIN POINT #1 — Wrapping pure-Python fetches in LlmAgents ───────────────
#
# In 1.x, `ParallelAgent` only orchestrates *agents*, not raw functions.
# To run three fetches in parallel, each fetch must be wrapped in an LlmAgent
# that calls the fetch as a tool. That adds 3 LLM calls just to dispatch tools
# that don't need any reasoning.
#
# In 2.0, function nodes go directly into the workflow graph — zero LLM calls
# for the fetches.

weather_agent = LlmAgent(
    name="weather_agent",
    model="gemini-flash-latest",
    instruction=(
        "Call the get_weather tool. Return the result verbatim. "
        "Do not add commentary, do not modify the output."
    ),
    tools=[FunctionTool(get_weather)],
    output_key="weather",  # Result lands in session.state["weather"]
)

course_agent = LlmAgent(
    name="course_agent",
    model="gemini-flash-latest",
    instruction=(
        "Call the get_course tool. Return the result verbatim. "
        "Do not add commentary, do not modify the output."
    ),
    tools=[FunctionTool(get_course)],
    output_key="course",
)

fitness_agent = LlmAgent(
    name="fitness_agent",
    model="gemini-flash-latest",
    instruction=(
        "Call the get_fitness tool. Return the result verbatim. "
        "Do not add commentary, do not modify the output."
    ),
    tools=[FunctionTool(get_fitness)],
    output_key="fitness",
)

# Three agents in parallel — three LLM calls just to fetch data.
gather_phase = ParallelAgent(
    name="gather_phase",
    sub_agents=[weather_agent, course_agent, fitness_agent],
)


# ─── PAIN POINT #2 — Routing in the prompt ───────────────────────────────────
#
# The strategist has to (a) read three pieces of state, (b) decide which
# weather bucket applies, AND (c) write the strategy. All in one prompt.
#
# The routing decision — "if temp >= 70, use hot-weather logic" — is LLM
# judgment, not Python. Usually correct, occasionally wrong on edge cases.
# In 2.0 this is a 4-line Python function that *cannot* be wrong.
#
# Also: outputs from ParallelAgent live in untyped session state. The
# strategist's prompt has to know the exact keys and trust the model
# reads them correctly. No typed handoff like 2.0's JoinNode.

strategist = LlmAgent(
    name="strategist",
    model="gemini-flash-latest",
    instruction="""You are a marathon race-day coach. You will produce a
RaceStrategy for the runner.

The runner's data is in session state:
- session.state["weather"]  — a WeatherData JSON object
- session.state["course"]   — a CourseData JSON object
- session.state["fitness"]  — a FitnessData JSON object

Read all three. Based on the temperature in weather.temp_f:

  - If temp_f >= 70, treat as HOT conditions:
      Slow the pace, emphasize hydration, recommend cooling gear.
      Goal time should be 15-25 seconds per mile slower than fitness pace.

  - If temp_f <= 40, treat as COLD conditions:
      Conservative early pacing to warm up, layered gear plan,
      drafting strategy if winds are strong.

  - Otherwise treat as NORMAL conditions:
      Even splits, PR-attempt territory, watch for going out too fast.

Output a RaceStrategy JSON with: target_finish, pacing_advice,
fueling_plan, gear, key_warning.

Reference specific numbers from the runner data — mile numbers,
temperatures, the runner's typical pace.
""",
    output_schema=RaceStrategy,
)


# ─── Root agent: sequential pipeline ─────────────────────────────────────────
#
# SequentialAgent runs gather_phase (which itself runs 3 agents in parallel)
# then runs strategist.

root_agent = SequentialAgent(
    name="marathon_planner_1x",
    sub_agents=[gather_phase, strategist],
)


# =============================================================================
# COMPARISON NOTES — Mode 1 (Graph workflow)
# =============================================================================
#
# LLM CALLS per request:
#   - weather_agent:   1 (just to call the get_weather tool)
#   - course_agent:    1 (just to call the get_course tool)
#   - fitness_agent:   1 (just to call the get_fitness tool)
#   - strategist:      1 (does the routing + strategy in one prompt)
#   - TOTAL: 4 LLM calls per request
#
# COMPARE: 2.0 equivalent in workflows/strategy_graph.py = 1 LLM call total
#
# LINES OF CODE (this file, excluding schemas and docstrings):
#   ~80 lines
#
# COMPARE: 2.0 equivalent edges definition = 8 lines
#
# WALL TIME (estimated, parallel fetches + strategist):
#   ~12-15 seconds (3 LLM calls for fetches, even in parallel, take ~3s each
#                   if the model is fast — then strategist adds 5-7s)
#
# COMPARE: 2.0 equivalent = ~7 seconds (no LLM calls for fetches)
#
# UNIQUE WEAKNESSES OF THIS 1.X APPROACH:
#   1. Three useless LLM calls just to dispatch tools that don't need reasoning
#   2. Routing decision is LLM judgment — not deterministic, hard to verify
#   3. Strategist must read untyped session state by key — no typed handoff
#   4. Adding a new weather bucket (e.g., HUMID) means editing the prompt,
#      not adding a graph edge — re-tuning required
#
# WHAT 2.0 GIVES YOU:
#   - Function nodes coexist with agent nodes as peers in `edges=[...]`
#   - Router is a 4-line Python function — deterministic, free, fast
#   - JoinNode bundles parallel outputs into a typed payload
#   - Adding a new weather bucket = 1 new agent + 1 new edge dict entry
# =============================================================================
