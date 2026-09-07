"""Thesis Impact Matrix — map each filing change to investment-case lenses.

Symbols (institutional shorthand):
  ✅  primary impact on that lens
  ◐  secondary / partial impact
  ❌  not material to that lens

Committee actions:
  Review   — include in IC pack for discussion
  Escalate — priority IC item (regulatory / thesis-breaking)
  Note     — informational; no mandatory debate
  Monitor  — watch next filing; no immediate debate
"""

from __future__ import annotations

from typing import Any

LENSES = ("business", "financial", "valuation", "risk", "committee")

# metric / change_type → lens impacts
_RULES: list[tuple[tuple[str, ...], tuple[str, ...], dict[str, str]]] = [
    # (metrics, change_types_substr, {business, financial, valuation, risk, committee})
    (
        ("NIM",),
        ("margin_compression", "margin_expansion"),
        {"business": "◐", "financial": "✅", "valuation": "✅", "risk": "◐", "committee": "Review"},
    ),
    (
        ("CASA", "Cost_of_Funds", "Deposit_Beta"),
        ("casa_decline", "casa_improvement"),
        {"business": "✅", "financial": "✅", "valuation": "◐", "risk": "◐", "committee": "Review"},
    ),
    (
        ("CET1", "CAR"),
        ("capital_ratio_decline", "capital_ratio_increase"),
        {"business": "◐", "financial": "✅", "valuation": "◐", "risk": "✅", "committee": "Review"},
    ),
    (
        ("ROE", "ROA", "ROIC"),
        ("roe_decline", "roe_improvement", "roic_decline", "roic_improvement"),
        {"business": "◐", "financial": "✅", "valuation": "✅", "risk": "❌", "committee": "Review"},
    ),
    (
        ("GNPA", "NNPA", "Credit_Cost"),
        ("asset_quality",),
        {"business": "◐", "financial": "✅", "valuation": "◐", "risk": "✅", "committee": "Review"},
    ),
    (
        ("Revenue_Growth", "Deposits_YoY", "PAT", "NII"),
        ("revenue_acceleration", "revenue_deceleration", "decline", "increase"),
        {"business": "◐", "financial": "✅", "valuation": "✅", "risk": "❌", "committee": "Note"},
    ),
    (
        ("Buybacks",),
        ("buyback",),
        {"business": "◐", "financial": "✅", "valuation": "✅", "risk": "❌", "committee": "Note"},
    ),
    (
        ("Dividends",),
        ("dividend",),
        {"business": "❌", "financial": "✅", "valuation": "✅", "risk": "❌", "committee": "Note"},
    ),
    (
        ("Acquisitions",),
        ("acquisition",),
        {"business": "✅", "financial": "◐", "valuation": "◐", "risk": "✅", "committee": "Escalate"},
    ),
    (
        ("Capex", "Organic_Investment", "Capital_Buffer", "Capital_Raises", "Debt_Reduction"),
        ("capex", "organic", "capital", "debt"),
        {"business": "◐", "financial": "✅", "valuation": "◐", "risk": "◐", "committee": "Note"},
    ),
    (
        ("Guidance_Status",),
        ("raised", "lowered", "withdrawn", "maintained"),
        {"business": "◐", "financial": "✅", "valuation": "✅", "risk": "◐", "committee": "Review"},
    ),
    (
        ("Optimism", "Management_Warning", "Margin_Commentary", "Key_Priorities"),
        ("optimism", "new_warning", "changed_outlook", "changed_language", "new_priority"),
        {"business": "✅", "financial": "◐", "valuation": "◐", "risk": "◐", "committee": "Review"},
    ),
    (
        (
            "Business_Risk",
            "Financial_Risk",
            "Regulatory_Risk",
            "Technology_Risk",
            "Competition_Risk",
            "Supply_Chain_Risk",
            "Execution_Risk",
            "Geopolitical_Risk",
        ),
        ("risk_added", "risk_removed"),
        {"business": "◐", "financial": "❌", "valuation": "◐", "risk": "✅", "committee": "Escalate"},
    ),
    (
        ("Business_Segments",),
        ("segment",),
        {"business": "✅", "financial": "◐", "valuation": "◐", "risk": "❌", "committee": "Note"},
    ),
    (
        ("CEO_Change",),
        ("ceo_change",),
        {"business": "✅", "financial": "◐", "valuation": "◐", "risk": "✅", "committee": "Escalate"},
    ),
]


_DEFAULT = {
    "business": "◐",
    "financial": "◐",
    "valuation": "◐",
    "risk": "◐",
    "committee": "Review",
}


def _match_rule(metric: str, change_type: str) -> dict[str, str]:
    m = metric or ""
    ct = (change_type or "").lower()
    for metrics, types, impact in _RULES:
        if m in metrics or any(m.startswith(x) or x in m for x in metrics if len(x) > 3):
            if not types or any(t in ct for t in types):
                return dict(impact)
            # metric matched but type loose — still use impact for known metrics
            if m in metrics:
                return dict(impact)
    # domain fallbacks applied by caller
    return dict(_DEFAULT)


