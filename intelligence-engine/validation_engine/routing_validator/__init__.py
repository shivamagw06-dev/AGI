"""Routing validator — analyst + layer routing quality."""

from __future__ import annotations

from typing import Any


def validate_routing(
    *,
    question: str,
    analyst_router: dict[str, Any] | None = None,
    layer_router: dict[str, Any] | None = None,
    primary_objective: str | None = None,
) -> dict[str, Any]:
    q = (question or "").lower()
    iar = analyst_router or {}
    ilr = layer_router or {}
    # unwrap nested soft-slices if present
    if "analyst_router" in iar and isinstance(iar.get("analyst_router"), dict):
        iar = iar["analyst_router"]
    if "layer_router" in ilr and isinstance(ilr.get("layer_router"), dict):
        ilr = ilr["layer_router"]

    required_analysts = list(iar.get("required_analysts") or [])
    suppressed_analysts = list(iar.get("suppressed_analysts") or [])
    required_layers = list(ilr.get("required_layers") or [])
    suppressed_layers = list(ilr.get("suppressed_layers") or [])

    issues: list[str] = []
    score = 0.7

    if required_analysts or required_layers:
        score = 0.9
    educational = "explain" in q or "educational" in (primary_objective or "").lower()
    if educational:
        # Ownership / Portfolio / Committee should be suppressed for education
        bad = [a for a in ("Portfolio", "Committee", "Ownership") if a in required_analysts]
        if bad:
            issues.append("irrelevant_analysts")
            score -= 0.3
        else:
            score = max(score, 0.92)

    if "should i buy" in q or "investment evaluation" in (primary_objective or "").lower():
        need = {"Business", "Financial", "Valuation"}
        if required_analysts and not need.issubset(set(required_analysts)):
            issues.append("incomplete_analyst_routing")
            score -= 0.15
        elif not required_analysts:
            # soft inferred ok
            score = max(score, 0.8)

    if required_analysts and suppressed_analysts:
        overlap = set(required_analysts) & set(suppressed_analysts)
        if overlap:
            issues.append("analyst_routing_conflict")
            score -= 0.35

    if required_layers and suppressed_layers:
        overlap_l = set(required_layers) & set(suppressed_layers)
        if overlap_l:
            issues.append("layer_routing_conflict")
            score -= 0.35

    if not required_analysts and not required_layers:
        issues.append("routing_not_provided")
        score = min(score, 0.78)

    score = max(0.0, min(1.0, score))
    status = "valid" if score >= 0.85 and not any(i.endswith("conflict") for i in issues) else (
        "invalid" if score < 0.5 else "warning" if issues else "inferred"
    )

    return {
        "status": status,
        "score": round(score, 4),
        "issues": issues,
        "required_analysts": required_analysts,
        "suppressed_analysts": suppressed_analysts,
        "required_layers": required_layers,
        "recommended_analysts": required_analysts
        or _infer_analysts(q, primary_objective),
        "suppressed": suppressed_analysts
        or _infer_suppressed(q, primary_objective),
    }


def _infer_analysts(q: str, objective: str | None) -> list[str]:
    obj = (objective or "").lower()
    if "explain" in q or "educational" in obj:
        return ["Academy", "Financial"]
    if "compare" in q:
        return ["Business", "Financial", "Valuation", "Sector"]
    if "portfolio" in q:
        return ["Portfolio", "Risk", "Macro"]
    if "rbi" in q or "macro" in obj:
        return ["Macro", "Sector", "Forecast"]
    if "risk" in q:
        return ["Risk", "Financial"]
    return ["Business", "Financial", "Valuation", "Risk", "Portfolio"]


def _infer_suppressed(q: str, objective: str | None) -> list[str]:
    obj = (objective or "").lower()
    if "explain" in q or "educational" in obj:
        return ["Ownership", "Accounting", "Portfolio", "Committee"]
    if "versus history" in q:
        return ["Business", "Management", "Portfolio"]
    return ["Ownership", "Accounting", "Academy"]
