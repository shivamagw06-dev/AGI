"""Deterministic, explainable Financial Quality Score."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.validation.schema import GRADES, SCORE_WEIGHTS


def _component_from_findings(findings: list[dict[str, Any]], rule_prefix: str) -> float:
    rows = [f for f in findings if str(f.get("rule_id") or "").startswith(rule_prefix)]
    if not rows:
        return 1.0
    scored = [f for f in rows if f.get("status") in ("PASS", "FAIL", "WARN")]
    if not scored:
        return 1.0
    score = 0.0
    for f in scored:
        st = f.get("status")
        if st == "PASS":
            score += 1.0
        elif st == "WARN":
            score += 0.7
        else:
            # FAIL
            sev = f.get("severity")
            score += 0.0 if sev in ("ERROR", "CRITICAL") else 0.3
    return score / len(scored)


def _grade(score: float, *, blocked: bool) -> str:
    if blocked or score < 0.50:
        return "Fail"
    if score >= 0.97:
        return "A+"
    if score >= 0.90:
        return "A"
    if score >= 0.80:
        return "B"
    if score >= 0.70:
        return "C"
    if score >= 0.50:
        return "D"
    return "Fail"


def compute_quality_score(
    findings: list[dict[str, Any]],
    *,
    coverage_scorecard: dict[str, Any] | None = None,
    confidence: dict[str, Any] | None = None,
    blocked: bool = False,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    w = dict(SCORE_WEIGHTS)
    if weights:
        w.update(weights)

    structural = _component_from_findings(findings, "STR_")
    # include input integrity in structural
    structural = min(structural, _component_from_findings(findings, "INP_"))
    accounting = _component_from_findings(findings, "ACCT_")
    temporal = _component_from_findings(findings, "TMP_")
    statistical = _component_from_findings(findings, "STAT_")
    # cross + sector fold into accounting/structural lightly
    cross = _component_from_findings(findings, "XST_")
    accounting = (accounting * 0.8) + (cross * 0.2)

    cov_pct = float((coverage_scorecard or {}).get("coverage_percentage") or 0.0)
    coverage_quality = max(0.0, min(1.0, cov_pct))
    parser_conf = float((confidence or {}).get("overall") or 0.0)
    parser_conf = max(0.0, min(1.0, parser_conf))

    components = {
        "structural_quality": round(structural, 6),
        "accounting_integrity": round(accounting, 6),
        "coverage_quality": round(coverage_quality, 6),
        "temporal_consistency": round(temporal, 6),
        "statistical_health": round(statistical, 6),
        "parser_confidence": round(parser_conf, 6),
    }
    total_w = sum(w.values()) or 1.0
    score = sum(components[k] * w.get(k, 0.0) for k in components) / total_w
    grade = _grade(score, blocked=blocked)
    assert grade in GRADES or grade == "Fail"

    explanation = [
        {"component": k, "score": components[k], "weight": w.get(k, 0.0)} for k in components
    ]
    return {
        "score": round(score, 6),
        "grade": grade,
        "components": components,
        "weights": w,
        "explanation": explanation,
        "explainable": True,
        "deterministic": True,
    }
