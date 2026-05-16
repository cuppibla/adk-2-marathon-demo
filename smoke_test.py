"""Smoke test: minimal Workflow with two function nodes to verify the API."""
import asyncio
from google.adk import Workflow, Event, Runner
from google.adk.workflow import START
from google.adk.sessions import InMemorySessionService


def step_one(node_input):
    print(f"  [step_one] received: {node_input!r}")
    return Event(output="HELLO FROM STEP ONE")


def step_two(node_input):
    print(f"  [step_two] received: {node_input!r}")
    return Event(output=f"step_two saw: {node_input}")


workflow = Workflow(
    name="smoke_workflow",
    description="Two-step smoke test",
    edges=[(START, step_one, step_two)],
)


async def main():
    session_service = InMemorySessionService()
    runner = Runner(
        node=workflow,
        app_name="smoke_app",
        session_service=session_service,
        auto_create_session=True,
    )
    print("=== Running workflow via run_async ===")
    async for event in runner.run_async(
        user_id="u1",
        session_id="s1",
        new_message=None,
    ):
        print(f"  EVENT from {event.author!r}: output={event.output!r} message={event.message!r}")
    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
