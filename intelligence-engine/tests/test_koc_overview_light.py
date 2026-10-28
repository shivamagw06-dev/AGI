"""KOC overview must stay light (no deep KIL/research packs) and cache."""

from __future__ import annotations


def test_koc_health_instant():
    from knowledge_operations.production import health

    h = health()
    assert h.get("ok") is True
    assert h.get("workstream_id") == "KOC-01"


def test_get_overview_light_and_cached(monkeypatch):
    from knowledge_operations import production as prod
    from knowledge_operations import desk as desk_mod

    calls = {"n": 0}

    def fake_build_desk(*, scope="TOP20", deep=False):
        calls["n"] += 1
        return {
            "ok": True,
            "scope": scope,
            "deep": deep,
            "coverage_table": [{"ticker": "RELIANCE"}],
            "kpis": {},
        }

    monkeypatch.setattr(desk_mod, "build_desk", fake_build_desk)
    prod._OVERVIEW_CACHE.clear()

    first = prod.get_overview(scope="TOP20", deep=False)
    second = prod.get_overview(scope="TOP20", deep=False)
    assert first["cache"] == "miss"
    assert second["cache"] == "hit"
    assert calls["n"] == 1
    assert first["endpoint"] == "overview"
    assert first["deep"] is False


def test_company_rows_light_does_not_call_integrate(monkeypatch):
    from knowledge_operations import desk as desk_mod

    called = {"integrate": 0}

    monkeypatch.setattr(desk_mod, "top20_tickers", lambda: ["RELIANCE"], raising=False)

    def fake_top20():
        return ["RELIANCE"]

    monkeypatch.setattr(
        "institutional_coverage_factory.universe.top20_tickers",
        fake_top20,
    )
    monkeypatch.setattr(
        "institutional_coverage_factory.universe.tier_for_ticker",
        lambda t: "TOP20",
    )
    monkeypatch.setattr(
        "institutional_coverage_factory.scorer.score.score_evidence_classes",
        lambda t, **k: {
            "coverage_pct": 40.0,
            "classes": {"annual_reports": {"present": True}},
            "missing_classes": ["shareholding"],
        },
    )
    monkeypatch.setattr(
        "institutional_coverage_factory.validator.icc.evaluate_icc",
        lambda t, score=None: {"institutional_coverage_complete": False, "status": "PARTIAL"},
    )

    def boom_integrate(*_a, **_k):
        called["integrate"] += 1
        raise RuntimeError("deep path only")

    import sys
    import types

    fake_layer = types.ModuleType("institutional_evidence.integration.layer")
    fake_layer.integrate_company = boom_integrate
    sys.modules["institutional_evidence.integration.layer"] = fake_layer

    rows = desk_mod._company_rows(scope="TOP20", deep=False)
    assert called["integrate"] == 0
    assert rows and rows[0]["ticker"] == "RELIANCE"
    assert rows[0]["deep"] is False
