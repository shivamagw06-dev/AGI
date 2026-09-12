"""PO-01 — Portfolio Office deterministic tests."""

from __future__ import annotations

from office_sdk.contracts import SCHEMA_EVIDENCE_BLOCK, SCHEMA_RESPONSE
from office_sdk.registry import dispatch
from office_sdk.contracts import office_request

from portfolio_office.production import (
    create,
    get_concentration,
    get_exposures,
    get_holdings,
    get_portfolio,
    get_quality,
    health,
    snapshot,
    soft_slice_mission_control,
)
from portfolio_office.schema import PO01_OFFICE_ID, PO01_WORKSTREAM_ID
from portfolio_office.service import import_holdings, take_snapshot
from portfolio_office import store as pf_store


def _holdings():
    return [
        {
            "ticker": "TCS",
            "company": "Tata Consultancy Services",
            "quantity": 10,
            "average_cost": 3000,
            "current_market_value": 40000,
            "sector": "Information Technology",
            "industry": "IT Services",
            "country": "IN",
            "market_cap_bucket": "Large",
            "currency": "INR",
        },
        {
            "ticker": "INFY",
            "company": "Infosys",
            "quantity": 20,
            "average_cost": 1400,
            "current_market_value": 30000,
            "sector": "Information Technology",
            "industry": "IT Services",
            "country": "IN",
            "market_cap_bucket": "Large",
            "currency": "INR",
        },
        {
            "ticker": "HDFCBANK",
            "company": "HDFC Bank",
            "quantity": 15,
            "average_cost": 1500,
            "current_market_value": 20000,
            "sector": "Financials",
            "industry": "Private Banks",
            "country": "IN",
            "market_cap_bucket": "Large",
            "currency": "INR",
        },
    ]


def _fire06():
    return {
        "TCS": {
            "ticker": "TCS",
            "overall_score": 0.82,
            "overall_label": "solid",
            "confidence": 0.8,
            "period": "FY2026",
            "pillars": [
                {"pillar": "growth", "score": 0.8, "evidence_ids": ["ev:tcs:g"]},
                {"pillar": "cash", "score": 0.85, "evidence_ids": ["ev:tcs:c"]},
            ],
            "evidence_ids": ["ev:tcs:g", "ev:tcs:c"],
        },
        "INFY": {
            "ticker": "INFY",
            "overall_score": 0.74,
            "confidence": 0.75,
            "period": "FY2026",
            "pillars": [
                {"pillar": "growth", "score": 0.7, "evidence_ids": ["ev:infy:g"]},
                {"pillar": "cash", "score": 0.72, "evidence_ids": ["ev:infy:c"]},
            ],
            "evidence_ids": ["ev:infy:g"],
        },
        "HDFCBANK": {
            "ticker": "HDFCBANK",
            "overall_score": 0.78,
            "confidence": 0.77,
            "period": "FY2026",
            "pillars": [
                {"pillar": "growth", "score": 0.76, "evidence_ids": ["ev:hdfc:g"]},
                {"pillar": "cash", "score": 0.7, "evidence_ids": ["ev:hdfc:c"]},
            ],
            "evidence_ids": ["ev:hdfc:g"],
        },
    }


def _fire05():
    return {
        "TCS": {
            "ticker": "TCS",
            "confidence": 0.7,
            "period": "FY2026",
            "objectives": [
                {
                    "objective_id": "tcs:1",
                    "title": "Margin",
                    "status": "Delivered",
                    "evidence_ids": ["ev:tcs:me"],
                }
            ],
            "evidence_ids": ["ev:tcs:me"],
        },
        "INFY": {
            "ticker": "INFY",
            "confidence": 0.65,
            "objectives": [
                {
                    "objective_id": "infy:1",
                    "title": "Deal wins",
                    "status": "Partial",
                    "evidence_ids": ["ev:infy:me"],
                }
            ],
            "evidence_ids": ["ev:infy:me"],
        },
        "HDFCBANK": {
            "ticker": "HDFCBANK",
            "confidence": 0.68,
            "objectives": [
                {
                    "objective_id": "hdfc:1",
                    "title": "CASA",
                    "status": "Not Yet",
                    "evidence_ids": ["ev:hdfc:me"],
                }
            ],
            "evidence_ids": ["ev:hdfc:me"],
        },
    }


def _seed_core():
    pf_store.reset_for_tests()
    return create(
        {
            "name": "Core",
            "owner": "desk",
            "base_currency": "INR",
            "benchmark": "NIFTY50",
            "holdings": _holdings(),
            "cash_balance": 10000,
        }
    )


def test_health():
    h = health()
    assert h["workstream_id"] == PO01_WORKSTREAM_ID
    assert h["office_id"] == PO01_OFFICE_ID
    assert h["buy_sell"] is False
    assert h["optimises"] is False
    assert h["snapshots_immutable"] is True


