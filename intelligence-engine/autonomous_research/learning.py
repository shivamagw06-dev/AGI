"""P6.10 Learning Feedback — operational improvements without altering history."""

from __future__ import annotations

from typing import Any

from autonomous_research.util import now_iso


def build_learning_feedback(
    *,
    company_packs: list[dict[str, Any]],
    qa_results: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    evidence_monitor: dict[str, Any] | None = None,
    publications: dict[str, Any] | None = None,
    analyst_edits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    findings = []

    # Replay / QA mismatches
    for r in (qa_results or {}).get("results") or []:
        qa = r.get("qa") or {}
        if qa.get("blocked"):
            findings.append(
                {
                    "type": "replay_or_qa_mismatch",
                    "company": r.get("company"),
                    "detail": qa.get("failures"),
                    "action": "Improve evidence completeness before next draft cycle",
                }
            )

    cov = (coverage or {}).get("coverage") or {}
    for s in cov.get("stale_reports") or []:
        findings.append(
            {
                "type": "stale_intelligence",
                "company": s.get("company"),
                "detail": s.get("reason"),
                "action": "Schedule coverage refresh",
            }
        )
    for m in cov.get("missing_coverage") or []:
        findings.append(
            {
                "type": "missing_coverage",
                "company": m.get("company"),
                "detail": m.get("reason"),
                "action": "Compile CompanyMemory / Opportunity pack",
            }
        )

    # Missed catalysts proxy: high catalysts without draft
    for p in company_packs:
        oie = p.get("opportunity") or {}
        high = [c for c in (oie.get("catalysts") or []) if c.get("importance") == "High"]
        if high and (oie.get("research_priority") in {"Low", "Monitor"}):
            findings.append(
                {
                    "type": "missed_catalyst_signal",
                    "company": p.get("display") or p.get("entity"),
                    "detail": [c.get("name") for c in high[:3]],
                    "action": "Raise planner weight for high catalysts",
                }
            )

    for edit in analyst_edits or []:
        findings.append(
            {
                "type": "analyst_edit",
                "company": edit.get("company"),
                "detail": edit.get("note"),
                "action": "Capture edit pattern for future draft templates",
            }
        )

    if (publications or {}).get("rejected_n"):
        findings.append(
            {
                "type": "evidence_conflicts_or_qa_rejects",
                "company": None,
                "detail": {"rejected_n": publications.get("rejected_n")},
                "action": "Tighten generator evidence requirements",
            }
        )

    # Turnaround proxy
    findings.append(
        {
            "type": "research_turnaround",
            "company": None,
            "detail": {
                "packs_ok": sum(1 for p in company_packs if p.get("ok")),
                "meaningful_evidence_events": (evidence_monitor or {}).get("meaningful_n"),
                "qa_passed": (qa_results or {}).get("passed_n"),
            },
            "action": "Track cycle time externally; do not mutate historical artefacts",
        }
    )

    return {
        "as_of": now_iso(),
        "n_findings": len(findings),
        "findings": findings,
        "policy": "improve_future_workflows_without_altering_historical_outputs",
        "issues_recommendations": False,
        "modifies_decision_engine": False,
    }
