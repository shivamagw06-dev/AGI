"""Single-flight protection for CMS Research Hub builds.

The API may be called by both embedded and external Node workers.  Keep the
gate in the intelligence service so process-local client queues cannot bypass
it, and execute the synchronous builder off the ASGI event loop.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any


class ResearchHubBusyError(RuntimeError):
    pass


_BUILD_LOCK = asyncio.Lock()


def build_in_progress() -> bool:
    return _BUILD_LOCK.locked()


async def run_single_flight(build: Callable[..., dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    if _BUILD_LOCK.locked():
        raise ResearchHubBusyError("research hub build already in progress")
    async with _BUILD_LOCK:
        return await asyncio.to_thread(build, **kwargs)
