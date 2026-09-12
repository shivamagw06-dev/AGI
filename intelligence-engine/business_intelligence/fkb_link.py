"""Soft FKB glossary links — never duplicate definitions."""

from __future__ import annotations

from typing import Any

# Concept hints → FKB glossary ids (CamelCase accepted by knowledge.glossary)
_CONCEPT_MAP: dict[str, tuple[str, ...]] = {
    "capital allocation": ("CapitalAllocation",),
    "capital expenditure": ("CapitalAllocation",),
    "capex": ("CapitalAllocation",),
    "buyback": ("CapitalAllocation",),
    "dividend": ("CapitalAllocation",),
    "debt reduction": ("CapitalAllocation", "Solvency"),
    "liquidity": ("Liquidity",),
    "cash deployment": ("CapitalAllocation", "Liquidity"),
    "operating leverage": ("OperatingLeverage",),
    "organic growth": ("OrganicGrowth",),
    "margin": ("MarginExpansion",),
    "margin expansion": ("MarginExpansion",),
    "margin improvement": ("MarginExpansion",),
    "working capital": ("WorkingCapital",),
    "cash conversion": ("CashConversion",),
    "recurring revenue": ("RecurringRevenue",),
    "return on capital": ("ReturnOnCapital",),
    "financial flexibility": ("FinancialFlexibility",),
}


def resolve_fkb_refs(*hints: str) -> list[dict[str, Any]]:
    """Return soft glossary refs for matching hints. Missing terms are omitted."""
    ids: list[str] = []
    for hint in hints:
        key = (hint or "").strip().lower()
        for term, refs in _CONCEPT_MAP.items():
            if term in key or key == term:
                for r in refs:
                    if r not in ids:
                        ids.append(r)
    out: list[dict[str, Any]] = []
    try:
        from financial_knowledge import knowledge
    except Exception:  # noqa: BLE001
        return [{"glossary_id": i, "ref": f'knowledge.glossary("{i}")', "resolved": False} for i in ids]

    for gid in ids:
        row = knowledge.glossary(gid)
        out.append(
            {
                "glossary_id": gid,
                "ref": f'knowledge.glossary("{gid}")',
                "resolved": row is not None,
                "term": (row or {}).get("term"),
                "definition": (row or {}).get("definition"),
            }
        )
    return out


def fkb_refs_for_category(category: str) -> list[dict[str, Any]]:
    return resolve_fkb_refs(category or "")
