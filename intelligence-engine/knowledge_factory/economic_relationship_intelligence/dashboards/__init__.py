"""Morning Board — Economic Relationship Coverage."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.schema import (
    ECONOMIC_SEMANTICS,
    IERI_VERSION,
)


def relationship_dashboard(*, ensure: bool = True) -> dict[str, Any]:
    if ensure and ieri_store.relationship_count() == 0:
        from knowledge_factory.economic_relationship_intelligence.pipeline import (
            run_economic_relationship_pipeline,
        )

        run_economic_relationship_pipeline()

    rows = ieri_store.list_relationships()
    commodities = ieri_store.list_commodities()
    n = len(rows) or 1

    by_sem = {s: 0 for s in ECONOMIC_SEMANTICS}
    company_rels = industry_rels = commodity_rels = gov_rels = macro_rels = 0
    confidences: list[float] = []
    validation_failures = 0
    missing = []

    for r in rows:
        sem = str(r.get("semantics") or "")
        if sem in by_sem:
            by_sem[sem] += 1
        sk = (r.get("source_ref") or {}).get("kind")
        tk = (r.get("target_ref") or {}).get("kind")
        kinds = {sk, tk}
        if "company" in kinds or "bank" in kinds:
            company_rels += 1
        if "industry" in kinds or "sector" in kinds:
            industry_rels += 1
        if "commodity" in kinds:
            commodity_rels += 1
        if "policy" in kinds or "government_body" in kinds:
            gov_rels += 1
        if "macro" in kinds:
            macro_rels += 1
        confidences.append(float(r.get("confidence") or 0))
        if (r.get("validation") or {}).get("status") == "fail":
            validation_failures += 1

    # Coverage gaps — known high-value entities with zero edges
    for ent, kind in (
        ("DIXON", "company"),
        ("crude_oil", "commodity"),
        ("repo_rate", "macro"),
        ("PLI-ELECTRONICS", "policy"),
        ("steel", "commodity"),
    ):
        if not ieri_store.list_relationships(entity=ent):
            missing.append({"entity": ent, "kind": kind})

    avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
    ready_pct = round(100.0 * (len(rows) - validation_failures) / n, 2)

    return {
        "north_star": "institutional_economic_relationship_coverage",
        "version": IERI_VERSION,
        "economic_relationship_coverage": {
            "relationships": len(rows),
            "commodities": len(commodities),
            "nodes": ieri_store.node_count(),
            "transmissions": len(ieri_store.list_transmissions()),
            "institutional_ready_pct": ready_pct,
        },
        "company_relationships": company_rels,
        "industry_relationships": industry_rels,
        "commodity_coverage": {
            "commodities": len(commodities),
            "linked_relationships": commodity_rels,
        },
        "government_links": gov_rels,
        "macro_links": macro_rels,
        "missing_relationships": missing,
        "validation_failures": validation_failures,
        "relationship_confidence": {
            "average": avg_conf,
            "min": round(min(confidences), 4) if confidences else 0.0,
            "max": round(max(confidences), 4) if confidences else 0.0,
        },
        "semantics_breakdown": by_sem,
        "fabricated": False,
        "reasoning": False,
    }
