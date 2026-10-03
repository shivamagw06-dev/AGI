"""CIO-01 — Comparative Intelligence Office deterministic tests."""

from __future__ import annotations

from comparative_intelligence.compare import key_differences, side_by_side
from comparative_intelligence.coordinator import ComparisonCoordinator, compare
from comparative_intelligence.production import (
    compare_companies,
    health,
    query,
    soft_slice_mission_control,
)
from comparative_intelligence.routing import extract_tickers, route_comparison
from comparative_intelligence.schema import (
    CIO01_VERSION,
    CIO01_WORKSTREAM_ID,
    ICR_SECTIONS,
    MODULE_FIRE01,
    MODULE_FIRE02,
    MODULE_FIRE05,
    MODULE_FIRE06,
)
from comparative_intelligence import store as cio_store


def _pack(
    ticker: str,
    *,
    quality: float,
    growth: float,
    balance: float,
    cash: float = 0.6,
    capital: float = 0.55,
) -> dict[str, dict]:
    return {
        MODULE_FIRE01: {
            "ticker": ticker,
            "period": "FY2026",
            "confidence": 0.8,
            "trends": [
                {
                    "id": f"{ticker}:t-rev",
                    "metric": "revenue",
                    "direction": "improving" if growth >= 0.7 else "stable",
                    "evidence_ids": [f"ev:{ticker}:rev"],
                    "confidence": 0.8,
                },
                {
                    "id": f"{ticker}:t-om",
                    "metric": "operating_margin",
                    "direction": "improving" if growth >= 0.75 else "stable",
                    "evidence_ids": [f"ev:{ticker}:om"],
                    "confidence": 0.75,
                },
            ],
            "evidence_ids": [f"ev:{ticker}:rev", f"ev:{ticker}:om"],
        },
        MODULE_FIRE02: {
            "ticker": ticker,
            "period": "FY2026",
            "confidence": 0.76,
            "relationships": [
                {
                    "id": f"{ticker}:r-lev",
                    "name": "leverage",
                    "status": "strong" if balance >= 0.7 else "moderate",
                    "evidence_ids": [f"ev:{ticker}:lev"],
                    "confidence": 0.7,
                }
            ],
            "evidence_ids": [f"ev:{ticker}:lev"],
        },
        "FIRE-03": {
            "ticker": ticker,
            "period": "FY2026",
            "confidence": 0.7,
            "facts": [
                {
                    "id": f"{ticker}:bf1",
                    "text": f"{ticker} business profile fact",
                    "evidence_ids": [f"ev:{ticker}:bf"],
                    "confidence": 0.7,
                }
            ],
            "evidence_ids": [f"ev:{ticker}:bf"],
        },
        "FIRE-04": {
            "ticker": ticker,
            "period": "FY2026",
            "confidence": 0.65,
            "assessments": [
                {
                    "id": f"{ticker}:a1",
                    "claim": "Strategy",
                    "status": "Supported",
                    "evidence_ids": [f"ev:{ticker}:ef"],
                    "confidence": 0.65,
                }
            ],
            "evidence_ids": [f"ev:{ticker}:ef"],
        },
        MODULE_FIRE05: {
            "ticker": ticker,
            "period": "FY2026",
            "confidence": 0.68,
            "objectives": [
                {
                    "objective_id": f"{ticker}:obj1",
                    "title": "Margin expansion",
                    "status": "Delivered" if quality >= 0.7 else "Partial",
                    "evidence_ids": [f"ev:{ticker}:me"],
                    "confidence": 0.68,
                }
            ],
            "evidence_ids": [f"ev:{ticker}:me"],
        },
        MODULE_FIRE06: {
            "ticker": ticker,
            "period": "FY2026",
            "confidence": 0.74,
            "overall_score": quality,
            "overall_label": "solid" if quality >= 0.7 else "mixed",
            "pillars": [
                {"pillar": "growth", "score": growth, "evidence_ids": [f"ev:{ticker}:g"], "confidence": 0.8},
                {
                    "pillar": "balance_sheet",
                    "score": balance,
                    "evidence_ids": [f"ev:{ticker}:bs"],
                    "confidence": 0.76,
                },
                {"pillar": "cash", "score": cash, "evidence_ids": [f"ev:{ticker}:c"], "confidence": 0.7},
                {
                    "pillar": "capital_allocation",
                    "score": capital,
                    "evidence_ids": [f"ev:{ticker}:ca"],
                    "confidence": 0.66,
                },
                {
                    "pillar": "profitability",
                    "score": (growth + cash) / 2,
                    "evidence_ids": [f"ev:{ticker}:p"],
                    "confidence": 0.7,
                },
            ],
            "evidence_ids": [f"ev:{ticker}:g", f"ev:{ticker}:bs", f"ev:{ticker}:c"],
        },
    }


def _universe() -> dict[str, dict[str, dict]]:
    return {
        "HDFCBANK": _pack("HDFCBANK", quality=0.82, growth=0.78, balance=0.85, cash=0.8, capital=0.75),
        "ICICIBANK": _pack("ICICIBANK", quality=0.71, growth=0.70, balance=0.72, cash=0.68, capital=0.62),
    }


def test_health():
    h = health()
    assert h["workstream_id"] == CIO01_WORKSTREAM_ID
    assert h["version"] == CIO01_VERSION
    assert h["compares_only"] is True
    assert h["not_fire_07"] is True
    assert h["buy_sell"] is False
    assert h["never_recalculates"] is True


