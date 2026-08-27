"""IC-10 Committee Certification v2.0 — unit tests with injected evidence rows."""

from __future__ import annotations

from committee_certification_v2.evaluate import (
    evidence_completeness,
    governance_integrity,
    sector_differentiation,
    valuation_intelligence,
)
from committee_certification_v2.production import health, run_certification
from committee_certification_v2.schema import AREA_WEIGHTS, CERT_VERSION, IC10_V2_UNIVERSE
from committee_certification_v2.score import grade_for, score_company


def _row(
    display: str,
    *,
    sector: str = "banks",
    resolve: str | None = None,
    pe: float = 20.0,
    peer_pe: float = 18.0,
) -> dict:
    resolve = resolve or display
    return {
        "display": display,
        "resolve": resolve,
        "sector_key": sector,
        "market": {"ok": True, "ltp": 100.0, "provider": "injected"},
        "ownership": {
            "ok": True,
            "promoter": 0.0 if display == "HDFCBANK" else 72.0,
            "fii": 52.0,
            "dii": 28.0,
            "mutual_funds": 18.0,
            "insurance": 6.0,
            "promoter_pledge_pct": 0.0,
            "qoq": {"fii": -0.2},
            "quarter_history": [{"period_end": "2026-06-30"}],
            "intelligence": {"observations": ["Institution dominated."]},
        },
        "earnings": {
            "ok": True,
            "coverage_pct": 100,
            "income_available": True,
            "balance_sheet_available": True,
            "cash_flow_available": True,
            "ttm_available": True,
            "ttm": {"available": True},
            "latest_quarter": {"income_statement": {"revenue_from_operations": 1e11}},
            "latest_annual": {
                "balance_sheet": {"total_equity": 1e12},
                "cash_flow": {"operating_cash_flow": 1e10},
            },
            "metrics": {
                "yoy_growth": {"revenue_growth_pct": 12.0},
                "latest_quarter": {"ebitda_margin_pct": 30.0},
                "latest_annual": {"roe_pct": 16.0, "pat_margin_pct": 20.0},
            },
            "intelligence": {"observations": ["TTM earnings available."]},
        },
        "valuation": {
            "ok": True,
            "issues_recommendations": False,
            "modifies_decision_engine": False,
            "current": {"pe": pe, "pb": 2.5, "ev_ebitda": 12.0, "peg": 1.4},
            "relative": {
                "pe": {
                    "current": pe,
                    "peer_median": peer_pe,
                    "premium_pct": round((pe / peer_pe - 1) * 100, 1),
                    "reasons": ["Higher ROE"],
                }
            },
            "historical": {"pe": {"median": 19.0, "high": 28.0, "low": 12.0, "percentile": 62.0}},
            "growth": {"eps_cagr_3y": 14.0},
            "peer_universe": {
                "resolved": True,
                "primary_peers": ["ICICIBANK", "AXISBANK"],
                "industry": "Banks",
            },
            "observations": ["Trading above peer median valuation.", "Premium supported by superior ROE."],
            "stance": "premium justified",
            "quality": {"roe": 18.0},
        },
        "cid": {
            "ticker": resolve,
            "ownership": {"promoter": 0.0, "fii": 52.0},
            "valuation": {"pe": pe, "peer_pe": peer_pe, "engine": "valuation_intelligence"},
            "financial_statements": {"income_statement": {"quarterly": [{}]}},
            "identity": {"sector_id": sector},
            "sector_framework": {"sector_id": sector},
        },
        "company_analysis": {
            "enabled": True,
            "investment_thesis": f"{display} franchise quality vs peers — evidence-backed.",
            "executive_summary": f"{display}: readiness assessed; not a recommendation.",
            "bull_case": "Margin durability.",
            "bear_case": "Cycle risk.",
            "risks": ["Credit cost", "Regulation"],
            "catalysts": ["Earnings", "Multiple re-rating"],
            "financial_intelligence": {"coverage_pct": 95, "narrative": "Strong TTM."},
            "valuation_intelligence": {"coverage_pct": 90, "current_pe": pe},
            "sector_intelligence": {
                "sector_id": sector,
                "reasoning": [
                    "Banking analysis prioritises CASA, NIM, credit cost, GNPA/NNPA, PCR, loan & deposit growth."
                    if sector == "banks"
                    else f"Sector lens emphasising {sector} KPIs."
                ],
                "priority_metrics": ["CASA", "NIM", "GNPA"] if sector == "banks" else ["margin"],
            },
            "recommendation_readiness": {"overall": 82, "gate": "Eligible", "band": "moderate"},
            "business_overview": "Institutional franchise.",
        },
        "decision": {
            "enabled": True,
            "summary": "Gate moderate — missing none critical; would change with higher evidence coverage.",
            "readiness_gate": {"band": "moderate_conviction_allowed", "overall": 82, "missing": []},
            "investment_thesis": "Long-term compounding case conditional on evidence.",
        },
        "latency_ms": 10,
        "errors": [],
    }


def test_health_and_universe():
    h = health()
    assert h["version"] == CERT_VERSION
    assert "TATAMOTORS" in h["universe"]
    assert h["resolve_map"]["TATAMOTORS"] == "TMPV"
    assert len(IC10_V2_UNIVERSE) == 10
    assert abs(sum(AREA_WEIGHTS.values()) - 100.0) < 1e-6


def test_evidence_and_valuation_pass():
    row = _row("HDFCBANK", sector="banks")
    e = evidence_completeness(row)
    assert e["pass"] is True
    assert e["score_pct"] >= 95
    v = valuation_intelligence(row)
    assert v["pass"] is True
    s = sector_differentiation(row)
    assert s["score_pct"] >= 50
    assert "casa" in s["vocab_hits"] or s["specific_reasoning"]


def test_governance_suite_pass():
    rows = [_row("TCS", sector="it_services"), _row("HAL", sector="defence")]
    g = governance_integrity(rows)
    assert g["pass"] is True
    assert g["checks"]["no_evidence_engine_buy_sell"] is True
    assert g["checks"]["gate_high_threshold"] is True


def test_run_certification_injected():
    rows = [
        _row("HDFCBANK", sector="banks"),
        _row("TCS", sector="it_services", pe=22, peer_pe=20),
        _row("ULTRACEMCO", sector="cement", pe=40, peer_pe=38),
    ]
    # enrich cement sector reasoning
    rows[2]["company_analysis"]["sector_intelligence"]["reasoning"] = [
        "Cement analysis prioritises capacity, utilisation, fuel/petcoke costs, realisations."
    ]
    result = run_certification(injected_rows=rows, persist=False, robustness_runs=1)
    assert result["aggregate"]["total_score"] >= 80
    assert result["unknown_drift"] == 0
    assert grade_for(result["aggregate"]["total_score"]) in {
        "Institutional Ready",
        "Production Ready",
        "Strong Beta",
        "Research Platform",
    }
    scored = score_company(rows[0])
    assert scored["verdict"] in {"Committee Ready", "Watchlist", "Deferred", "Research Required"}
