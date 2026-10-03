"""IKG report builder for desks, committee, CIO, research writer."""

from __future__ import annotations

from typing import Any


def build_report(pack: dict[str, Any]) -> dict[str, Any]:
    rels = pack.get("relationships") or []
    deps = pack.get("dependencies") or {}
    ticker = pack.get("ticker") or pack.get("canonical_id")
    top = rels[:8]
    return {
        "executive_summary": (
            f"{ticker} is connected across {len(rels)} evidenced relationships "
            f"with {len(deps.get('suppliers') or [])} supplier links, "
            f"{len(deps.get('customers') or [])} customer links, and "
            f"{len(deps.get('macro_drivers') or [])} macro drivers."
        ),
        "relationship_map": [
            {
                "relation": r.get("relation"),
                "counterpart": r.get("counterpart_label") or r.get("counterpart"),
                "confidence": r.get("confidence"),
                "direction": r.get("direction"),
            }
            for r in top
        ],
        "dependency_map": {
            "suppliers": deps.get("suppliers"),
            "customers": deps.get("customers"),
            "regulators": deps.get("regulators"),
            "macro_drivers": deps.get("macro_drivers"),
            "technology_exposure": deps.get("technology_exposure"),
            "paths": [
                {"path": p.get("path_labels"), "confidence": p.get("path_confidence")}
                for p in (deps.get("traversal_paths") or [])[:6]
            ],
        },
        "ownership_chart": [r for r in rels if r.get("relation") in {"owns", "invests_in", "listed_on"}],
        "supply_chain_diagram": [r for r in rels if r.get("relation") in {"supplies", "customer_of", "produces", "depends_on"}],
        "technology_ecosystem": [r for r in rels if "tech" in str(r.get("counterpart") or "").lower() or r.get("relation") == "depends_on"],
        "committee": {
            "relationship_maps": top,
            "dependency_risks": deps.get("suppliers") or [],
            "cross_holding_risks": [r for r in rels if r.get("relation") in {"shares_director", "owns", "invests_in"}],
            "supply_chain_risks": deps.get("suppliers") or [],
            "hidden_concentration": {
                "shared_customers": deps.get("customers"),
                "macro": deps.get("macro_drivers"),
                "technology": deps.get("technology_exposure"),
            },
        },
        "cio_brief": (
            f"Institutional relationship intelligence for {ticker}: "
            f"map dependencies and contagion paths rather than isolated facts. "
            f"Graph confidence {(pack.get('confidence') or {}).get('label')}."
        ),
        "writer_blocks": {
            "relationship_diagrams": top,
            "dependency_maps": deps,
            "ownership_charts": [r for r in rels if r.get("relation") in {"owns", "invests_in"}],
            "supply_chain_diagrams": [r for r in rels if r.get("relation") in {"supplies", "customer_of"}],
            "technology_ecosystem_maps": deps.get("technology_exposure"),
        },
        "portfolio": {
            "hidden_dependencies": deps.get("traversal_paths") or [],
            "shared_suppliers": deps.get("suppliers"),
            "customer_concentration": deps.get("customers"),
            "country_exposure": [r for r in rels if r.get("relation") in {"exports_to", "imports_from"}],
            "technology_exposure": deps.get("technology_exposure"),
            "management_overlap": [r for r in rels if r.get("relation") in {"shares_director", "ceo_of", "board_of"}],
            "never_recommendation": True,
        },
        "text": f"What is connected for {ticker}: {len(rels)} evidenced edges.",
    }
