"""Unit tests for Phase 3.0 Business Intelligence Foundation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("IKT_STORE_ROOT", str(ROOT / "data" / "institutional_knowledge_tables"))


def test_health_ask_wired_via_kul():
    from business_intelligence.foundation.production import health

    h = health()
    assert h["ok"] is True
    assert h["ask_wired"] is True
    assert "knowledge_unification" in (h.get("ask_wired_via") or "")
    assert h["uses_llm"] is False


def test_soft_slice_enabled_via_kul():
    from business_intelligence.foundation.production import soft_slice_for_ask_agi

    out = soft_slice_for_ask_agi("What is HDFC Bank's business model?")
    assert out["enabled"] is True
    assert out["ask_wired"] is True
    assert out.get("summary")


def test_bank_value_drivers():
    from business_intelligence.foundation.production import industry

    out = industry("banks")
    drivers = out["value_drivers"]["value_drivers"]
    assert "NIM" in drivers
    assert "CASA" in drivers
    assert "Credit Cost" in drivers


def test_saas_unit_economics_chain():
    from business_intelligence.foundation.production import analyse

    out = analyse("Explain unit economics for SaaS.")
    assert "unit_economics" in out["modules_used"]
    chain = (out.get("unit_economics") or {}).get("industry_chain") or []
    assert any("Subscription" in x or "subscription" in x.lower() for x in chain)


def test_moat_dimensions_scored():
    from business_intelligence.foundation.production import moat

    out = moat("What is HDFC Bank's moat?", ticker="HDFCBANK")
    dims = out.get("dimensions") or []
    assert len(dims) >= 8
    assert out.get("durability") in {"Strong", "Medium", "Weak"}


def test_company_answers_use_readable_names_instead_of_raw_tickers():
    from business_intelligence.foundation.production import analyse

    moat = analyse("Does Asian Paints have pricing power?", ticker="ASIANPAINT")
    growth = analyse("What drives growth for Infosys?", ticker="INFY")
    risks = analyse("What are the biggest business risks for Reliance Industries?", ticker="RELIANCE")

    assert "Asian Paints" in moat["summary"]
    assert "Infosys" in growth["summary"]
    assert "Reliance Industries" in risks["summary"]


def test_compare_uses_business_axes():
    from business_intelligence.foundation.production import compare

    out = compare("Compare TCS vs Infosys.")
    assert out.get("policy") == "business_axes_not_ratios_only"
    assert out.get("ok") is True
    assert len(out.get("companies") or []) == 2


def test_management_does_not_invent():
    from business_intelligence.foundation.production import analyse

    out = analyse("Evaluate management quality for Reliance Industries.")
    mg = out.get("management") or {}
    assert mg.get("policy") == "no_fabricated_management_claims"
    assert "Unknown" in str(mg.get("axes"))


def test_knowledge_graph_has_relationships():
    from business_intelligence.foundation.production import graph

    out = graph("HDFCBANK")
    assert out.get("nodes")
    assert out.get("edges")
    assert any(e.get("rel") == "operates_in" for e in out["edges"])


def test_analyse_business_model_for_listed_company():
    from business_intelligence.foundation.production import analyse
    from institutional_knowledge_tables.store import list_companies

    if len(list_companies()) < 50:
        return
    out = analyse("What is HDFC Bank's business model?")
    assert out["ok"] is True
    assert "business_model" in out["modules_used"]
    assert (out.get("business_model") or {}).get("business_type") in {
        "bank",
        "nbfc",
        "unknown",
        "conglomerate",
    }
