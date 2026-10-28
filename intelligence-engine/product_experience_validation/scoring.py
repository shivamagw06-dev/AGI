"""E2E-01 scoring — dimension weights → total / 100."""

from __future__ import annotations

from typing import Any

from product_experience_validation.schema import PASS_SCORE, RUBRIC_WEIGHTS, WORKFLOWS


def _workflow_pass_ratio(wf: dict[str, Any]) -> float:
    checks = wf.get("checks") or []
    if not checks:
        return 0.0
    ok = sum(1 for c in checks if c.get("ok"))
    return ok / len(checks)


def score_run(workflows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate workflow results into weighted dimension scores."""
    by_id = {str(w.get("workflow")): w for w in workflows}
    dim_scores: dict[str, list[float]] = {k: [] for k in RUBRIC_WEIGHTS}
    failure_codes: list[str] = []

    for meta in WORKFLOWS:
        wid = meta["id"]
        dim = meta["dimension"]
        wf = by_id.get(wid) or {}
        ratio = _workflow_pass_ratio(wf)
        dim_scores.setdefault(dim, []).append(ratio)
        for c in wf.get("checks") or []:
            if not c.get("ok") and c.get("code"):
                code = str(c["code"])
                if code not in failure_codes:
                    failure_codes.append(code)

    dimensions: dict[str, Any] = {}
    raw_total = 0.0
    weight_total = float(sum(RUBRIC_WEIGHTS.values()) or 100.0)
    for dim, weight in RUBRIC_WEIGHTS.items():
        ratios = dim_scores.get(dim) or [0.0]
        avg = sum(ratios) / len(ratios)
        points = round(avg * weight, 2)
        dimensions[dim] = {
            "weight": weight,
            "ratio": round(avg, 4),
            "points": points,
            "passed": avg >= 0.9,
        }
        raw_total += points

    # Spec weights sum to 105; normalize to a 0–100 institutional scorecard.
    total = round((raw_total / weight_total) * 100.0, 2)
    critical = {"HALLUCINATED_FACT", "ENGINE_JARGON_LEAK"}
    passed = total >= PASS_SCORE and not any(c in critical for c in failure_codes)

    return {
        "score": total,
        "raw_points": round(raw_total, 2),
        "weight_total": weight_total,
        "pass_score": PASS_SCORE,
        "passed": passed,
        "dimensions": dimensions,
        "failure_codes": failure_codes,
        "summary": (
            f"PASS — product experience score {total}/100 (pass≥{PASS_SCORE})"
            if passed
            else f"FAIL — product experience score {total}/100 (pass≥{PASS_SCORE}); codes={failure_codes}"
        ),
    }
