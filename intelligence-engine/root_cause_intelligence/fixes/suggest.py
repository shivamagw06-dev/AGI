"""Deterministic suggested fixes + recommended PR briefs from clusters."""

from __future__ import annotations

from typing import Any


_FIX_TEMPLATES: dict[str, dict[str, Any]] = {
    "framework_mismatch": {
        "title": "Optimise framework selector rules",
        "files": [
            "intelligence-engine/framework_selection/mappings/sectors.py",
            "intelligence-engine/framework_selection/mappings/questions.py",
            "intelligence-engine/framework_selection/selector/engine.py",
        ],
        "actions": [
            "Add/adjust sector→framework mappings for the cluster sector",
            "Ensure expected primary frameworks are composed for matching intents",
            "Add regression gold for this sector × intent × framework family",
            "Re-run IEL institutional_1000 and confirm cluster shrinks",
        ],
        "next_sprint": "3.3 Framework Optimisation",
    },
    "intent_mismatch": {
        "title": "Tighten intent resolution routing",
        "files": [
            "intelligence-engine/ask_pipeline/intent_resolution/resolver.py",
            "intelligence-engine/ask_pipeline/intent_resolution/tests/test_intent_resolution.py",
        ],
        "actions": [
            "Add routing gold for misrouted intents in this cluster",
            "Disambiguate Macro/Government/Industry/CrossDomain cues",
            "Preserve concept_mode / as_of behaviour",
            "Re-run IEL and measure intent accuracy proxy",
        ],
        "next_sprint": "3.4 Intent Optimisation",
    },
    "playbook_mismatch": {
        "title": "Align playbook selector with frameworks",
        "files": [
            "intelligence-engine/institutional_playbooks/selector/engine.py",
            "intelligence-engine/institutional_playbooks/registry/",
        ],
        "actions": [
            "Map framework families to playbook prefixes for this sector",
            "Strengthen cue matching (avoid substring traps)",
            "Add playbook selection acceptance cases for the cluster",
        ],
        "next_sprint": "3.3 Framework Optimisation",
    },
    "evidence_cues_miss": {
        "title": "Improve evidence graph domain coverage / cues",
        "files": [
            "intelligence-engine/institutional_evidence_graph/",
        ],
        "actions": [
            "Seed missing domain nodes for sector",
            "Ensure surface/chain bullets expose expected evidence cues",
        ],
        "next_sprint": "3.5 Evidence Weighting",
    },
    "empty_evidence_graph": {
        "title": "Guarantee non-empty evidence graph for category",
        "files": [
            "intelligence-engine/institutional_evidence_graph/assembler/engine.py",
        ],
        "actions": [
            "Add concept-mode stubs for category",
            "Fail soft with transparent insufficiency rather than empty graph",
        ],
        "next_sprint": "3.5 Evidence Weighting",
    },
    "memory_miss_on_analog_question": {
        "title": "Expand IMAI analogue seeds for regime/sector",
        "files": [
            "intelligence-engine/institutional_analog_intelligence/registry/",
            "intelligence-engine/institutional_analog_intelligence/similarity/engine.py",
        ],
        "actions": [
            "Add validated historical seeds for the missing regime",
            "Tune similarity cues (word-safe) for the question pattern",
        ],
        "next_sprint": "imai_seed_expansion",
    },
    "future_leakage": {
        "title": "Harden point-in-time filters",
        "files": [
            "intelligence-engine/institutional_evidence_graph/replay/",
            "intelligence-engine/institutional_analog_intelligence/replay/",
        ],
        "actions": [
            "Enforce available_from <= as_of on all surfaced text",
            "Add replay leakage acceptance tests for cluster as_of dates",
        ],
        "next_sprint": "replay_integrity",
    },
}


def suggest_fix_for_cluster(cluster: dict[str, Any]) -> dict[str, Any]:
    cause = str(cluster.get("root_cause") or "")
    tmpl = _FIX_TEMPLATES.get(
        cause,
        {
            "title": f"Investigate {cause}",
            "files": ["intelligence-engine/institutional_evaluation_lab/"],
            "actions": [
                "Inspect sample failures in the cluster",
                "Add IEL gold labels if expectations are wrong",
                "Re-run benchmark after patch",
            ],
            "next_sprint": "quality_programme",
        },
    )
    branch = (
        f"cursor/fix-{str(cause).replace('_', '-')[:28]}-"
        f"{str(cluster.get('sector') or 'generic')[:12]}-4cc0"
    ).lower()
    return {
        "cluster_id": cluster.get("cluster_id"),
        "cluster_key": cluster.get("cluster_key"),
        "impact": cluster.get("impact_statement"),
        "count": cluster.get("count"),
        "severity": cluster.get("severity"),
        "recommended_branch": branch,
        "title": tmpl["title"],
        "files": list(tmpl["files"]),
        "actions": list(tmpl["actions"]),
        "next_sprint": tmpl["next_sprint"],
        "pr_brief": (
            f"Fix cluster {cluster.get('cluster_id')}: {cluster.get('count')} failures — "
            f"{cause} / {cluster.get('sector')} / {cluster.get('framework_family')}. "
            f"Expected frameworks sample: {cluster.get('expected_frameworks_sample')}; "
            f"actual: {cluster.get('actual_frameworks_sample')}."
        ),
        "acceptance": [
            f"Cluster count decreases on institutional_1000 soft re-run",
            f"No regression vs IEL baseline pass_pct",
            f"Root cause `{cause}` rate declines",
        ],
    }


def recommend_prs(clusters: list[dict[str, Any]], *, top_n: int = 10) -> list[dict[str, Any]]:
    out = []
    for c in clusters[:top_n]:
        fix = suggest_fix_for_cluster(c)
        out.append(fix)
    return out
