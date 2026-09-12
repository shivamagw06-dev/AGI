"""P3.1 Knowledge Delta Engine — unit tests (injected memory, no live market)."""

from __future__ import annotations

from knowledge_delta_engine.diff import build_memory_delta
from knowledge_delta_engine.explain import explain_observation
from knowledge_delta_engine.production import health, package_for_ask_agi
from knowledge_delta_engine.schema import DELTA_TYPES, ENGINE_CODE, VERSION
from knowledge_delta_engine.util import memory_fingerprint


def _injected() -> dict:
    annual = []
    for i, mult in enumerate([0.7, 0.85, 1.0, 1.15, 1.3, 1.45]):
        y = 2020 + i
        annual.append(
            {
                "period_end": f"{y}-03-31",
                "fiscal_year_label": f"FY{y % 100:02d}",
                "income_statement": {
                    "revenue_from_operations": 1e12 * mult,
                    "ebitda": 2.5e11 * mult,
                    "pat": 2e11 * mult,
                    "pat_owners": 2e11 * mult,
                    "eps_basic": 40 * mult,
                },
                "balance_sheet": {"total_equity": 8e11, "total_debt": 5e10, "cash": 1e11},
                "cash_flow": {"operating_cash_flow": 2.2e11, "free_cash_flow": 1.8e11},
            }
        )
    periods = [
        "2023-06-30",
        "2023-09-30",
        "2023-12-31",
        "2024-03-31",
        "2024-06-30",
        "2024-09-30",
        "2024-12-31",
        "2025-03-31",
    ]
    history = []
    for i, (pe, fii) in enumerate(zip(periods, [44, 45, 46, 47, 48, 49, 50, 51])):
        history.append(
            {
                "period_end": pe,
                "promoter": 72.0,
                "fii": float(fii),
                "dii": 12.0,
                "mutual_funds": 10.0 - i * 0.2,
                "insurance": 4.5,
                "promoter_pledge_pct": 0.0,
            }
        )
    return {
        "market": {"ok": True, "ltp": 4000.0, "provider": "injected", "as_of": "2026-07-28"},
        "ownership": {
            "ok": True,
            "promoter": 72.0,
            "fii": 51.0,
            "dii": 12.0,
            "mutual_funds": 8.6,
            "insurance": 4.5,
            "promoter_pledge_pct": 0.0,
            "quarter_history": history,
            "as_of_quarter": "2025-12-30",
            "source": "injected",
        },
        "earnings": {
            "ok": True,
            "coverage_pct": 100,
            "source": "injected",
            "annual_history": list(reversed(annual)),
            "quarter_history": [],
            "ttm": {
                "available": True,
                "income_statement": {
                    "revenue_from_operations": 1.45e12,
                    "ebitda": 3.6e11,
                    "pat": 2.9e11,
                    "pat_owners": 2.9e11,
                    "eps_basic": 58.0,
                },
            },
            "metrics": {
                "yoy_growth": {"revenue_growth_pct": 12.0, "pat_growth_pct": 11.0, "eps_growth_pct": 10.0},
                "qoq_growth": {"revenue_growth_pct": 2.0},
                "latest_annual": {
                    "roe_pct": 25.0,
                    "roce_pct": 28.0,
                    "ebitda_margin_pct": 25.0,
                    "pat_margin_pct": 20.0,
                },
                "latest_quarter": {"ebitda_margin_pct": 25.0, "pat_margin_pct": 20.0},
            },
        },
        "valuation": {
            "ok": True,
            "current": {"pe": 22.0, "pb": 8.0, "ev_ebitda": 14.0, "peg": 1.5},
            "historical": {
                "pe": {
                    "window": "10Y",
                    "median": 20.0,
                    "high": 30.0,
                    "low": 12.0,
                    "current": 22.0,
                    "percentile": 60.0,
                    "observations": 10,
                }
            },
            "relative": {
                "pe": {
                    "current": 22.0,
                    "peer_median": 20.0,
                    "premium_pct": 10.0,
                    "reasons": ["Higher ROE"],
                }
            },
            "peer_universe": {
                "resolved": True,
                "primary_peers": ["INFY", "HCLTECH"],
                "sector": "Information Technology",
                "industry": "IT Services",
                "source": "valuation_peer_registry",
            },
            "stance": "premium versus peers",
            "observations": ["Trading above peer median valuation."],
        },
    }


def _compile_mem(**kwargs):
    from company_memory.production import compile as memory_compile

    return memory_compile(
        "TCS",
        injected=_injected(),
        persist=False,
        skip_live=True,
        allow_live_prices=False,
        use_cache=False,
        **kwargs,
    )


