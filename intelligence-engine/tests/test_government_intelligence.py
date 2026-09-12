"""AGIB v2.0 Sprint 3 Phase 1 — high-impact Government Intelligence acceptance.

Phase 1 only: RBI, Budget/Finance, SEBI, GST, PLI, import/export duties.
MCA / other industry / state remain extensible — not required for exit.
"""

from __future__ import annotations

from knowledge_factory.government_intelligence import store as igri_store
from knowledge_factory.government_intelligence.objects.compile import compile_government_intelligence
from knowledge_factory.government_intelligence.pipeline import run_government_intelligence_pipeline
from knowledge_factory.government_intelligence.production import (
    dashboard,
    domain_view,
    get_policy,
    health,
    list_policies,
    search,
    timeline,
)
from knowledge_factory.government_intelligence.schema import (
    DELIVERY_PHASE,
    FREEZE_LOCKS,
    IGRI_VERSION,
    INSTITUTIONAL_COMPLETE_LEVEL,
    PHASE_1_DOMAINS,
    PHASE_2_EXTENSIBLE_DOMAINS,
)
from knowledge_factory.government_intelligence.timeline.build import replay_as_of
from knowledge_factory.government_intelligence.validators.gates import (
    detect_duplicate_policies,
    validate_pack,
    validate_policy,
)


def setup_function() -> None:
    igri_store.reset()


def test_freeze_locks_and_phase1_health():
    h = health()
    assert h["version"] == IGRI_VERSION
    assert h["delivery_phase"] == DELIVERY_PHASE
    assert h["phase_1_domains"] == list(PHASE_1_DOMAINS)
    assert "mca" not in h["phase_1_domains"]
    assert "MCA Intelligence" not in h["modules"]
    assert h["never_political_opinion"] is True
    assert h["freeze_locks"]["company_intelligence_architecture"] is True
    assert FREEZE_LOCKS["never_fabricate"] is True


def test_phase1_six_domains_only():
    pack = compile_government_intelligence()
    assert pack["delivery_phase"] == "phase_1_high_impact"
    assert pack["phase_1_complete"] is True
    domains = set(pack["domains"])
    assert domains == set(PHASE_1_DOMAINS)
    for d in PHASE_2_EXTENSIBLE_DOMAINS:
        assert d not in domains
    assert pack["coverage_level"] == INSTITUTIONAL_COMPLETE_LEVEL
    assert pack["institutional_ready"] is True
    # Phase 1 registry is lean (core bodies only)
    assert pack["registry"]["body_count"] >= 6
    assert pack["registry"]["body_count"] <= 10


def test_rbi_budget_sebi_gst_pli_trade_views():
    compile_government_intelligence()
    assert domain_view("rbi")["n"] >= 4  # includes banking reg under RBI
    assert domain_view("budget")["n"] >= 2
    assert domain_view("sebi")["n"] >= 3
    assert domain_view("gst")["n"] >= 1
    assert domain_view("pli")["n"] >= 4
    assert domain_view("trade")["n"] >= 1
    # Extensible domains empty in Phase 1 pack
    assert domain_view("mca")["n"] == 0
    assert domain_view("industry")["n"] == 0


def test_import_export_duties_in_trade():
    p = get_policy("TRADE-CUSTOMS-TARIFF-CORPUS")
    assert p["found"] is True
    assert "Import" in p["name"] or "import" in str(p["transmission"]["primary"]).lower()
    assert p["domain"] == "trade"


def test_rbi_includes_banking_regulation():
    p = get_policy("RBI-BANKING-REG-CORPUS")
    assert p["found"] is True
    assert p["domain"] == "rbi"
    assert p["government_body"] == "RBI"


def test_policy_object_fields_and_provenance():
    pack = compile_government_intelligence()
    for p in pack["policies"]:
        assert p["delivery_phase"] == "phase_1"
        assert p["domain"] in PHASE_1_DOMAINS
        assert p["provenance"]
        assert p["immutable"] is True
        assert validate_policy(p)["gate_pass"] is True


def test_point_in_time_replay_no_future_leak():
    pack = compile_government_intelligence()
    tl = pack["timeline"]
    replay = replay_as_of(tl, "2018-01-01")
    assert replay["future_leakage"] is False
    for p in replay["policies"]:
        assert p["available_from"] <= "2018-01-01"
    assert replay["excluded_future_count"] > 0
    api = timeline(as_of="2015-01-01")
    assert api["policy_count"] < tl["policy_count"]


def test_pli_timeline_and_gates():
    pack = compile_government_intelligence()
    pli = list_policies(domain="pli")["policies"]
    assert "PLI-ELECTRONICS-2020" in [p["policy_id"] for p in pli]
    q = validate_pack(
        bodies=pack["registry"]["bodies"],
        policies=pack["policies"],
        timeline=pack["timeline"],
    )
    assert q["phase_1_complete"] is True
    assert q["gate_pass"] is True
    assert detect_duplicate_policies(pack["policies"]) == []


def test_sector_company_portfolio_mapping():
    p = get_policy("GST-LAUNCH-2017")
    assert p["affected_companies"]
    assert p["relationships"]["portfolio"] == "institutional_reasoning.ipi"


def test_pipeline_dashboard_phase1():
    report = run_government_intelligence_pipeline()
    assert report["status"] == "ok"
    dash = dashboard(ensure=False)
    assert dash["delivery_phase"] == DELIVERY_PHASE
    assert dash["phase_1_complete"] is True
    assert dash["coverage_pct"] == 100.0
    assert dash["trade_duty_updates"] >= 1
    assert "mca" in dash["phase_2_extensible_domains"]
    hits = search("PLI")
    assert hits["n"] >= 1


def test_soft_wire_prior_sprints_untouched():
    from knowledge_factory.company_intelligence.schema import ICI_VERSION
    from knowledge_factory.corporate_events.schema import ICEI_VERSION

    assert ICI_VERSION
    assert ICEI_VERSION
