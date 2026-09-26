"""Unified, read-first Causal Research Engine facade."""
from __future__ import annotations
from typing import Any
from causal_research_engine.event_analysis import event_candidates, normalize_event
from causal_research_engine.reasoning import detect_contradictions, temporal_slice
from causal_research_engine.retrieval import relevant_subgraph

def research_context(*, entity: str, question: str = "", industry: str | None = None, event: dict[str, Any] | None = None,
                     depth: int = 3, analysis_as_of: str | None = None) -> dict[str, Any]:
    graph = relevant_subgraph([entity], depth=depth, company_id=entity, industry=industry, analysis_as_of=analysis_as_of)
    relationships = temporal_slice(graph["relationships"], as_of=analysis_as_of) if analysis_as_of else graph["relationships"]
    normalized = normalize_event(event, analysis_as_of=analysis_as_of) if event and analysis_as_of else None
    selected = event_candidates(normalized, relationships) if normalized else relationships
    return {"cre_version": "cre-v1.0.0", "entity": entity, "question": question, "analysis_as_of": analysis_as_of,
            "event": normalized, "relationships": selected, "contradictions": detect_contradictions(selected),
            "source_graph": graph["source_graph"], "execution_eligible": False, "allowed_use": "research_context",
            "epistemic_warning": "Evidence-governed context, not investment advice."}

def ask_context(**kwargs: Any) -> dict[str, Any]:
    out = research_context(**kwargs)
    return {"causal_research": {"version": out["cre_version"], "analysis_as_of": out["analysis_as_of"],
            "entity": out["entity"], "question": out["question"],
            "chains": [row.to_dict() for row in out["relationships"][:12]],
            "contradictions": [row.to_dict() for row in out["contradictions"]],
            "allowed_use": out["allowed_use"], "execution_eligible": False}}
