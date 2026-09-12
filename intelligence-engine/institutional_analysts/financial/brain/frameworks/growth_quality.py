"""Framework 3 — Growth Quality."""

from __future__ import annotations

from typing import Any

from institutional_analysts.financial.brain._text import as_list, blob_of, txt, trend_label


def assess(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    revenue = txt(evidence.get("revenue"))
    ebit = txt(evidence.get("ebit"))
    cash = txt(evidence.get("cash_flow"))
    trend = txt(evidence.get("trend"))
    narrative = txt(evidence.get("narrative"))
    monitors = as_list(evidence.get("monitors"), limit=5)
    b = blob_of(revenue, ebit, cash, trend, narrative, monitors)

    organic = "acquisition" not in b and "inorganic" not in b
    profitable = any(k in b for k in ("margin", "cash", "earn", "improv", "profit"))
    genuine = organic and (profitable or "growth" in b or revenue)

    assessment = (
        f"Growth quality for {name} looks "
        + (
            "genuine and financially supported — revenue expansion is accompanied by earnings and/or cash generation, "
            "which is more consistent with fundamental demand than with aggressive recognition alone."
            if genuine and profitable
            else "only partly confirmed — top-line movement is visible, but profitable and cash-backed character "
            "still needs stronger multi-period evidence."
            if genuine
            else "at risk of being less durable if growth is acquisition-led or poorly cash-converted."
        )
    )

    return {
        "framework": "Growth Quality",
        "completed": bool(revenue or trend or narrative),
        "revenue_growth": revenue or trend or "Revenue growth under review",
        "ebit_growth": ebit or "EBIT growth under review",
        "eps_growth": txt(evidence.get("eps")) or "EPS trajectory under review",
        "cash_flow_growth": cash or "Cash flow growth under review",
        "asset_growth": txt(evidence.get("asset_growth")) or "Asset growth versus returns under review",
        "organic_vs_acquisition": "Primarily organic on present file" if organic else "Inorganic contribution may be material",
        "genuine": bool(genuine),
        "profitable_growth": bool(profitable),
        "sustainable": bool(genuine and profitable),
        "trajectory": trend_label(trend or narrative),
        "assessment": assessment,
    }
