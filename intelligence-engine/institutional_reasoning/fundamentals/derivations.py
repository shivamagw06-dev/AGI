"""Derived metric producers.

Every ratio is computed from primitives with an explicit formula and a
recorded input set, so any number can be reproduced and audited:

    price + eps  ->  PE
    ebit, tax, invested_capital  ->  ROIC

Nothing here stores a ratio.
"""

from __future__ import annotations

from typing import Any, Callable

from institutional_reasoning.fundamentals.primitives import (
    FISCAL_YEARS,
    PRIMITIVES_VERSION,
    primitive_panel,
)

DERIVATIONS_VERSION = "metric-derivations-v1.0.0"

DEFAULT_TAX_RATE = 0.25

# Metrics that must never be derived for financial issuers.
NOT_APPLICABLE: dict[str, tuple[str, ...]] = {
    "bank": ("EV_EBITDA", "FCF", "Cash_Conversion", "Net_Debt_EBITDA", "Debt_Equity"),
    "insurance": ("EV_EBITDA", "FCF", "Cash_Conversion", "Net_Debt_EBITDA", "Debt_Equity"),
    "nbfc": ("EV_EBITDA", "FCF", "Net_Debt_EBITDA", "Debt_Equity"),
}


class Derivation:
    """A single reproducible metric definition."""

    def __init__(
        self,
        metric: str,
        inputs: tuple[str, ...],
        formula: str,
        fn: Callable[[dict[str, float]], float | None],
        *,
        unit: str = "x",
        requires_positive: tuple[str, ...] = (),
    ) -> None:
        self.metric = metric
        self.inputs = inputs
        self.formula = formula
        self.fn = fn
        self.unit = unit
        self.requires_positive = requires_positive

    def compute(self, row: dict[str, float]) -> dict[str, Any]:
        missing = [i for i in self.inputs if row.get(i) is None]
        if missing:
            return {"value": None, "rejected": "missing_inputs", "missing_inputs": missing}
        for field in self.requires_positive:
            val = row.get(field)
            if val is None or float(val) <= 0:
                return {
                    "value": None,
                    "rejected": f"non_positive_{field}",
                    "input_values": {i: row.get(i) for i in self.inputs},
                }
        try:
            value = self.fn(row)
        except ZeroDivisionError:
            return {"value": None, "rejected": "division_by_zero"}
        if value is None:
            return {"value": None, "rejected": "not_computable"}
        return {
            "value": round(float(value), 6),
            "rejected": None,
            "input_values": {i: row.get(i) for i in self.inputs},
        }


def _ev(row: dict[str, float]) -> float:
    return row["price"] * row["shares"] + row["total_debt"] - row["cash"]


