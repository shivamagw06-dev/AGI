"""Module 6 — Institutional Committee Orchestration.

Specialised committees consume only their own task outputs and produce
structured verdicts. The investment committee merges them — it cannot
invent findings that no committee produced.
"""

from __future__ import annotations

from typing import Any

COMMITTEES_VERSION = "committee-orchestration-v1.0.0"

COMMITTEES = ("valuation", "business", "accounting", "risk", "portfolio")

_LABELS = {
    "valuation": "Valuation Committee",
    "business": "Business Committee",
    "accounting": "Accounting Committee",
    "risk": "Risk Committee",
    "portfolio": "Portfolio Committee",
    "investment": "Investment Committee",
}


def _stance_for(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No submissions"
    statuses = {r.get("status") for r in results}
    if statuses <= {"not_applicable", "skipped"}:
        return "Not applicable"
    if "executed" in statuses and not (statuses & {"insufficient", "adapted"}):
        return "Evidence-supported"
    if statuses & {"executed", "adapted"}:
        return "Partial evidence"
    return "Insufficient evidence"


def run_committee(name: str, task_results: list[dict[str, Any]]) -> dict[str, Any]:
    mine = [r for r in task_results if r.get("committee") == name]
    stance = _stance_for(mine)
    findings = []
    for r in mine:
        prefix = r.get("label") or r.get("task_id")
        if r.get("status") == "executed":
            findings.append(f"{prefix}: {r.get('summary') or 'executed'}")
        elif r.get("status") == "adapted":
            route = (r.get("adaptations") or [{}])[-1].get("route")
            findings.append(f"{prefix}: executed via alternative route ({route}).")
        elif r.get("status") == "insufficient":
            missing = ", ".join((r.get("missing_evidence") or [])[:4])
            findings.append(f"{prefix}: insufficient evidence (missing {missing}).")
        elif r.get("status") == "not_applicable":
            findings.append(f"{prefix}: not applicable.")
    confidences = [
        float(r["confidence"]) for r in mine if isinstance(r.get("confidence"), (int, float))
    ]
    return {
        "committee": name,
        "label": _LABELS.get(name, name),
        "stance": stance,
        "findings": findings,
        "task_ids": [r.get("task_id") for r in mine],
        "n_tasks": len(mine),
        "executed": sum(1 for r in mine if r.get("status") in {"executed", "adapted"}),
        "insufficient": sum(1 for r in mine if r.get("status") == "insufficient"),
        "confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
        "justification_graphs": [
            r.get("task_id") for r in mine if (r.get("justification_graph") or {}).get("nodes")
        ],
        "committees_version": COMMITTEES_VERSION,
    }


def run_all_committees(task_results: list[dict[str, Any]]) -> dict[str, Any]:
    present = [c for c in COMMITTEES if any(r.get("committee") == c for r in task_results)]
    return {name: run_committee(name, task_results) for name in present}


def investment_committee(
    *,
    committees: dict[str, Any],
    task_results: list[dict[str, Any]],
    goal: dict[str, Any],
) -> dict[str, Any]:
    """Merges specialised committee verdicts — never invents its own findings."""
    stances = {name: c.get("stance") for name, c in committees.items()}
    supported = [n for n, s in stances.items() if s == "Evidence-supported"]
    partial = [n for n, s in stances.items() if s == "Partial evidence"]
    insufficient = [n for n, s in stances.items() if s == "Insufficient evidence"]

    blocking = [
        r
        for r in task_results
        if r.get("status") == "insufficient" and not r.get("optional")
    ]
    optional_gaps = [
        r for r in task_results if r.get("status") == "insufficient" and r.get("optional")
    ]
    # A committee whose entire remit was optional is a gap, not a blocker.
    optional_only_committees = {
        name
        for name in insufficient
        if all(
            r.get("optional")
            for r in task_results
            if r.get("committee") == name and r.get("status") == "insufficient"
        )
    }
    hard_insufficient = [n for n in insufficient if n not in optional_only_committees]

    if not supported and not partial:
        stance = "Insufficient evidence"
        recommendation = (
            "No committee could reach an evidence-supported view. "
            "No portfolio recommendation is issued."
        )
    elif blocking or hard_insufficient:
        stance = "Partial evidence"
        missing = sorted({m for r in blocking for m in (r.get("missing_evidence") or [])})
        recommendation = (
            "Partial research package. "
            f"Supported: {', '.join(supported) or 'none'}. "
            f"Blocked: {', '.join(hard_insufficient + [r['task_id'] for r in blocking]) or 'none'}. "
            + (f"Missing evidence: {', '.join(missing[:6])}. " if missing else "")
            + "A portfolio recommendation is withheld."
        )
    elif optional_gaps:
        stance = "Partial evidence"
        gap_ids = ", ".join(sorted({r["task_id"] for r in optional_gaps}))
        recommendation = (
            f"Required workstreams executed ({', '.join(supported + partial)}). "
            f"Optional workstreams without evidence producers: {gap_ids}. "
            "A portfolio recommendation is withheld until those workstreams can execute."
        )
    else:
        stance = "Evidence-supported"
        recommendation = (
            f"All required workstreams executed ({', '.join(supported + partial)}). "
            "Recommendation reflects committee outputs only."
        )

    disagreements: list[str] = []
    for r in task_results:
        for c in ((r.get("justification_graph") or {}).get("nodes") or []):
            if c.get("kind") == "conflict" and (c.get("attrs") or {}).get("explanation"):
                disagreements.append(f"{r.get('task_id')}: {c['attrs']['explanation']}")

    return {
        "committee": "investment",
        "label": _LABELS["investment"],
        "goal_type": goal.get("goal_type"),
        "stance": stance,
        "recommendation": recommendation,
        "supported_committees": supported,
        "partial_committees": partial,
        "insufficient_committees": insufficient,
        "blocking_committees": hard_insufficient,
        "optional_gap_tasks": [r.get("task_id") for r in optional_gaps],
        "blocking_tasks": [r.get("task_id") for r in blocking],
        "member_stances": stances,
        "disagreements": disagreements[:12],
        "can_recommend": stance == "Evidence-supported",
        "committees_version": COMMITTEES_VERSION,
    }
