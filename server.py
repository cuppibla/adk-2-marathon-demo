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
from workflows.strategy_graph import root_agent

app = FastAPI(title="Marathon Strategy Demo")

STATIC_DIR = Path(__file__).parent / "static"

# Module-level state: remembers the most recent run's strategy + data so /chat
# can reference them. Demo-grade — single user, single context.
_latest: dict[str, Any] = {"strategy": None, "data": None, "scenario": None}


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
