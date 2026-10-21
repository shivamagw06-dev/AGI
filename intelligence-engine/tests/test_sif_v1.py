"""SIF v1.0 — Sector Intelligence Framework tests."""

from __future__ import annotations

from sif.detection import SECTOR_IDS, detect_sector
from sif.frameworks import FRAMEWORKS, get_framework
from sif.production import analyse_query, quality_gates, valuation_guidance
from sif.usage import reset_sif_store


def setup_function() -> None:
    reset_sif_store()


def test_all_phase1_sectors_have_frameworks():
    missing = [sid for sid in SECTOR_IDS if sid not in FRAMEWORKS]
    assert missing == []
    assert len(FRAMEWORKS) >= 30


def test_hdfc_maps_to_banks_and_prioritises_banking_kpis():
    det = detect_sector("Should I buy HDFC Bank?", "HDFCBANK")
    assert det["sector_id"] == "banks"
    pkg = analyse_query("Should I buy HDFC Bank?", ticker="HDFCBANK")
    assert pkg["sector_id"] == "banks"
    kpis = set(pkg["kpis_retrieved"])
    for kpi in ("nim", "casa", "credit_cost", "gnpa", "nnpa", "cet1", "roe", "pb"):
        assert kpi in kpis, kpi
    # Generics must not lead
    top_labels = [r.get("concept_id") or r.get("kpi") for r in (pkg.get("ranked") or [])[:8]]
    assert "risk_and_diversification" not in top_labels
    assert "liquidity" not in top_labels or str(top_labels[0]).startswith("sif_kpi")
    assert any(str(x).startswith("sif_kpi:nim") or x == "nim" for x in top_labels)
    assert pkg["sector_outranks_generic"] is True
    # Without company docs → block recommendation
    assert pkg["recommendation_gate"]["blocked"] is True
    assert "Insufficient" in (pkg["recommendation_gate"]["message"] or "")


def test_ve_methodology_sector_aware():
    assert "pb" in " ".join(valuation_guidance("banks")["methodology"]).lower() or any(
        m in valuation_guidance("banks")["methodology"] for m in ("justified_pb", "residual_income", "excess_return", "pb")
    )
    assert valuation_guidance("utilities")["primary_method"] in {"dcf_fcff", "regulated_dcf", "pb"}
    assert "ev_sales" in valuation_guidance("software")["methodology"] or "EV/Sales" in valuation_guidance("software")["preferred_multiples"]
    assert "sotp" in valuation_guidance("conglomerates")["methodology"]


def test_validation_namesakes_select_different_frameworks():
    cases = {
        "INFY": ("it_services", "Should I buy Infosys?"),
        "ULTRACEMCO": ("cement", "UltraTech Cement outlook"),
        "ASIANPAINT": ("fmcg", "Asian Paints investment case"),
        "RELIANCE": ("conglomerates", "Should I buy Reliance Industries?"),
        "SUNPHARMA": ("pharma", "Sun Pharma thesis"),
        "TATASTEEL": ("steel", "Tata Steel outlook"),
        "POWERGRID": ("utilities", "Power Grid valuation"),
    }
    selected = {}
    for ticker, (sector, q) in cases.items():
        pkg = analyse_query(q, ticker=ticker)
        assert pkg["sector_id"] == sector, (ticker, pkg["sector_id"])
        selected[ticker] = {
            "sector": pkg["sector_id"],
            "kpis": pkg["kpis_retrieved"][:6],
            "valuation": (pkg.get("valuation_framework") or {}).get("methodology"),
            "why": get_framework(sector).decision_framework[0] if get_framework(sector) else None,
        }
    # Different frameworks
    assert len({v["sector"] for v in selected.values()}) == len(cases)
    # IT prioritises deal/utilisation style KPIs
    assert "deal_wins" in set(selected["INFY"]["kpis"]) or "utilisation" in set(selected["INFY"]["kpis"])
    # Cement prioritises ebitda/tonne or utilisation
    assert "ebitda_per_tonne" in set(selected["ULTRACEMCO"]["kpis"]) or "capacity_utilisation" in set(
        selected["ULTRACEMCO"]["kpis"]
    )


def test_evidence_supplied_can_unlock_recommendation_gate():
    supplied = {
        "latest_annual_report": True,
        "latest_quarterly_results": True,
        "latest_investor_presentation": True,
        "financial_statements": True,
        "valuation_metrics": True,
        "sector_benchmarks": True,
    }
    pkg = analyse_query(
        "Should I buy HDFC Bank?",
        ticker="HDFCBANK",
        evidence_supplied=supplied,
    )
    assert pkg["company_evidence"]["sufficient"] is True
    assert pkg["recommendation_gate"]["blocked"] is False


def test_quality_gates_pass():
    gates = quality_gates(warm=True)
    assert gates["passed"] is True, gates


def test_fapi_package_uses_sif_for_hdfc():
    from academy.fapi.production import package_for_query

    pkg = package_for_query("Should I buy HDFC Bank?", engine="ask_agi", ticker="HDFCBANK")
    sif = pkg.get("sector_intelligence") or {}
    assert sif.get("sector_id") == "banks"
    assert "nim" in set(sif.get("kpis_retrieved") or [])
    # Academy concepts should prefer banking-relevant over pure generics in top set
    top = pkg.get("concept_ids") or []
    assert "risk_and_diversification" not in top[:3]
