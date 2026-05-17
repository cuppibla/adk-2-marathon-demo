"""FastAPI + SSE server that runs the marathon workflow and streams node events."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from google.adk import Runner
from google.adk.sessions import InMemorySessionService

from workflows.strategy_graph import root_agent

app = FastAPI(title="Marathon Strategy Demo")

STATIC_DIR = Path(__file__).parent / "static"


def _node_name(event) -> str:
    """Pull the bare node name out of `node_info.path` like
    'marathon_strategy@1/pull_fitness@1' → 'pull_fitness'."""
    path = getattr(event.node_info, "path", "") or ""
    last = path.rsplit("/", 1)[-1]
    return last.split("@", 1)[0]


def _event_output(event) -> object:
    """Function nodes set event.output directly. LLM agents put their structured
    output in event.content.parts[0].text as a JSON string — extract and parse it."""
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


@app.get("/")
async def index():
    index_html = STATIC_DIR / "index.html"
    if not index_html.exists():
        return {"status": "ok", "message": "no frontend yet — try GET /run?scenario=HOT"}
    return FileResponse(index_html)


@app.get("/run")
async def run(
    scenario: str = Query("HOT", pattern="^(HOT|NORMAL|COLD)$"),
    slow_mo: float = Query(1.0, ge=0.5, le=5.0),
):
    """Run the workflow and stream node events as SSE."""
    os.environ["MARATHON_SCENARIO"] = scenario
    os.environ["MARATHON_SLOW_MO"] = str(slow_mo)

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
        try:
            async for event in runner.run_async(
                user_id="demo_user",
                session_id=f"demo_session_{int(time.time()*1000)}",
                new_message=None,
            ):
                node = _node_name(event)
                payload = {
                    "node": node,
                    "ts": round(time.perf_counter() - t0, 3),
                    "output": _event_output(event),
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
