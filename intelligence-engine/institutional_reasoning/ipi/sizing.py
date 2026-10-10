"""Module 2 — Position Sizing Intelligence.

Institutional investors think in weights, not BUY/SELL.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ipi.portfolio_book import default_book, holding_for

SIZING_VERSION = "position-sizing-v1.0.0"


def _conviction(expected_return: float, downside: float, confidence: float) -> str:
    score = expected_return * 2.0 - downside + (confidence - 0.5)
    if score >= 0.35:
        return "High"
    if score >= 0.12:
        return "Medium"
    return "Low"


def size_position(
    *,
    entity_id: str | None,
    evidence: dict[str, Any] | None = None,
    downside: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
    exposure: dict[str, Any] | None = None,
    policy_eval: dict[str, Any] | None = None,
    research_confidence: float | None = None,
    book: dict[str, Any] | None = None,
) -> dict[str, Any]:
    book = book or default_book()
    evidence = evidence or {}
    downside = downside or {}
    risk = risk or {}
    exposure = exposure or {}
    policy_eval = policy_eval or {}
    policy = policy_eval.get("policy") or (book.get("policy") or {})

    symbol = str(entity_id or "").upper()
    current = holding_for(symbol, book)
    current_w = float((current or {}).get("weight") or 0.0)

    base_ret = float(((downside.get("base_case") or {}).get("expected_return")) or 0.0)
    exp_loss = float(downside.get("expected_loss") or 0.0)
    conf = float(research_confidence if research_confidence is not None else 0.75)
    vol = float(risk.get("volatility") or 0.24)
    max_stock = float(policy.get("max_stock_weight") or 0.07)
    risk_budget = float(policy.get("risk_budget") or 0.12)

    # Kelly-lite / risk-budget sizing: w ≈ (edge / vol^2) clipped to policy.
    edge = max(-0.2, min(0.35, base_ret))
    raw = (edge / max(vol * vol, 1e-4)) * 0.02
    # Confidence scales size; downside shrinks it.
    raw *= max(0.35, min(1.15, conf))
    raw *= max(0.4, 1.0 - exp_loss)
    # Correlated sector risk shrinks further
    rc = float(risk.get("risk_contribution") or 0.0)
    if rc > risk_budget:
        raw *= risk_budget / max(rc, 1e-6)

    target = max(0.0, min(max_stock, raw if raw > 0 else current_w * 0.5))
    # Prefer modest increases from current when edge positive
    if edge > 0.03 and current_w > 0:
        target = max(target, min(max_stock, current_w + 0.01))
    if edge > 0.08:
        target = max(target, min(max_stock, 0.04 + edge * 0.08))

    # Liquidity cap
    liq_risk = float(risk.get("liquidity_risk") or 0.0)
    if liq_risk >= 0.45:
        target = min(target, 0.02)

    # Policy hard cap
    capped = float(policy_eval.get("capped_weight") or target)
    target = min(target, capped, max_stock)

    # Bucket headroom is a hard ceiling: a position may never push its sector,
    # country, or theme past the mandate limit.
    headroom = exposure.get("max_allowed_weight")
    if headroom is None:
        headroom = (exposure.get("exposure") or {}).get("max_allowed_weight")
    if headroom is not None:
        target = min(target, max(0.0, float(headroom)))

    ceiling = min(max_stock, float(headroom)) if headroom is not None else max_stock
    max_w = min(ceiling, round(target + 0.01, 4))
    min_w = round(max(0.0, target * 0.7 if target > 0 else 0.0), 4)
    target = round(target, 4)

    if not downside.get("computable", True) or downside.get("withhold"):
        return {
            "sizing_version": SIZING_VERSION,
            "action": "Withhold",
            "target_weight": current_w,
            "maximum_weight": current_w,
            "minimum_weight": current_w,
            "current_weight": current_w,
            "conviction": "None",
            "confidence": conf,
            "reason": "Downside not computable — portfolio recommendation withheld",
            "withheld": True,
        }

    eps = 0.0025
    if target <= eps and current_w <= eps:
        action = "Watch"
    elif target + eps < current_w * 0.5 and current_w > 0.03:
        action = "Exit"
    elif target + eps < current_w:
        action = "Reduce"
    elif target > current_w + eps:
        action = "Increase"
    else:
        action = "Hold"

    # Replace suggestion when funding required
    if action == "Increase" and (policy_eval.get("replace_candidate")):
        # Keep Increase but annotate; committee may choose Replace
        pass

    conviction = _conviction(edge, exp_loss, conf)
    reasons = []
    if float(evidence.get("roic") or 0) >= 0.2 or float(evidence.get("roic") or 0) >= 20:
        reasons.append("High quality")
    pe = evidence.get("current_pe")
    peer = evidence.get("peer_pe") or evidence.get("peer_median_pe")
    try:
        if pe and peer and float(pe) > float(peer):
            reasons.append("Moderate valuation premium")
        elif pe and peer and float(pe) < float(peer):
            reasons.append("Valuation discount vs peers")
    except (TypeError, ValueError):
        pass
    if exp_loss <= 0.15:
        reasons.append("Acceptable downside")
    if liq_risk >= 0.45:
        reasons.append("Liquidity cap applied")
    if any(b.get("kind") == "sector" for b in (policy_eval.get("breaches") or [])):
        reasons.append("Sector limit constrains weight")
    if not reasons:
        reasons = ["Evidence-backed risk budget sizing"]

    return {
        "sizing_version": SIZING_VERSION,
        "action": action,
        "target_weight": target,
        "maximum_weight": max_w,
        "minimum_weight": min_w,
        "current_weight": current_w,
        "conviction": conviction,
        "confidence": round(conf, 4),
        "reason": "; ".join(reasons),
        "reasons": reasons,
        "withheld": False,
        "expected_return": edge,
        "expected_downside": exp_loss,
    }
