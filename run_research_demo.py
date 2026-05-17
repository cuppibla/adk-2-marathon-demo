"""CLI verification for Phase 4: deep_research_workflow decomposes, fans out, synthesizes.

Tests the deep research pattern end-to-end with one preset query, verifying:
- Decomposer produces 3-7 sub-questions
- Each is researched in parallel
- Some recursively spawn deeper sub-questions
- Final synthesizer aggregates into a briefing
"""
import asyncio
import json
import time

from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as gtypes

from workflows.deep_research import deep_research_workflow

load_dotenv()


PRESETS = {
    "boston": "Tell me everything I should know about racing the Boston Marathon — course, weather history, common pitfalls, pacing strategy, and what to wear.",
    "heat":   "What do I need to know about racing a marathon in hot conditions (above 78°F)? Cover pacing, fueling, gear, and medical risks.",
    "recovery": "I just finished my first marathon. Give me a comprehensive recovery plan for the next 4 weeks.",
}


async def run_research(label: str, query: str) -> None:
    print(f"\n{'=' * 70}\n  PRESET: {label}\n  QUERY: {query}\n{'=' * 70}")
    rs = InMemorySessionService()
    runner = Runner(
        node=deep_research_workflow,
        app_name="research_app",
        session_service=rs,
        auto_create_session=True,
    )

    msg = gtypes.Content(role="user", parts=[gtypes.Part(text=query)])
    t0 = time.perf_counter()
    final_output = None
    research_node_count = 0

    async for event in runner.run_async(
        user_id="researcher",
        session_id=f"research_{label}_{int(time.time())}",
        new_message=msg,
    ):
        out = event.output
        if isinstance(out, dict) and "briefing" in out:
            final_output = out
        elif isinstance(out, dict) and "question" in out and "children" in out:
            research_node_count += 1
        elif isinstance(out, list) and out and isinstance(out[0], dict) and "question" in out[0]:
            # decompose output — list of question specs
            pass

    total = time.perf_counter() - t0
    print(f"\n  Total wall time: {total:.2f}s")
    print(f"  Research node events seen: {research_node_count}")

    if final_output:
        briefing = final_output["briefing"]
        tree = final_output["research_tree"]
        top_count = len(tree)
        deeper_count = sum(len(t.get("children", [])) for t in tree)
        print(f"  Tree shape: {top_count} top-level + {deeper_count} recursive children")
        print(f"\n  HEADLINE: {briefing['headline']}")
        print(f"\n  SECTIONS:")
        for i, s in enumerate(briefing.get("sections", []), 1):
            print(f"    {i}. {s[:200]}")
        print(f"\n  KEY WARNINGS:")
        for w in briefing.get("key_warnings", []):
            print(f"    ⚠ {w}")
        print(f"\n  SUMMARY: {briefing['summary'][:300]}")


async def main():
    import sys
    presets_to_run = sys.argv[1:] or ["boston"]
    for label in presets_to_run:
        if label not in PRESETS:
            print(f"Unknown preset {label!r}. Available: {list(PRESETS)}")
            continue
        await run_research(label, PRESETS[label])


if __name__ == "__main__":
    asyncio.run(main())
