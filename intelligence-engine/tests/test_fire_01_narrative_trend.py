"""FIRE-01 — Financial Narrative & Trend Engine tests."""

from __future__ import annotations

from financial_intelligence.confidence import score_confidence
from financial_intelligence.findings import assert_no_hallucination, findings_from_series
from financial_intelligence.production import company, dashboard, findings, health
from financial_intelligence.quality import quality_signals
from financial_intelligence.report import build_report
from financial_intelligence.schema import CONF_HIGH, CONF_LOW, REPORT_SECTIONS, WORKSTREAM_ID
from financial_intelligence.trends import compare_window, detect_trends, normalize_series


def _pts(metric: str, pairs: list[tuple[str, float]]) -> list[dict]:
    return [{"metric": metric, "period": pe, "value": v, "version": 1, "warehouse_version": "fwh-v1.0.0", "validation_status": "APPROVED"} for pe, v in pairs]


def test_fire_health():
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["never_mutates_warehouse"] is True
    assert h["uses_llm"] is False
    assert h["buy_sell"] is False
    assert h["issues_recommendations"] is False
    d = dashboard()
    assert d["buy_sell"] is False


def test_revenue_trend_yoy():
    series = _pts(
        "revenue",
        [
            ("2020-03-31", 90.0),
            ("2021-03-31", 100.0),
            ("2022-03-31", 110.0),
            ("2023-03-31", 125.0),
            ("2024-03-31", 140.0),
            ("2025-03-31", 160.0),
        ],
    )
    yoy = compare_window(series, window="yoy", metric="revenue")
    assert yoy is not None
    assert yoy["current_value"] == 160.0
    assert yoy["prior_value"] == 140.0
    assert yoy["pct_change"] is not None and yoy["pct_change"] > 0
    assert yoy["evidence"]["metric"] == "revenue"
    trend = detect_trends("revenue", series)
    assert trend["trend_label"] in {"revenue_growth", "revenue_acceleration", "revenue_deceleration"}
    assert "yoy" in trend["windows"]
    assert "y3" in trend["windows"]
    assert "y5" in trend["windows"]


def test_margin_trend_bps():
    series = _pts(
        "operating_margin",
        [
            ("2023-03-31", 15.8),
            ("2024-03-31", 16.5),
            ("2025-03-31", 18.0),
        ],
    )
    yoy = compare_window(series, window="yoy", metric="operating_margin")
    assert yoy is not None
    assert yoy["change_unit"] == "bps"
    assert yoy["change"] == 150.0  # 18.0 - 16.5 = 1.5pp → 150 bps
    trend = detect_trends("operating_margin", series)
    assert trend["trend_label"] == "margin_expansion"


def test_debt_and_cash_trends():
    debt = _pts("total_debt", [("2023-03-31", 80.0), ("2024-03-31", 70.0), ("2025-03-31", 55.0)])
    cash = _pts("cash", [("2023-03-31", 20.0), ("2024-03-31", 30.0), ("2025-03-31", 45.0)])
    assert detect_trends("total_debt", debt)["trend_label"] == "debt_falling"
    assert detect_trends("cash", cash)["trend_label"] == "cash_rising"


def test_quality_cash_conversion():
    series_map = {
        "operating_cash_flow": _pts("operating_cash_flow", [("2025-03-31", 40.0)]),
        "net_income": _pts("net_income", [("2025-03-31", 30.0)]),
    }
    sigs = quality_signals(series_map)
    codes = {s["code"] for s in sigs}
    assert "strong_cash_conversion" in codes
    assert all(s.get("evidence") for s in sigs)


def test_finding_generation_and_evidence():
    series_map = {
        "revenue": _pts(
            "revenue",
            [("2022-03-31", 100.0), ("2023-03-31", 110.0), ("2024-03-31", 130.0), ("2025-03-31", 150.0)],
        ),
        "operating_margin": _pts(
            "operating_margin",
            [("2023-03-31", 16.0), ("2024-03-31", 17.0), ("2025-03-31", 19.0)],
        ),
        "total_debt": _pts("total_debt", [("2023-03-31", 90.0), ("2025-03-31", 60.0)]),
        "cash": _pts("cash", [("2023-03-31", 10.0), ("2025-03-31", 25.0)]),
        "operating_cash_flow": _pts("operating_cash_flow", [("2024-03-31", 20.0), ("2025-03-31", 35.0)]),
        "net_income": _pts("net_income", [("2024-03-31", 18.0), ("2025-03-31", 28.0)]),
    }
    findings = findings_from_series(series_map, coverage_pct=85.0, ticker="TCS")
    assert findings
    for f in findings:
        ev = f["evidence"]
        assert ev.get("metric") or ev.get("metrics") or ev.get("supporting_codes")
        assert f["confidence"] in {"High", "Medium", "Low"}
        assert f["narrative"]
        assert "BUY" not in f["narrative"].upper()
        assert "SELL" not in f["narrative"].upper()


def test_no_hallucination_guard():
    bad = [{"finding_id": "x", "narrative": "invented", "evidence": {}}]
    assert assert_no_hallucination(bad) == []
    good = [
        {
            "finding_id": "y",
            "narrative": "ok",
            "evidence": {
                "metric": "revenue",
                "current": {"period": "2025-03-31", "value": 1},
                "prior": {"period": "2024-03-31", "value": 0.5},
            },
        }
    ]
    assert len(assert_no_hallucination(good)) == 1


def test_confidence_calculation():
    assert score_confidence(history_n=10, windows_n=3, validation_status="APPROVED", coverage_pct=90) == CONF_HIGH
    assert score_confidence(history_n=1, windows_n=0, validation_status=None, coverage_pct=10) == CONF_LOW


def test_report_sections_and_api_shape():
    series_map = {
        "revenue": _pts(
            "revenue",
            [("2021-03-31", 80.0), ("2022-03-31", 90.0), ("2023-03-31", 100.0), ("2024-03-31", 120.0), ("2025-03-31", 140.0)],
        ),
        "operating_margin": _pts("operating_margin", [("2024-03-31", 17.0), ("2025-03-31", 18.5)]),
        "free_cash_flow": _pts("free_cash_flow", [("2024-03-31", 15.0), ("2025-03-31", 22.0)]),
        "operating_cash_flow": _pts("operating_cash_flow", [("2025-03-31", 30.0)]),
        "net_income": _pts("net_income", [("2024-03-31", 20.0), ("2025-03-31", 25.0)]),
    }
    report = build_report("TCS", series_map=series_map)
    assert report["ok"] is True
    assert report["buy_sell"] is False
    assert report["uses_llm"] is False
    assert report["mutated_warehouse"] is False
    for sec in REPORT_SECTIONS:
        assert sec in report["sections"]
    assert report["executive_summary"] is not None
    assert report["mission_control"]["financial_findings"] == len(report["findings"])

    # production façades with injected path via empty warehouse still ok
    pack = company("ZZZZNOPE")
    assert pack["ok"] is True
    assert pack["buy_sell"] is False
    assert "findings" in pack
    assert "evidence" in pack
    assert "confidence" in pack

    fpack = findings("ZZZZNOPE")
    assert "findings" in fpack


def test_normalize_series_dedupes():
    rows = normalize_series(
        [
            {"period": "2025-03-31", "value": 1.0, "version": 1},
            {"period": "2025-03-31", "value": 2.0, "version": 2},
            {"period": "2024-03-31", "value": 0.5, "version": 1},
        ]
    )
    assert len(rows) == 2
    assert rows[-1]["value"] == 2.0