DERIVATIONS: dict[str, Derivation] = {
    "PE": Derivation(
        "PE", ("price", "eps"), "price / eps",
        lambda r: r["price"] / r["eps"], requires_positive=("eps", "price"),
    ),
    "PB": Derivation(
        "PB", ("price", "bvps"), "price / book_value_per_share",
        lambda r: r["price"] / r["bvps"], requires_positive=("bvps", "price"),
    ),
    "EV": Derivation(
        "EV", ("price", "shares", "total_debt", "cash"),
        "price * shares + total_debt - cash", _ev, unit="crore",
        requires_positive=("price",),
    ),
    "EV_EBITDA": Derivation(
        "EV_EBITDA", ("price", "shares", "total_debt", "cash", "ebitda"),
        "(price * shares + total_debt - cash) / ebitda",
        lambda r: _ev(r) / r["ebitda"], requires_positive=("ebitda", "price"),
    ),
    "ROE": Derivation(
        "ROE", ("net_income", "equity"), "net_income / equity * 100",
        lambda r: r["net_income"] / r["equity"] * 100.0, unit="%",
        requires_positive=("equity",),
    ),
    "ROIC": Derivation(
        "ROIC", ("ebit", "total_debt", "equity", "cash"),
        "ebit * (1 - tax) / (total_debt + equity - cash) * 100",
        lambda r: (
            r["ebit"] * (1.0 - DEFAULT_TAX_RATE)
            / max(1e-9, (r["total_debt"] + r["equity"] - r["cash"]))
            * 100.0
        ),
        unit="%",
    ),
    "EBITDA_Margin": Derivation(
        "EBITDA_Margin", ("ebitda", "revenue"), "ebitda / revenue * 100",
        lambda r: r["ebitda"] / r["revenue"] * 100.0, unit="%",
        requires_positive=("revenue",),
    ),
    "Operating_Margin": Derivation(
        "Operating_Margin", ("ebit", "revenue"), "ebit / revenue * 100",
        lambda r: r["ebit"] / r["revenue"] * 100.0, unit="%",
        requires_positive=("revenue",),
    ),
    "Net_Margin": Derivation(
        "Net_Margin", ("net_income", "revenue"), "net_income / revenue * 100",
        lambda r: r["net_income"] / r["revenue"] * 100.0, unit="%",
        requires_positive=("revenue",),
    ),
    "FCF": Derivation(
        "FCF", ("ocf", "capex"), "operating_cash_flow - capex",
        lambda r: r["ocf"] - r["capex"], unit="crore",
    ),
    "FCF_Margin": Derivation(
        "FCF_Margin", ("ocf", "capex", "revenue"), "(ocf - capex) / revenue * 100",
        lambda r: (r["ocf"] - r["capex"]) / r["revenue"] * 100.0, unit="%",
        requires_positive=("revenue",),
    ),
    "Cash_Conversion": Derivation(
        "Cash_Conversion", ("ocf", "capex", "net_income"),
        "(ocf - capex) / net_income * 100",
        lambda r: (r["ocf"] - r["capex"]) / r["net_income"] * 100.0, unit="%",
        requires_positive=("net_income",),
    ),
    "Revenue": Derivation(
        "Revenue", ("revenue",), "revenue", lambda r: r["revenue"], unit="crore",
    ),
    "Debt": Derivation(
        "Debt", ("total_debt",), "total_debt", lambda r: r["total_debt"], unit="crore",
    ),
    "Net_Debt": Derivation(
        "Net_Debt", ("total_debt", "cash"), "total_debt - cash",
        lambda r: r["total_debt"] - r["cash"], unit="crore",
    ),
    "Debt_Equity": Derivation(
        "Debt_Equity", ("total_debt", "equity"), "total_debt / equity",
        lambda r: r["total_debt"] / r["equity"], requires_positive=("equity",),
    ),
    "Net_Debt_EBITDA": Derivation(
        "Net_Debt_EBITDA", ("total_debt", "cash", "ebitda"),
        "(total_debt - cash) / ebitda",
        lambda r: (r["total_debt"] - r["cash"]) / r["ebitda"],
        requires_positive=("ebitda",),
    ),
    "Capex": Derivation(
        "Capex", ("capex",), "capex", lambda r: r["capex"], unit="crore",
    ),
    "EPS": Derivation(
        "EPS", ("eps",), "reported_diluted_eps", lambda r: r["eps"], unit="INR",
    ),
}

# Growth metrics are derived across periods rather than within one row.
GROWTH_METRICS = {
    "Revenue_Growth": "Revenue",
    "EPS_Growth": "EPS",
    "FCF_Growth": "FCF",
}


def available_metrics() -> list[str]:
    return sorted(list(DERIVATIONS) + list(GROWTH_METRICS))


def is_applicable(metric: str, sector: str | None) -> bool:
    if not sector:
        return True
    return metric not in NOT_APPLICABLE.get(str(sector).lower(), ())


