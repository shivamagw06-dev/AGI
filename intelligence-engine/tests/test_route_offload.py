from __future__ import annotations

import asyncio
import inspect
import time
import threading

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

    container = next((r.original_router for r in app.routes
                      if hasattr(r, "original_router")), app)
    routes = {route.path: route for route in container.routes if isinstance(route, APIRoute)}
    assert inspect.iscoroutinefunction(routes["/v1/health"].dependant.call)
    assert not inspect.iscoroutinefunction(routes["/v1/slow"].dependant.call)


@pytest.mark.asyncio
async def test_health_remains_responsive_during_blocking_legacy_request(monkeypatch):
    monkeypatch.setenv("AGI_ROUTE_OFFLOAD_ENABLED", "true")
    app = _build_app()
    assert install_legacy_route_offload(app, exempt_paths={"/v1/health"}) == 1

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        started = time.monotonic()
        slow_request = asyncio.create_task(client.get("/v1/slow"))
        await asyncio.sleep(0.03)
        health_response = await client.get("/v1/health")
        health_elapsed = time.monotonic() - started
        slow_response = await slow_request

    assert health_response.json() == {"ok": True}
    assert slow_response.status_code == 200
    assert health_elapsed < 0.15


@pytest.mark.asyncio
async def test_nested_router_preserves_auth_validation_and_sync_execution(monkeypatch):
    from fastapi import Depends, Header, HTTPException

    monkeypatch.setenv("AGI_ROUTE_OFFLOAD_ENABLED", "true")
    loop_thread = threading.get_ident()
    app = FastAPI()
    parent = APIRouter(prefix="/v1")
    child = APIRouter()

    def auth(x_test_token: str | None = Header(default=None)):
        if x_test_token != "test-only":
            raise HTTPException(status_code=401)

    @child.get("/item/{item_id}", dependencies=[Depends(auth)])
    async def item(item_id: int, limit: int = 2):
        return {"item_id": item_id, "limit": limit,
                "worker": threading.get_ident() != loop_thread}

    parent.include_router(child, prefix="/nested")
    app.include_router(parent)
    assert install_legacy_route_offload(app) == 1
    assert install_legacy_route_offload(app) == 0
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/v1/nested/item/7")).status_code == 401
        headers = {"x-test-token": "test-only"}
        response = await client.get("/v1/nested/item/7?limit=3", headers=headers)
        assert response.json() == {"item_id": 7, "limit": 3, "worker": True}
        assert (await client.get("/v1/nested/item/not-an-int", headers=headers)).status_code == 422
    assert "/v1/nested/item/{item_id}" in app.openapi()["paths"]
