"""Business Knowledge Graph — structured relationships (deterministic)."""

from __future__ import annotations

from typing import Any


def build_knowledge_graph(ev: dict[str, Any]) -> dict[str, Any]:
    company = ev.get("company") or {}
    ticker = ev.get("ticker")
    industry = ev.get("industry_key") or "unknown"
    name = company.get("company_name") or ticker or "UnknownCompany"

    nodes = [
        {"id": f"company:{ticker or name}", "type": "company", "label": name},
        {"id": f"industry:{industry}", "type": "industry", "label": industry.replace("_", " ")},
    ]
    edges = [
        {
            "from": f"company:{ticker or name}",
            "to": f"industry:{industry}",
            "rel": "operates_in",
        }
    ]

    def _add_list(values: Any, ntype: str, rel: str) -> None:
        if not values:
            return
        text = str(values)
        # CapIQ often stores comma/semicolon separated names.
        parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
        for i, part in enumerate(parts[:8]):
            nid = f"{ntype}:{part[:40]}"
            nodes.append({"id": nid, "type": ntype, "label": part[:80]})
            edges.append({"from": f"company:{ticker or name}", "to": nid, "rel": rel})

    _add_list(company.get("competitors"), "competitor", "competes_with")
    _add_list(company.get("customers"), "customer", "sells_to")
    _add_list(company.get("products"), "product", "offers")
    if company.get("geography"):
        geo = str(company["geography"])[:80]
        nodes.append({"id": f"geo:{geo}", "type": "geography", "label": geo})
        edges.append({"from": f"company:{ticker or name}", "to": f"geo:{geo}", "rel": "operates_in_geography"})

    # Structural placeholders — explicit unknowns rather than invented entities.
    for ntype, rel in (
        ("supplier", "buys_from"),
        ("substitute", "threatened_by"),
        ("regulator", "regulated_by"),
        ("distribution", "distributes_via"),
    ):
        if not any(n["type"] == ntype for n in nodes):
            nid = f"{ntype}:unverified"
            nodes.append({"id": nid, "type": ntype, "label": f"{ntype} (unverified)"})
            edges.append({"from": f"company:{ticker or name}", "to": nid, "rel": rel, "status": "unverified"})

    return {
        "company": name,
        "ticker": ticker,
        "industry": industry,
        "nodes": nodes,
        "edges": edges,
        "summary": f"Knowledge graph for {name}: {len(nodes)} nodes, {len(edges)} relationships.",
        "confidence": 0.7 if ticker else 0.4,
        "fabricated": False,
    }
