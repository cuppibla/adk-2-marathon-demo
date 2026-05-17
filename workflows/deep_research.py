"""Deep Research workflow — Pillar 3: Dynamic workflows.

A user asks an open-ended marathon question. The workflow:
1. **Decomposes** the question into N sub-research-questions (one LLM call)
2. **Researches** each sub-question in parallel via parallel_worker
3. **Recursively** spawns deeper questions when findings warrant it
   (variable tree depth, decided by the LLM at runtime)
4. **Synthesizes** all findings into a comprehensive briefing (one LLM call)

What's uniquely ADK 2.0 here:
- The tree's WIDTH is decided at runtime (decomposer picks 3-7 sub-questions)
- The tree's DEPTH is decided at runtime (each researcher decides to spawn)
- The recursive `ctx.run_node(research_topic, list)` from inside a
  parallel_worker is impossible to express cleanly in ADK 1.x — that
  requires bypassing the framework primitives and writing raw asyncio.

Topology:
    START ─► decompose ─► research_topic (parallel_worker, recursive) ─► synthesize
                                  │  │  │
                                  │  │  └─ research(q3) ──► (maybe spawn children)
                                  │  └─── research(q2) ──► (maybe spawn children)
                                  └────── research(q1) ──► (maybe spawn children)
"""
from __future__ import annotations

import json
from typing import Any

from dotenv import load_dotenv

from google.adk import Agent, Event, Workflow
from google.adk.workflow import START, node

from workflows.shared import (
    DecomposerOutput,
    DeepResearchBriefing,
    ResearchFinding,
)

load_dotenv()

MODEL = "gemini-flash-latest"

# Cap how deep the recursion can go. Pillar 3's wow is "depth is data-driven"
# but we still need a safety net.
MAX_DEPTH = 2


# ─── LLM agents (single-turn) ─────────────────────────────────────────────────

decompose_agent = Agent(
    name="decompose_agent",
    model=MODEL,
    mode="single_turn",
    output_schema=DecomposerOutput,
    instruction="""You are a research coordinator for marathon and endurance running questions.

Given a user's open-ended question, break it down into 3-7 specific, non-overlapping
sub-questions that, together, comprehensively answer the user's intent. Each sub-question
should be:

- SPECIFIC (not "tell me about Boston" but "what is the Boston course elevation profile?")
- INDEPENDENTLY RESEARCHABLE (each can be answered without depending on the others)
- COVERING A DISTINCT ANGLE (course, weather history, common mistakes, gear norms, etc.)

Be concise. Don't repeat sub-questions in different words.
""",
)


research_agent = Agent(
    name="research_agent",
    model=MODEL,
    mode="single_turn",
    output_schema=ResearchFinding,
    instruction="""You are a marathon research specialist with deep knowledge of running,
race conditions, and endurance physiology.

Given a single specific research question, produce a focused finding with:
- A concise 2-3 sentence summary
- 3-5 specific factual or actionable insights
- A judgment on whether deeper investigation is warranted

Set needs_deeper=True ONLY if your findings uncover a sub-topic that genuinely deserves
its own focused investigation (not just "this could be discussed more" — but a real
narrow technical question that emerged from your research). Provide 1-3 specific
deeper questions if so.

If needs_deeper is True, deeper_questions must be specific, well-formed questions
suitable for a research agent to investigate independently.

Examples of good deeper_questions:
- "What specific shoe types perform best in 78°F+ conditions?"
- "How do elite Boston Marathon runners pace the Newton Hills?"

Examples of bad deeper_questions (too vague):
- "More about gear"
- "Other things to consider"
""",
)


synthesize_agent = Agent(
    name="synthesize_agent",
    model=MODEL,
    mode="single_turn",
    output_schema=DeepResearchBriefing,
    instruction="""You are a marathon coach synthesizing a body of research into a
comprehensive briefing for a runner.

Given a nested JSON tree of research findings (each with a question, summary, key_facts,
and optional children with their own deeper findings), produce a unified DeepResearchBriefing:

- HEADLINE: One sentence with the most important takeaway from all the research.
- SECTIONS: 3-6 thematic paragraphs organizing the research into coherent topics.
  Combine related findings. Cite specific facts.
- KEY_WARNINGS: 2-4 actionable warnings the runner should NOT ignore.
- SUMMARY: One closing paragraph tying everything together with a clear recommendation.

Write for the runner, not for the researcher. Be direct and useful.
""",
)


# ─── Workflow nodes ───────────────────────────────────────────────────────────

