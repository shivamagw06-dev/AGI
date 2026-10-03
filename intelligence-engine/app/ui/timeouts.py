"""Hard timeouts for Ask AGI external dependencies.

Collectors (FAA/Playwright) must never sit on the Ask request path.
Optional live deps get a short ceiling; on timeout Ask continues degraded.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# Shared pool so Ask does not spawn unbounded threads per soft-call.
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ask-ext")


def ask_slim_enabled() -> bool:
    """Starter-plan safe Ask path: skip live LEO/ECP/AIL fan-out that OOMs Render.

    Default **on**. Set ``ASK_SLIM=0`` only when profiling proves headroom.
    """
    return str(os.environ.get("ASK_SLIM", "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def ask_ext_timeout_sec(default: float = 5.0) -> float:
    raw = (os.environ.get("ASK_EXT_TIMEOUT_SEC") or "").strip()
    if not raw:
        return default
    try:
        return max(0.5, float(raw))
    except ValueError:
        return default


def call_with_timeout(
    fn: Callable[..., T],
    *args: Any,
    timeout_sec: float | None = None,
    default: T | None = None,
    **kwargs: Any,
) -> tuple[T | None, bool]:
    """Run ``fn`` with a hard wall-clock timeout.

    Returns ``(result, timed_out)``. On timeout/error returns ``(default, True/False)``.
    """
    budget = ask_ext_timeout_sec() if timeout_sec is None else timeout_sec
    try:
        fut = _POOL.submit(lambda: fn(*args, **kwargs))
        return fut.result(timeout=budget), False
    except FuturesTimeout:
        return default, True
    except Exception:
        return default, False
