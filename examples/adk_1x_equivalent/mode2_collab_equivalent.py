"""ADK 1.x equivalent of Mode 2 (Race Concierge — coordinator with 6 specialists).

This file shows the two 1.x ways to build "coordinator with specialists who
should be called dynamically based on user input." Neither matches what 2.0's
collaborative agents do natively.

NOT RUNNABLE in this project — this project depends on google-adk 2.0.0b1.
This file imports 1.x APIs for reference / video comparison only.
See ../README.md for context.

==============================================================================
2.0 EQUIVALENT: ../../workflows/concierge.py
PROBLEM:        Runner asks a question → LLM picks 1-6 relevant specialists →
                run them IN PARALLEL → synthesize their responses
==============================================================================
"""
from __future__ import annotations

# NOTE: These imports require ADK 1.x — they will fail in this 2.0 project.
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from pydantic import BaseModel, Field
from typing import Literal


# ─── Shared schemas ──────────────────────────────────────────────────────────

class SpecialistResponse(BaseModel):
    concern_level: Literal["none", "minor", "moderate", "serious"]
    recommendation: str
    reasoning: str


# ─── Specialist agents (the "easy" part — identical in 1.x and 2.0) ─────────

def _specialist(name: str, domain: str, focus: str) -> LlmAgent:
    return LlmAgent(
        name=name,
        model="gemini-flash-latest",
        instruction=f"""You are a marathon {domain} specialist. Focus: {focus}

Read the user question and runner context from session state. Produce a
SpecialistResponse with concern_level, recommendation, and reasoning.
""",
        output_schema=SpecialistResponse,
        output_key=f"{name}_response",
    )


medical_specialist   = _specialist("medical",   "medical",   "injury, pain, hydration safety")
weather_specialist   = _specialist("weather",   "weather",   "conditions and adjustments")
pacing_specialist    = _specialist("pacing",    "pacing",    "pace strategy, splits")
gear_specialist      = _specialist("gear",      "gear",      "clothing, shoes, accessories")
nutrition_specialist = _specialist("nutrition", "nutrition", "fueling, hydration")
mental_specialist    = _specialist("mental",    "mental",    "mindset, motivation")

ALL_SPECIALISTS = [
    medical_specialist, weather_specialist, pacing_specialist,
    gear_specialist, nutrition_specialist, mental_specialist,
]


# =============================================================================
# 1.X APPROACH #1 — ParallelAgent: always run ALL 6 specialists
# =============================================================================
#
# This works but wastes LLM calls. If the user just asked "what about my
# fueling plan?", running medical + weather + pacing + gear + mental is
# pure waste. 5 of 6 calls produce irrelevant output.
#
# In 1.x, ParallelAgent is the only primitive that runs sub-agents
# concurrently. Its sub-agent list is fixed at construction — there's no
# way to dynamically pick a subset per request.

all_specialists_parallel = ParallelAgent(
    name="all_specialists_always",
    sub_agents=ALL_SPECIALISTS,
)

# Then a synthesizer reads all 6 responses from session state.
synthesizer = LlmAgent(
    name="synthesizer",
    model="gemini-flash-latest",
    instruction="""You are a marathon coach concierge synthesizing specialist input.

The user's question is in session.state["user_question"].
The specialist responses are in session.state, keyed by specialist name:
  - session.state["medical_response"]
  - session.state["weather_response"]
  - session.state["pacing_response"]
  - session.state["gear_response"]
  - session.state["nutrition_response"]
  - session.state["mental_response"]

Synthesize their responses into one concise answer that directly addresses
the user's question. If some specialists' responses are irrelevant to the
user's question (concern_level == "none"), ignore them in your synthesis.

Lead with the most important concern. Keep it under 4 sentences.
""",
)

# Root: parallel-all-6 then synthesize.
concierge_1x_always_all = SequentialAgent(
    name="concierge_always_all",
    sub_agents=[all_specialists_parallel, synthesizer],
)


