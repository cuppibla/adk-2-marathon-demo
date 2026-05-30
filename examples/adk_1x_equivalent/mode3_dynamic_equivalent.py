"""ADK 1.x equivalent of Mode 3 (Deep Research — recursive parallel fan-out).

This file shows the two 1.x options for "decompose a question into N
sub-questions, research each in parallel, some may recursively spawn more
sub-questions, then synthesize." Neither option is good. The first is
unreliable (single mega-agent loses control). The second forces you to drop
OUT of the framework entirely.

NOT RUNNABLE in this project — this project depends on google-adk 2.0.0b1.
This file imports 1.x APIs for reference / video comparison only.
See ../README.md for context.

==============================================================================
2.0 EQUIVALENT: ../../workflows/deep_research.py
PROBLEM:        Decompose question → research each sub-question in parallel →
                recursively spawn deeper questions where warranted → synthesize.
                Tree shape (width + depth) decided by LLM at runtime.
==============================================================================
"""
from __future__ import annotations

import asyncio
from typing import Literal

# NOTE: These imports require ADK 1.x — they will fail in this 2.0 project.
from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from pydantic import BaseModel, Field


# ─── Shared schemas ──────────────────────────────────────────────────────────

class ResearchFinding(BaseModel):
    question: str
    findings: str
    needs_deeper: bool
    deeper_questions: list[str] = Field(default_factory=list)


class DeepResearchBriefing(BaseModel):
    headline: str
    sections: list[dict]
    key_warnings: list[str]


# =============================================================================
# 1.X APPROACH #1 — One mega-agent does it all
# =============================================================================
#
# Cram decompose + research + recurse + synthesize into one LlmAgent with
# a huge prompt. The LLM is supposed to manage the entire tree mentally.
#
# In practice:
#   - Loses track of which sub-questions it's answered vs not
#   - "Recursion" exists only in the prompt; no actual parallel work
#   - Synthesis is mixed with research — output quality drops
#   - No way to checkpoint progress or resume after a failure

mega_research_agent = LlmAgent(
    name="mega_research_agent_1x",
    model="gemini-flash-latest",
    instruction="""You are a deep research agent.

Given a user query, you must:

  1. Decompose the query into 5-8 sub-questions covering different angles.
  2. For each sub-question, do mental research and produce findings.
  3. If a sub-question's findings warrant deeper investigation, generate
     1-3 follow-up questions about that finding and research those too.
  4. Recurse up to 2 levels deep.
  5. After researching everything, synthesize all findings into a final
     briefing with a headline, sections, and key warnings.

Important constraints:
  - You must keep track of which sub-questions are still open vs answered.
  - Do not skip the recursive step.
  - Do not summarize prematurely — research first, then synthesize.
  - Output the final briefing as JSON matching the DeepResearchBriefing schema.

Begin.
""",
    output_schema=DeepResearchBriefing,
)


# PROBLEM: There is no actual parallelism. The LLM does everything serially
# in one giant context. Wall time is whatever the LLM takes to produce its
# huge response (~30-60s) and quality degrades dramatically as the prompt
# context grows. Not viable for real production use.


# =============================================================================
# 1.X APPROACH #2 — Drop OUT of the framework and use raw asyncio
# =============================================================================
#
# To get actual parallelism + recursion, you abandon the ADK workflow
# primitives and write Python orchestration code yourself.
#
# This works but you lose every framework benefit:
#   - No event tracing (each sub-research has its own Runner)
#   - No checkpointing / resumability
#   - No graph visualization in observability tools
#   - No deterministic node IDs for retry
#   - You must build the orchestration logic from scratch

# Individual agents (these are fine — same shape as 2.0)
decompose_agent = LlmAgent(
    name="decompose_1x",
    model="gemini-flash-latest",
    instruction="Decompose the user query into 5-8 research sub-questions. "
                "Return a JSON list of strings.",
)

research_agent = LlmAgent(
    name="research_1x",
    model="gemini-flash-latest",
    instruction="Research the given question. Return a ResearchFinding JSON "
                "with findings and a needs_deeper boolean.",
    output_schema=ResearchFinding,
)

synthesize_agent = LlmAgent(
    name="synthesize_1x",
    model="gemini-flash-latest",
    instruction="Aggregate the research findings into a DeepResearchBriefing.",
    output_schema=DeepResearchBriefing,
)


