"""Semantic retrieval across Finance Academy objects for production use."""

from __future__ import annotations

import re
from typing import Any

from academy.catalog import all_causal_models, all_knowledge_objects, all_mental_models, knowledge_by_id
from academy.graph import concept_neighborhood


def _course_of(ko: Any) -> str:
    cid = getattr(ko, "course_id", None) or ""
    tags = set(getattr(ko, "tags", None) or [])
    if cid:
        if "mankiw" in cid or "economics" in cid:
            return "economics"
        if "accounting" in cid:
            return "accounting"
        if "corporate" in cid or "applied" in cid:
            return "corporate_finance"
    if "acf" in tags or "corporate_finance" in tags:
        return "corporate_finance"
    if "accounting" in tags:
        return "accounting"
    if "economics" in tags or "mankiw" in tags:
        return "economics"
    return "unknown"


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(t) > 2}


def retrieve_academy(
    query: str,
    *,
    domains: list[str] | None = None,
    limit: int = 12,
) -> dict[str, Any]:
    """Rank Academy concepts, causal models, mental models for a query."""
    q = (query or "").strip()
    q_tokens = _tokens(q)
    preferred = set(domains or [])

    scored: list[dict[str, Any]] = []
    for ko in all_knowledge_objects():
        course = _course_of(ko)
        if preferred and course not in preferred and course != "unknown":
            # still allow weak matches outside preferred domains
            domain_boost = 0.0
        else:
            domain_boost = 1.5 if preferred else 0.5

        blob_tokens = _tokens(
            " ".join(
                [
                    ko.concept_id,
                    ko.concept,
                    ko.definition,
                    " ".join(ko.tags or []),
                    " ".join(ko.first_principles or [])[:400],
                ]
            )
        )
        overlap = q_tokens & blob_tokens
        if not overlap and ko.concept_id.replace("_", " ") not in q.lower() and ko.concept.lower() not in q.lower():
            # keep tiny residual for graph expansion later
            score = 0.0
        else:
            score = float(len(overlap)) + domain_boost
            if ko.concept_id in q_tokens or ko.concept_id.replace("_", "") in "".join(q_tokens):
                score += 3.0
            if any(t in ko.concept.lower().split() for t in q_tokens):
                score += 1.5
        if score <= 0:
            continue
        scored.append(
            {
                "concept_id": ko.concept_id,
                "concept": ko.concept,
                "course": course,
                "score": round(score, 3),
                "definition": ko.definition,
                "formula": ko.formula,
                "decision_framework": list(ko.decision_framework or [])[:4],
                "valuation_impact": ko.valuation_impact if isinstance(ko.valuation_impact, dict) else {},
                "forecast_impact": list(ko.forecast_impact or [])[:4],
                "investment_impact": list(ko.investment_impact or [])[:4],
                "why_selected": f"token overlap {sorted(overlap)[:8]}; domain_boost={domain_boost}",
            }
        )
    scored.sort(key=lambda r: r["score"], reverse=True)

    # Graph expansion from top hits
    expanded: dict[str, dict[str, Any]] = {r["concept_id"]: r for r in scored[:limit]}
    for top in scored[:5]:
        try:
            neigh = concept_neighborhood(top["concept_id"])
        except Exception:
            neigh = {}
        for rel in (neigh.get("related") or neigh.get("neighbors") or [])[:6]:
            cid = rel if isinstance(rel, str) else (rel.get("concept_id") or rel.get("id"))
            if not cid or cid in expanded:
                continue
            ko = knowledge_by_id().get(cid)
            if not ko:
                continue
            expanded[cid] = {
                "concept_id": cid,
                "concept": ko.concept,
                "course": _course_of(ko),
                "score": round(float(top["score"]) * 0.55, 3),
                "definition": ko.definition,
                "formula": ko.formula,
                "decision_framework": list(ko.decision_framework or [])[:3],
                "valuation_impact": ko.valuation_impact if isinstance(ko.valuation_impact, dict) else {},
                "forecast_impact": list(ko.forecast_impact or [])[:3],
                "investment_impact": list(ko.investment_impact or [])[:3],
                "why_selected": f"graph neighbor of {top['concept_id']}",
            }

    ranked = sorted(expanded.values(), key=lambda r: r["score"], reverse=True)[:limit]
    ranked_ids = {r["concept_id"] for r in ranked}

    causal = []
    for cm in all_causal_models():
        rel = set(cm.related_concepts or [])
        hit = rel & ranked_ids
        chain_l = " ".join(cm.chain).lower()
        if hit or any(t in chain_l for t in list(q_tokens)[:8]):
            causal.append(
                {
                    "model_id": cm.model_id,
                    "name": cm.name,
                    "chain": list(cm.chain),
                    "related_concepts": list(cm.related_concepts or [])[:12],
                    "score": len(hit) + (1 if any(t in chain_l for t in q_tokens) else 0),
                }
            )
    causal.sort(key=lambda c: c["score"], reverse=True)

    mental = []
    for mm in all_mental_models():
        rel = set(mm.related_concepts or [])
        hit = rel & ranked_ids
        if hit or any(t in (mm.name or "").lower() for t in q_tokens):
            mental.append(
                {
                    "model_id": mm.model_id,
                    "name": mm.name,
                    "related_concepts": list(mm.related_concepts or [])[:12],
                    "score": len(hit),
                }
            )
    mental.sort(key=lambda m: m["score"], reverse=True)

    formulas = [
        {"concept_id": r["concept_id"], "formula": r["formula"]}
        for r in ranked
        if r.get("formula")
    ][:8]

    relationships = []
    for r in ranked[:6]:
        try:
            neigh = concept_neighborhood(r["concept_id"])
            relationships.append({"concept_id": r["concept_id"], "neighborhood": neigh})
        except Exception:
            continue

    return {
        "query": q,
        "concepts": ranked,
        "concept_ids": [r["concept_id"] for r in ranked],
        "courses": sorted({r["course"] for r in ranked if r.get("course") and r["course"] != "unknown"}),
        "causal_models": causal[:8],
        "mental_models": mental[:8],
        "formulas": formulas,
        "relationships": relationships,
        "multi_discipline": len({r["course"] for r in ranked if r.get("course") != "unknown"}) >= 2,
    }