# =============================================================================
# 1.X APPROACH #2 — Coordinator with sub_agents + transfer_to_agent (serial)
# =============================================================================
#
# More efficient than approach #1 — only relevant specialists fire. BUT
# transfer_to_agent is SERIAL. You can't transfer to two specialists at the
# same time. So for "Should I race today?" (needs medical + weather + pacing),
# you transfer to one, get the answer, transfer back, transfer to the next,
# get the answer, transfer back, etc.
#
# Wall time scales linearly with the number of specialists needed.
# Plus: the coordinator's prompt has to manage the transfer choreography,
# which is brittle.

concierge_coordinator_1x_serial = LlmAgent(
    name="concierge_coordinator_serial",
    model="gemini-flash-latest",
    sub_agents=ALL_SPECIALISTS,  # auto-injects transfer_to_agent for each
    instruction="""You are a marathon race day concierge. The runner has a
strategy and is asking follow-up questions. Six specialists are available
via sub_agents:

- medical    — injury, pain, physical health
- weather    — weather conditions and adjustments
- pacing     — pace strategy, splits, finish time
- gear       — clothing, shoes, accessories
- nutrition  — fueling, hydration
- mental     — mindset, motivation, anxiety

For each user question:

1. Decide which specialist(s) are relevant.
2. If only one is relevant, call transfer_to_agent(<specialist>) once,
   wait for the response, then summarize for the user.
3. If multiple are relevant, you must call transfer_to_agent SEQUENTIALLY
   — one at a time. After each returns, decide if you need another.
4. After collecting all relevant responses, synthesize into one answer.

IMPORTANT: You cannot call multiple specialists in parallel. Each
transfer_to_agent call is a separate turn that must complete before the
next can begin.
""",
)


# =============================================================================
# COMPARISON NOTES — Mode 2 (Collaborative agents)
# =============================================================================
#
# LLM CALLS per question:
#
#   Question: "What about my fueling plan?" (only nutrition is relevant)
#     - Approach #1 (always-all): 7 calls (6 specialists + 1 synthesizer)
#     - Approach #2 (serial transfer): 3 calls (coordinator decision + nutrition + synthesis turn)
#     - 2.0 equivalent: 2 calls (coordinator + nutrition, in parallel)
#
#   Question: "Should I race today?" (medical + weather + pacing all relevant)
#     - Approach #1 (always-all): 7 calls (6 specialists + 1 synthesizer)
#     - Approach #2 (serial transfer): 5 calls SERIALLY (~30s wall time)
#     - 2.0 equivalent: 4 calls IN PARALLEL (~13s wall time)
#
#   Question: "Full review" (all 6 relevant)
#     - Approach #1: 7 calls (correct count, but no different from "fueling" question)
#     - Approach #2: 7 calls SERIALLY (~45s wall time)
#     - 2.0 equivalent: 7 calls IN PARALLEL (~16s wall time)
#
# LINES OF CODE (this file, excluding schemas):
#   ~140 lines (both approaches)
#
# COMPARE: 2.0 equivalent in workflows/concierge.py = ~80 lines (one approach,
# which is strictly better than both 1.x options)
#
# UNIQUE WEAKNESSES OF EACH 1.X APPROACH:
#
#   Approach #1 (ParallelAgent always-all):
#     - 5-6 wasted LLM calls per narrow question
#     - At Gemini Flash pricing: ~$0.005 wasted per question × thousands
#       of questions × N users = real money
#     - Synthesizer has to ignore irrelevant responses in its prompt
#
#   Approach #2 (Coordinator with transfer_to_agent serial):
#     - Wall time scales linearly with number of specialists needed
#     - Brittle: coordinator might mis-spell transfer target, or forget to
#       transfer at all, or transfer to wrong specialist
#     - Coordinator's prompt has to manage transfer choreography (~200 tokens
#       of "first do X, then Y, never Z" instructions)
#
# WHAT 2.0 GIVES YOU:
#   - Coordinator picks a DYNAMIC SUBSET (not all, not one — exactly the right N)
#   - Selected specialists run IN PARALLEL via auto-injected tool calls in
#     a single coordinator turn
#   - mode="single_turn" subagents return automatically — no transfer
#     choreography in the coordinator's prompt
#   - For a 6-specialist question: 7 LLM calls in ~16s instead of 7 in ~45s
# =============================================================================
