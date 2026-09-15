"""Module 6 — Portfolio Policy Engine.

Executable mandate constraints — not prose guidelines.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ipi.portfolio_book import default_book, holding_for
from institutional_reasoning.ipi.schema import DEFAULT_POLICY

POLICY_VERSION = "portfolio-policy-v1.0.0"


def evaluate_policy(
    *,
    entity_id: str | None,
    proposed_weight: float,
    exposure: dict[str, Any] | None = None,
    risk: dict[str, Any] | None = None,
    book: dict[str, Any] | None = None,
) -> dict[str, Any]:
    book = book or default_book()
    policy = dict(DEFAULT_POLICY.to_dict())
    policy.update(book.get("policy") or {})
    # Phase 7 — approved policy overlays (versioned; never silent rewrite of defaults).
    # A learned overlay may only ever TIGHTEN a limit. The mandate stated by the
    # book is a hard ceiling: learning must never widen a client constraint.
    try:
        from institutional_reasoning.cal.overlays import policy_overlay

        overlay = policy_overlay().get("policy") or {}
        for key in ("max_stock_weight", "max_sector_weight", "max_country_weight", "max_theme_weight"):
            if key in overlay and key in policy:
                policy[key] = min(float(policy[key]), float(overlay[key]))
            elif key in overlay:
                policy[key] = float(overlay[key])
    except Exception:
        pass
    symbol = str(entity_id or "").upper()
    exposure = exposure or {}
    risk = risk or {}
    breaches = list(exposure.get("breaches") or [])
    reasons: list[str] = []
    allowed = True

    max_stock = float(policy.get("max_stock_weight") or 0.07)
    if proposed_weight > max_stock + 1e-9:
        allowed = False
        reasons.append(f"stock_weight>{max_stock:.0%}")
        breaches.append({"kind": "stock", "limit": max_stock, "projected": proposed_weight})

    # Cash availability
    cash = float(book.get("cash_weight") or 0.0)
    current = holding_for(symbol, book)
    current_w = float((current or {}).get("weight") or 0.0)
    delta = proposed_weight - current_w
    cash_min = float(policy.get("cash_reserve_min") or 0.05)
    if delta > 0 and cash - delta < cash_min - 1e-9:
        # Not a hard reject — mark needs funding / replace
        reasons.append("cash_insufficient_needs_funding")

    # Risk budget
    rc = float(risk.get("risk_contribution") or 0.0)
    max_rc = float(policy.get("max_single_name_risk_contribution") or 0.18)
    if rc > max_rc + 1e-9:
        allowed = False
        reasons.append("risk_contribution_exceeds_budget")
        breaches.append({"kind": "risk_budget", "limit": max_rc, "projected": rc})

    # Liquidity
    liq = 1.0 - float(risk.get("liquidity_risk") or 0.0)
    min_liq = float(policy.get("min_liquidity_score") or 0.55)
    if liq + 1e-9 < min_liq:
        allowed = False
        reasons.append("liquidity_below_minimum")
        breaches.append({"kind": "liquidity", "limit": min_liq, "projected": liq})

    # Exposure breaches already computed
    if exposure.get("rejected"):
        allowed = False
        for b in exposure.get("breaches") or []:
            reasons.append(str(b.get("kind") or "exposure"))

    # Drawdown policy
    max_dd_policy = float(policy.get("max_drawdown") or 0.28)
    if float(risk.get("maximum_drawdown") or 0) > max_dd_policy + 1e-9 and proposed_weight >= 0.05:
        reasons.append("drawdown_elevated")

    replace_candidate = None
    if delta > 0 and ("cash_insufficient_needs_funding" in reasons or any(b.get("kind") == "sector" for b in breaches)):
        # Suggest reducing largest same-sector peer
        sector = str(((exposure.get("exposure") or {}).get("sector")) or "")
        peers = [
            h
            for h in (book.get("holdings") or [])
            if str(h.get("sector") or "") == sector and str(h.get("symbol") or "").upper() != symbol
        ]
        peers.sort(key=lambda h: float(h.get("weight") or 0), reverse=True)
        if peers:
            replace_candidate = {
                "symbol": peers[0].get("symbol"),
                "current_weight": peers[0].get("weight"),
                "reason": "fund_increase_within_sector_limit",
            }

    can_own_more = allowed and delta > 0
    return {
        "policy_version": POLICY_VERSION,
        "policy": policy,
        "allowed": allowed,
        "can_own_more": can_own_more,
        "violates_concentration": any(b.get("kind") in {"stock", "sector", "theme"} for b in breaches),
        "fits_mandate": allowed,
        "fits_risk_budget": rc <= max_rc + 1e-9,
        "cash_available": cash - max(0.0, delta) >= cash_min - 1e-9,
        "replace_candidate": replace_candidate,
        "breaches": breaches,
        "reasons": reasons,
        "capped_weight": min(proposed_weight, max_stock, max(0.0, current_w + max(0.0, cash - cash_min))),
    }
