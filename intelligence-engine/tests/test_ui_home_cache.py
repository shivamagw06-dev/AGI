import asyncio
import time

import pytest

from app.api import routes


class _View:
    def __init__(self, payload):
        self.payload = payload

    def model_dump(self, *, mode):
        assert mode == "json"
        return self.payload


class _FakeUi:
    def __init__(self, *, delay=0.0):
        self.calls = 0
        self.delay = delay

    def home(self):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        return _View({"generation": self.calls})


def _clear_cache():
    if hasattr(routes._cached_ui_home, "_cache"):
        delattr(routes._cached_ui_home, "_cache")


@pytest.mark.asyncio
async def test_ui_home_reuses_the_process_snapshot(monkeypatch):
    fake = _FakeUi()
    monkeypatch.setattr(routes, "_ui", fake)
    _clear_cache()

    first = await routes.ui_home()
    second = await routes.ui_home()

    assert first == {"generation": 1}
    assert second == first
    assert fake.calls == 1


@pytest.mark.asyncio
async def test_ui_home_collapses_concurrent_refreshes(monkeypatch):
    fake = _FakeUi(delay=0.05)
    monkeypatch.setattr(routes, "_ui", fake)
    _clear_cache()

    results = await asyncio.gather(*(routes.ui_home() for _ in range(4)))

    assert results == [{"generation": 1}] * 4
    assert fake.calls == 1
