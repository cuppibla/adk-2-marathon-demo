"""Marathon race concierge — Pillar 2: Collaborative agents.

A coordinator agent delegates user questions to a dynamic subset of specialist
subagents, running them in parallel where appropriate. Demonstrates ADK 2.0's
unique collab feature: LLM-driven dynamic subset selection with parallel
execution under one coordinator.

Topology:
    race_concierge (coordinator)
      ├─ medical_specialist    (single_turn)
      ├─ weather_specialist    (single_turn)
      ├─ pacing_specialist     (single_turn)
      ├─ gear_specialist       (single_turn)
      ├─ nutrition_specialist  (single_turn)
      └─ mental_specialist     (single_turn)

The coordinator decides which specialists to invoke based on the user's
question. Sometimes 1, sometimes 3, sometimes all 6. Multiple invocations
happen in parallel via auto-injected delegation tools.
"""
from __future__ import annotations

from dotenv import load_dotenv

from google.adk import Agent

from workflows.shared import SpecialistInput, SpecialistResponse

load_dotenv()

MODEL = "gemini-flash-latest"


# ─── Specialist factory ───────────────────────────────────────────────────────

def _specialist(name: str, domain: str, focus: str) -> Agent:
    """Build one specialist subagent with a focused, narrow instruction."""
    return Agent(
        name=name,
        model=MODEL,
        mode="single_turn",
        input_schema=SpecialistInput,
        output_schema=SpecialistResponse,
        instruction=f"""You are a marathon {domain} specialist. Answer ONLY questions
within your domain. Focus: {focus}

Given the user's question, their current race strategy, and the runner's data,
produce a SpecialistResponse with:
- concern_level: how serious is this for race day ("none", "minor", "moderate", "serious")
- recommendation: ONE concrete actionable sentence
- reasoning: ONE sentence citing specific numbers from the strategy or runner data

If the question is outside your domain, set concern_level="none" and explain
briefly that this isn't your area.
""",
    )


# ─── The six specialists ──────────────────────────────────────────────────────

medical_specialist = _specialist(
    name="medical_specialist",
    domain="medical",
    focus="injury risk, physical health, pain, when to stop, hydration safety, heat stroke",
)

weather_specialist = _specialist(
    name="weather_specialist",
    domain="weather",
    focus="weather conditions, heat, cold, wind, rain, race-day forecast adjustments",
)

pacing_specialist = _specialist(
    name="pacing_specialist",
    domain="pacing",
    focus="pace strategy, mile splits, heart rate, target finish time adjustments",
)

gear_specialist = _specialist(
    name="gear_specialist",
    domain="gear",
    focus="clothing, shoes, accessories (hats, glasses, gloves), drop-bag contents",
)

nutrition_specialist = _specialist(
    name="nutrition_specialist",
    domain="nutrition",
    focus="fueling plan, gels, electrolytes, hydration timing, pre-race meals",
)

mental_specialist = _specialist(
    name="mental_specialist",
    domain="mental",
    focus="race mindset, motivation, pre-race anxiety, dealing with low points mid-race",
)


# ─── Coordinator ──────────────────────────────────────────────────────────────

race_concierge = Agent(
    name="race_concierge",
    model=MODEL,
    sub_agents=[
        medical_specialist,
        weather_specialist,
        pacing_specialist,
        gear_specialist,
        nutrition_specialist,
        mental_specialist,
    ],
    instruction="""You are a marathon race day concierge. The runner already has a race
strategy and is now asking follow-up questions. Six specialist agents are available:

- medical_specialist     — injury, pain, physical health, when to stop
- weather_specialist     — weather conditions and adjustments
- pacing_specialist      — pace strategy, splits, target time
- gear_specialist        — clothing, shoes, accessories
- nutrition_specialist   — fueling, hydration, electrolytes
- mental_specialist      — mindset, motivation, anxiety

For each user question:

1. DECIDE which specialists are genuinely relevant. Be precise. Examples:
   - "My knee hurts" → medical only
   - "What about fueling?" → nutrition only
   - "Should I race today?" → medical + weather + pacing (3 in parallel)
   - "It's raining now" → weather + gear + pacing (3 in parallel)
   - "Anything I should worry about?" → all 6 in parallel
   Do NOT invoke specialists whose domain doesn't apply.

2. Call the relevant specialist tools IN PARALLEL by emitting multiple function
   calls in one turn. Each call takes a SpecialistInput payload with:
     - user_question: the runner's question verbatim
     - current_strategy: forward the strategy from the user's initial message
     - runner_data: forward the runner data from the user's initial message

3. After specialists respond, SYNTHESIZE their responses into one cohesive
   answer that directly addresses the user's question. Cite specific
   recommendations. Keep it under 4 sentences. Lead with the most important
   concern.

The user's initial message will contain the runner's strategy + data in JSON.
Extract these and forward to each specialist you invoke.
""",
)