def derive_series(
    entity_id: str,
    metric: str,
    *,
    sector: str | None = None,
) -> dict[str, Any]:
    """Compute a full derived series with per-point audit."""
    panel = primitive_panel(entity_id)
    if not panel:
        return {
            "found": False,
            "metric": metric,
            "entity_id": str(entity_id or "").upper(),
            "reason": "no_primitive_coverage",
            "derivations_version": DERIVATIONS_VERSION,
        }

    if not is_applicable(metric, sector):
        return {
            "found": False,
            "metric": metric,
            "entity_id": str(entity_id or "").upper(),
            "reason": f"not_applicable_for_{sector}",
            "not_applicable": True,
            "derivations_version": DERIVATIONS_VERSION,
        }

    if metric in GROWTH_METRICS:
        base = derive_series(entity_id, GROWTH_METRICS[metric], sector=sector)
        if not base.get("found"):
            return base
        points: dict[str, float] = {}
        audit: list[dict[str, Any]] = []
        base_points = base.get("points") or {}
        years = [fy for fy in FISCAL_YEARS if fy in base_points]
        for prev, cur in zip(years, years[1:]):
            p, c = base_points[prev], base_points[cur]
            if p in (None, 0) or p <= 0:
                continue
            growth = (c / p - 1.0) * 100.0
            points[cur] = round(growth, 6)
            audit.append(
                {
                    "period": cur,
                    "formula": f"({GROWTH_METRICS[metric]}[{cur}] / {GROWTH_METRICS[metric]}[{prev}] - 1) * 100",
                    "inputs": {prev: p, cur: c},
                    "value": round(growth, 6),
                }
            )
        return {
            "found": bool(points),
            "metric": metric,
            "entity_id": str(entity_id or "").upper(),
            "unit": "%",
            "points": points,
            "audit": audit,
            "derived_from": [GROWTH_METRICS[metric]],
            "primitives_version": PRIMITIVES_VERSION,
            "derivations_version": DERIVATIONS_VERSION,
            "reproducible": True,
        }

    spec = DERIVATIONS.get(metric)
    if not spec:
        return {
            "found": False,
            "metric": metric,
            "reason": "unknown_metric",
            "derivations_version": DERIVATIONS_VERSION,
        }

    points: dict[str, float] = {}
    audit: list[dict[str, Any]] = []
    rejected: dict[str, str] = {}
    for fy in FISCAL_YEARS:
        row = {field: panel.get(field, {}).get(fy) for field in spec.inputs}
        out = spec.compute(row)
        if out.get("value") is None:
            if out.get("rejected"):
                rejected[fy] = out["rejected"]
            continue
        points[fy] = out["value"]
        audit.append(
            {
                "period": fy,
                "formula": spec.formula,
                "inputs": out.get("input_values") or {},
                "value": out["value"],
            }
        )

    return {
        "found": bool(points),
        "metric": metric,
        "entity_id": str(entity_id or "").upper(),
        "unit": spec.unit,
        "formula": spec.formula,
        "points": points,
        "audit": audit,
        "rejected_periods": rejected,
        "derived_from": list(spec.inputs),
        "primitives_version": PRIMITIVES_VERSION,
        "derivations_version": DERIVATIONS_VERSION,
        "reproducible": True,
    }


def derive_latest(entity_id: str, metric: str, *, sector: str | None = None) -> dict[str, Any]:
    series = derive_series(entity_id, metric, sector=sector)
    if not series.get("found"):
        return series
    points = series.get("points") or {}
    for fy in reversed(FISCAL_YEARS):
        if fy in points:
            audit = next((a for a in series.get("audit") or [] if a["period"] == fy), {})
            return {
                "found": True,
                "metric": metric,
                "entity_id": series.get("entity_id"),
                "period": fy,
                "value": points[fy],
                "unit": series.get("unit"),
                "formula": series.get("formula"),
                "inputs": audit.get("inputs") or {},
                "derived_from": series.get("derived_from"),
                "primitives_version": PRIMITIVES_VERSION,
                "derivations_version": DERIVATIONS_VERSION,
                "reproducible": True,
            }
    return {"found": False, "metric": metric, "reason": "no_points"}


def verify_derivation(entity_id: str, metric: str, period: str) -> dict[str, Any]:
    """Recompute one point from stored inputs — proves reproducibility."""
    series = derive_series(entity_id, metric)
    if not series.get("found"):
        return {"verified": False, "reason": series.get("reason")}
    audit = next((a for a in series.get("audit") or [] if a["period"] == period), None)
    if not audit:
        return {"verified": False, "reason": "period_not_derived"}
    spec = DERIVATIONS.get(metric)
    if not spec:
        return {"verified": False, "reason": "growth_metric_verified_via_base"}
    recomputed = spec.compute(dict(audit["inputs"]))
    return {
        "verified": recomputed.get("value") == audit["value"],
        "metric": metric,
        "period": period,
        "stored": audit["value"],
        "recomputed": recomputed.get("value"),
        "formula": spec.formula,
        "inputs": audit["inputs"],
    }
