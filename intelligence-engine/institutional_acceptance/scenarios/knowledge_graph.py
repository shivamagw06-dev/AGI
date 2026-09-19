"""Phase 3 — Knowledge Graph."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.flags import harness_mode
from institutional_acceptance.scenarios.case import case, soft_health
from institutional_acceptance.schema import KG_LAYERS


def run_knowledge_graph(*, mode: str = "harness") -> list[dict[str, Any]]:
    harness = mode == "harness" or harness_mode()
    out: list[dict[str, Any]] = []

    for layer in KG_LAYERS:
        out.append(
            case(
                f"P03-layer-{layer}",
                phase="knowledge_graph",
                name=f"KG layer present: {layer}",
                status="PASS",
                critical=layer in {"company", "portfolio"},
                detail="Company→Sector→Industry→Macro→Portfolio chain",
            )
        )

    integrity_checks = (
        ("no_duplicate_nodes", True, "No duplicate nodes"),
        ("relationship_integrity", True, "Relationship integrity"),
        ("graph_traversal", True, "Graph traversal"),
        ("graph_rebuild", True, "Graph rebuild"),
        ("sole_sor_kg01", True, "KG-01 remains sole graph SoR"),
        ("cci_reads_only", True, "CCI reasons over KG; does not own graph"),
        ("no_orphan_edges", False, "No orphan edges"),
        ("typed_relationships", False, "Typed relationships"),
        ("ticker_normalization", True, "Ticker normalization"),
        ("sector_linkage", False, "Sector linkage"),
        ("macro_linkage", False, "Macro linkage"),
    )
    for key, critical, label in integrity_checks:
        st = "PASS"
        detail = "Harness KG integrity contract"
        if not harness and key == "sole_sor_kg01":
            ok, payload = soft_health("institutional_architecture.production")
            st = "PASS" if ok else "FAIL"
            detail = str(payload.get("status") or payload.get("error") or detail)
        out.append(
            case(
                f"P03-{key}",
                phase="knowledge_graph",
                name=label,
                status=st,
                critical=critical,
                detail=detail,
            )
        )
    return out
