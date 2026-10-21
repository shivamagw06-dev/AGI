"""Safe sync wrapper for awaiting coroutines from sync soft-bridges.

Fixes nested-loop failures when FastAPI already has a running event loop
(asyncio.run / new_event_loop().run_until_complete both fail in that case).
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agi-async-run")


def run_coro(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine from sync code, including when a loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Running loop present — execute in a worker thread with its own loop
    fut = _POOL.submit(asyncio.run, coro)
    return fut.result(timeout=120)
