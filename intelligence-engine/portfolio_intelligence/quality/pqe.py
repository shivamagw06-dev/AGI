"""Portfolio Quality Engine (PQE) — portfolio-level quality, not return optimisation.

Scores Business / Financial / Management / Accounting / Capital Allocation /
Valuation Discipline / Evidence Coverage / Knowledge Confidence at book level.
Soft-consumes MII + ACI when available for held names.
"""

from __future__ import annotations

from typing import Any


_SOFT_Q_CACHE: dict[str, dict[str, float]] = {}


def _soft_company_quality(ticker: str) -> dict[str, float]:
    """Pull soft quality signals from MII/ACI without redesign (cached per process)."""
    t = (ticker or "").upper()
    if t in _SOFT_Q_CACHE:
        return dict(_SOFT_Q_CACHE[t])
    out = {
        "business_quality": 70.0,
        "financial_quality": 70.0,
        "management_quality": 65.0,
        "accounting_quality": 70.0,
        "capital_allocation_quality": 65.0,
        "valuation_discipline": 60.0,
        "evidence_coverage": 55.0,
        "knowledge_confidence": 60.0,
    }
    try:
        from management_intelligence.production import analyse as mii_analyse

        mii = mii_analyse(t)
        if mii.get("found"):
            conf = (mii.get("confidence") or {}).get("confidence")
            if conf is not None:
                out["management_quality"] = float(conf)
            cap = (mii.get("capital") or {}).get("capital_allocation")
            if cap is not None:
                out["capital_allocation_quality"] = float(cap)
    except Exception:
        pass
    try:
        from accounting_intelligence.production import analyse as aci_analyse

        aci = aci_analyse(t)
        if aci.get("found"):
            aq = (aci.get("report") or {}).get("accounting_quality_score")
            if aq is not None:
                out["accounting_quality"] = float(aq)
            conf = (aci.get("confidence") or {}).get("confidence")
            if conf is not None:
                out["financial_quality"] = (out["financial_quality"] + float(conf)) / 2
                out["knowledge_confidence"] = max(out["knowledge_confidence"], float(conf) * 0.9)
            ev = (aci.get("evidence") or {}).get("count") or 0
            out["evidence_coverage"] = min(100.0, 40.0 + float(ev) * 8.0)
    except Exception:
        pass
    _SOFT_Q_CACHE[t] = dict(out)
    return dict(out)


def portfolio_quality(holdings: list[dict[str, Any]]) -> dict[str, Any]:
    if not holdings:
        return {"portfolio_quality": 0.0, "dimensions": {}, "holdings_scored": 0}

    dims = {
        "business_quality": 0.0,
        "financial_quality": 0.0,
        "management_quality": 0.0,
        "accounting_quality": 0.0,
        "capital_allocation_quality": 0.0,
        "valuation_discipline": 0.0,
        "evidence_coverage": 0.0,
        "knowledge_confidence": 0.0,
    }
    tw = 0.0
    per_name = []
    for h in holdings:
        w = float(h.get("weight") or 0)
        if w <= 0:
            continue
        q = _soft_company_quality(str(h.get("ticker")))
        # Valuation discipline prior: quality/value blend from factors
        factors = h.get("factors") if isinstance(h.get("factors"), dict) else {}
        q["valuation_discipline"] = 40.0 + 40.0 * float(factors.get("value") or 0.4) + 10.0 * float(
            factors.get("quality") or 0.5
        )
        q["business_quality"] = 55.0 + 40.0 * float(factors.get("quality") or 0.6)
        conv = str(h.get("conviction") or "medium").lower()
        if conv == "high":
            q["knowledge_confidence"] = min(100.0, q["knowledge_confidence"] + 8)
        elif conv == "low":
            q["knowledge_confidence"] = max(0.0, q["knowledge_confidence"] - 10)
        for k in dims:
            dims[k] += w * float(q[k])
        tw += w
        per_name.append({"ticker": h.get("ticker"), "weight": round(w, 4), **{k: round(q[k], 1) for k in dims}})

    if tw:
        dims = {k: round(v / tw, 1) for k, v in dims.items()}
    # Equal-weight dimensions for portfolio quality score
    score = round(sum(dims.values()) / len(dims), 1)
    return {
        "portfolio_quality": score,
        "dimensions": dims,
        "holdings_scored": len(per_name),
        "per_holding": per_name[:12],
        "question": "If I replace A with B, does portfolio quality rise even if expected return is similar?",
        "never_return_optimisation": True,
    }


def quality_delta(current: dict[str, Any], pro_forma: dict[str, Any]) -> dict[str, Any]:
    c = float((current or {}).get("portfolio_quality") or 0)
    p = float((pro_forma or {}).get("portfolio_quality") or 0)
    return {
        "current": c,
        "pro_forma": p,
        "delta": round(p - c, 2),
        "improves": p > c + 0.2,
    }
