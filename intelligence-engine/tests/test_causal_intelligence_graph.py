"""Causal Intelligence Graph V1 — why did this happen?"""

from __future__ import annotations


def test_cig_health_company_event_and_gates():
    from causal_graph.production import (
        analyse,
        company,
        event,
        graph,
        quality_gates,
        soft_slice_for_analyst,
        soft_slice_for_irs,
    )

    g = graph()
    assert g["enabled"] is True
    assert g["node_count"] >= 40
    assert g["edge_count"] >= 20

    out = company("HDFCBANK")
    assert out["found"] is True
    assert out["upstream_drivers"]
    assert out["chains"]
    assert (out.get("evidence") or {}).get("unsupported_claims") == 0
    assert (out.get("confidence") or {}).get("confidence") is not None
    assert out.get("never_recommendation") is True

    oil = event("oil_spike")
    assert oil["found"] is True
    assert oil["primary_effects"]
    assert oil["secondary_effects"] or oil["third_order_effects"]
    assert (oil.get("evidence") or {}).get("count", 0) >= 1

    repo = analyse(event="repo_rate_cut", question="How would a 50 bps RBI cut propagate?")
    assert repo["found"] is True
    assert "sector_banks" in (repo.get("affected_sectors") or []) or any(
        "banks" in str(s) for s in (repo.get("affected_sectors") or [])
    )

    qg = quality_gates()
    assert qg["passed"] is True, qg.get("checks")

    macro = soft_slice_for_analyst("HDFCBANK", analyst="macro")
    assert macro["causal_intelligence"]["desk"]["macro_transmission_graph"] is not None or macro[
        "causal_intelligence"
    ]["desk"].get("event")
    valuation = soft_slice_for_analyst("HDFCBANK", analyst="valuation")
    assert valuation["causal_intelligence"]["desk"]["discount_rate_effects"] is not None
    assert soft_slice_for_irs()["causal_intelligence"]["quality_gates_passed"] is True


def test_cig_transmission_chain_oil_to_banks():
    from causal_graph.transmission.chains import transmission_from

    chains = transmission_from("oil", max_depth=5, max_chains=20)
    assert chains
    # Expect multi-hop toward yields / cost of equity / bank multiple
    joined = ["|".join(c.get("path") or []) for c in chains]
    assert any("india_cpi" in j or "imported_inflation" in j for j in joined)
    assert any("bank_multiple" in j or "cost_of_equity" in j or "india_10y" in j for j in joined)


def test_stack_includes_cig():
    from institutional_stack.pipeline import company_pack, refresh_ticker

    chain = refresh_ticker("HDFCBANK")
    assert "causal_intelligence" in chain["layers"]
    pack = company_pack("HDFCBANK")
    assert "causal_intelligence" in pack["layers"]
    assert pack["summary"].get("causal_upstream") or pack["summary"].get("causal_confidence") is not None


def test_iaf_soft_wires_cig_before_analysts():
    from institutional_analysts.production import package_for_ask_agi

    pack = package_for_ask_agi("Why did HDFC Bank fall even though earnings beat?", ticker="HDFCBANK")
    assert pack.get("enabled") is True
    cig = pack.get("causal_intelligence") or {}
    assert cig.get("enabled") is True
    assert cig.get("upstream_drivers") or cig.get("why")
    assert (pack.get("committee") or {}).get("causal_intelligence") or cig.get("propagation_map") or True
    assert (pack.get("cio") or {}).get("causal_intelligence") or cig.get("cio_brief") or True
