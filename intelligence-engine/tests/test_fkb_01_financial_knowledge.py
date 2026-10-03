"""FKB-01 — Institutional Financial Knowledge Base tests."""

from __future__ import annotations

from financial_knowledge import knowledge
from financial_knowledge.fire_bridge import narrative_template, threshold_value
from financial_knowledge.production import dashboard, health, metrics, ratios
from financial_knowledge.schema import VERSION, WORKSTREAM_ID


def test_health_and_dashboard():
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["performs_analysis"] is False
    assert h["is_llm"] is False
    assert h["buy_sell"] is False
    assert h["validation"]["ok"] is True
    d = dashboard()
    assert d["metrics_loaded"] >= 20
    assert d["ratios_loaded"] >= 15
    assert d["relationships_loaded"] >= 8
    assert d["thresholds_loaded"] >= 8
    assert d["validation_status"] == "passed"
    assert d["version"] == VERSION


def test_unique_identifiers_and_registry_lookup():
    v = knowledge.validate()
    assert v["ok"] is True, v["errors"]
    assert knowledge.metric("Revenue")["id"] == "revenue"
    assert knowledge.metric("PAT")["id"] == "pat"
    assert knowledge.ratio("ROCE")["id"] == "roce"
    assert knowledge.ratio("OperatingMargin")["id"] == "operating_margin"
    assert knowledge.relationship("PAT_OCF")["id"] == "PAT_OCF"
    assert knowledge.glossary("OperatingLeverage")["id"] == "operating_leverage"
    assert knowledge.threshold("InterestCoverage")["id"] == "interest_coverage_warning"


def test_formula_completeness_and_cross_references():
    for r in knowledge.list_ratios():
        assert r.get("formula"), r["id"]
        assert r.get("required_metrics"), r["id"]
        for m in r["required_metrics"]:
            assert knowledge.metric(m) is not None, f"{r['id']} -> {m}"
    for rel in knowledge.list_relationships():
        assert rel.get("narrative_template")
        assert rel.get("inputs")
        for inp in rel["inputs"]:
            assert knowledge.metric(inp) is not None, f"{rel['id']} -> {inp}"


def test_threshold_loading_and_sector_override():
    base = knowledge.threshold("debt_to_ebitda_warning")
    assert base["value"] == 2.5
    soft = knowledge.threshold("debt_to_ebitda_warning", sector="software")
    # software may not override debt; capital_intensive does
    cap = knowledge.threshold("debt_to_ebitda_warning", sector="capital_intensive")
    assert cap.get("overridden") is True
    assert cap["value"] == 3.0
    banks = knowledge.sector("banks")
    assert banks is not None
    assert "ROE" in " ".join(banks.get("notes") or "") or banks.get("preferred_return_metric") == "roe"


def test_relationship_validity_and_fire_bridge():
    rel = knowledge.relationship("PAT_OCF")
    assert "cash conversion" in rel["narrative_template"].lower()
    assert narrative_template("PAT_OCF")
    assert threshold_value("cash_conversion_adequate") == 0.8
    assert threshold_value("margin_expansion_bps") == 100.0


def test_confidence_modifiers():
    mods = knowledge.list_confidence_modifiers()
    assert len(mods) >= 5
    assert knowledge.confidence("conflicting_evidence")["points"] == -1
    from financial_knowledge.confidence import apply_points

    scored = apply_points(history_n=10, windows_n=3, validation_status="APPROVED", coverage_pct=90)
    assert scored["points"] >= 5
    thin = apply_points(history_n=0, conflict=True)
    assert thin["band_downgrade"] == 1


def test_api_list_shapes():
    m = metrics()
    assert m["n"] == len(m["metrics"])
    r = ratios()
    assert r["n"] == len(r["ratios"])
    ids = {x["id"] for x in m["metrics"]}
    assert len(ids) == m["n"]


def test_versioning_and_no_analysis_flags():
    assert VERSION.startswith("fkb-01")
    for m in knowledge.list_metrics():
        assert m.get("performs_analysis") is False
    for rel in knowledge.list_relationships():
        assert rel.get("performs_analysis") is False
        assert rel.get("executes_rules") is False


def test_backward_compatible_aliases():
    assert knowledge.metric("ocf")["id"] == "operating_cash_flow"
    assert knowledge.metric("equity")["id"] == "total_equity"
    assert knowledge.ratio("Debt/EBITDA") is not None or knowledge.ratio("debt_to_ebitda") is not None
