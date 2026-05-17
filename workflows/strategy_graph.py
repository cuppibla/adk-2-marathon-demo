"""Marathon race day strategy — Pillar 1: Graph workflow.

Topology:
    START ──► fetch_weather ──┐
    START ──► analyze_course ─┼─► JoinNode ─► router ──► hot_strategy_agent
    START ──► pull_fitness ───┘                      ──► normal_strategy_agent
                                                     ──► cold_strategy_agent

Function nodes are pure Python (no LLM). Strategy nodes are gemini-flash agents
configured as single_turn with structured output.
"""
from __future__ import annotations

import asyncio

from dotenv import load_dotenv

from google.adk import Agent, Event, Workflow
from google.adk.workflow import JoinNode, START

from workflows.shared import BundledRunData, RaceStrategy, scenario, slow_mo

load_dotenv()  # pulls GOOGLE_API_KEY / GEMINI_API_KEY from .env

MODEL = "gemini-flash-latest"


# ─── Fetch nodes (parallel, simulated latency) ────────────────────────────────

async def fetch_weather(node_input):
    await asyncio.sleep(1.5 * slow_mo())
    return Event(output=scenario()["weather"].model_dump())


async def analyze_course(node_input):
    await asyncio.sleep(2.0 * slow_mo())
    return Event(output=scenario()["course"].model_dump())


async def pull_fitness(node_input):
    await asyncio.sleep(1.0 * slow_mo())
    return Event(output=scenario()["fitness"].model_dump())


# ─── Join + router ────────────────────────────────────────────────────────────

join_inputs = JoinNode(name="join_inputs")


def route_by_weather(node_input):
    """Deterministic branch on temperature. node_input is the JoinNode payload,
    keyed by upstream function names: {'fetch_weather': {...}, 'analyze_course': {...}, ...}.
    """
    weather = node_input["fetch_weather"]
    temp = weather["temp_f"]
    if temp >= 70:
        route = "HOT"
    elif temp <= 40:
        route = "COLD"
    else:
        route = "NORMAL"

    print(f"  [router] temp={temp}°F → route={route}")
    return Event(output=node_input, route=route)


# ─── Strategy agents (LLM, single-turn) ───────────────────────────────────────

_STRATEGY_FORMAT = """
Use the BundledRunData input to produce a RaceStrategy:
- weather is at <BundledRunData.fetch_weather from fetch_weather>
- course is at <BundledRunData.analyze_course from analyze_course>
- fitness is at <BundledRunData.pull_fitness from pull_fitness>

Be specific and concrete. Reference actual numbers from the data (mile numbers,
temperatures, the runner's typical pace). Each field should be 1-2 short sentences.
"""

hot_strategy = Agent(
    name="hot_strategy",
    model=MODEL,
    mode="single_turn",
    input_schema=BundledRunData,
    output_schema=RaceStrategy,
    instruction=f"""You are a marathon coach planning a race in HOT conditions.
Heat is the primary risk — the runner needs to slow down, hydrate aggressively,
and dress to stay cool. Their goal time should be adjusted SLOWER than ideal.
{_STRATEGY_FORMAT}
""",
)

normal_strategy = Agent(
    name="normal_strategy",
    model=MODEL,
    mode="single_turn",
    input_schema=BundledRunData,
    output_schema=RaceStrategy,
    instruction=f"""You are a marathon coach planning a race in IDEAL conditions.
This is a PR-attempt day. Recommend even splits or a slight negative split.
The main risk is going out too fast on cool, fast-feeling pavement.
{_STRATEGY_FORMAT}
""",
)

cold_strategy = Agent(
    name="cold_strategy",
    model=MODEL,
    mode="single_turn",
    input_schema=BundledRunData,
    output_schema=RaceStrategy,
    instruction=f"""You are a marathon coach planning a race in COLD conditions.
The runner needs layered gear they can shed, a careful warm-up, and a fueling
plan that accounts for cold-suppressed thirst. Crosswinds matter — recommend
drafting strategy if winds are strong.
{_STRATEGY_FORMAT}
""",
)


# ─── Workflow ─────────────────────────────────────────────────────────────────

root_agent = Workflow(
    name="marathon_strategy",
    description="Race day strategy planner with parallel data gathering.",
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
