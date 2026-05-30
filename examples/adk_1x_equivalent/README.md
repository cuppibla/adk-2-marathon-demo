# ADK 1.x Equivalent Implementations

This directory contains hand-written ADK 1.x equivalents of each of the three modes in this demo (`workflows/strategy_graph.py`, `workflows/concierge.py`, `workflows/deep_research.py`).

## ⚠️ These files are NOT runnable in this project

This project depends on `google-adk==2.0.0b1`. The snippets in this directory import from ADK 1.x APIs (`google.adk.agents`, etc.) that exist in 1.x but have different shapes in 2.0. Trying to `uv run` any of these files in this project will fail.

The snippets are **reference implementations** intended for:

1. **The Ep 4 "ADK 1.x vs 2.0" comparison video** — these are the literal code blocks shown on screen
2. **Anyone migrating from 1.x to 2.0** — clear "before / after" pairs for each pattern
3. **Verifying the comparison numbers** — the LLM call counts and structural claims in the video are derivable from these snippets by inspection

## File map

| 1.x reference | 2.0 actual implementation | What's compared |
|---|---|---|
| `mode1_graph_equivalent.py` | `../../workflows/strategy_graph.py` | Pillar 1: parallel fetches → router → strategy |
| `mode2_collab_equivalent.py` | `../../workflows/concierge.py` | Pillar 2: coordinator with N specialists |
| `mode3_dynamic_equivalent.py` | `../../workflows/deep_research.py` | Pillar 3: recursive parallel fan-out |

## What each comparison shows

### Mode 1 (Graph workflows)
- **1.x**: requires wrapping every fetch in an `LlmAgent` because `ParallelAgent` only orchestrates agents. Routing decision lives in a long prompt that the strategist agent has to parse.
- **2.0**: function nodes and agent nodes coexist as peers in one `edges=[...]` array. Routing is a 4-line Python function.

### Mode 2 (Collaborative agents)
- **1.x**: forced to choose between (a) `ParallelAgent` that always runs every specialist (wasteful) or (b) a coordinator with `transfer_to_agent` that runs specialists serially (slow). No way to express "LLM picks subset, runs in parallel."
- **2.0**: coordinator with `sub_agents=[...]` + `mode="single_turn"` lets the LLM pick a dynamic subset and run them in parallel in one turn.

### Mode 3 (Dynamic workflows)
- **1.x**: either (a) one mega-`LlmAgent` with a huge prompt trying to do everything (hallucinates) or (b) raw `asyncio.gather` outside the framework (no tracing, no checkpointing, no resumability).
- **2.0**: `@node(parallel_worker=True)` with recursive `ctx.run_node` keeps everything inside the framework while supporting recursive, runtime-shaped parallel fan-out.

## The numbers

Each snippet ends with a `# COMPARISON NOTES:` block listing:
- LLM calls per request
- Lines of code
- Verbal description of the unique weakness

These are countable from the code itself. You can verify the claims by reading the snippet, not by running it.

## Authenticity disclaimer

These are written by someone (the author of this 2.0 demo) familiar with both 1.x and 2.0 patterns, aimed at being honest about how 1.x developers actually wrote this kind of code. If you spot anything that misrepresents 1.x, open an issue — corrections welcome.
