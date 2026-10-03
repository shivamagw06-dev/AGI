"""Automatic QA — governance + logical consistency sanity checks."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.golden_universe.schema import (
    CONSTRUCTIVE_DECISIONS,
    HIGH_CONVICTION_BANDS,
    HIGH_CONVICTION_READINESS_FLOOR,
)


def _f(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def run_qa_checks(row: dict[str, Any]) -> dict[str, Any]:
    """Return violations + pass flag for one evaluation row."""
    violations: list[dict[str, Any]] = []
    readiness = _f(row.get("recommendation_readiness"))
    decision = str(row.get("decision") or "").strip()
    decision_l = decision.lower()
    band = str(row.get("readiness_band") or "")
    thesis = str(row.get("investment_thesis_status") or "")
    gate = str(row.get("gate") or "")

    # --- Governance ---
    if (
        decision_l in {"high conviction"}
        or band in HIGH_CONVICTION_BANDS
        or "high conviction" in decision_l
    ):
        if readiness is not None and readiness < HIGH_CONVICTION_READINESS_FLOOR:
            violations.append(
                {
                    "rule": "no_high_conviction_below_readiness_floor",
                    "severity": "governance",
                    "detail": (
                        f"High Conviction / high_conviction_allowed with readiness "
                        f"{readiness}% < {HIGH_CONVICTION_READINESS_FLOOR}%."
                    ),
                }
            )

    if decision_l in CONSTRUCTIVE_DECISIONS or decision_l in {"high conviction", "constructive"}:
        if not row.get("price_available"):
            # Valuation-sensitive constructive calls require a live/available price
            if (_f(row.get("valuation")) or 0) > 0 or "valuation" in decision_l:
                violations.append(
                    {
                        "rule": "no_valuation_call_without_price",
                        "severity": "governance",
                        "detail": "Constructive/valuation-linked decision without available live price.",
                    }
                )

    # INCONCLUSIVE when mandatory evidence missing / gate failed
    if gate == "FAIL" or (readiness is not None and readiness < 50):
        if decision_l in {"high conviction", "constructive"} and thesis != "INCONCLUSIVE":
            violations.append(
                {
                    "rule": "inconclusive_required_when_evidence_missing",
                    "severity": "governance",
                    "detail": (
                        f"Gate={gate}, readiness={readiness}: decision should be Deferred/INCONCLUSIVE, "
                        f"got {decision!r} (thesis={thesis!r})."
                    ),
                }
            )

    # --- Logical consistency ---
    cq = _f(row.get("company_quality"))
    fq = _f(row.get("financial_quality"))
    overall = _f(row.get("overall_score"))
    val = _f(row.get("valuation"))

    if cq is not None and fq is not None and overall is not None:
        if cq >= 9.0 and fq >= 9.0 and overall <= 3.5:
            # Allow if gate failed / deferred with documented not_a_negative_view
            if not (
                row.get("not_a_negative_view")
                or thesis == "INCONCLUSIVE"
                or decision_l in {"deferred", "inconclusive", "watchlist"}
            ):
                violations.append(
                    {
                        "rule": "quality_vs_overall_inconsistency",
                        "severity": "logic",
                        "detail": (
                            f"Company Quality {cq} + Financial Quality {fq} vs overall {overall} "
                            "without documented deferral/INCONCLUSIVE reason."
                        ),
                    }
                )

    if val is not None and val <= 3.5:
        if decision_l in {"high conviction"} or band in HIGH_CONVICTION_BANDS:
            justification = row.get("valuation_justification") or row.get("decision_reason")
            if not justification:
                violations.append(
                    {
                        "rule": "weak_valuation_high_conviction_needs_justification",
                        "severity": "logic",
                        "detail": (
                            f"Valuation {val} is very weak but decision is High Conviction "
                            "without explicit justification."
                        ),
                    }
                )

    return {
        "ticker": row.get("ticker"),
        "passed": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations,
    }


def suite_qa_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    checks = [run_qa_checks(r) for r in rows]
    failed = [c for c in checks if not c["passed"]]
    by_rule: dict[str, int] = {}
    for c in failed:
        for v in c.get("violations") or []:
            rule = str(v.get("rule") or "unknown")
            by_rule[rule] = by_rule.get(rule, 0) + 1
    n = len(rows) or 1
    return {
        "n": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "pass_pct": round(100.0 * (len(rows) - len(failed)) / n, 1),
        "by_rule": by_rule,
        "failures": failed[:50],
    }
