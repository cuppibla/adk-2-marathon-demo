"""Smoke test for Phase 4a: recursive ctx.run_node from inside parallel_worker.

The critical question: can a @node(parallel_worker=True) function call
itself recursively via ctx.run_node to spawn deeper children, gather their
results, and integrate them into its own output?

If yes → deep research pattern works, build it.
If no → need to find a different recursion mechanism.

This test simulates "decompose a number into smaller numbers" without any
LLM cost. No marathon logic, no Gemini calls — just pure async + delays.
"""
import asyncio
import time

from google.adk import Event, Runner, Workflow
from google.adk.workflow import node, START
from google.adk.sessions import InMemorySessionService


# Top-level fan-out: decompose a list of "topics"
@node
async def emit_initial_topics(ctx, node_input):
    """Top-level: produce a list of topics to research."""
    topics = ["topic_a", "topic_b", "topic_c"]
    yield Event(output=topics)


@node(parallel_worker=True, rerun_on_resume=True)
async def research_topic(ctx, node_input):
    """One topic. May recursively spawn sub-topics.

    Pattern: do a unit of work, decide if it needs deeper investigation,
    recursively call ctx.run_node(research_topic, [sub_a, sub_b]) to
    spawn children, await their results, return combined.
    """
    topic = node_input
    t_start = time.perf_counter()

    # Simulate base research
    await asyncio.sleep(0.5)

    # Decide whether to spawn children. For the test, topic_a and topic_b
    # each spawn 2 children; topic_c does not. The deeper levels do not
    # spawn further (to keep the tree finite without explicit depth gating).
    is_leaf = topic.startswith("leaf_") or topic == "topic_c"

    if not is_leaf:
        # Spawn 2 children — list goes into ctx.run_node, parallel_worker
        # fans them out.
        children_topics = [f"leaf_{topic}_x", f"leaf_{topic}_y"]
        print(f"  [{topic}] spawning children: {children_topics}")
        children_results = await ctx.run_node(
            research_topic,
            node_input=children_topics,
        )
        elapsed = time.perf_counter() - t_start
        result = {
            "topic": topic,
            "depth": 0,
            "elapsed": round(elapsed, 2),
            "summary": f"researched {topic} + recursively spawned",
            "children": children_results,
        }
    else:
        elapsed = time.perf_counter() - t_start
        result = {
            "topic": topic,
            "depth": 1 if topic.startswith("leaf_") else 0,
            "elapsed": round(elapsed, 2),
            "summary": f"researched {topic} (leaf)",
        }

    print(f"  [{topic}] done in {elapsed:.2f}s")
    yield Event(output=result)


@node
async def aggregate(node_input):
    """Receive the list of top-level results (each possibly containing children)."""
    print(f"\n  [aggregate] received {len(node_input)} top-level results")
    yield Event(output={"total": len(node_input), "tree": node_input})


test_workflow = Workflow(
    name="recursive_smoke",
    edges=[(START, emit_initial_topics, research_topic, aggregate)],
)


async def main():
    print("=" * 70)
    print("Phase 4a smoke test: recursive ctx.run_node from parallel_worker")
    print("=" * 70)
    print("Expected tree shape:")
    print("  topic_a (spawns 2 children)")
    print("  topic_b (spawns 2 children)")
    print("  topic_c (leaf, no spawn)")
    print("Expected total work units: 3 + 2 + 2 = 7")
    print("Expected wall time if parallel: ~1.0s (0.5 base + 0.5 children)")
    print()

    rs = InMemorySessionService()
    runner = Runner(
        node=test_workflow,
        app_name="smoke",
        session_service=rs,
        auto_create_session=True,
    )
    t0 = time.perf_counter()
    final_output = None
    async for event in runner.run_async(
        user_id="u", session_id="s", new_message=None,
    ):
        out = event.output
        ts = time.perf_counter() - t0
        if isinstance(out, dict) and "tree" in out:
            final_output = out
            print(f"\n  [t={ts:.2f}s] aggregate result: {out['total']} top-level items")

    total = time.perf_counter() - t0
    print(f"\nTotal wall time: {total:.2f}s")
    print()

    if final_output:
        print("Tree structure:")
        for item in final_output["tree"]:
            print(f"  - {item['topic']} (depth={item['depth']})")
            if "children" in item:
                for child in item["children"]:
                    print(f"      └─ {child['topic']} (depth={child['depth']})")
        # Verify counts
        top_count = len(final_output["tree"])
        child_count = sum(len(t.get("children", [])) for t in final_output["tree"])
        print(f"\nVerification: {top_count} top-level + {child_count} children = "
              f"{top_count + child_count} total work units")
        if top_count == 3 and child_count == 4:
            print("✓ RECURSION WORKS — Phase 4 is feasible.")
        else:
            print("✗ Unexpected tree shape — investigate before continuing.")


if __name__ == "__main__":
    asyncio.run(main())
