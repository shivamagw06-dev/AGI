from __future__ import annotations

import asyncio

from app.api import routes


def test_health_exposes_render_revision(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-1")
    monkeypatch.setenv("RENDER_INSTANCE_ID", "instance-1")

    result = asyncio.run(routes.health())

    assert result["ok"] is True
    assert result["deployment"] == {
        "commit": "abc123",
        "service_id": "srv-1",
        "instance_id": "instance-1",
    }
