"""RC-01 — Architecture Conformance architectural tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from institutional_architecture.conformance import run_conformance
from institutional_architecture.dependency_rules import (
    build_import_graph,
    check_forbidden_imports,
    layer_isolation_summary,
)
from institutional_architecture.invariants import run_invariant_checks
from institutional_architecture.lineage_validator import (
    validate_canonical_lineage,
    validate_context_propagation_contracts,
    validate_publication_manifest_contract,
    validate_uag_no_direct_recommendations,
)
from institutional_architecture.production import (
    health,
    reset_for_tests,
    run,
    soft_slice_mission_control,
)
from institutional_architecture.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_RELEASE_CANDIDATE,
    ARCHITECTURE_FROZEN,
    CANONICAL_LINEAGE,
    FORBIDDEN_IMPORTS,
    RC_WORKSTREAM_ID,
)
from institutional_architecture.validator import assert_conformance_or_raise, validate_architecture


@pytest.fixture(autouse=True)
def _clean():
    reset_for_tests()
    yield
    reset_for_tests()


def test_health_is_quality_gate_not_feature():
    from institutional_architecture.schema import (
        AGIB_GENERAL_AVAILABILITY,
        AGIB_RELEASE_STATUS,
    )

    h = health()
    assert h["workstream_id"] == RC_WORKSTREAM_ID
    assert h["is_quality_gate"] is True
    assert h["is_feature"] is False
    assert h["adds_intelligence_engines"] is False
    assert h["architecture_frozen"] is True
    assert h["agib_release_candidate"] is True
    assert h["agib_general_availability"] is True
    assert h["agib_release_status"] == "GENERAL_AVAILABILITY"
    assert h["phase"] == "general_availability"
    assert ADDS_INTELLIGENCE_ENGINES is False
    assert ARCHITECTURE_FROZEN is True
    assert AGIB_RELEASE_CANDIDATE is True
    assert AGIB_GENERAL_AVAILABILITY is True
    assert AGIB_RELEASE_STATUS == "GENERAL_AVAILABILITY"


def test_ga_declaration_artifacts_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    assert (root / "AGIB_VERSION").read_text(encoding="utf-8").strip() == "1.0.0"
    assert (root / "docs" / "AGIB_V1_0_GA.md").is_file()
    assert (root / "docs" / "AGIB_V1_0_SUCCESS_METRICS.md").is_file()


def test_intelligence_invariants_pass():
    inv = run_invariant_checks()
    assert inv["ok"] is True, inv.get("violations")
    ids = {r["id"] for r in inv["results"]}
    assert "kg_sole_graph_owner" in ids
    assert "cci_relationships_not_graph" in ids
    assert "uag_orchestration_not_recommendations" in ids
    assert "pub_compose_not_reasoning" in ids
    assert "mpc_tenancy_not_intelligence" in ids


def test_production_invariants_pass():
    inv = run_invariant_checks()
    prod = [r for r in inv["results"] if r["group"] == "production"]
    assert prod and all(r["ok"] for r in prod), prod


def test_layer_isolation_and_forbidden_imports():
    layers = layer_isolation_summary()
    assert layers["layers"]
    assert layers["forbidden_edges"]
    deps = check_forbidden_imports()
    assert deps["ok"] is True, deps.get("violations")
    assert len(FORBIDDEN_IMPORTS) >= 5


def test_import_graph_built():
    g = build_import_graph()
    assert g["nodes"]
    # Ownership packages should appear when present on disk
    ids = {n["id"] for n in g["nodes"]}
    assert "institutional_orchestrator" in ids or "institutional_graph" in ids


def test_canonical_lineage():
    lin = validate_canonical_lineage()
    assert lin["ok"] is True, lin.get("errors")
    assert list(CANONICAL_LINEAGE)[0] == "Evidence"
    assert "Publication" in lin["canonical"]


def test_publication_manifest_contract():
    pub = validate_publication_manifest_contract()
    assert pub["ok"] is True, pub.get("errors")
    assert pub["contract"] == ["Publication", "Manifest", "Evidence"]


def test_uag_no_direct_recommendations():
    uag = validate_uag_no_direct_recommendations()
    assert uag["ok"] is True, uag.get("errors")


def test_three_contexts_present():
    ctx = validate_context_propagation_contracts()
    assert ctx["ok"] is True, ctx.get("errors")
    assert ctx["present"]["execution_context"] is True
    assert ctx["present"]["security_context"] is True
    assert ctx["present"]["observability_context"] is True


def test_full_conformance_pass_and_score():
    result = run_conformance()
    assert result["ok"] is True, result.get("violations")
    score = result["architecture_score"]
    assert score["score"] >= 95
    assert score["release_candidate_ready"] is True
    assert result["violation_count"] == 0


def test_production_run_and_soft_slice():
    out = run({"force": True})
    assert out["ok"] is True
    assert out["is_quality_gate"] is True
    board = soft_slice_mission_control()
    assert board["architecture_center"] is True
    assert board["architecture_score"] is not None


def test_validator_assert():
    v = validate_architecture()
    assert v["ok"] is True
    assert_conformance_or_raise()


def test_cli_exit_zero():
    import os

    engine = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(engine)
    env["AGI_RC_01_FAIL_ON_VIOLATION"] = "true"
    proc = subprocess.run(
        [sys.executable, "-m", "institutional_architecture", "--quiet", "--force"],
        cwd=str(engine),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS" in proc.stdout


def test_registry_ownership_schema():
    from institutional_architecture.schema import OWNERSHIP

    assert OWNERSHIP["institutional_graph"]["owns"] == "knowledge_graph"
    assert OWNERSHIP["institutional_cross_company"]["graph_sor"] == "KG-01"
    assert OWNERSHIP["institutional_orchestrator"]["must_not"] == (
        "recommendations",
        "business_state",
    )
    assert OWNERSHIP["institutional_publishing"]["owns"] == "composition"
    assert OWNERSHIP["institutional_multi_portfolio"]["owns"] == "tenancy"
