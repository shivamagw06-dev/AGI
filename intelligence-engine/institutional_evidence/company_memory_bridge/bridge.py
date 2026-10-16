"""Company Memory bridge — persistent institutional memory per listed company."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schema import PHASE1_TOP20


MEMORY_SLOTS = (
    "company_identity",
    "business_model",
    "segments",
    "products",
    "management",
    "subsidiaries",
    "competitive_position",
    "capital_allocation",
    "financial_history",
    "historical_guidance",
    "risks",
    "catalysts",
    "timeline",
    "valuation_history",
    "ownership",
    "corporate_actions",
    "evidence_graph",
)


def _phase1_meta(ticker: str) -> Dict[str, str]:
    for c in PHASE1_TOP20:
        if c["ticker"] == ticker.upper():
            return dict(c)
    return {"ticker": ticker.upper(), "company": ticker.upper(), "sector": "unknown"}


def build_company_memory_view(
    ticker: str,
    *,
    canonical: Optional[Dict[str, Any]] = None,
    registry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    t = str(ticker or "").upper().strip()
    meta = _phase1_meta(t)
    slots: Dict[str, Any] = {k: None for k in MEMORY_SLOTS}
    filled: List[str] = []
    sources: List[str] = []

    # Soft-consume company_memory (KC.1) if present
    try:
        from company_memory.production import get_company_memory  # type: ignore

        mem = get_company_memory(t)
        if isinstance(mem, dict):
            sources.append("company_memory")
            for slot in MEMORY_SLOTS:
                if mem.get(slot) is not None:
                    slots[slot] = mem.get(slot)
                    filled.append(slot)
            # common alternate keys
            identity = mem.get("identity") or mem.get("profile") or mem.get("company_identity")
            if identity is not None:
                slots["company_identity"] = identity
                if "company_identity" not in filled:
                    filled.append("company_identity")
    except Exception:
        pass

    if slots["company_identity"] is None:
        slots["company_identity"] = {
            "ticker": t,
            "company": meta.get("company"),
            "sector": meta.get("sector"),
        }
        filled.append("company_identity")

    if canonical and canonical.get("periods"):
        slots["financial_history"] = {
            "period_count": canonical.get("period_count") or len(canonical.get("periods") or []),
            "published": canonical.get("published"),
            "latest_period": (canonical.get("periods") or [{}])[0].get("period"),
            "ratios": canonical.get("ratios") or {},
        }
        if "financial_history" not in filled:
            filled.append("financial_history")
        sources.append("canonical_financial_statements")

    if registry and registry.get("items"):
        slots["evidence_graph"] = {
            "evidence_count": registry.get("evidence_count"),
            "primary_count": registry.get("primary_count"),
            "evidence_ids": [i.get("evidence_id") for i in (registry.get("items") or [])[:50]],
        }
        if "evidence_graph" not in filled:
            filled.append("evidence_graph")
        sources.append("evidence_registry")

    # Soft KG / risks if available
    try:
        from institutional_knowledge_graph.production import get_company_graph  # type: ignore

        g = get_company_graph(t)
        if isinstance(g, dict) and g:
            slots["competitive_position"] = slots["competitive_position"] or g.get("competitive_position") or g.get("summary")
            sources.append("institutional_knowledge_graph")
    except Exception:
        pass

    coverage = len(set(filled)) / max(1, len(MEMORY_SLOTS))
    return {
        "ok": True,
        "ticker": t,
        "company": meta.get("company"),
        "sector": meta.get("sector"),
        "slots": slots,
        "filled_slots": sorted(set(filled)),
        "slot_coverage": round(coverage, 4),
        "sources": sorted(set(sources)),
        "persistent": True,
        "note": "AGI permanent institutional memory — evidence-backed slots only",
    }
