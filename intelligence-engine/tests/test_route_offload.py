from __future__ import annotations

import asyncio
import inspect
import time

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from app.core.route_offload import install_legacy_route_offload


def _build_app() -> FastAPI:
    router = APIRouter(prefix="/v1")

    @router.get("/health")
    async def health():
        return {"ok": True}

    @router.get("/slow")
    async def slow():
        time.sleep(0.25)
        return {"ok": True}

    app = FastAPI()
    app.include_router(router)
    return app


def test_offloads_legacy_routes_but_exempts_health(monkeypatch):
    monkeypatch.setenv("AGI_ROUTE_OFFLOAD_ENABLED", "true")
    app = _build_app()

    assert install_legacy_route_offload(app, exempt_paths={"/v1/health"}) == 1

    routes = {
        route.path: route
        for route in app.routes
        if isinstance(route, APIRoute)
    }
    assert inspect.iscoroutinefunction(routes["/v1/health"].dependant.call)
    assert not inspect.iscoroutinefunction(routes["/v1/slow"].dependant.call)


@pytest.mark.asyncio
async def test_health_remains_responsive_during_blocking_legacy_request(monkeypatch):
    monkeypatch.setenv("AGI_ROUTE_OFFLOAD_ENABLED", "true")
    app = _build_app()
    install_legacy_route_offload(app, exempt_paths={"/v1/health"})

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        slow_request = asyncio.create_task(client.get("/v1/slow"))
        await asyncio.sleep(0.03)
        started = time.monotonic()
        health_response = await client.get("/v1/health")
        health_elapsed = time.monotonic() - started
        slow_response = await slow_request

    assert health_response.json() == {"ok": True}
    assert slow_response.status_code == 200
    assert health_elapsed < 0.15
