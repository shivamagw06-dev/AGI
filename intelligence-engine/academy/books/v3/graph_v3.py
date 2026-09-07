"""Knowledge graph builder for Academy Books V3 institutional objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from academy.books.v3.schema import GraphLink

if TYPE_CHECKING:
    from academy.books.v3.store import BooksV3Store


def build_graph(store: "BooksV3Store") -> list[GraphLink]:
    edges: list[GraphLink] = []
    n = 0

    def add(source: str, target: str, relation: str, weight: float = 1.0) -> None:
        nonlocal n
        n += 1
        edges.append(
            GraphLink(
                edge_id=f"e{n}_{relation}_{source}_{target}"[:120],
                source=source,
                target=target,
                relation=relation,
                weight=weight,
            )
        )

    for c in store.concepts.values():
        for fw in c.related_frameworks:
            add(c.concept_id, fw, "uses_framework")
        for f in c.related_formulas:
            add(c.concept_id, f, "uses_formula")
        for rc in c.related_concepts:
            add(c.concept_id, f"concept_{rc}" if not rc.startswith("concept_") else rc, "related_concept", 0.7)
        for a in c.analysts_using:
            add(c.concept_id, f"analyst_{a}", "used_by_analyst")
        for book in c.source_books:
            add(c.concept_id, f"book:{book}", "synthesized_from_book", 0.5)
        for author in c.source_authors:
            add(c.concept_id, f"author:{author}", "synthesized_from_author", 0.6)

    for fw in store.frameworks.values():
        for rc in fw.related_concepts:
            add(fw.framework_id, f"concept_{rc}" if not rc.startswith("concept_") else rc, "framework_concept")
        for a in fw.analysts_using:
            add(fw.framework_id, f"analyst_{a}", "used_by_analyst")

    for case in store.cases.values():
        for fw in case.framework_applied:
            add(case.case_id, fw, "applies_framework")
        for rc in case.related_concepts:
            add(case.case_id, f"concept_{rc}" if not rc.startswith("concept_") else rc, "case_concept")
        add(case.case_id, f"company:{case.company}", "about_company")
        add(case.case_id, f"industry:{case.industry}", "about_industry", 0.8)

    for mm in store.mental_models.values():
        for rc in mm.related_concepts:
            add(mm.model_id, f"concept_{rc}" if not rc.startswith("concept_") else rc, "model_concept")

    for rule in store.decision_rules.values():
        for fw in rule.related_frameworks:
            add(rule.rule_id, fw, "rule_from_framework")
        for rc in rule.related_concepts:
            add(rule.rule_id, f"concept_{rc}" if not rc.startswith("concept_") else rc, "rule_concept")

    for chain in store.reasoning_chains.values():
        for rc in chain.related_concepts:
            add(chain.chain_id, f"concept_{rc}" if not rc.startswith("concept_") else rc, "chain_concept")

    for pat in store.patterns.values():
        for rc in pat.related_concepts:
            add(pat.pattern_id, f"concept_{rc}" if not rc.startswith("concept_") else rc, "pattern_concept")
        for fw in pat.related_frameworks:
            add(pat.pattern_id, fw, "pattern_framework")

    for sector in store.sectors.values():
        for fw in sector.frameworks:
            add(sector.sector_id, fw, "sector_framework")
        for kpi in sector.kpis:
            add(sector.sector_id, f"kpi:{kpi}", "sector_kpi", 0.5)

    for obj in store.institutional_objects.values():
        for fw in obj.frameworks:
            add(obj.object_id, fw, "iko_framework")
        for f in obj.formulas:
            add(obj.object_id, f, "iko_formula")
        for r in obj.decision_rules:
            add(obj.object_id, r, "iko_rule")
        for c in obj.cases:
            add(obj.object_id, c, "iko_case")
        for a in obj.analysts:
            add(obj.object_id, f"analyst_{a}", "iko_analyst")
        for author in obj.source_authors:
            add(obj.object_id, f"author:{author}", "iko_author")
        for book in obj.source_books:
            add(obj.object_id, f"book:{book}", "iko_book", 0.5)

    for ch in store.chapters.values():
        for cid in ch.core_concepts:
            add(ch.chapter_id, f"concept_{cid}" if not cid.startswith("concept_") else cid, "chapter_concept")
        for fw in ch.frameworks:
            add(ch.chapter_id, fw, "chapter_framework")
        add(ch.chapter_id, f"book:{ch.book_id}", "from_book", 0.4)

    return edges


def graph_preview(store: "BooksV3Store", *, node_limit: int = 60, edge_limit: int = 100) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    for c in list(store.concepts.values())[:20]:
        nodes.append({"id": c.concept_id, "label": c.name, "type": "concept"})
    for f in list(store.frameworks.values())[:15]:
        nodes.append({"id": f.framework_id, "label": f.name, "type": "framework"})
    for obj in store.institutional_objects.values():
        nodes.append({"id": obj.object_id, "label": obj.topic, "type": "institutional_object"})
    for p in list(store.patterns.values())[:10]:
        nodes.append({"id": p.pattern_id, "label": p.name, "type": "pattern"})
    for s in list(store.sectors.values())[:10]:
        nodes.append({"id": s.sector_id, "label": s.name, "type": "sector"})
    edges = [e.to_dict() for e in list(store.edges.values())[:edge_limit]]
    return {"nodes": nodes[:node_limit], "edges": edges, "edge_count": len(store.edges)}