def test_health_catalog():
    h = health()
    assert h["engine"] == ENGINE_CODE
    assert h["version"] == VERSION
    assert h["never_overwrite_silently"] is True
    assert h["modifies_decision_engine"] is False
    assert set(DELTA_TYPES).issubset(set(h["delta_types"]))


def test_memory_delta_detects_updates():
    a = _compile_mem()
    b = dict(a)
    fh = dict(b.get("financial_history") or {})
    rev = dict(fh.get("revenue") or {})
    rev["ttm"] = float(rev.get("ttm") or 1e12) * 1.12
    rev["yoy"] = 12.0
    fh["revenue"] = rev
    pat = dict(fh.get("pat") or {})
    pat["ttm"] = float(pat.get("ttm") or 2e11) * 1.19
    fh["pat"] = pat
    b["financial_history"] = fh

    oh = dict(b.get("ownership_history") or {})
    latest = dict(oh.get("latest") or {})
    latest["fii"] = float(latest.get("fii") or 50) + 0.8
    oh["latest"] = latest
    b["ownership_history"] = oh

    vh = dict(b.get("valuation_history") or {})
    rel = dict(vh.get("relative") or {})
    pe = dict(rel.get("pe") or {})
    pe["premium_pct"] = float(pe.get("premium_pct") or 10) + 5
    rel["pe"] = pe
    vh["relative"] = rel
    b["valuation_history"] = vh

    delta = build_memory_delta(a, b)
    assert delta["status"] == "UPDATED"
    assert delta["identical_to_prior"] is False
    assert (delta.get("sections") or {}).get("financial", {}).get("changed") is True
    assert any("Revenue" in o or "PAT" in o for o in delta.get("observations") or [])
    assert any("premium" in o.lower() for o in delta.get("observations") or [])


def test_identical_evidence_noop(monkeypatch):
    from knowledge_delta_engine import compile as cmod

    mem = _compile_mem()
    assert mem["ok"] is True
    fp = memory_fingerprint(mem)

    monkeypatch.setattr(cmod, "load_current", lambda entity: dict(mem))

    def _same_compile(entity, **kwargs):
        out = dict(mem)
        out["compiled_at"] = "2099-01-01T00:00:00+00:00"
        out["latency_ms"] = 999
        assert memory_fingerprint(out) == fp
        return out

    monkeypatch.setattr("company_memory.production.compile", _same_compile)

    out = cmod.incremental_compile("TCS", persist=False, injected=_injected())
    assert out["noop"] is True
    assert out["rebuilt"] is False
    assert (out.get("memory_delta") or {}).get("status") == "UNCHANGED"
    assert out.get("delta_engine", {}).get("version_written") is False


def test_version_persist_skips_identical(monkeypatch):
    from knowledge_delta_engine import versioning as vmod

    mem = _compile_mem()
    calls = {"put": 0}

    class FakeStore:
        def get_object(self, kind, key):
            if kind == "company_memory":
                return dict(mem)
            if kind == "company_memory_meta":
                return {
                    "entity": "TCS",
                    "current_version": 3,
                    "versions": [{"version": 1}, {"version": 2}, {"version": 3}],
                }
            return None

        def put_object(self, *a, **k):
            calls["put"] += 1

        def put_series(self, *a, **k):
            return None

    monkeypatch.setattr(vmod, "_store", lambda: FakeStore())
    result = vmod.persist_versioned(mem, reason="test", memory_delta={"status": "UNCHANGED"})
    assert result["noop"] is True
    assert result["written"] is False
    assert calls["put"] == 0


def test_explain_management_confidence():
    mem = _compile_mem()
    exp = explain_observation(mem, topic="management_confidence")
    assert exp["topic"] == "management_confidence"
    assert exp["conclusion"] in {"HIGH", "MODERATE", "LOW"}
    assert "because" in exp
    assert exp["provenance"]["sources"]


def test_package_for_ask_agi_no_recommendation(monkeypatch):
    from knowledge_delta_engine import compile as cmod

    mem = _compile_mem()
    monkeypatch.setattr(cmod, "load_current", lambda entity: None)

    def _compile(entity, **kwargs):
        return dict(mem)

    monkeypatch.setattr("company_memory.production.compile", _compile)
    pkg = package_for_ask_agi("TCS", persist=False, injected=_injected())
    assert pkg["enabled"] is True
    assert pkg["recommendation_policy"] == "delta_memory_no_buy_sell"
    assert "memory_delta" in pkg
