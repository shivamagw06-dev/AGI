"""Knowledge graph builder over Academy concepts and causal models."""

from __future__ import annotations

from typing import Any

from academy.catalog import all_causal_models, all_knowledge_objects, all_mental_models


def build_knowledge_graph(course_id: str | None = None) -> dict[str, Any]:
    concepts = all_knowledge_objects(course_id)
    nodes = [
        {
            "id": k.concept_id,
            "label": k.concept,
            "type": "concept",
            "tags": k.tags,
            "course_id": k.course_id,
            "confidence": k.confidence,
        }
        for k in concepts
    ]
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    concept_ids = {k.concept_id for k in concepts}

    def add_edge(src: str, dst: str, rel: str) -> None:
        key = (src, dst, rel)
        if src == dst or key in seen:
            return
        # Keep graph focused on known concept endpoints when possible
        if rel != "causes" and src not in concept_ids and dst not in concept_ids:
            if not src.endswith(tuple(concept_ids)) and not any(src.startswith(c) for c in ("repo_", "inflation_", "gdp_")):
                pass
        seen.add(key)
        edges.append({"from": src, "to": dst, "type": rel})

    for k in concepts:
        rel = k.relationships
        for p in rel.parent:
            add_edge(p, k.concept_id, "parent_of")
        for c in rel.children:
            add_edge(k.concept_id, c, "parent_of")
        for d in rel.dependencies:
            add_edge(k.concept_id, d, "depends_on")
        for r in rel.related:
            add_edge(k.concept_id, r, "related")
        for o in rel.opposing:
            add_edge(k.concept_id, o, "opposes")
        for m in k.mental_models:
            add_edge(k.concept_id, m, "uses_mental_model")

    for cm in all_causal_models():
        # include causal model if any related concept is in scope
        if course_id and not any(c in concept_ids for c in cm.related_concepts):
            continue
        nodes.append({"id": cm.model_id, "label": cm.name, "type": "causal_model"})
        for cid in cm.related_concepts:
            add_edge(cm.model_id, cid, "applies_concept")
        for i in range(len(cm.chain) - 1):
            edges.append(
                {
                    "from": f"{cm.model_id}:{i}:{cm.chain[i]}",
                    "to": f"{cm.model_id}:{i+1}:{cm.chain[i+1]}",
                    "type": "causes",
                    "causal_model": cm.model_id,
                }
            )

    for mm in all_mental_models():
        if course_id and not any(c in concept_ids for c in mm.related_concepts):
            continue
        nodes.append({"id": mm.model_id, "label": mm.name, "type": "mental_model"})
        for cid in mm.related_concepts:
            add_edge(mm.model_id, cid, "frames")

    return {
        "nodes": nodes,
        "edges": edges,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "concepts": len(concepts),
            "causal_models": len([n for n in nodes if n.get("type") == "causal_model"]),
            "mental_models": len([n for n in nodes if n.get("type") == "mental_model"]),
        },
    }


def concept_neighborhood(concept_id: str) -> dict[str, Any]:
    graph = build_knowledge_graph()
    edges = [
        e
        for e in graph["edges"]
        if e.get("from") == concept_id or e.get("to") == concept_id or concept_id in str(e.get("from", ""))
    ]
    kos = {k.concept_id: k for k in all_knowledge_objects()}
    ko = kos.get(concept_id)
    return {
        "concept_id": concept_id,
        "concept": ko.to_dict() if ko else None,
        "edges": edges,
        "causal_models": [c.to_dict() for c in all_causal_models() if concept_id in c.related_concepts],
    }
