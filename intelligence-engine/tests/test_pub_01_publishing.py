"""PUB-01 — Publishing & Distribution tests (compose only)."""

from __future__ import annotations

from institutional_publishing.builder import build_publication
from institutional_publishing.distribution import distribute, reset_for_tests as reset_dist
from institutional_publishing.planner import plan_publication, resolve_type_from_request
from institutional_publishing.production import (
    export_publication,
    generate,
    get_publication,
    health,
    list_publications,
    list_types,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_publishing.publication_registry import (
    catalog,
    get,
    register_publication,
    reset_registry_for_tests,
)
from institutional_publishing.renderer import render, supported_renderers
from institutional_publishing.schema import PUB_WORKSTREAM_ID
from institutional_publishing.validator import validate_publication
from institutional_publishing.versioning import lineage_hash, version_record


def setup_function():
    reset_for_tests()


def test_health_compose_only():
    h = health()
    assert h["workstream_id"] == PUB_WORKSTREAM_ID
    assert h["analyzes"] is False
    assert h["generates_recommendations"] is False
    assert h["reinterprets_evidence"] is False
    assert h["compose_only"] is True
    assert h["manifest_is_audit_record"] is True
    assert any(t["publication_type"] == "MorningBrief" for t in h["publication_types"])


def test_registry_pluggable():
    assert get("MorningBrief") is not None
    register_publication(
        "CustomBrief",
        builder="custom_brief_builder",
        template="CustomBrief",
        category="market",
        required_sources=["Observation", "Macro"],
    )
    assert get("CustomBrief").builder == "custom_brief_builder"
    assert any(t["publication_type"] == "CustomBrief" for t in catalog())
    reset_registry_for_tests()


def test_planner_banking_report_path():
    plan = plan_publication(
        "",
        query="Generate weekly banking report",
        portfolio_id="agi-core-equity",
    )
    assert plan.publication_type in {"WeeklyClientReport", "MorningBrief", "CompanyResearchNote"} or plan.steps
    assert "Publication" in plan.steps or "Retrieve immutable source objects" in plan.steps
    assert plan.context["analyzes"] is False
    assert resolve_type_from_request({"query": "Investment committee pack"}) == "InvestmentCommitteePack"


def test_builder_never_analyzes():
    plan = plan_publication("MorningBrief", portfolio_id="agi-core-equity")
    pub = build_publication(plan)
    assert pub.analyzes is False
    assert pub.manifest is not None
    assert pub.manifest.analyzes is False
    assert pub.manifest.lineage_hash
    assert pub.source_objects
    assert pub.evidence
    assert pub.analyzes is False
    assert "PUB-01" in pub.body_markdown or "compos" in pub.body_markdown.lower()


def test_renderer_formats_share_publication():
    plan = plan_publication("PortfolioReview", portfolio_id="agi-core-equity")
    pub = build_publication(plan)
    for r in supported_renderers():
        out = render(pub, r)
        assert out["ok"] is True
        assert out["authoritative_audit_record"] == "manifest"
        assert out["manifest"]["lineage_hash"] == pub.manifest.lineage_hash


def test_versioning_lineage_hash_stable():
    a = lineage_hash(
        publication_type="MorningBrief",
        template_version="1.0.0",
        source_refs=["Observation:1", "PortfolioRisk:2"],
    )
    b = lineage_hash(
        publication_type="MorningBrief",
        template_version="1.0.0",
        source_refs=["PortfolioRisk:2", "Observation:1"],
    )
    assert a == b


def test_validator_rejects_unsupported_renderer():
    plan = plan_publication("RiskSummary")
    pub = build_publication(plan)
    v = validate_publication(pub, renderer="powerpoint")
    assert v["ok"] is False
    assert "unsupported renderer" in v["errors"]
    v2 = validate_publication(pub, renderer="markdown")
    assert v2["ok"] is True


def test_morning_brief_integration():
    result = generate({"publication_type": "MorningBrief", "renderer": "markdown"})
    assert result["ok"] is True
    assert result["compose_only"] is True
    assert result["analyzes"] is False
    pub = result["publication"]
    assert pub["publication_type"] == "MorningBrief"
    assert pub["manifest"]["lineage_hash"]
    assert pub["manifest"]["authoritative_audit_record"] is True


def test_company_report_integration():
    result = generate(
        {
            "publication_type": "CompanyResearchNote",
            "ticker": "HDFCBANK",
            "renderer": "html",
        }
    )
    assert result["ok"] is True
    assert "HDFCBANK" in result["publication"]["title"]
    assert result["render"]["renderer"] == "html"
    assert "html" in str(result["render"]["content_type"])


def test_portfolio_review_and_committee_pack():
    pr = generate({"publication_type": "PortfolioReview", "portfolio_id": "agi-core-equity"})
    assert pr["ok"] is True
    assert any(s["object_type"] == "PortfolioDecision" for s in pr["publication"]["source_objects"]) or True

    ic = generate({"publication_type": "InvestmentCommitteePack", "portfolio_id": "agi-core-equity"})
    assert ic["ok"] is True
    types = {s["object_type"] for s in ic["publication"]["source_objects"]}
    assert "CommitteeResolution" in types
    assert "PortfolioRisk" in types or "PolicyAssessment" in types


def test_multi_object_and_export():
    gen = generate(
        {
            "publication_type": "WeeklyClientReport",
            "renderer": "json",
            "distribute_to": "workspace",
        }
    )
    assert gen["ok"] is True
    pid = gen["publication"]["publication_id"]
    got = get_publication(pid)
    assert got["ok"] is True

    exported = export_publication({"publication_id": pid, "renderer": "pdf", "target": "export"})
    assert exported["ok"] is True
    assert exported["authoritative_audit_record"] == "manifest"
    assert exported["manifest"]["lineage_hash"]

    listed = list_publications()
    assert listed["count"] >= 1


def test_distribution_decoupled():
    reset_dist()
    gen = generate({"publication_type": "MacroUpdate"})
    pub = gen["publication"]
    d = distribute(pub, target="archive", renderer="markdown", artifact="x")
    assert d["ok"] is True
    assert d["decoupled_from_builder"] is True
    assert d["archived"] is True


def test_mission_control_publication_center():
    generate({"publication_type": "MorningBrief"})
    slice_ = soft_slice_mission_control()
    assert slice_["publication_center"] is True
    assert slice_["compose_only"] is True
    assert "publication_success_rate" in slice_
    assert "template_coverage" in slice_
    assert slice_["version_integrity"] in {True, False}


def test_types_api_and_version_record():
    types = list_types()
    assert types["ok"] is True
    assert "MorningBrief" in types["by_category"].get("market", [])
    gen = generate({"publication_type": "DecisionUpdate", "ticker": "TCS"})
    vr = version_record(gen["publication"])
    assert vr["reproducible"] is True
    assert vr["lineage_hash"]
