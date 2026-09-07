"""Derived valuation producers — never store PE; compute from primitives."""

from __future__ import annotations

from typing import Any


def _pe_from_primitives(primitives: dict[str, dict[str, float]]) -> dict[str, Any]:
    price = primitives.get("price") or {}
    eps = primitives.get("eps") or {}
    points: dict[str, float] = {}
    rejected: dict[str, str] = {}
    for fy, px in price.items():
        e = eps.get(fy)
        if e is None:
            rejected[fy] = "missing_eps"
            continue
        if float(e) <= 0:
            rejected[fy] = "non_positive_eps"
            continue
        points[fy] = round(float(px) / float(e), 6)
    if not points:
        return {
            "found": False,
            "insufficient": True,
            "reason": "missing_or_non_positive_eps",
            "rejected_periods": rejected,
            "formula": "price / eps",
            "derived_from": ["price", "eps"],
            "provider": "kf_derived_producer",
        }
    return {
        "points": points,
        "formula": "price / eps",
        "derived_from": ["price", "eps"],
        "rejected_periods": rejected,
        "provider": "kf_derived_producer",
    }


def produce_valuation(entity: str, primitives: dict[str, dict[str, float]] | None) -> dict[str, Any]:
    e = entity.upper()
    if not primitives:
        return {"found": False, "entity": e, "reason": "missing_primitives", "insufficient": True}

    # Prefer computing from the supplied validated primitives (KF path).
    out: dict[str, Any] = {}
    insufficient: list[str] = []
    pe = _pe_from_primitives(primitives)
    out["PE"] = pe
    if pe.get("insufficient"):
        insufficient.append("PE")

    try:
        from institutional_reasoning.fundamentals.derivations import derive_series

        for metric in ("PB", "EV_EBITDA", "ROE", "ROIC", "Net_Margin", "Cash_Conversion"):
            series = derive_series(e, metric)
            if series.get("found") and series.get("points"):
                out[metric] = {
                    "points": series["points"],
                    "formula": series.get("formula"),
                    "derived_from": series.get("derived_from"),
                    "rejected_periods": series.get("rejected_periods"),
                    "provider": "kf_derived_producer",
                }
            else:
                insufficient.append(metric)
                out[metric] = {
                    "found": False,
                    "insufficient": True,
                    "reason": series.get("reason") or "insufficient_inputs",
                }
    except Exception:
        pass

    return {
        "found": True,
        "entity": e,
        "metrics": out,
        "insufficient": insufficient,
        "derived_not_stored": True,
        "provider": "kf_derived_producer",
    }
