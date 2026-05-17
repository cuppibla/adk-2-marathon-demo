"""FastAPI + SSE server for the marathon demo.

Endpoints:
- GET /                       — serves the visualization page
- GET /run?scenario=...       — streams Pillar 1 (graph workflow) events
- GET /chat?question=...      — streams Pillar 2 (collab concierge) events,
                                using the latest strategy from /run
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as gtypes

from workflows.concierge import race_concierge
from workflows.deep_research import deep_research_workflow
from workflows.strategy_graph import root_agent
from workflows.team_planner import team_workflow

app = FastAPI(title="Marathon Strategy Demo")

STATIC_DIR = Path(__file__).parent / "static"

# Module-level state: remembers the most recent run's strategy + data so /chat
# can reference them. Demo-grade — single user, single context.
_latest: dict[str, Any] = {"strategy": None, "data": None, "scenario": None}

# Preset rosters for Mode 3 team demos. Names + scenarios are canned so the
# routing is reproducible on stage.
TEAM_ROSTERS: dict[str, list[dict]] = {
    "alpha": [
        {"name": "Alice",   "scenario": "HOT"},
        {"name": "Bob",     "scenario": "NORMAL"},
        {"name": "Carol",   "scenario": "COLD"},
    ],
    "omega": [
        {"name": f"Runner-{i:02d}", "scenario": s}
        for i, s in enumerate([
            "HOT", "HOT", "HOT",
            "NORMAL", "NORMAL", "NORMAL", "NORMAL",
            "COLD", "COLD", "COLD",
        ], start=1)
    ],
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _node_name(event) -> str:
    """'marathon_strategy@1/pull_fitness@1' → 'pull_fitness'."""
    path = getattr(event.node_info, "path", "") or ""
    last = path.rsplit("/", 1)[-1]
    return last.split("@", 1)[0]


def _event_output(event) -> object:
    """Function nodes use event.output; LLM agents use event.content.parts[0].text as JSON."""
    if event.output is not None:
        return event.output
    content = getattr(event, "content", None)
    if content and getattr(content, "parts", None):
        text = getattr(content.parts[0], "text", None)
        if text:
            try:
                return json.loads(text)
            except (ValueError, json.JSONDecodeError):
                return text
    return None


def _parse_concierge_event(ev) -> dict | None:
    """Convert a runner event from the concierge workflow into a UI-friendly payload.

    Returns one of:
      {"kind": "dispatched", "specialist": str}            — coordinator emitted a function_call
      {"kind": "specialist_done", "specialist": str, "response": dict}  — subagent returned
      {"kind": "synthesized", "text": str}                 — coordinator emitted final text
      None if the event isn't UI-relevant.
    """
    if not ev.content or not ev.content.parts:
        return None
    author = ev.author
    for p in ev.content.parts:
        fc = getattr(p, "function_call", None)
        fr = getattr(p, "function_response", None)
        text = getattr(p, "text", None)

        if fc and author == "race_concierge":
            # Coordinator dispatched a specialist (may have multiple parts for parallel)
            return {"kind": "dispatched", "specialist": fc.name}
        if text and author != "race_concierge":
            # Specialist subagent returned its structured response
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {"raw": text}
            return {"kind": "specialist_done", "specialist": author, "response": payload}
        if text and author == "race_concierge":
            # Final synthesized answer from coordinator
            return {"kind": "synthesized", "text": text}
    return None


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    index_html = STATIC_DIR / "index.html"
    if not index_html.exists():
        return {"status": "ok", "message": "no frontend yet — try /run?scenario=HOT"}
    return FileResponse(index_html)


@app.get("/run")
async def run(
    scenario: str = Query("HOT", pattern="^(HOT|NORMAL|COLD)$"),
    slow_mo: float = Query(1.0, ge=0.5, le=5.0),
):
    """Run the Pillar 1 graph workflow and stream node events as SSE."""
    os.environ["MARATHON_SCENARIO"] = scenario
    os.environ["MARATHON_SLOW_MO"] = str(slow_mo)
    # Reset the cached strategy — a new run is starting
    _latest["scenario"] = scenario
    _latest["data"] = None
    _latest["strategy"] = None

    async def event_gen():
        t0 = time.perf_counter()
        yield {
            "event": "workflow_start",
            "data": json.dumps({"scenario": scenario, "ts": 0.0}),
        }

        session_service = InMemorySessionService()
        runner = Runner(
            node=root_agent,
            app_name="marathon_app",
            session_service=session_service,
            auto_create_session=True,
        )
        strategy_node_names = {"hot_strategy", "normal_strategy", "cold_strategy"}
        try:
            async for event in runner.run_async(
                user_id="demo_user",
                session_id=f"demo_session_{int(time.time()*1000)}",
                new_message=None,
            ):
                node = _node_name(event)
                output = _event_output(event)
                # Stash the join payload (bundled runner data) and the final strategy
                if node == "join_inputs" and isinstance(output, dict):
                    _latest["data"] = output
                elif node in strategy_node_names and isinstance(output, dict):
                    _latest["strategy"] = output

                payload = {
                    "node": node,
                    "ts": round(time.perf_counter() - t0, 3),
                    "output": output,
                }
                yield {"event": "node_complete", "data": json.dumps(payload, default=str)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
            raise
        finally:
            yield {
                "event": "workflow_complete",
                "data": json.dumps({"ts": round(time.perf_counter() - t0, 3)}),
            }

    return EventSourceResponse(event_gen())


@app.get("/chat")
async def chat(question: str = Query(..., min_length=1, max_length=500)):
    """Run the Pillar 2 concierge coordinator and stream collab events as SSE.

    The coordinator decides which specialist subset to dispatch based on the
    question. Multiple specialists run in parallel where appropriate.
    """
    if _latest["strategy"] is None or _latest["data"] is None:
        # No prior strategy — return a single error event and end the stream
        async def err_gen():
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": "No strategy yet. Run /run first to generate a strategy "
                             "before chatting with the concierge."
                }),
            }
        return EventSourceResponse(err_gen())

    async def event_gen():
        t0 = time.perf_counter()
        yield {
            "event": "chat_start",
            "data": json.dumps({"question": question, "ts": 0.0}),
        }

        user_msg = gtypes.Content(
            role="user",
            parts=[gtypes.Part(text=(
                f"QUESTION: {question}\n\n"
                f"CURRENT STRATEGY (JSON):\n{json.dumps(_latest['strategy'], indent=2)}\n\n"
                f"RUNNER DATA (JSON):\n{json.dumps(_latest['data'], indent=2)}\n"
            ))],
        )

        session_service = InMemorySessionService()
        runner = Runner(
            node=race_concierge,
            app_name="concierge_app",
            session_service=session_service,
            auto_create_session=True,
        )
        try:
            async for event in runner.run_async(
                user_id="demo_user",
                session_id=f"chat_{int(time.time()*1000)}",
                new_message=user_msg,
            ):
                # A single event from the coordinator can contain MULTIPLE function_call
                # parts (parallel dispatch). Yield one SSE event per part so the UI
                # can light up specialists individually.
                if not event.content or not event.content.parts:
                    continue
                author = event.author
                for p in event.content.parts:
                    fc = getattr(p, "function_call", None)
                    text = getattr(p, "text", None)

                    if fc and author == "race_concierge":
                        yield {
                            "event": "dispatched",
                            "data": json.dumps({
                                "specialist": fc.name,
                                "ts": round(time.perf_counter() - t0, 3),
                            }),
                        }
                    elif text and author != "race_concierge":
                        try:
                            payload = json.loads(text)
                        except json.JSONDecodeError:
                            payload = {"raw": text}
                        yield {
                            "event": "specialist_done",
                            "data": json.dumps({
                                "specialist": author,
                                "response": payload,
                                "ts": round(time.perf_counter() - t0, 3),
                            }),
                        }
                    elif text and author == "race_concierge":
                        yield {
                            "event": "synthesized",
                            "data": json.dumps({
                                "text": text,
                                "ts": round(time.perf_counter() - t0, 3),
                            }),
                        }
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
            raise
        finally:
            yield {
                "event": "chat_complete",
                "data": json.dumps({"ts": round(time.perf_counter() - t0, 3)}),
            }

    return EventSourceResponse(event_gen())


@app.get("/team")
async def team(roster: str = Query(..., pattern="^(alpha|omega)$")):
    """Run the Pillar 3 team workflow over a preset roster.

    Streams per-runner completion events and a final team summary. The wow
    is that all runners are planned in parallel — wall time should scale
    with the slowest runner, not the sum.
    """
    chosen = TEAM_ROSTERS[roster]
    import json as _json
    roster_msg = gtypes.Content(
        role="user",
        parts=[gtypes.Part(text=_json.dumps(chosen))],
    )

    async def event_gen():
        t0 = time.perf_counter()
        yield {
            "event": "team_start",
            "data": json.dumps({"roster": chosen, "count": len(chosen), "ts": 0.0}),
        }

        session_service = InMemorySessionService()
        runner = Runner(
            node=team_workflow,
            app_name="team_app",
            session_service=session_service,
            auto_create_session=True,
        )
        try:
            async for event in runner.run_async(
                user_id="coach",
                session_id=f"team_session_{int(time.time()*1000)}",
                new_message=roster_msg,
            ):
                out = _event_output(event)
                ts = round(time.perf_counter() - t0, 3)
                # Per-runner completion event (output of plan_for_runner)
                if isinstance(out, dict) and "runner_name" in out:
                    yield {
                        "event": "runner_complete",
                        "data": json.dumps({
                            "name": out["runner_name"],
                            "scenario": out["scenario"],
                            "strategy": out.get("strategy"),
                            "ts": ts,
                        }, default=str),
                    }
                # Final team summary (output of summarize_team)
                elif isinstance(out, dict) and "plans" in out and "count" in out:
                    yield {
                        "event": "team_complete",
                        "data": json.dumps({
                            "summary": out.get("notes", ""),
                            "count": out.get("count", 0),
                            "ts": ts,
                        }),
                    }
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
            raise

    return EventSourceResponse(event_gen())


RESEARCH_PRESETS: dict[str, str] = {
    "boston": "Tell me everything I should know about racing the Boston Marathon — course, weather history, common pitfalls, pacing strategy, and what to wear.",
    "heat": "What do I need to know about racing a marathon in hot conditions (above 78°F)? Cover pacing, fueling, gear, and medical risks.",
    "recovery": "I just finished my first marathon. Give me a comprehensive recovery plan for the next 4 weeks.",
}


def _make_node_id(path: str, idx: int) -> str:
    """Derive a stable id for a node from its node_info.path and a counter."""
    # Strip everything before the last meaningful component
    last = path.rsplit("/", 1)[-1] if path else f"n{idx}"
    return f"{last}_{idx}"


@app.get("/research")
async def research(
    preset: str | None = Query(None, pattern="^(boston|heat|recovery)$"),
    query: str | None = Query(None, min_length=5, max_length=500),
):
    """Run the Pillar 3 deep research workflow over a user query (or preset).

    Streams events as the research tree grows:
    - workflow_start: query received
    - decompose_complete: top-level sub-questions known
    - research_complete: a research node finished (may include spawned children)
    - synthesize_complete: final briefing ready
    """
    if preset:
        chosen_query = RESEARCH_PRESETS[preset]
    elif query:
        chosen_query = query
    else:
        async def err_gen():
            yield {
                "event": "error",
                "data": json.dumps({"error": "Pass either ?preset=boston|heat|recovery or ?query=..."}),
            }
        return EventSourceResponse(err_gen())

    msg = gtypes.Content(role="user", parts=[gtypes.Part(text=chosen_query)])

    async def event_gen():
        t0 = time.perf_counter()
        yield {
            "event": "workflow_start",
            "data": json.dumps({"query": chosen_query, "ts": 0.0}),
        }

        session_service = InMemorySessionService()
        runner = Runner(
            node=deep_research_workflow,
            app_name="research_app",
            session_service=session_service,
            auto_create_session=True,
        )

        # Track which top-level questions we've already announced via decompose_complete
        # so we can correctly attribute research events to "root" vs a parent question.
        top_level_questions: set[str] = set()

        try:
            async for event in runner.run_async(
                user_id="researcher",
                session_id=f"research_session_{int(time.time()*1000)}",
                new_message=msg,
            ):
                out = _event_output(event)
                node = _node_name(event)
                ts = round(time.perf_counter() - t0, 3)

                # decompose node emits a list of {question, depth, original_query} dicts
                if node == "decompose" and isinstance(out, list) and out and isinstance(out[0], dict) and "question" in out[0]:
                    top_level_questions = {item["question"] for item in out}
                    yield {
                        "event": "decompose_complete",
                        "data": json.dumps({
                            "sub_questions": [item["question"] for item in out],
                            "ts": ts,
                        }),
                    }

                # research_topic node — emits a dict with question/summary/children/etc.
                elif node == "research_topic" and isinstance(out, dict) and "question" in out and "summary" in out:
                    is_top_level = out["question"] in top_level_questions
                    yield {
                        "event": "research_complete",
                        "data": json.dumps({
                            "question": out["question"],
                            "depth": out.get("depth", 1),
                            "is_top_level": is_top_level,
                            "summary": out["summary"],
                            "key_facts": out.get("key_facts", []),
                            "spawned_children": [
                                {"question": c["question"], "summary": c.get("summary", "")}
                                for c in out.get("children", []) or []
                            ],
                            "ts": ts,
                        }),
                    }

                # synthesize node — final briefing
                elif node == "synthesize" and isinstance(out, dict) and "briefing" in out:
                    yield {
                        "event": "synthesize_complete",
                        "data": json.dumps({
                            "briefing": out["briefing"],
                            "tree_total": _count_tree_nodes(out.get("research_tree", [])),
                            "ts": ts,
                        }, default=str),
                    }
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": str(e)})}
            raise
        finally:
            yield {
                "event": "workflow_complete",
                "data": json.dumps({"ts": round(time.perf_counter() - t0, 3)}),
            }

    return EventSourceResponse(event_gen())


def _count_tree_nodes(tree: list) -> int:
    """Count total nodes in a nested research tree (top-level + children + grandchildren)."""
    total = 0
    for node in tree:
        total += 1
        total += _count_tree_nodes(node.get("children", []) or [])
    return total


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
