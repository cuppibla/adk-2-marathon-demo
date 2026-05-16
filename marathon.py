"""Marathon race day strategy workflow.

Graph:
    START ──► fetch_weather ──┐
    START ──► analyze_course ─┼─► JoinNode ─► router ──► hot_strategy_agent
    START ──► pull_fitness ───┘                      ──► normal_strategy_agent
                                                     ──► cold_strategy_agent

Function nodes are pure Python (no LLM). Strategy nodes are gemini-flash agents.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google.adk import Agent, Event, Workflow
from google.adk.workflow import JoinNode, START

load_dotenv()  # pulls GOOGLE_API_KEY / GEMINI_API_KEY from .env

MODEL = "gemini-flash-latest"


# ─── Schemas ──────────────────────────────────────────────────────────────────

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
    target_finish: str = Field(
        description="Clean finish time only, format H:MM:SS. Example: '3:30:00'. "
        "Do NOT include explanations, parentheticals, or extra commentary."
    )
    pacing_advice: str = Field(description="One concise sentence about race pacing strategy.")
    fueling_plan: str = Field(description="One concise sentence about hydration and nutrition.")
    gear: str = Field(description="One concise sentence about clothing and equipment.")
    key_warning: str = Field(description="One concise sentence flagging the biggest risk for this race.")


class BundledRunData(BaseModel):
    """Shape of the JoinNode payload — keys match the upstream function names."""
    fetch_weather: WeatherData
    analyze_course: CourseData
    pull_fitness: FitnessData


# ─── Canned scenarios ─────────────────────────────────────────────────────────

SCENARIOS: dict[str, dict[str, Any]] = {
    "HOT": {
        "weather": WeatherData(
            temp_f=78, wind_mph=12, wind_direction="headwind",
            humidity_pct=70, conditions="sunny",
        ),
        "course": CourseData(
            name="Boston Marathon", distance_mi=26.2,
            total_elevation_gain_ft=815, hardest_mile=20,
            hardest_mile_grade_pct=4.5,
        ),
        "fitness": FitnessData(
            avg_pace_per_mile_sec=450,  # 7:30
            longest_recent_run_mi=22, weekly_mileage_mi=55,
        ),
    },
    "NORMAL": {
        "weather": WeatherData(
            temp_f=58, wind_mph=4, wind_direction="calm",
            humidity_pct=55, conditions="overcast",
        ),
        "course": CourseData(
            name="Berlin Marathon", distance_mi=26.2,
            total_elevation_gain_ft=240, hardest_mile=0,
            hardest_mile_grade_pct=0.5,
        ),
        "fitness": FitnessData(
            avg_pace_per_mile_sec=420,  # 7:00
            longest_recent_run_mi=24, weekly_mileage_mi=65,
        ),
    },
    "COLD": {
        "weather": WeatherData(
            temp_f=35, wind_mph=15, wind_direction="crosswind",
            humidity_pct=65, conditions="cloudy",
        ),
        "course": CourseData(
            name="Chicago Marathon", distance_mi=26.2,
            total_elevation_gain_ft=140, hardest_mile=0,
            hardest_mile_grade_pct=0.3,
        ),
        "fitness": FitnessData(
            avg_pace_per_mile_sec=440,  # 7:20
            longest_recent_run_mi=22, weekly_mileage_mi=60,
        ),
    },
}


def _scenario() -> dict[str, Any]:
    name = os.environ.get("MARATHON_SCENARIO", "HOT").upper()
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario {name!r}; expected HOT/NORMAL/COLD")
    return SCENARIOS[name]


# ─── Fetch nodes (parallel, simulated latency) ────────────────────────────────

def _slow_mo() -> float:
    try:
        return float(os.environ.get("MARATHON_SLOW_MO", "1.0"))
    except ValueError:
        return 1.0


async def fetch_weather(node_input):
    await asyncio.sleep(1.5 * _slow_mo())
    return Event(output=_scenario()["weather"].model_dump())


async def analyze_course(node_input):
    await asyncio.sleep(2.0 * _slow_mo())
    return Event(output=_scenario()["course"].model_dump())


async def pull_fitness(node_input):
    await asyncio.sleep(1.0 * _slow_mo())
    return Event(output=_scenario()["fitness"].model_dump())


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
