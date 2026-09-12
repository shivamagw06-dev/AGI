"""AGIB Phase 3 Sprint 3.2 — Root Cause Intelligence acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_evaluation_lab.production import run as iel_run
from root_cause_intelligence import RCI_VERSION, analyze, status
from root_cause_intelligence.clustering.engine import cluster_failures, cluster_key
from root_cause_intelligence.failures.extract import extract_failures
from root_cause_intelligence.failures.models import build_failure
from root_cause_intelligence.fixes.suggest import recommend_prs, suggest_fix_for_cluster
from root_cause_intelligence.production import board

ROOT = Path(__file__).resolve().parents[1]


def test_rci_health() -> None:
    assert RCI_VERSION.startswith("root-cause-intelligence")
    st = status()
    assert st["status"] == "ready"
    assert st["freeze_locks"]["reasoning_frozen"] is True
    assert st["freeze_locks"]["does_not_patch_selectors_yet"] is True


def test_failure_object_shape() -> None:
    row = {
        "question_id": "GEN-X-1",
        "question": "Test bank residual income framework?",
        "passed": False,
        "overall": 52.0,
        "verdict": "FAIL",
        "root_causes": ["framework_mismatch", "playbook_mismatch"],
        "category": "valuation",
        "sector": "banks",
        "expected_intent": ["Explain"],
        "actual_intent": "Analyse",
        "expected_framework": ["FW_PB", "FW_RESIDUAL_INCOME"],
        "actual_framework": ["FW_PE"],
        "expected_playbook": ["PB_VAL_BANK"],
        "actual_playbook": "PB_IND_IT_SERVICES",
        "expected_evidence": ["banks", "accounting"],
        "evidence_present": {"n_nodes": 2, "entities": ["INFY"], "surface_bullets": []},
        "reasoning_path": {"mode": "soft"},
        "communication": {},
        "dimensions": {},
    }
    f = build_failure(row)
    for key in (
        "failure_id",
        "question",
        "expected_intent",
        "actual_intent",
        "expected_framework",
        "actual_framework",
        "expected_playbook",
        "actual_playbook",
        "evidence_present",
        "evidence_missing",
        "reasoning_path",
        "communication",
        "severity",
        "root_cause",
        "confidence",
        "diagnostic_chain",
    ):
        assert key in f
    assert f["root_cause"] == "framework_mismatch"
    assert "suggested_fix" in f["diagnostic_chain"] or f["diagnostic_chain"][-1] == "suggested_fix"
    assert "banks" in f["evidence_missing"] or "accounting" in f["evidence_missing"]


def test_clustering_groups_same_signature() -> None:
    base = {
        "passed": False,
        "overall": 60.0,
        "root_causes": ["framework_mismatch"],
        "category": "valuation",
        "sector": "banks",
        "expected_framework": ["FW_PB", "FW_RESIDUAL_INCOME"],
        "actual_framework": ["FW_PE"],
        "expected_playbook": ["PB_VAL_BANK"],
        "actual_playbook": "PB_VAL_OTHER",
        "expected_intent": ["Explain"],
        "actual_intent": "Explain",
        "expected_evidence": [],
        "evidence_present": {},
        "reasoning_path": {"mode": "soft"},
        "communication": {},
        "dimensions": {},
        "question": "q",
    }
    rows = [
        {**base, "question_id": f"Q{i}"} for i in range(5)
    ]
    failures = extract_failures(rows)
    keys = {cluster_key(f) for f in failures}
    assert len(keys) == 1
    clustered = cluster_failures(failures)
    assert clustered["n_failures"] == 5
    assert clustered["top_10"][0]["count"] == 5
    assert "banks" in clustered["top_10"][0]["impact_statement"]
    assert "framework_mismatch" in clustered["top_10"][0]["impact_statement"]
    assert clustered["top_10"][0]["count"] == 5


def test_suggested_fix_and_pr() -> None:
    cluster = {
        "cluster_id": "clu-test",
        "cluster_key": "framework_mismatch|banks|PB|valuation|PB_VAL",
        "root_cause": "framework_mismatch",
        "sector": "banks",
        "framework_family": "PB",
        "count": 42,
        "severity": "high",
        "impact_statement": "42 questions ↓ framework_mismatch ↓ banks ↓ PB ↓ one patch",
        "expected_frameworks_sample": ["FW_PB"],
        "actual_frameworks_sample": ["FW_PE"],
        "owner": "sprint_3_3_framework_optimisation",
    }
    fix = suggest_fix_for_cluster(cluster)
    assert "framework" in fix["title"].lower()
    assert fix["count"] == 42
    assert fix["recommended_branch"].startswith("cursor/fix-")
    assert fix["recommended_branch"].endswith("-4cc0")
    assert "selector" in " ".join(fix["actions"]).lower() or "mapping" in " ".join(fix["actions"]).lower()
    prs = recommend_prs([cluster], top_n=1)
    assert len(prs) == 1


def test_iel_soft_wire_produces_rci() -> None:
    summary = iel_run(suite="smoke", mode="soft", limit=25, persist_baseline=False)
    rci = summary.get("root_cause_intelligence") or {}
    assert rci.get("analysis_id") or rci.get("status") == "error"
    if rci.get("analysis_id"):
        assert "n_clusters" in rci
        assert "recommended_prs" in rci
        assert rci.get("version", "").startswith("root-cause-intelligence")


def test_analyze_api() -> None:
    iel = iel_run(suite="smoke", mode="soft", limit=15, persist_baseline=False)
    out = analyze(iel)
    assert out["n_questions"] == 15
    assert "top_10_clusters" in out
    assert "recommended_prs" in out
    assert out["reasoning_changed"] is False
    assert "n_hard_failures" in out
    assert "n_dimension_misses" in out
    b = board()
    assert b["module"] == "RCI"


def test_dimension_misses_surface_framework_clusters() -> None:
    """Framework dimension fails should cluster even when overall score still passes."""
    rows = []
    for i in range(8):
        rows.append(
            {
                "question_id": f"SOFT-{i}",
                "question": "Bank valuation framework?",
                "passed": True,
                "overall": 78.0,
                "verdict": "PASS",
                "root_causes": [],
                "category": "valuation",
                "sector": "banks",
                "expected_intent": ["Explain"],
                "actual_intent": "Explain",
                "expected_framework": ["FW_PB", "FW_RESIDUAL_INCOME"],
                "actual_framework": ["FW_PE"],
                "expected_playbook": ["PB_VAL_BANK"],
                "actual_playbook": "PB_VAL_BANK_PB_RI",
                "expected_evidence": [],
                "evidence_present": {},
                "reasoning_path": {"mode": "soft"},
                "communication": {},
                "dimensions": {
                    "framework": {
                        "passed": False,
                        "score": 40.0,
                        "root_cause": "framework_mismatch",
                    },
                    "intent": {"passed": True, "score": 100.0, "root_cause": None},
                },
            }
        )
    failures = extract_failures(rows, include_dimension_misses=True)
    assert len(failures) == 8
    assert all(f.get("failure_class") == "dimension_miss" for f in failures)
    clustered = cluster_failures(failures)
    assert clustered["top_10"][0]["root_cause"] == "framework_mismatch"
    assert clustered["top_10"][0]["count"] == 8


def test_no_llm_imports() -> None:
    banned = ("openai", "anthropic", "litellm", "langchain")
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(b in alias.name.lower() for b in banned)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(b in node.module.lower() for b in banned)
