"""Knowledge graph edges among concepts, frameworks, formulas, industries."""

from __future__ import annotations

from academy.books.schema import BookConcept, FormulaObject, FrameworkObject, GraphEdge
from academy.books.store import BooksStore


def rebuild_graph(store: BooksStore) -> list[GraphEdge]:
    edges: list[GraphEdge] = []

    def add(src: str, tgt: str, rel: str, w: float = 1.0) -> None:
        if not src or not tgt or src == tgt:
            return
        eid = f"{rel}:{src}->{tgt}"
        edges.append(GraphEdge(edge_id=eid, source=src, target=tgt, relation=rel, weight=w))

    concepts = list(store.concepts.values())
    formulas = list(store.formulas.values())
    frameworks = list(store.frameworks.values())

    by_title = {c.title.lower(): c for c in concepts}

    for c in concepts:
        for rel in c.related_concepts:
            other = by_title.get(rel.lower()) or store.concepts.get(rel)
            if other:
                add(c.concept_id, other.concept_id if isinstance(other, BookConcept) else rel, "related")
        for fid in c.linked_formulas:
            add(c.concept_id, fid, "measures")
        for fw in c.linked_frameworks:
            add(c.concept_id, fw, "framework_of")
        for ind in c.linked_industries:
            add(c.concept_id, f"industry:{ind.lower()}", "applies_to", 0.8)
        for co in c.linked_companies:
            add(c.concept_id, f"company:{co.upper()}", "applies_to", 0.7)

    for f in formulas:
        # soft link formulas to similarly named concepts
        for c in concepts:
            if f.name.lower() in (c.title.lower() + " " + c.definition.lower()):
                add(c.concept_id, f.formula_id, "measures", 0.9)

    for fw in frameworks:
        for rc in fw.related_concepts:
            other = by_title.get(rc.lower()) or store.concepts.get(rc)
            if other:
                add(fw.framework_id, other.concept_id if isinstance(other, BookConcept) else rc, "framework_of")

    # Canonical investment chain (always present when nodes exist)
    chain = [
        ("roe", "capital_allocation"),
        ("capital_allocation", "competitive_advantage"),
        ("competitive_advantage", "valuation"),
        ("economic_moat", "valuation"),
        ("roic", "economic_moat"),
    ]
    ids = {c.concept_id: c for c in concepts}
    titles = {c.title.lower(): c.concept_id for c in concepts}
    for a, b in chain:
        sa = titles.get(a) or next((cid for cid in ids if a in cid), None)
        sb = titles.get(b) or next((cid for cid in ids if b in cid), None)
        if sa and sb:
            add(sa, sb, "depends_on", 1.1)

    for e in edges:
        store.upsert_edge(e)
    return edges
