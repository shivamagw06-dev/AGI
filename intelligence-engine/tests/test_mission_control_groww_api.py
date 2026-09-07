"""Mission Control must catalogue Groww and other .env APIs."""

from __future__ import annotations

from mission_control.aggregate import build_mission_control


class _FakeDash:
    def model_dump(self, mode: str = "json"):
        return {
            "overall_health": "healthy",
            "provider_health": [
                {"provider_id": "indianapi", "status": "healthy", "configured": True},
                {"provider_id": "yahoo", "status": "healthy", "configured": True},
            ],
            "engine_status": {},
            "platform_status": {},
        }


class _FakeIoc:
    def dashboard(self):
        return _FakeDash()


def test_api_status_includes_groww_and_env_apis():
    desk = build_mission_control(ioc_service=_FakeIoc())
    names = {str(p.get("name") or "").lower() for p in desk.get("api_status") or []}
    assert "groww" in names
    assert "indianapi" in names or "indian api" in names
    assert any("finnhub" in n for n in names)
    assert any("fred" in n for n in names)
    assert any("newsapi" in n for n in names)
    assert any("perplexity" in n for n in names)
    assert any("alpha" in n for n in names)
