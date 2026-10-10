"""Entity domain ontology for Institutional Evidence Graph."""

from __future__ import annotations

from typing import Any

from institutional_evidence_graph.schema import ENTITY_DOMAINS


DOMAIN_LABELS: dict[str, str] = {
    "financials": "Financials",
    "segments": "Segments",
    "products": "Products",
    "customers": "Customers",
    "suppliers": "Suppliers",
    "competitors": "Competitors",
    "management": "Management",
    "shareholding": "Shareholding",
    "risks": "Risks",
    "valuation": "Valuation",
    "corporate_actions": "Corporate actions",
    "news": "News",
    "earnings": "Earnings",
    "guidance": "Guidance",
    "macro_exposure": "Macro exposure",
    "esg": "ESG",
    "credit": "Credit",
    "historical_events": "Historical events",
}


def empty_domain_tree(entity_id: str) -> dict[str, Any]:
    """Skeleton: every company knows these facets (nodes filled later)."""
    return {
        "entity_id": entity_id,
        "domains": {
            d: {
                "domain": d,
                "label": DOMAIN_LABELS.get(d, d),
                "node_ids": [],
                "n_nodes": 0,
                "coverage": "empty",
            }
            for d in ENTITY_DOMAINS
        },
    }


def domain_coverage(tree: dict[str, Any]) -> dict[str, Any]:
    domains = tree.get("domains") or {}
    filled = [d for d, v in domains.items() if (v.get("n_nodes") or 0) > 0]
    empty = [d for d in ENTITY_DOMAINS if d not in filled]
    pct = int(round(100.0 * len(filled) / max(len(ENTITY_DOMAINS), 1)))
    return {
        "filled_domains": filled,
        "empty_domains": empty,
        "n_filled": len(filled),
        "n_total": len(ENTITY_DOMAINS),
        "coverage_pct": pct,
        "band": "high" if pct >= 60 else ("medium" if pct >= 35 else "low"),
    }
