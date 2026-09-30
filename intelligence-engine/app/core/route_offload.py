"""Keep legacy blocking API handlers off FastAPI's main event loop."""

from __future__ import annotations

import asyncio
import inspect
import os
from functools import wraps
from typing import Any, Callable

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute, request_response


def _enabled() -> bool:
    return os.getenv("AGI_ROUTE_OFFLOAD_ENABLED", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def install_legacy_route_offload(
    app: FastAPI | APIRouter,
    *,
    exempt_paths: set[str] | None = None,
) -> int:
    """Run legacy async handlers in FastAPI's worker thread pool.

    The intelligence API predates its current workload and many endpoints are
    declared ``async`` while calling synchronous warehouse/model code. FastAPI
    therefore runs them on the main event loop, where one long calculation can
    also stall health checks. Replacing the already-built dependency callable
    with a synchronous adapter makes FastAPI use its standard AnyIO thread pool
    without changing request validation or endpoint contracts.
    """
    if not _enabled():
        return 0

    exempt = exempt_paths or set()
    installed = 0
    # FastAPI 0.141 stores included routers as lazy branches, not APIRoutes.
    # Traverse these before the application starts serving requests.
    def routes(container, prefix=""):
        for route in container.routes:
            original = getattr(route, "original_router", None)
            if original is not None:
                yield from routes(original, prefix + route.include_context.prefix)
            else:
                yield prefix + getattr(route, "path", ""), route

    for path, route in routes(app):
        if not isinstance(route, APIRoute) or path in exempt:
            continue

        endpoint = route.dependant.call
        if endpoint is None or not inspect.iscoroutinefunction(endpoint):
            continue

        @wraps(endpoint)
        def offloaded_endpoint(
            _endpoint: Callable[..., Any] = endpoint,
            **kwargs: Any,
        ) -> Any:
            return asyncio.run(_endpoint(**kwargs))

        # FastAPI now unwraps decorators when detecting coroutine handlers.
        # Preserve the API signature without pointing to an async __wrapped__.
        offloaded_endpoint.__signature__ = inspect.signature(endpoint, eval_str=True)
        del offloaded_endpoint.__wrapped__
        route.endpoint = offloaded_endpoint
        route.dependant.call = offloaded_endpoint
        # APIRoute caches ``is_coroutine`` inside its request handler during
        # construction, so rebuild that handler after replacing the callable.
        route.app = request_response(route.get_route_handler())
        installed += 1

    if hasattr(app, "state"):
        app.state.legacy_routes_offloaded = installed
    return installed