def _extract_text(node_input) -> str:
    """Pull the user's query text out of whatever shape the runner passed."""
    if isinstance(node_input, str):
        return node_input
    if hasattr(node_input, "parts") and node_input.parts:
        text = getattr(node_input.parts[0], "text", None)
        if text:
            return text
    return str(node_input)


def _coerce_to_schema(payload, schema_cls):
    """ctx.run_node returns whatever the agent yielded. For LLM agents with
    output_schema this is the JSON string of the schema — parse it."""
    if isinstance(payload, schema_cls):
        return payload
    if isinstance(payload, dict):
        return schema_cls.model_validate(payload)
    if isinstance(payload, str):
        return schema_cls.model_validate_json(payload)
    if hasattr(payload, "parts") and payload.parts:
        text = getattr(payload.parts[0], "text", None)
        if text:
            return schema_cls.model_validate_json(text)
    raise ValueError(f"Cannot coerce {type(payload).__name__} into {schema_cls.__name__}: {payload!r}")


@node(rerun_on_resume=True)
async def decompose(ctx, node_input):
    """Run decompose_agent on the user's query; emit a list of sub-question specs."""
    user_query = _extract_text(node_input)
    raw = await ctx.run_node(decompose_agent, node_input=user_query)
    plan = _coerce_to_schema(raw, DecomposerOutput)
    print(f"  [decompose] plan: {plan.plan_summary}")
    print(f"  [decompose] {len(plan.sub_questions)} sub-questions:")
    for q in plan.sub_questions:
        print(f"    - {q}")

    # Pack each sub-question with its depth (1 = first level) and the original
    # user query for context. Each dict becomes one item the parallel_worker
    # consumes.
    items = [
        {"question": q, "depth": 1, "original_query": user_query}
        for q in plan.sub_questions
    ]
    yield Event(output=items)


@node(parallel_worker=True, rerun_on_resume=True)
async def research_topic(ctx, node_input):
    """One research task — parallel_worker fans this out across the question list.

    Recursive: a research finding may spawn 1-3 deeper questions, which are
    themselves invoked via ctx.run_node(research_topic, [...]) — fanning out
    at the next depth. Depth is capped at MAX_DEPTH.
    """
    question = node_input["question"]
    depth = node_input["depth"]
    context = node_input.get("original_query", "")

    print(f"  [research d={depth}] {question[:80]}")

    research_input = (
        f"ORIGINAL USER QUERY (for context): {context}\n\n"
        f"YOUR SPECIFIC RESEARCH QUESTION: {question}"
    )
    raw = await ctx.run_node(research_agent, node_input=research_input)
    finding = _coerce_to_schema(raw, ResearchFinding)

    children = []
    if finding.needs_deeper and finding.deeper_questions and depth < MAX_DEPTH:
        deeper_items = [
            {"question": dq, "depth": depth + 1, "original_query": context}
            for dq in finding.deeper_questions
        ]
        print(f"  [research d={depth}] '{question[:50]}' spawning {len(deeper_items)} deeper:")
        for di in deeper_items:
            print(f"    └─ {di['question'][:70]}")
        children_raw = await ctx.run_node(
            research_topic,
            node_input=deeper_items,
        )
        # children_raw is a list of dicts (each is one finding-with-children)
        children = children_raw

    yield Event(output={
        "question": question,
        "depth": depth,
        "summary": finding.summary,
        "key_facts": finding.key_facts,
        "needs_deeper": finding.needs_deeper,
        "children": children,
    })


@node(rerun_on_resume=True)
async def synthesize(ctx, node_input):
    """Pull together the nested research tree into a final briefing."""
    findings_tree = node_input  # list of finding-dicts with nested children
    print(f"  [synthesize] aggregating {len(findings_tree)} top-level findings")
    findings_json = json.dumps(findings_tree, indent=2)
    raw = await ctx.run_node(synthesize_agent, node_input=findings_json)
    briefing = _coerce_to_schema(raw, DeepResearchBriefing)
    print(f"  [synthesize] briefing: {briefing.headline}")
    # Include the raw tree alongside the briefing so the UI can render both
    yield Event(output={
        "briefing": briefing.model_dump(),
        "research_tree": findings_tree,
    })


# ─── Workflow ─────────────────────────────────────────────────────────────────

deep_research_workflow = Workflow(
    name="deep_research",
    description="Decompose user query into sub-research questions, fan out recursively, synthesize.",
    edges=[(START, decompose, research_topic, synthesize)],
)
