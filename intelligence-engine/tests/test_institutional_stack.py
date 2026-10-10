"""Institutional Intelligence Stack — soft integration tests."""

from __future__ import annotations


def test_bootstrap_and_company_pack():
    from institutional_stack.production import bootstrap_stack, company, health, quality_gates

    h = health()
    assert h["enabled"] is True
    assert h["not_an_engine"] is True

    boot = bootstrap_stack(["HDFCBANK"])
    assert boot["seed"]["seeded"] is True
    assert boot["seed"]["document_count"] >= 1

    pack = company("HDFCBANK")
    assert pack["enabled"] is True
    layers = pack["layers"]
    assert "filing_intelligence" in layers
    assert "filing_diff" in layers
    assert "management_intelligence" in layers
    assert "peer_intelligence" in layers
    assert "evidence_intelligence" in layers
    assert pack["summary"]["management_confidence"] is not None
    assert pack["summary"]["management_dna"]

    qg = quality_gates()
    assert qg["passed"] is True


def test_fil_ingest_auto_chains_stack():
    from filing_intelligence.production import ingest
    from institutional_stack.pipeline import company_pack

    doc_id = "test_stack_chain_hdfc_note"
    result = ingest(
        {
            "doc_id": doc_id,
            "ticker": "HDFCBANK",
            "company": "HDFC Bank",
            "doc_type": "transcript",
            "title": "Stack chain test note",
            "period": "Q1FY27",
            "as_of": "2026-07-20",
            "url": "https://example.com/stack-test",
            "evidence_tier": 2,
            "source_publisher": "HDFC Bank",
            "text": "Management reiterated liability franchise rebuild. NIM near-term pressure acknowledged.",
        }
    )
    # Duplicate ingest on re-run is fine — first run should accept
    if result.get("accepted"):
        assert "institutional_stack_chain" in result
        assert result["institutional_stack_chain"].get("ticker") == "HDFCBANK"

    pack = company_pack("HDFCBANK")
    assert pack["layers"]["management_intelligence"].get("enabled") is not False


def test_soft_slices_for_consumers():
    from company_analysis.assemble import analyse_company
    from institutional_analysts.production import package_for_ask_agi
    from institutional_stack.production import soft_slice_for_ask_agi, soft_slice_for_irs

    irs = soft_slice_for_irs()
    assert irs["institutional_stack"]["enabled"] is True

    ask = soft_slice_for_ask_agi("HDFCBANK")
    assert ask["institutional_stack"]["summary"]["management_dna"]

    ca = analyse_company(query="Analyse HDFC Bank", ticker="HDFCBANK", record=False)
    assert ca.get("institutional_stack")
    assert ca.get("management_trust", {}).get("dna") or ca["institutional_stack"].get("summary")

    iaf = package_for_ask_agi("Should I invest in HDFC Bank?", ticker="HDFCBANK")
    assert iaf.get("enabled") is True
    assert iaf.get("institutional_stack")
    assert iaf["institutional_stack"].get("summary", {}).get("management_dna")


def test_knowledge_packs_resolve_live_slices():
    from institutional_analysts.business.brain.knowledge import knowledge_pack as ba_pack
    from institutional_analysts.financial.brain.knowledge.catalog import knowledge_pack as fa_pack

    ba = ba_pack("HDFCBANK")
    assert ba["management_intelligence"].get("enabled") is True
    assert ba["management_intelligence"].get("dna") or ba["management_intelligence"].get("confidence") is not None

    fa = fa_pack("HDFCBANK")
    assert fa["filing_intelligence"].get("enabled") is True
    assert fa["management_intelligence"].get("enabled") is True
