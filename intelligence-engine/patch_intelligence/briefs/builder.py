"""Build human-review patch briefs — never writes application code."""

from __future__ import annotations

from typing import Any

from patch_intelligence.planner.gains import estimate_gains
from patch_intelligence.planner.risk import assess_risk
from patch_intelligence.schema import PI_VERSION


_FILE_MAP: dict[str, list[str]] = {
    "framework_mismatch": [
        "intelligence-engine/framework_selection/selector/engine.py",
        "intelligence-engine/framework_selection/mappings/sectors.py",
        "intelligence-engine/framework_selection/mappings/cues.py",
        "intelligence-engine/framework_selection/mappings/questions.py",
        "intelligence-engine/institutional_playbooks/selector/engine.py",
    ],
    "intent_mismatch": [
        "intelligence-engine/ask_pipeline/intent_resolution/resolver.py",
        "intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py",
    ],
    "playbook_mismatch": [
        "intelligence-engine/institutional_playbooks/selector/engine.py",
        "intelligence-engine/institutional_playbooks/registry/",
    ],
    "future_leakage": [
        "intelligence-engine/institutional_evidence_graph/replay/",
        "intelligence-engine/institutional_analog_intelligence/replay/",
    ],
    "memory_miss_on_analog_question": [
        "intelligence-engine/institutional_analog_intelligence/registry/",
        "intelligence-engine/institutional_analog_intelligence/similarity/engine.py",
    ],
}


def build_brief(
    cluster: dict[str, Any],
    *,
    rci_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = rci_context or {}
    n_questions = int(ctx.get("n_questions") or 1000)
    kpis = ctx.get("kpi_proxies") or {}
    gains = estimate_gains(
        cluster,
        n_questions=n_questions,
        current_pass_pct=ctx.get("iel_pass_pct"),
        current_framework_pct=kpis.get("framework_accuracy_pct"),
        current_intent_pct=kpis.get("intent_accuracy_pct"),
    )
    risk = assess_risk(cluster)
    cause = str(cluster.get("root_cause") or "unknown")
    sector = str(cluster.get("sector") or "generic")
    branch = (
        f"cursor/fix-{cause.replace('_', '-')[:28]}-{sector[:12]}-4cc0"
    ).lower()

    tests = [
        "intelligence-engine/framework_selection/tests",
        "intelligence-engine/institutional_evaluation_lab/tests",
        "intelligence-engine/root_cause_intelligence/tests",
    ]
    if sector in {"banks", "nbfc"}:
        tests.append("banking_suite (IEL sector filter)")
    if cause == "future_leakage":
        tests.append("replay_suite")
    tests.append("cio_frozen_25 soft")

    return {
        "format": "patch_brief_v1",
        "pi_version": PI_VERSION,
        "cluster_id": cluster.get("cluster_id"),
        "cluster_key": cluster.get("cluster_key"),
        "root_cause": cause,
        "sector": sector,
        "framework_family": cluster.get("framework_family"),
        "category": cluster.get("category"),
        "affected_questions": gains["affected_questions"],
        "question_ids_sample": list(cluster.get("question_ids") or [])[:12],
        "expected_gain": {
            "framework_accuracy": f"+{gains['framework_accuracy_pp']}%",
            "intent_accuracy": f"+{gains['intent_accuracy_pp']}%",
            "overall_benchmark": f"+{gains['overall_benchmark_pp']}%",
            "projected_pass_pct": gains.get("projected_pass_pct"),
            "projected_framework_accuracy": gains.get("projected_framework_accuracy"),
            "heuristic": True,
        },
        "files_to_review": list(_FILE_MAP.get(cause) or ["intelligence-engine/"]),
        "tests_to_run": tests,
        "risk": risk["risk"],
        "risk_rationale": risk["rationale"],
        "must_not_regress": risk["must_not_regress"],
        "recommended_pr": branch,
        "recommended_title": (
            f"fix({cause}): {sector} / {cluster.get('framework_family')} "
            f"({gains['affected_questions']} Q)"
        ),
        "human_actions": [
            "Review files_to_review — do not apply blindly",
            "Implement minimal selector/mapping change for this cluster only",
            "Run tests_to_run",
            "Re-run IEL institutional_1000 + RCI",
            "Accept only if pass_pct and target dimension improve without CIO-25 regression",
        ],
        "auto_code_written": False,
        "fabricated": False,
    }


def build_queue(
    rci_analysis: dict[str, Any],
    *,
    top_n: int = 10,
) -> dict[str, Any]:
    clusters = list(rci_analysis.get("top_10_clusters") or [])[:top_n]
    briefs = [build_brief(c, rci_context=rci_analysis) for c in clusters]
    # Rank by expected overall gain then affected count
    briefs.sort(
        key=lambda b: (
            -float(str(b["expected_gain"]["overall_benchmark"]).strip("+%")),
            -int(b["affected_questions"]),
        )
    )
    return {
        "pi_version": PI_VERSION,
        "rci_analysis_id": rci_analysis.get("analysis_id"),
        "iel_pass_pct": rci_analysis.get("iel_pass_pct"),
        "n_briefs": len(briefs),
        "briefs": briefs,
        "highest_roi": briefs[0] if briefs else None,
        "never_writes_code_automatically": True,
        "human_in_the_loop": True,
        "fabricated": False,
    }
