"""Run the marathon strategy workflow end-to-end and print every event."""
import asyncio
import os
import sys
import time

from google.adk import Runner
from google.adk.sessions import InMemorySessionService

from marathon import root_agent


async def run_scenario(scenario: str) -> None:
    os.environ["MARATHON_SCENARIO"] = scenario
    print(f"\n{'='*60}")
    print(f"  SCENARIO: {scenario}")
    print(f"{'='*60}")

    session_service = InMemorySessionService()
    runner = Runner(
        node=root_agent,
        app_name="marathon_app",
        session_service=session_service,
        auto_create_session=True,
    )

    t0 = time.perf_counter()
    async for event in runner.run_async(
        user_id="runner_user",
        session_id=f"session_{scenario}",
        new_message=None,
    ):
        elapsed = time.perf_counter() - t0
        out = event.output
        if isinstance(out, dict) and len(str(out)) > 120:
            out_str = f"<{type(out).__name__} with {len(out)} keys>"
        else:
            out_str = repr(out)
        print(f"  [t={elapsed:5.2f}s] {out_str}")

    total = time.perf_counter() - t0
    print(f"\n  Total wall time: {total:.2f}s")


async def main():
    scenarios = sys.argv[1:] or ["HOT", "NORMAL", "COLD"]
    for s in scenarios:
        await run_scenario(s.upper())


if __name__ == "__main__":
    asyncio.run(main())