# Orchestration outside the framework — you write this by hand.
# This is what people actually had to do in 1.x for recursive fan-out.
async def deep_research_1x(user_query: str, max_depth: int = 2) -> DeepResearchBriefing:
    """Manual orchestration of a deep-research workflow.

    This is NOT a workflow. It is async Python that happens to use ADK
    agents inside it. The framework has no visibility into the structure
    you're building here.
    """
    session_service = InMemorySessionService()

    async def _run_agent(agent: LlmAgent, prompt: str) -> dict:
        """Stand up a new Runner for each agent invocation. Yes — this
        wastes resources, but Runners are not reusable across invocations
        in arbitrary positions. There is no `ctx.run_node(agent, input)`
        equivalent in 1.x."""
        runner = Runner(
            agent=agent,
            app_name="deep_research_1x",
            session_service=session_service,
        )
        # ... pretend code to invoke the runner with prompt and collect output ...
        # (omitting the verbose 1.x runner invocation boilerplate)
        return {"placeholder": "agent output"}

    async def _research_recursively(question: str, depth: int) -> ResearchFinding:
        # Step 1: research this question
        finding_raw = await _run_agent(research_agent, question)
        finding = ResearchFinding.model_validate(finding_raw)

        # Step 2: if needs_deeper AND under max_depth, recursively spawn
        if finding.needs_deeper and depth < max_depth:
            # Manual parallel fan-out using asyncio.gather
            child_tasks = [
                _research_recursively(q, depth + 1)
                for q in finding.deeper_questions
            ]
            children = await asyncio.gather(*child_tasks)
            # You manually attach children to the finding
            finding.deeper_questions = [c.question for c in children]
            # ... and you manually track the tree structure for synthesis

        return finding

    # Step 1: decompose
    decomp_raw = await _run_agent(decompose_agent, user_query)
    sub_questions = decomp_raw["placeholder"]  # parse the list

    # Step 2: parallel research at depth 1, with recursion baked into the function
    top_level_tasks = [_research_recursively(q, depth=1) for q in sub_questions]
    findings = await asyncio.gather(*top_level_tasks)

    # Step 3: synthesize
    flat_findings = _flatten_findings_tree(findings)  # you write this helper
    briefing_raw = await _run_agent(synthesize_agent, str(flat_findings))
    return DeepResearchBriefing.model_validate(briefing_raw)


def _flatten_findings_tree(findings: list[ResearchFinding]) -> list[dict]:
    """You write this. The framework doesn't help — it has no notion of
    a 'tree of findings'. You're managing the data structure yourself."""
    flat = []
    for f in findings:
        flat.append(f.model_dump())
        # ... recursive flatten ...
    return flat


# =============================================================================
# COMPARISON NOTES — Mode 3 (Dynamic workflow / Deep research)
# =============================================================================
#
# LLM CALLS per request (assuming 5 top-level sub-questions, 2 spawn deeper):
#   - Approach #1 (mega-agent): 1 LLM call but takes 30-60s; output quality
#     degrades; no real parallelism
#   - Approach #2 (raw asyncio): 1 decompose + 5 research + 4 deeper research
#     + 1 synthesize = 11 LLM calls, parallel where possible, ~25s wall time
#   - 2.0 equivalent: 11-15 LLM calls, parallel where possible, ~25s wall time
#
# So Approach #2 and 2.0 have SIMILAR runtime numbers. The difference is
# everything else.
#
# LINES OF CODE (this file):
#   ~150 lines (just the orchestration), and most of it is the manual
#   recursion + fan-out logic you have to write yourself
#
# COMPARE: 2.0 equivalent in workflows/deep_research.py = ~50 lines, and
# the orchestration is declarative — the framework handles the recursion
# and fan-out
#
# UNIQUE WEAKNESSES OF EACH 1.X APPROACH:
#
#   Approach #1 (mega-agent):
#     - Single LLM context fills up — output quality drops as it tries to
#       remember which sub-questions it's answered
#     - No actual parallelism — wall time is whatever one massive LLM call
#       takes (often 30-60s)
#     - No way to resume after failure
#     - Can't visualize the tree — there isn't one, only a paragraph
#
#   Approach #2 (raw asyncio):
#     - You're OUTSIDE the framework. The 1.x graph engine has no idea
#       what's happening in your orchestration code.
#     - No event tracing in observability tools
#     - No checkpointing — if research_agent fails on item 7 of 11, you
#       have to start over (rerun all 11)
#     - No graph visualization
#     - You write all the tree-management code by hand (_flatten_findings_tree,
#       recursion bookkeeping, error handling, etc.)
#     - You stand up a new Runner per agent invocation — wasteful but
#       necessary because Runners aren't reusable in arbitrary positions
#
# WHAT 2.0 GIVES YOU:
#   - @node(parallel_worker=True, rerun_on_resume=True) — fan-out is one
#     decorator
#   - Recursive ctx.run_node(self, list) inside the parallel_worker handles
#     variable depth automatically
#   - All work stays INSIDE the framework — full tracing, checkpointing,
#     resumability
#   - If a single research task fails mid-flight, you can retry just that
#     one — the framework's event log knows which are done
#   - Tree structure is maintained automatically; you don't write
#     flatten/aggregate helpers
#
# THE BIG PICTURE:
#   Approach #1 fails on quality. Approach #2 succeeds on runtime but
#   requires abandoning the framework. ADK 2.0's @node(parallel_worker=True)
#   is the first time you can express recursive parallel fan-out
#   declaratively WITHIN the framework, with all the framework benefits
#   intact. That's the genuinely-new thing.
# =============================================================================
