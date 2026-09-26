"""Architecture score + Mission Control Architecture Center report (RC-01)."""

from __future__ import annotations

from typing import Any, Dict, List


def score_architecture(sections: Dict[str, Any]) -> dict[str, Any]:
    """0–100 architecture score from section pass rates."""
    weights = {
        "invariants": 30,
        "dependencies": 25,
        "lineage": 15,
        "publication": 10,
        "uag": 10,
        "contexts": 10,
    }
    earned = 0.0
    possible = 0.0
    breakdown = {}
    for key, weight in weights.items():
        possible += weight
        section = sections.get(key) or {}
        if key == "invariants":
            total = int(section.get("total") or 0)
            passed = int(section.get("passed") or 0)
            ratio = (passed / total) if total else (1.0 if section.get("ok") else 0.0)
        else:
            ratio = 1.0 if section.get("ok") else 0.0
        points = weight * ratio
        earned += points
        breakdown[key] = {
            "weight": weight,
            "ratio": round(ratio, 4),
            "points": round(points, 2),
            "ok": section.get("ok"),
        }
    score = round(100.0 * earned / possible, 1) if possible else 0.0
    grade = (
        "A"
        if score >= 95
        else "B"
        if score >= 85
        else "C"
        if score >= 70
        else "D"
        if score >= 50
        else "F"
    )
    return {
        "score": score,
        "grade": grade,
        "breakdown": breakdown,
        "release_candidate_ready": score >= 95 and all(
            (sections.get(k) or {}).get("ok") for k in weights
        ),
    }


def build_report(
    *,
    ok: bool,
    score: dict[str, Any],
    sections: dict[str, Any],
    violations: List[dict[str, Any]],
    import_graph: dict[str, Any],
    layers: dict[str, Any],
) -> dict[str, Any]:
    inv = sections.get("invariants") or {}
    return {
        "title": "AGIB v1.0 Architecture Conformance Report",
        "ok": ok,
        "architecture_score": score,
        "invariant_summary": {
            "passed": inv.get("passed"),
            "failed": inv.get("failed"),
            "total": inv.get("total"),
        },
        "violation_count": len(violations),
        "violations": violations[:50],
        "layer_dependencies": layers,
        "import_graph_summary": {
            "node_count": len(import_graph.get("nodes") or []),
            "edge_count": len(import_graph.get("edges") or []),
        },
        "context_propagation": (sections.get("contexts") or {}).get("present"),
        "lineage_health": {
            "ok": (sections.get("lineage") or {}).get("ok"),
            "canonical": (sections.get("lineage") or {}).get("canonical"),
            "publication_path": (sections.get("lineage") or {}).get("publication_path"),
        },
        "release_candidate_ready": bool(score.get("release_candidate_ready")),
        "general_availability": True,
        "release_status": "GENERAL_AVAILABILITY",
        "next_gate": "Operate AGIB v1.0 GA — preserve architecture; track product metrics"
        if score.get("release_candidate_ready")
        else "Remediate violations — GA baseline requires PASS",
    }


def architecture_center_board(conformance: dict[str, Any]) -> dict[str, Any]:
    score = conformance.get("architecture_score") or {}
    sections = conformance.get("sections") or {}
    return {
        "architecture_center": True,
        "architecture_score": score.get("score"),
        "architecture_grade": score.get("grade"),
        "release_candidate_ready": score.get("release_candidate_ready"),
        "invariant_passed": (sections.get("invariants") or {}).get("passed"),
        "invariant_total": (sections.get("invariants") or {}).get("total"),
        "violation_count": conformance.get("violation_count"),
        "violations": (conformance.get("violations") or [])[:12],
        "layer_dependencies": conformance.get("layers"),
        "import_graph": {
            "nodes": len((conformance.get("import_graph") or {}).get("nodes") or []),
            "edges": len((conformance.get("import_graph") or {}).get("edges") or []),
        },
        "context_propagation": (sections.get("contexts") or {}).get("present"),
        "lineage_health": (conformance.get("report") or {}).get("lineage_health"),
        "invariants": (sections.get("invariants") or {}).get("results") or [],
        "is_quality_gate": True,
        "is_feature": False,
        "architecture_frozen": True,
        "adds_intelligence_engines": False,
        "agib_general_availability": True,
        "agib_release_status": "GENERAL_AVAILABILITY",
        "ga_spec": "docs/AGIB_V1_0_GA.md",
    }
