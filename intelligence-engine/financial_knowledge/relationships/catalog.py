"""Canonical relationship rules (FKB-01). Templates only — no analysis execution."""

from __future__ import annotations

from typing import Any


def _rel(
    id_: str,
    *,
    inputs: list[str],
    conditions: str,
    narrative_template: str,
    severity: str,
    confidence_modifier: int,
    category: str,
) -> dict[str, Any]:
    return {
        "id": id_,
        "inputs": inputs,
        "conditions": conditions,
        "narrative_template": narrative_template,
        "severity": severity,
        "confidence_modifier": confidence_modifier,
        "category": category,
        "performs_analysis": False,
        "executes_rules": False,
    }


RELATIONSHIPS: dict[str, dict[str, Any]] = {
    "REV_OM_LEVERAGE": _rel(
        "REV_OM_LEVERAGE",
        inputs=["revenue", "operating_margin"],
        conditions="Revenue ↑ AND Operating Margin ↑",
        narrative_template="Revenue and operating margin both increased — possible operating leverage.",
        severity="Low",
        confidence_modifier=0,
        category="Profitability Drivers",
    ),
    "REV_GM_PRESSURE": _rel(
        "REV_GM_PRESSURE",
        inputs=["revenue", "gross_margin"],
        conditions="Revenue ↑ AND Gross Margin ↓",
        narrative_template="Revenue increased while gross margin declined — pricing or cost pressure.",
        severity="Medium",
        confidence_modifier=0,
        category="Margin Drivers",
    ),
    "REV_OM_PRESSURE": _rel(
        "REV_OM_PRESSURE",
        inputs=["revenue", "operating_margin"],
        conditions="Revenue ↑ AND Operating Margin ↓",
        narrative_template="Revenue increased while operating margin declined — margin pressure.",
        severity="Medium",
        confidence_modifier=0,
        category="Profitability Drivers",
    ),
    "REV_DOWN_OM_UP": _rel(
        "REV_DOWN_OM_UP",
        inputs=["revenue", "operating_margin"],
        conditions="Revenue ↓ AND Operating Margin ↑",
        narrative_template="Revenue declined while operating margin expanded — cost discipline.",
        severity="Low",
        confidence_modifier=0,
        category="Profitability Drivers",
    ),
    "PAT_OCF": _rel(
        "PAT_OCF",
        inputs=["pat", "operating_cash_flow"],
        conditions="PAT ↑ AND OCF ↓ (or OCF conversion below threshold)",
        narrative_template="Profit improved while operating cash flow lagged — weak cash conversion.",
        severity="High",
        confidence_modifier=-1,
        category="Cash Quality",
    ),
    "PAT_OCF_STRONG": _rel(
        "PAT_OCF_STRONG",
        inputs=["pat", "operating_cash_flow"],
        conditions="OCF / PAT >= cash_conversion_strong threshold",
        narrative_template="Operating cash flow covers reported profit — strong cash conversion.",
        severity="Low",
        confidence_modifier=1,
        category="Cash Quality",
    ),
    "DEBT_DOWN_CASH_UP": _rel(
        "DEBT_DOWN_CASH_UP",
        inputs=["total_debt", "cash"],
        conditions="Debt ↓ AND Cash ↑",
        narrative_template="Debt declined while cash increased — balance sheet strengthening.",
        severity="Low",
        confidence_modifier=0,
        category="Balance Sheet Drivers",
    ),
    "REC_REV_WC": _rel(
        "REC_REV_WC",
        inputs=["receivables", "revenue"],
        conditions="Receivables ↑↑ relative to Revenue ↑",
        narrative_template="Receivables grew faster than revenue — working capital deterioration.",
        severity="Medium",
        confidence_modifier=0,
        category="Working Capital Drivers",
    ),
    "REV_PAT_DETERIORATION": _rel(
        "REV_PAT_DETERIORATION",
        inputs=["revenue", "pat"],
        conditions="Revenue ↑ AND PAT ↓",
        narrative_template="Revenue increased while PAT declined — profitability deterioration.",
        severity="High",
        confidence_modifier=0,
        category="Profitability Drivers",
    ),
    "REV_FCF_PRESSURE": _rel(
        "REV_FCF_PRESSURE",
        inputs=["revenue", "free_cash_flow"],
        conditions="Revenue ↑ AND FCF ↓",
        narrative_template="Revenue increased while free cash flow declined — cash conversion pressure.",
        severity="Medium",
        confidence_modifier=-1,
        category="Cash Flow Drivers",
    ),
    "DELEVERAGING": _rel(
        "DELEVERAGING",
        inputs=["total_debt"],
        conditions="Total Debt ↓",
        narrative_template="Total debt declined — deleveraging.",
        severity="Low",
        confidence_modifier=0,
        category="Balance Sheet Drivers",
    ),
    "LEVERAGE_UP": _rel(
        "LEVERAGE_UP",
        inputs=["total_debt"],
        conditions="Total Debt ↑",
        narrative_template="Total debt increased — increasing leverage.",
        severity="Medium",
        confidence_modifier=0,
        category="Balance Sheet Drivers",
    ),
}


def all_relationships() -> list[dict[str, Any]]:
    return [RELATIONSHIPS[k] for k in sorted(RELATIONSHIPS)]


def get_relationship(key: str) -> dict[str, Any] | None:
    k = key.strip().upper().replace(" ", "_").replace("-", "_")
    aliases = {
        "PAT_VS_OCF": "PAT_OCF",
        "PATOCF": "PAT_OCF",
        "OPERATING_LEVERAGE": "REV_OM_LEVERAGE",
        "WC_RECEIVABLES": "REC_REV_WC",
    }
    k = aliases.get(k, k)
    row = RELATIONSHIPS.get(k)
    return dict(row) if row else None