def test_portfolio_creation_and_weights():
    out = _seed_core()
    assert out["ok"] is True
    pf = out["portfolio"]
    assert pf["portfolio_id"] == "core"
    totals = pf["totals"]
    # 40000+30000+20000+10000 = 100000
    assert totals["total_market_value"] == 100000
    weights = {h["ticker"]: h["weight"] for h in pf["holdings"]}
    assert abs(weights["TCS"] - 0.4) < 1e-9
    assert abs(weights["INFY"] - 0.3) < 1e-9
    assert abs(pf["cash"]["weight"] - 0.1) < 1e-9


def test_holding_import():
    _seed_core()
    pf = import_holdings(
        "core",
        [
            {
                "ticker": "RELIANCE",
                "quantity": 5,
                "average_cost": 2000,
                "current_market_value": 15000,
                "sector": "Energy",
                "industry": "Oil",
                "country": "IN",
                "market_cap_bucket": "Large",
            }
        ],
        replace=True,
        cash_balance=5000,
    )
    assert len(pf["holdings"]) == 1
    assert pf["holdings"][0]["ticker"] == "RELIANCE"


def test_exposures():
    _seed_core()
    exp = get_exposures("Core")
    assert exp["ok"] is True
    sectors = {r["name"]: r["weight"] for r in exp["exposures"]["sector"]}
    assert abs(sectors["Information Technology"] - 0.7) < 1e-9
    assert abs(sectors["Financials"] - 0.2) < 1e-9


def test_concentration():
    _seed_core()
    c = get_concentration("core")
    assert c["ok"] is True
    conc = c["concentration"]
    assert conc["number_of_holdings"] == 3
    assert conc["largest_position"]["ticker"] == "TCS"
    assert abs(conc["top_5_weight"] - 0.9) < 1e-9
    assert conc["hhi"] > 0


def test_quality_aggregation_no_rescore():
    _seed_core()
    fire06 = _fire06()
    original = fire06["TCS"]["overall_score"]
    q = get_quality("core", fire06_map=fire06)
    assert q["ok"] is True
    assert q["rescores"] is False
    assert q["module"] == "FIRE-06"
    # weight avg: 0.82*0.4 + 0.74*0.3 + 0.78*0.2 = 0.328+0.222+0.156 = 0.706 / 0.9
    pq = q["quality"]["portfolio_quality_score"]
    assert abs(pq - (0.706 / 0.9)) < 1e-9
    assert fire06["TCS"]["overall_score"] == original


def test_execution_aggregation():
    _seed_core()
    e_state = get_portfolio("core", fire05_map=_fire05(), fire06_map=_fire06())
    execution = e_state["execution"]
    assert execution["module"] == "FIRE-05"
    assert execution["rescores"] is False
    assert execution["delivered_weight"] > 0
    assert execution["outstanding_weight"] > 0


def test_immutable_snapshot():
    _seed_core()
    s1 = snapshot("core", {"kind": "manual", "label": "t0"}, fire06_map=_fire06(), fire05_map=_fire05())
    assert s1["ok"] is True
    assert s1["immutable"] is True
    snap = s1["snapshot"]
    sid = snap["snapshot_id"]
    hash1 = snap["content_hash"]
    # Mutate live portfolio
    import_holdings("core", _holdings()[:1], replace=True, cash_balance=0)
    stored = pf_store.get_snapshot(sid)
    assert stored["content_hash"] == hash1
    assert len(stored["portfolio"]["holdings"]) == 3  # historical unchanged
    # put_snapshot again with same id returns existing (immutability)
    again = pf_store.put_snapshot(snap)
    assert again["snapshot_id"] == sid


def test_office_sdk_compliance():
    _seed_core()
    pack = get_portfolio("Core", fire05_map=_fire05(), fire06_map=_fire06())
    resp = pack["office_response"]
    assert resp["schema"] == SCHEMA_RESPONSE
    assert resp["metadata"]["office_id"] == PO01_OFFICE_ID
    assert resp["metadata"]["guardrails"]["buy_sell"] is False
    assert resp["report_type"] == "portfolio_state_report"
    assert resp["sections"]
    assert resp["sections"][0]["blocks"][0]["schema"] == SCHEMA_EVIDENCE_BLOCK
    assert resp["provenance"]["references"]

    # dispatch path
    req = office_request(
        office_id="po-01",
        options={
            "portfolio_id": "core",
            "fire05_map": _fire05(),
            "fire06_map": _fire06(),
        },
    )
    dispatched = dispatch(req)
    assert dispatched["ok"] is True
    assert dispatched["metadata"]["office_id"] == "po-01"


def test_soft_slice_and_holdings_endpoint():
    _seed_core()
    h = get_holdings("Core")
    assert h["ok"] is True
    assert len(h["holdings"]) == 3
    slice_ = soft_slice_mission_control()
    assert slice_["workstream_id"] == PO01_WORKSTREAM_ID
    assert "portfolios" in slice_["panels"]


def test_snapshot_via_service_daily():
    _seed_core()
    snap = take_snapshot("core", kind="daily", fire05_map=_fire05(), fire06_map=_fire06())
    assert snap["kind"] == "daily"
    assert snap["immutable"] is True
    assert "quality" in snap["computed"]
