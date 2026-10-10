import asyncio
import threading

from app.api.routes import (
    continuous_gather_learn_dashboard,
    continuous_gather_learn_health,
)


def test_cgl_read_endpoints_run_disk_work_off_event_loop(monkeypatch):
    import continuous_gather_learn.production as production

    caller_thread = threading.get_ident()
    monkeypatch.setattr(
        production,
        "health",
        lambda: {"ok": True, "thread": threading.get_ident()},
    )
    monkeypatch.setattr(
        production,
        "dashboard",
        lambda: {"ok": True, "thread": threading.get_ident()},
    )

    health, dashboard = asyncio.run(
        _call_health_and_dashboard(
            continuous_gather_learn_health,
            continuous_gather_learn_dashboard,
        )
    )

    assert health["ok"] and dashboard["ok"]
    assert health["thread"] != caller_thread
    assert dashboard["thread"] != caller_thread


async def _call_health_and_dashboard(health_call, dashboard_call):
    return await health_call(), await dashboard_call()
