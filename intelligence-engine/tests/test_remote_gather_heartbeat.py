from __future__ import annotations

import time

from continuous_gather_learn import persist
from scripts import gather_worker


def test_remote_heartbeat_uses_server_time_and_is_fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path))

    row = persist.write_remote_gather_heartbeat(
        {
            "phase": "running",
            "role": "gather_worker",
            "unix_ts": 1,
            "unexpected": "discard-me",
        }
    )

    assert row["source"] == "authenticated_remote_worker"
    assert row["unix_ts"] > time.time() - 5
    assert "unexpected" not in row
    assert persist.read_gather_heartbeat()["fresh"] is True


def test_worker_publishes_authenticated_remote_heartbeat(monkeypatch):
    monkeypatch.setenv("INTELLIGENCE_ENGINE_URL", "engine.internal")
    monkeypatch.setenv("INTELLIGENCE_ENGINE_TOKEN", "test-token")
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def raise_for_status():
            return None

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, json=json, timeout=timeout)
        return Response()

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    result = gather_worker._publish_remote_heartbeat({"phase": "ready"})

    assert result == {"published": True, "status_code": 200}
    assert captured["url"] == "https://engine.internal/v1/continuous-gather-learn/heartbeat"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    assert captured["json"]["phase"] == "ready"
    assert "test-token" not in str(result)
