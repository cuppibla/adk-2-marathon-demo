"""CLI verification for Phase 1: race_concierge dispatches to the right specialist subsets.

Tests several questions and prints which specialists the coordinator invoked
plus the synthesized answer. Verifies that different questions invoke
different subsets (1, 3, 6) and that parallel calls happen in single turns.
"""
import asyncio
import json
import os
import time

from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as gtypes

from workflows.concierge import race_concierge
from workflows.shared import RaceStrategy, BundledRunData, WeatherData, CourseData, FitnessData

load_dotenv()


# A canned "Mode 1 output" — strategy + data the user would have from Pillar 1
SAMPLE_STRATEGY = RaceStrategy(
    target_finish="3:25:00",
    pacing_advice="Start at 8:00/mile and lock in by mile 5 to manage 78°F heat.",
    fueling_plan="Gel every 4 miles, electrolytes every 2 miles, extra salt at mile 13.",
    gear="Singlet, white cap, sunglasses, ice bandana at aid stations.",
    key_warning="78°F + headwind miles 17-21 creates high heat stroke risk.",
)
SAMPLE_DATA = BundledRunData(
    fetch_weather=WeatherData(temp_f=78, wind_mph=12, wind_direction="headwind",
                              humidity_pct=70, conditions="sunny"),
    analyze_course=CourseData(name="Boston Marathon", distance_mi=26.2,
                              total_elevation_gain_ft=815, hardest_mile=20,
                              hardest_mile_grade_pct=4.5),
    pull_fitness=FitnessData(avg_pace_per_mile_sec=450,
                             longest_recent_run_mi=22, weekly_mileage_mi=55),
)


def _make_user_msg(question: str) -> gtypes.Content:
    """Bundle the question + strategy + data into the user message."""
    body = (
        f"QUESTION: {question}\n\n"
        f"CURRENT STRATEGY (JSON):\n{SAMPLE_STRATEGY.model_dump_json(indent=2)}\n\n"
        f"RUNNER DATA (JSON):\n{SAMPLE_DATA.model_dump_json(indent=2)}\n"
    )
    return gtypes.Content(role="user", parts=[gtypes.Part(text=body)])


async def run_question(question: str) -> None:
    print(f"\n{'='*70}\n  QUESTION: {question!r}\n{'='*70}")
    rs = InMemorySessionService()
    runner = Runner(
        node=race_concierge,
        app_name="concierge_demo",
        session_service=rs,
        auto_create_session=True,
    )
    t0 = time.perf_counter()
    dispatched: list[str] = []
    responses: dict[str, dict] = {}
    final_text: str | None = None

    async for ev in runner.run_async(
        user_id="u",
        session_id=f"s_{hash(question)}",
        new_message=_make_user_msg(question),
    ):
        if not ev.content or not ev.content.parts:
            continue
        for p in ev.content.parts:
            fc = getattr(p, "function_call", None)
            fr = getattr(p, "function_response", None)
            text = getattr(p, "text", None)

            if fc and ev.author == "race_concierge":
                dispatched.append(fc.name)
                elapsed = time.perf_counter() - t0
                print(f"  [t={elapsed:.2f}s] DISPATCH → {fc.name}")
            elif text and ev.author != "race_concierge":
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = {"answer": text[:200]}
                responses[ev.author] = payload
                elapsed = time.perf_counter() - t0
                print(f"  [t={elapsed:.2f}s] RESPONSE from {ev.author}: "
                      f"concern={payload.get('concern_level', '?')} | "
                      f"{payload.get('recommendation', payload.get('answer', ''))[:80]}")
            elif text and ev.author == "race_concierge":
                final_text = text

    total = time.perf_counter() - t0
    print(f"\n  Dispatched: {dispatched}")
    print(f"  Total time: {total:.2f}s")
    if final_text:
        print(f"\n  SYNTHESIZED ANSWER:\n  {final_text}")


async def main():
    questions = [
        "My left knee is twinging at mile 18, is it safe to keep going?",
        "What about my fueling plan?",
        "Should I race today?",
        "Anything I should worry about overall?",
    ]
    for q in questions:
        await run_question(q)


if __name__ == "__main__":
    asyncio.run(main())
