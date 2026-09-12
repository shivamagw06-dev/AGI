"""Phase 4 — sector-aware retrieval: sector KPIs outrank generic Academy concepts."""

from __future__ import annotations

from typing import Any

from academy.catalog import knowledge_by_id, teach
from academy.fapi.retrieval import retrieve_academy
from sif.frameworks import get_framework
from sif.schema import SectorFramework


def _kpi_to_pseudo_concept(kpi: str) -> dict[str, Any]:
    label = kpi.replace("_", " ").title()
    return {
        "concept_id": f"sif_kpi:{kpi}",
        "concept": label,
        "course": "sector_framework",
        "score": 100.0,
        "definition": f"Sector-priority KPI: {label}",
        "formula": "",
        "why_selected": "sector_framework_priority_metric",
        "kind": "sector_kpi",
        "kpi": kpi,
    }


def sector_aware_retrieve(
    query: str,
    framework: SectorFramework | None,
    *,
    limit: int = 16,
) -> dict[str, Any]:
    """Retrieve sector KPIs first, then Finance Academy concepts mapped to the framework."""
    if framework is None:
        academy = retrieve_academy(query, limit=limit)
        return {
            "sector_kpis": [],
            "academy": academy,
            "ranked": academy.get("concepts") or [],
            "concept_ids": academy.get("concept_ids") or [],
            "generic_suppressed": [],
            "sector_outranks_generic": False,
        }

    # 1) Sector KPIs / priority metrics always lead
    kpi_rows = []
    seen_kpi = set()
    for kpi in list(framework.priority_metrics) + list(framework.required_kpis):
        if kpi in seen_kpi:
            continue
        seen_kpi.add(kpi)
        kpi_rows.append(_kpi_to_pseudo_concept(kpi))

    # 2) Academy retrieval, then re-rank by framework priority
    academy = retrieve_academy(query, limit=max(limit, 20))
    kb = knowledge_by_id()
    priority = {cid: 100 - i for i, cid in enumerate(framework.academy_concept_priority)}
    suppress = set(framework.suppress_generic_concepts or [])

    ranked_academy = []
    suppressed = []
    for row in academy.get("concepts") or []:
        cid = row["concept_id"]
        if cid in suppress:
            suppressed.append(cid)
            continue
        boost = priority.get(cid, 0)
        # also boost if concept matches accounting/cf focus labels loosely
        score = float(row.get("score") or 0) + boost
        if cid in framework.academy_concept_priority:
            score += 25
        ranked_academy.append({**row, "score": round(score, 3), "sector_boost": boost, "why_selected": (row.get("why_selected") or "") + "; sector_framework_boost"})

    # Ensure priority Academy concepts appear even if weak lexical match
    have = {r["concept_id"] for r in ranked_academy}
    for cid in framework.academy_concept_priority:
        if cid in have or cid not in kb:
            continue
        ko = kb[cid]
        ranked_academy.append(
            {
                "concept_id": cid,
                "concept": ko.concept,
                "course": ko.course_id,
                "score": 80.0 + priority.get(cid, 0),
                "definition": ko.definition,
                "formula": ko.formula,
                "why_selected": "sector_framework_required_academy_concept",
                "sector_boost": priority.get(cid, 0),
            }
        )

    ranked_academy.sort(key=lambda r: r["score"], reverse=True)
    # Drop remaining suppressed generics if they slipped in
    ranked_academy = [r for r in ranked_academy if r["concept_id"] not in suppress]

    combined = kpi_rows[:12] + ranked_academy
    combined = combined[:limit]

    # Teach blocks for top academy concepts (for answer hints)
    teachings = []
    for r in ranked_academy[:6]:
        try:
            teachings.append(teach(r["concept_id"]))
        except Exception:
            continue

    return {
        "sector_id": framework.sector_id,
        "sector_kpis": kpi_rows[:12],
        "kpi_ids": [k["kpi"] for k in kpi_rows[:12]],
        "academy": {**academy, "concepts": ranked_academy, "concept_ids": [r["concept_id"] for r in ranked_academy]},
        "ranked": combined,
        "concept_ids": [r["concept_id"] for r in ranked_academy[:16]],
        "generic_suppressed": suppressed,
        "sector_outranks_generic": True,
        "teachings": teachings,
        "valuation_methodology": list(framework.valuation_methodology),
        "preferred_multiples": list(framework.preferred_multiples),
    }
