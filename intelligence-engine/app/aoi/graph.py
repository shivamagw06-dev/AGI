"""Knowledge graph relationships — traversable institutional links."""

from __future__ import annotations

from app.aoi.models import ExtractedFact, GraphEdge
from app.aoi.registry import CompanyRegistry
from app.aoi.store import AoiStore


def upsert_company_graph(
    store: AoiStore,
    registry: CompanyRegistry,
    *,
    company_id: str,
    facts: list[ExtractedFact],
    document_id: str = "",
) -> list[GraphEdge]:
    co = registry.get(company_id)
    if not co:
        return []
    edges: list[GraphEdge] = []

    def link(rel: str, dst: str, confidence: float = 0.75) -> None:
        edge = GraphEdge(
            src=company_id,
            rel=rel,
            dst=dst,
            confidence=confidence,
            source_document_id=document_id,
        )
        store.add_edge(edge)
        edges.append(edge)

    if co.sector:
        sector_node = f"sector:{co.sector.lower().replace(' ', '_')}"
        link("in_sector", sector_node, 0.95)
        link("in_industry", f"industry:{(co.industry or co.sector).lower().replace(' ', '_')}", 0.9)

    for fact in facts:
        field = (fact.field or "").lower()
        val = (fact.value_text or "").strip()
        if not val:
            continue
        if "competitor" in field:
            link("competitor", f"entity:{_slug(val)}", fact.confidence)
        elif "supplier" in field:
            link("supplier", f"entity:{_slug(val)}", fact.confidence)
        elif "customer" in field:
            link("customer", f"entity:{_slug(val)}", fact.confidence)
        elif field.startswith("macro_") or "affected_sectors" in field:
            link("impacted_by_macro", f"macro:{_slug(val)[:48]}", fact.confidence)
        elif "risk" in field:
            link("has_risk", f"risk:{_slug(val)[:48]}", fact.confidence)

    # Peer links within same sector (light)
    for other in registry.nifty50():
        if other.company_id == company_id:
            continue
        if other.sector and other.sector == co.sector:
            link("sector_peer", other.company_id, 0.6)
    return edges


def traverse(store: AoiStore, start: str, *, max_depth: int = 2) -> list[dict]:
    seen: set[str] = {start}
    frontier = [start]
    paths: list[dict] = []
    depth = 0
    while frontier and depth < max_depth:
        nxt: list[str] = []
        for node in frontier:
            for edge in store.edges.values():
                if edge.src != node:
                    continue
                paths.append(edge.model_dump(mode="json"))
                if edge.dst not in seen:
                    seen.add(edge.dst)
                    nxt.append(edge.dst)
        frontier = nxt
        depth += 1
    return paths


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value)[:64].strip("_")
