"""Module 7 — DCF Intelligence.

Real DCF requires full input set. Missing any required input → Insufficient.
Does not invent template defaults as evidence.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.institutional_evidence.provenance import now_iso

DCF_VERSION = "dcf-intelligence-v1.0.0"

REQUIRED_DCF_INPUTS = (
    "revenue",
    "margins",
    "capex",
    "working_capital",
    "tax",
    "fcf",
    "beta",
    "erp",
    "risk_free",
    "debt",
    "cash",
    "shares",
    "terminal_growth",
    "wacc",
)


def _extract(inputs: dict[str, Any]) -> dict[str, Any]:
    flat = dict(inputs or {})
    for nest in ("assumptions", "dcf", "model_inputs", "valuation"):
        sub = inputs.get(nest) if isinstance(inputs, dict) else None
        if isinstance(sub, dict):
            flat.update(sub)
    return flat


def produce_dcf_intelligence(
    entity_id: str,
    *,
    inputs: dict[str, Any] | None = None,
    entity_type: str | None = None,
) -> dict[str, Any]:
    eid = str(entity_id or "").upper()
    et = str(entity_type or "")
    if et == "Index":
        return {
            "entity": eid,
            "applicable": False,
            "status": "not_applicable",
            "reason": "DCF invalid for Index",
            "intrinsic_value": None,
            "confidence": None,
            "as_of": now_iso(),
            "dcf_version": DCF_VERSION,
        }

    flat = _extract(inputs or {})
    aliases = {
        "revenue": ("revenue", "sales", "revenue_t0"),
        "margins": ("ebit_margin", "operating_margin", "margins", "fcf_margin"),
        "capex": ("capex", "capex_pct", "maintenance_capex"),
        "working_capital": ("working_capital", "nwc", "delta_nwc"),
        "tax": ("tax_rate", "tax", "effective_tax"),
        "fcf": ("fcf", "fcff", "free_cash_flow"),
        "beta": ("beta", "levered_beta"),
        "erp": ("erp", "equity_risk_premium", "market_premium"),
        "risk_free": ("risk_free", "rf", "risk_free_rate"),
        "debt": ("debt", "net_debt", "total_debt"),
        "cash": ("cash", "cash_and_equivalents"),
        "shares": ("shares", "shares_outstanding", "diluted_shares"),
        "terminal_growth": ("terminal_growth", "g_terminal", "perpetuity_growth"),
        "wacc": ("wacc", "discount_rate"),
    }
    observed: dict[str, Any] = {}
    missing: list[str] = []
    for key, keys in aliases.items():
        val = None
        for k in keys:
            if flat.get(k) is not None and flat.get(k) != 0:
                val = flat.get(k)
                break
        if val is None:
            missing.append(key)
        else:
            observed[key] = val

    if missing:
        return {
            "entity": eid,
            "applicable": True,
            "status": "insufficient",
            "reason": f"Missing DCF inputs: {', '.join(missing)}",
            "required": list(REQUIRED_DCF_INPUTS),
            "observed": observed,
            "missing": missing,
            "intrinsic_value": None,
            "wacc": observed.get("wacc"),
            "confidence": None,
            "as_of": now_iso(),
            "dcf_version": DCF_VERSION,
        }

    # Explicit computation only when all inputs present — no template fill.
    # Intrinsic value left to VE when wired; here we certify readiness.
    return {
        "entity": eid,
        "applicable": True,
        "status": "ready",
        "reason": "All required DCF inputs present",
        "required": list(REQUIRED_DCF_INPUTS),
        "observed": observed,
        "missing": [],
        "intrinsic_value": flat.get("intrinsic_value"),
        "wacc": observed.get("wacc"),
        "terminal_growth": observed.get("terminal_growth"),
        "confidence": 0.7,
        "as_of": now_iso(),
        "dcf_version": DCF_VERSION,
    }
