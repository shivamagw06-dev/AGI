"""Materiality Engine — filter noise; escalate institutional learning events."""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge.schema import MacroKnowledgeObject, MaterialityTier

# Policy: absolute change thresholds by indicator family
_BPS_HIGH = 0.25  # 25 bps for rates
_BPS_CRITICAL = 0.50
_PCT_POINTS_MEDIUM = 0.20
_PCT_POINTS_HIGH = 0.50


def evaluate_materiality(mko: MacroKnowledgeObject) -> dict[str, Any]:
    """Score materiality. Immaterial updates are filtered (Ignore)."""
    indicator = mko.indicator.lower()
    cur = mko.current_value
    prev = mko.previous_value
    delta = None if cur is None or prev is None else cur - prev
    surprise = mko.normalized.get("surprise_vs_consensus")

    tier: MaterialityTier = "Low"
    score = 0.15
    reason = "routine_update"
    learn = False

    # Document releases
    if cur is None:
        if mko.importance == "Critical":
            tier, score, reason, learn = "High", 0.75, "critical_document_release", True
        else:
            tier, score, reason, learn = "Medium", 0.45, "document_release", True
        return _result(mko, tier, score, reason, learn, delta)

    # Policy rates / repo family
    if any(k in indicator for k in ("repo", "federal funds", "reverse repo", "sdf", "msf", "crr", "slr")):
        if delta is None or abs(delta) < 1e-9:
            return _result(mko, "Ignore", 0.0, "rate_unchanged", False, delta)
        ad = abs(delta)
        if ad >= _BPS_CRITICAL:
            return _result(mko, "Critical", 0.95, f"rate_move_{ad:.2f}", True, delta)
        if ad >= _BPS_HIGH:
            return _result(mko, "High", 0.80, f"rate_move_{ad:.2f}", True, delta)
        return _result(mko, "Medium", 0.55, f"rate_move_{ad:.2f}", True, delta)

    # Inflation / growth print surprises
    if any(k in indicator for k in ("cpi", "wpi", "gdp", "gva", "iip")):
        base = abs(delta) if delta is not None else 0.0
        sur = abs(float(surprise)) if surprise is not None else 0.0
        magnitude = max(base, sur)
        if magnitude >= _PCT_POINTS_HIGH:
            return _result(mko, "High", 0.85, "macro_print_material", True, delta)
        if magnitude >= _PCT_POINTS_MEDIUM or (surprise is not None and abs(float(surprise)) >= 0.15):
            return _result(mko, "Medium", 0.60, "macro_print_notable", True, delta)
        if mko.importance in {"Critical", "High"}:
            # Still publish knowledge but light learning
            return _result(mko, "Low", 0.30, "macro_print_immaterial_delta", False, delta)
        return _result(mko, "Ignore", 0.05, "immaterial_print", False, delta)

    # Fiscal / liquidity / forex / flows
    if any(k in indicator for k in ("fiscal", "gst", "forex", "liquidity", "credit", "mutual fund", "cli", "growth")):
        if delta is None:
            return _result(mko, "Low", 0.25, "non_numeric_or_first", mko.importance == "Critical", delta)
        # Relative move if previous non-zero
        rel = abs(delta / prev) if prev not in (None, 0) else abs(delta)
        if rel >= 0.10 or abs(delta) >= 1.0:
            return _result(mko, "Medium", 0.55, "flow_or_stock_move", True, delta)
        if mko.importance == "Critical":
            return _result(mko, "Low", 0.35, "critical_but_small_move", False, delta)
        return _result(mko, "Ignore", 0.08, "immaterial_flow", False, delta)

    # Default
    if mko.importance == "Critical":
        return _result(mko, "Medium", 0.50, "critical_importance_default", True, delta)
    if delta is not None and abs(delta) > 0:
        return _result(mko, "Low", 0.25, "small_change", False, delta)
    return _result(mko, "Ignore", 0.0, "no_material_change", False, delta)


def _result(
    mko: MacroKnowledgeObject,
    tier: MaterialityTier,
    score: float,
    reason: str,
    learn: bool,
    delta: float | None,
) -> dict[str, Any]:
    mko.materiality_tier = tier
    mko.materiality_score = score
    return {
        "mko_id": mko.mko_id,
        "indicator": mko.indicator,
        "tier": tier,
        "score": score,
        "reason": reason,
        "learn": learn,
        "delta": delta,
        "filtered": tier == "Ignore",
    }
