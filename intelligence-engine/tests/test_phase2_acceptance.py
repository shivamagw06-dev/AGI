"""Phase 2 acceptance — Institutional Evidence Intelligence.

Definition of Done checks:
  * Frameworks execute from validated evidence packs
  * Historical / peer / sector metrics available for supported entities
  * Provenance + quality on every metric
  * Frameworks consume packs via contracts (never fetch)
  * Missing series → transparent insufficient / partial committee
"""

from __future__ import annotations

from institutional_reasoning.execution_governance import govern_answer
from institutional_reasoning.institutional_evidence.analytics import analyse_series
from institutional_reasoning.institutional_evidence.production import (
    build_evidence_pack,
    package_for_governance,
    quality_gates,
)
from institutional_reasoning.institutional_evidence.quality import MIN_FRAMEWORK_SCORE
from institutional_reasoning.institutional_evidence.seeds import IT_PE_SERIES, NIFTYIT_PE_SERIES


def test_infosys_expensive_frameworks_execute():
    record = govern_answer("Is Infosys expensive?")
    assert record["entity"]["entity_id"] == "INFY"
    assert record["validation"]["complete"] is True
    by_id = {f["framework_id"]: f for f in record["frameworks"]}
    assert by_id["rel_val_damodaran"]["status"] == "executed"
    assert by_id["hist_multiples"]["status"] == "executed"
    assert by_id["margin_of_safety"]["status"] == "executed"
    assert record["committee"]["stance"] in {"Evidence-supported", "Partial evidence"}
    assert record["committee"]["executed_count"] >= 3
    assert record["narrative_allowed"] is True
    ie = record.get("institutional_evidence") or {}
    assert ie.get("historical_pe") is not None
    assert ie.get("peer_pe") is not None
    assert ie.get("evidence_score", 0) >= MIN_FRAMEWORK_SCORE


def test_nifty_it_expensive_historical_peer_sector_found():
    record = govern_answer("Is Nifty IT expensive versus history?")
    assert record["entity"]["entity_id"] == "NIFTYIT"
    observed = set(record["validation"]["observed"] or [])
    assert "historical_pe" in observed
    assert "historical_percentile" in observed
    assert "peer_pe" in observed
    assert "current_pe" in observed
    ie = record.get("institutional_evidence") or {}
    modules = (ie.get("modules") or ie.get("institutional_evidence", {}).get("modules") or {})
    # package_for_governance nests under institutional_evidence key inside record
    pack = ie.get("institutional_evidence") or ie
    modules = pack.get("modules") or {}
    assert (modules.get("sector") or {}).get("sector_pe") is not None
    assert (modules.get("historical") or {}).get("historical_percentile") is not None
    assert (modules.get("peer") or {}).get("peer_pe") is not None
    hist = next(f for f in record["frameworks"] if f["framework_id"] == "hist_multiples")
    rel = next(f for f in record["frameworks"] if f["framework_id"] == "rel_val_damodaran")
    assert hist["status"] == "executed"
    assert rel["status"] == "executed"
    assert record["committee"]["stance"] in {"Evidence-supported", "Partial evidence"}
    assert record["narrative_allowed"] is True


def test_missing_historical_pe_partial_committee():
    """Nifty Bank has no PE seed → historical insufficient; relative may still run if peer exists."""
    record = govern_answer("Is Nifty Bank expensive versus history?")
    assert record["entity"]["entity_id"] == "NIFTYBANK"
    hist = next(f for f in record["frameworks"] if f["framework_id"] == "hist_multiples")
    # No PE series for NIFTYBANK → historical insufficient
    assert hist["status"] == "insufficient_evidence"
    assert "historical_pe" in hist["missing_evidence"] or "historical_pe" in (
        record.get("missing_evidence") or []
    )
    # Committee must not claim full support
    assert record["committee"]["stance"] in {"Partial evidence", "Insufficient evidence"}
    assert record["narrative_allowed"] is False or record["committee"]["can_conclude"] is False


def test_evidence_pack_summary_shape():
    pack = build_evidence_pack("INFY", entity_name="Infosys", entity_type="Company")
    summary = pack["summary"]
    assert summary["company"] == "Infosys"
    assert summary["current_pe"] is not None
    assert summary["historical_pe"] is not None
    assert summary["historical_percentile"] is not None
    assert summary["peer_median"] is not None
    assert summary["sector_pe"] is not None
    assert summary["evidence_quality"] >= MIN_FRAMEWORK_SCORE
    assert summary["coverage"] == 100.0
    # Provenance on every validated metric
    for field, env in (pack.get("validated") or {}).items():
        assert env.get("provider")
        assert env.get("verified_at") or env.get("as_of")
        assert env.get("symbol") == "INFY"
        assert env.get("quality") is None or env.get("quality") >= MIN_FRAMEWORK_SCORE


def test_quality_engine_rejects_below_threshold():
    from institutional_reasoning.institutional_evidence.quality import score_metric

    low = score_metric(
        value=20,
        entity_id="X",
        metric_entity="Y",  # mismatch
        provider=None,
        as_of=None,
        series_n=0,
        data_class="unknown",
        validated=False,
        consistency_ok=False,
    )
    assert low["score"] < MIN_FRAMEWORK_SCORE
    assert low["accept_for_framework"] is False


def test_historical_analytics_compute_all():
    stats = analyse_series(NIFTYIT_PE_SERIES, current=29.5)
    assert stats["found"] is True
    assert stats["average"] is not None
    assert stats["median"] is not None
    assert stats["std_dev"] is not None
    assert stats["z_score"] is not None
    assert stats["historical_percentile"] is not None
    assert stats["rolling_average"] is not None
    assert stats["premium_vs_average_pct"] is not None
    assert stats["trend"] in {"rising", "falling", "stable", "insufficient"}
    assert stats["volatility"] is not None


def test_peer_engine_not_framework():
    """Peer median comes from Peer Engine, not framework calculation."""
    pkg = package_for_governance("INFY")
    peer = (pkg.get("modules") or {}).get("peer") or {}
    assert peer.get("found") is True
    assert peer.get("median") == peer.get("peer_pe")
    assert set(IT_PE_SERIES).issuperset(set(peer.get("universe_values") or {}))
    assert peer.get("provenance", {}).get("how") == "universe_median"


def test_dcf_insufficient_without_inputs():
    pack = build_evidence_pack("INFY", entity_type="Company")
    dcf = pack["modules"]["dcf"]
    assert dcf["status"] == "insufficient"
    assert "revenue" in dcf["missing"] or len(dcf["missing"]) > 0
    assert dcf["intrinsic_value"] is None


def test_dcf_not_applicable_index_in_pack():
    pack = build_evidence_pack("NIFTYIT", entity_type="Index")
    assert pack["modules"]["dcf"]["status"] == "not_applicable"


def test_quality_gates_pass_supported_universe():
    gates = quality_gates(["INFY", "NIFTYIT", "TCS"])
    assert gates["pass"] is True


def test_frameworks_never_need_raw_api_when_pack_present():
    """Contract satisfied solely by institutional evidence pack."""
    record = govern_answer(
        "Is Infosys expensive?",
        packs={},  # no DVC / Yahoo / CID
        build_institutional_evidence=True,
    )
    assert record["validation"]["complete"] is True
    core = {"rel_val_damodaran", "hist_multiples", "margin_of_safety"}
    for f in record["frameworks"]:
        if f["framework_id"] in core:
            assert f["status"] in {"executed", "not_applicable"}, f
    assert any(
        f["framework_id"] == "rel_val_damodaran" and f["status"] == "executed"
        for f in record["frameworks"]
    )