def test_extract_tickers():
    assert extract_tickers(None, explicit=["hdfcbank", "icicibank"]) == ["HDFCBANK", "ICICIBANK"]
    assert "TCS" in extract_tickers("Compare TCS and INFY")
    assert "INFY" in extract_tickers("Compare TCS and INFY")


def test_routing_balance_sheet():
    r = route_comparison("Which private bank has the strongest balance sheet?")
    assert r["comparison_type"] == "Balance Sheet Comparison"
    assert set(r["modules"]) == {MODULE_FIRE02, MODULE_FIRE06}


def test_routing_execution():
    r = route_comparison("Which companies consistently execute on capital allocation?")
    # capital allocation rule may win before execution — either is valid orchestration
    assert r["compares_only"] is True
    assert MODULE_FIRE05 in r["modules"] or MODULE_FIRE06 in r["modules"]


def test_routing_compare_default():
    r = route_comparison("Compare HDFCBANK and ICICIBANK")
    assert r["comparison_type"] == "Institutional Comparison"
    assert MODULE_FIRE06 in r["modules"]


def test_side_by_side_passthrough_ranking():
    uni = {
        t: {m: {"ok": True, "module": m, "payload": p} for m, p in packs.items()}
        for t, packs in _universe().items()
    }
    board = side_by_side(["HDFCBANK", "ICICIBANK"], uni, "business_quality_comparison")
    ranking = board["ranking_by_passthrough_score"]
    assert ranking[0]["ticker"] == "HDFCBANK"
    assert ranking[0]["score"] == 0.82
    assert ranking[1]["score"] == 0.71


def test_key_differences_preserve_scores():
    uni = {
        t: {m: {"ok": True, "module": m, "payload": p} for m, p in packs.items()}
        for t, packs in _universe().items()
    }
    diffs = key_differences(["HDFCBANK", "ICICIBANK"], uni)
    assert diffs
    assert diffs[0]["higher"] == "HDFCBANK"
    assert "gap" in diffs[0]
    assert diffs[0]["evidence_ids"]


def test_compare_orchestration():
    cio_store.reset_for_tests()
    icr = compare(
        tickers=["HDFCBANK", "ICICIBANK"],
        question="Compare HDFCBANK and ICICIBANK",
        prebuilt_map=_universe(),
    )
    assert icr["tickers"] == ["HDFCBANK", "ICICIBANK"]
    assert icr["guardrails"]["compares_only"] is True
    assert icr["guardrails"]["recalculates"] is False
    assert icr["company_payloads"]["HDFCBANK"][MODULE_FIRE06]["payload"]["overall_score"] == 0.82
    keys = {s["key"] for s in icr["sections"]}
    assert set(ICR_SECTIONS).issubset(keys)


def test_provenance_on_blocks():
    icr = ComparisonCoordinator().compare(
        tickers=["HDFCBANK", "ICICIBANK"],
        prebuilt_map=_universe(),
    )
    for sec in icr["sections"]:
        for b in sec["blocks"]:
            assert "module" in b
            assert "evidence_ids" in b
            assert "confidence" in b


def test_balance_sheet_modules_only():
    icr = compare(
        tickers=["HDFCBANK", "ICICIBANK"],
        question="How strong is the balance sheet comparatively?",
        prebuilt_map=_universe(),
    )
    assert set(icr["modules_invoked"]) == {MODULE_FIRE02, MODULE_FIRE06}


def test_no_score_mutation():
    uni = _universe()
    original = uni["HDFCBANK"][MODULE_FIRE06]["overall_score"]
    icr = compare(tickers=["HDFCBANK", "ICICIBANK"], prebuilt_map=uni)
    assert (
        icr["company_payloads"]["HDFCBANK"][MODULE_FIRE06]["payload"]["overall_score"] == original
    )
    assert uni["HDFCBANK"][MODULE_FIRE06]["overall_score"] == original


def test_production_and_metrics():
    cio_store.reset_for_tests()
    pack = compare_companies(
        ["HDFCBANK", "ICICIBANK"],
        question="Compare the banks",
        prebuilt_map=_universe(),
    )
    assert pack["ok"] is True
    assert pack["workstream_id"] == CIO01_WORKSTREAM_ID
    assert pack["compares_only"] is True
    q = query(
        tickers=["TCS", "INFY"],
        question="Compare TCS vs INFY on business quality",
        prebuilt_map={
            "TCS": _pack("TCS", quality=0.8, growth=0.75, balance=0.8),
            "INFY": _pack("INFY", quality=0.72, growth=0.7, balance=0.74),
        },
    )
    assert q["tickers"] == ["TCS", "INFY"]
    m = cio_store.metrics()
    assert m["comparisons_served"] == 2
    assert m["panels"]["comparisons_served"] == 2


def test_soft_slice():
    cio_store.reset_for_tests()
    compare_companies(["HDFCBANK", "ICICIBANK"], prebuilt_map=_universe())
    slice_ = soft_slice_mission_control()
    assert slice_["workstream_id"] == CIO01_WORKSTREAM_ID
    assert "comparisons_served" in slice_["panels"]


def test_requires_two_tickers():
    try:
        compare(tickers=["TCS"], prebuilt_map={"TCS": _pack("TCS", quality=0.7, growth=0.7, balance=0.7)})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "two tickers" in str(exc)