def matrix_for_change(change: dict[str, Any]) -> dict[str, Any]:
    metric = str(change.get("metric") or "")
    change_type = str(change.get("change_type") or "")
    domain = str(change.get("domain") or "")
    impact = _match_rule(metric, change_type)

    # domain overlays when rule was default-ish
    if impact == _DEFAULT or metric not in {m for rule in _RULES for m in rule[0]}:
        if domain == "risks":
            impact = {
                "business": "◐",
                "financial": "❌",
                "valuation": "◐",
                "risk": "✅",
                "committee": "Escalate" if "added" in change_type else "Review",
            }
        elif domain == "guidance":
            impact = {
                "business": "◐",
                "financial": "✅",
                "valuation": "✅",
                "risk": "◐",
                "committee": "Escalate" if change_type in {"lowered", "withdrawn"} else "Review",
            }
        elif domain == "capital":
            impact = {
                "business": "◐",
                "financial": "✅",
                "valuation": "✅",
                "risk": "❌",
                "committee": "Note",
            }
        elif domain == "management":
            impact = {
                "business": "✅",
                "financial": "◐",
                "valuation": "◐",
                "risk": "◐",
                "committee": "Review",
            }
        elif domain == "statement":
            impact = {
                "business": "◐",
                "financial": "✅",
                "valuation": "✅",
                "risk": "◐",
                "committee": "Review",
            }
        elif domain in {"governance"}:
            impact = {
                "business": "✅",
                "financial": "❌",
                "valuation": "◐",
                "risk": "✅",
                "committee": "Escalate",
            }
        elif domain in {"notes", "accounting"}:
            impact = {
                "business": "❌",
                "financial": "✅",
                "valuation": "◐",
                "risk": "◐",
                "committee": "Note",
            }

    # escalate committee on critical materiality
    if change.get("materiality") == "critical" and impact.get("committee") == "Note":
        impact["committee"] = "Review"
    if change.get("materiality") == "critical" and impact.get("committee") == "Review":
        if domain in {"risks", "governance", "guidance"} or change_type in {"withdrawn", "lowered"}:
            impact["committee"] = "Escalate"

    label = (
        f"{metric} "
        f"{'↓' if any(x in change_type for x in ('decline', 'compression', 'decreased', 'lowered', 'deterioration')) else ''}"
        f"{'↑' if any(x in change_type for x in ('increase', 'expansion', 'improvement', 'raised', 'acceleration', 'added')) and 'decline' not in change_type else ''}"
    ).strip()

    return {
        "filing_change": label or metric,
        "metric": metric,
        "change_type": change_type,
        "business": impact["business"],
        "financial": impact["financial"],
        "valuation": impact["valuation"],
        "risk": impact["risk"],
        "committee": impact["committee"],
        "legend": {
            "✅": "primary impact",
            "◐": "secondary / partial impact",
            "❌": "not material to lens",
            "Review": "include in IC discussion",
            "Escalate": "priority IC item",
            "Note": "informational",
            "Monitor": "watch next filing",
        },
    }


def build_thesis_impact_matrix(changes: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for c in changes:
        if c.get("cosmetic") or c.get("materiality") in {"ignore", None}:
            continue
        row = matrix_for_change(c)
        rows.append(row)
        c["thesis_impact_matrix"] = {
            "business": row["business"],
            "financial": row["financial"],
            "valuation": row["valuation"],
            "risk": row["risk"],
            "committee": row["committee"],
        }

    # analyst routing: which changes each desk owns
    def _primary(lens: str, symbol: str = "✅") -> list[dict[str, Any]]:
        return [r for r in rows if r.get(lens) == symbol]

    escalate = [r for r in rows if r.get("committee") == "Escalate"]
    review = [r for r in rows if r.get("committee") == "Review"]

    return {
        "columns": ["Filing Change", "Business", "Financial", "Valuation", "Risk", "Committee"],
        "rows": rows,
        "count": len(rows),
        "analyst_routing": {
            "business_analyst": _primary("business"),
            "financial_analyst": _primary("financial"),
            "valuation_analyst": _primary("valuation"),
            "risk_analyst": _primary("risk"),
        },
        "committee_queue": {
            "escalate": escalate,
            "review": review,
            "note": [r for r in rows if r.get("committee") == "Note"],
        },
        "markdown_table": _to_markdown(rows),
        "rule": (
            "Every material filing change maps to Business / Financial / Valuation / Risk / Committee "
            "so Analyst → Committee → CIO can act without re-reading the change list."
        ),
    }


def _to_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Filing Change | Business | Financial | Valuation | Risk | Committee |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows[:25]:
        lines.append(
            f"| {r.get('filing_change')} | {r.get('business')} | {r.get('financial')} | "
            f"{r.get('valuation')} | {r.get('risk')} | {r.get('committee')} |"
        )
    return "\n".join(lines)
