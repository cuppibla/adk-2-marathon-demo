"""CLI verification for Phase 2: team_planner fans out N parallel per-runner workflows.

Tests two roster sizes (3 runners and 10 runners) to verify:
- Roster size is data-driven, not hardcoded
- All per-runner workflows run in parallel
- Each runner gets a personalized RaceStrategy from the LLM
- Wall time scales with the SLOWEST runner, not the sum
"""
import asyncio
import json
import time

from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as gtypes

from workflows.team_planner import team_workflow

load_dotenv()


# Sample roster: 3 runners across 3 different conditions
TEAM_ALPHA = [
    {"name": "Alice",   "scenario": "HOT"},
    {"name": "Bob",     "scenario": "NORMAL"},
    {"name": "Carol",   "scenario": "COLD"},
]

# Sample roster: 10 runners — Pillar 3's "scale" story
TEAM_OMEGA = [
    {"name": f"Runner-{i:02d}", "scenario": s}
    for i, s in enumerate([
        "HOT", "HOT", "HOT",
        "NORMAL", "NORMAL", "NORMAL", "NORMAL",
        "COLD", "COLD", "COLD",
    ], start=1)
]


async def run_team(label: str, roster: list[dict]) -> None:
    print(f"\n{'=' * 70}\n  {label}: {len(roster)} runners\n{'=' * 70}")
    rs = InMemorySessionService()
    runner = Runner(
        node=team_workflow,
        app_name="team_app",
        session_service=rs,
        auto_create_session=True,
    )

    t0 = time.perf_counter()
    runner_completions = {}
    final_summary = None

    roster_msg = gtypes.Content(
        role="user",
        parts=[gtypes.Part(text=json.dumps(roster))],
    )
    async for event in runner.run_async(
        user_id="coach",
        session_id=f"team_{label}_{int(time.time())}",
        new_message=roster_msg,
    ):
        out = event.output
        ts = time.perf_counter() - t0
        # Per-runner completion events come from plan_for_runner
        if isinstance(out, dict) and "runner_name" in out:
            runner_completions[out["runner_name"]] = ts
            scenario = out.get("scenario")
            strategy = out.get("strategy", {})
            target = strategy.get("target_finish", "?") if isinstance(strategy, dict) else "?"
            print(f"  [t={ts:5.2f}s] runner DONE: {out['runner_name']:12s} ({scenario:6s}) target={target}")
        # Team summary event from summarize_team
        elif isinstance(out, dict) and "count" in out and "plans" in out:
            final_summary = out
            print(f"  [t={ts:5.2f}s] team summary: {out['notes']}")

    total = time.perf_counter() - t0
    print(f"\n  Total wall time: {total:.2f}s")
    if runner_completions:
        slowest = max(runner_completions.values())
        sum_if_serial = sum(runner_completions.values())
        print(f"  Slowest runner finished at: {slowest:.2f}s")
        print(f"  Sum (if serial would be roughly): {sum_if_serial:.2f}s")
        print(f"  Speedup from parallel fan-out: {sum_if_serial / total:.1f}x")


async def main():
    await run_team("TEAM_ALPHA", TEAM_ALPHA)
    await run_team("TEAM_OMEGA", TEAM_OMEGA)


if __name__ == "__main__":
    asyncio.run(main())
