"""Patch Intelligence — briefs only; never auto-codes."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_evaluation_lab.production import run as iel_run
from patch_intelligence import PI_VERSION, from_rci, status
from patch_intelligence.briefs.builder import build_brief, build_queue
from root_cause_intelligence.analyze import analyze_iel_run

ROOT = Path(__file__).resolve().parents[1]


def test_pi_health() -> None:
    assert PI_VERSION.startswith("patch-intelligence")
    st = status()
    assert st["never_writes_code_automatically"] is True
    assert st["human_in_the_loop"] is True


def test_brief_shape() -> None:
    cluster = {
        "cluster_id": "clu-banks-fw",
        "cluster_key": "framework_mismatch|banks|CORPORATE|documents|PB_DOC",
        "root_cause": "framework_mismatch",
        "sector": "banks",
        "framework_family": "CORPORATE",
        "category": "documents",
        "count": 21,
        "question_ids": [f"Q{i}" for i in range(21)],
        "severity": "high",
    }
    brief = build_brief(
        cluster,
        rci_context={
            "n_questions": 1000,
            "iel_pass_pct": 88.2,
            "kpi_proxies": {"framework_accuracy_pct": 75.3, "intent_accuracy_pct": 84.7},
        },
    )
    assert brief["affected_questions"] == 21
    assert brief["auto_code_written"] is False
    assert "framework_accuracy" in brief["expected_gain"]
    assert brief["files_to_review"]
    assert brief["recommended_pr"].startswith("cursor/fix-")
    assert brief["risk"] in {"low", "medium", "high"}
    assert "banking" in brief["risk_rationale"].lower() or "forbid" in brief["risk_rationale"].lower()


def test_queue_from_iel_rci() -> None:
    iel = iel_run(suite="smoke", mode="soft", limit=30, persist_baseline=False)
    rci = analyze_iel_run(iel, persist=False)
    queue = from_rci(rci, top_n=5)
    assert queue["never_writes_code_automatically"] is True
    assert queue["n_briefs"] <= 5
    if queue["briefs"]:
        assert queue["highest_roi"]["affected_questions"] >= 1


def test_no_llm_and_no_codegen_claims() -> None:
    banned = ("openai", "anthropic", "litellm", "langchain")
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "auto_apply" not in text.lower()
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(b in alias.name.lower() for b in banned)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(b in node.module.lower() for b in banned)
