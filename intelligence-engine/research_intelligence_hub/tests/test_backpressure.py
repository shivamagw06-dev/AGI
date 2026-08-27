import asyncio
from threading import Event

import pytest

from research_intelligence_hub.backpressure import ResearchHubBusyError, run_single_flight


def test_overlapping_build_is_rejected_and_event_loop_stays_responsive():
    started = Event()
    release = Event()

    def slow_build(**kwargs):
        started.set()
        release.wait(timeout=2)
        return {"ok": True, **kwargs}

    async def scenario():
        first = asyncio.create_task(run_single_flight(slow_build, note_id="one"))
        while not started.is_set():
            await asyncio.sleep(0.001)

        with pytest.raises(ResearchHubBusyError):
            await run_single_flight(slow_build, note_id="two")

        # If slow_build were running on the event loop this callback could not run.
        await asyncio.sleep(0)
        release.set()
        assert await first == {"ok": True, "note_id": "one"}

    asyncio.run(scenario())
