"""KG-01 production façades — health / company graph / Mission Control."""

from __future__ import annotations

from typing import Any, Optional

from institutional_graph.diagnostics import build_diagnostics, quality_gates
from institutional_graph.flags import flags_dict, is_enabled
from institutional_graph.graph import InstitutionalKnowledgeGraph, build_company_graph
from institutional_graph.impact import compute_impacts, impact_summary
from institutional_graph.inference import infer
from institutional_graph.schema import (
    GRAPH_ENGINE_VERSION,
    INFERENCE_VERSION,
    KG_PRODUCT,
    KG_ROLE,
    KG_SPEC,
    KG_VERSION,
    KG_WORKSTREAM_ID,
)
from institutional_graph.traversal import (
    decision_chain,
    evidence_chain,
    explain_via_traversal,
    impact_chain,
    shortest_reason_path,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


# In-memory company graphs (single-company scope store)
_GRAPHS: dict[str, InstitutionalKnowledgeGraph] = {}


def reset_for_tests() -> None:
    _GRAPHS.clear()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": KG_WORKSTREAM_ID,
        "product": KG_PRODUCT,
        "version": KG_VERSION,
        "role": KG_ROLE,
        "llm": False,
        "scope": "single_company",
        "graph_engine_version": GRAPH_ENGINE_VERSION,
        "inference_version": INFERENCE_VERSION,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": KG_SPEC,
        "brand": "AGI",
        "graphs_cached": sorted(_GRAPHS.keys()),
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    # Aggregate lightweight knowledge health across cached graphs
    entity_count = 0
    rel_count = 0
    disconnected = 0
    inference_quality = []
    path_lengths = []
    for g in _GRAPHS.values():
        diag = build_diagnostics(g)
        entity_count += int(diag.get("entity_count") or 0)
        rel_count += int(diag.get("relationship_count") or 0)
        disconnected += int(diag.get("disconnected_count") or 0)
        inference_quality.append(1.0 if diag.get("quality_gates", {}).get("inference_supported") else 0.0)
        path_lengths.append(float(diag.get("average_path_length") or 0.0))
    avg_inf = sum(inference_quality) / len(inference_quality) if inference_quality else None
    avg_path = sum(path_lengths) / len(path_lengths) if path_lengths else None
    coverage = None
    if _GRAPHS:
        coverage = sum(
            float(build_diagnostics(g).get("evidence_coverage") or 0.0) for g in _GRAPHS.values()
        ) / len(_GRAPHS)
    return {
        "status": h.get("status"),
        "workstream_id": KG_WORKSTREAM_ID,
        "product": KG_PRODUCT,
        "version": KG_VERSION,
        "llm": False,
        "scope": "single_company",
        "knowledge_health": "ok" if h.get("enabled") else "disabled",
        "graph_coverage": coverage,
        "disconnected_nodes": disconnected,
        "inference_quality": avg_inf,
        "average_path_length": avg_path,
        "entity_count": entity_count,
        "relationship_count": rel_count,
        "graphs_cached": h.get("graphs_cached"),
    }


def _serialize_graph(
    graph: InstitutionalKnowledgeGraph,
    *,
    include_paths: bool = False,
    include_inference: bool = True,
) -> dict[str, Any]:
    diagnostics = build_diagnostics(graph)
    payload = graph.to_dict()
    if not include_inference:
        inferred = set(graph.inferred_relationship_ids)
        payload["relationships"] = [
            r for r in payload["relationships"] if r["id"] not in inferred
        ]
        payload["inferred_relationship_ids"] = []
        payload["inference_count"] = 0
    payload["diagnostics"] = diagnostics
    payload["impact"] = impact_summary(graph)
    payload["quality_gates"] = diagnostics.get("quality_gates")
    payload["ok"] = bool(diagnostics.get("quality_gate_pass"))
    payload["workstream_id"] = KG_WORKSTREAM_ID
    if include_paths:
        payload["paths"] = {
            "shortest_reason_path": shortest_reason_path(graph),
            "decision_chain": decision_chain(graph),
            "impact_chain": impact_chain(graph),
            "evidence_to_decision": evidence_chain(graph, graph.decision_node_id)
            if graph.decision_node_id
            else [],
        }
        payload["explanations"] = {
            "why_recommendation": explain_via_traversal(
                graph, f"Why {((graph.get(graph.decision_node_id).attributes or {}).get('recommendation') if graph.decision_node_id and graph.get(graph.decision_node_id) else 'HOLD')}?"
            ),
            "which_evidence_mattered": explain_via_traversal(graph, "Which evidence mattered most?"),
            "macro_to_earnings": explain_via_traversal(graph, "Which macro event affects earnings?"),
            "risks_to_recommendation": explain_via_traversal(
                graph, "Which risks support the recommendation?"
            ),
        }
    return payload


def build_graph_for_company(
    ticker: str,
    *,
    include_paths: bool = False,
    include_inference: bool = True,
) -> dict[str, Any]:
    """Build (or rebuild) the single-company knowledge graph end-to-end."""
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": KG_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["KG-01 disabled"],
        }

    from institutional_decision import history as decision_history
    from institutional_decision.production import decide_company
    from institutional_reporting.fixtures import get_fixture
    from institutional_reporting.reason_composer import compose_reasons

    key = str(ticker or "").strip().upper()
    fixture = get_fixture(key)
    if fixture is None:
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": KG_WORKSTREAM_ID,
            "validation_errors": [f"no fixture for ticker {key}"],
        }

    # Ensure decision + calibration exist
    latest = decision_history.latest(key)
    if latest is None or not getattr(latest, "calibrated", False):
        decide_company(
            {
                "ticker": key,
                "include_calibration": True,
                "include_drift": False,
            }
        )
        latest = decision_history.latest(key)

    reasons = compose_reasons(fixture)
    graph = build_company_graph(fixture, reasons=reasons.reasons, decision=latest)
    if include_inference:
        infer(graph)
    compute_impacts(graph, fixture)

    gates, errors = quality_gates(graph)
    if not all(gates.values()):
        return {
            "ok": False,
            "rejected": True,
            "workstream_id": KG_WORKSTREAM_ID,
            "validation_errors": errors,
            "quality_gates": gates,
            "graph": _serialize_graph(
                graph, include_paths=include_paths, include_inference=include_inference
            ),
        }

    _GRAPHS[key] = graph
    return _serialize_graph(
        graph, include_paths=include_paths, include_inference=include_inference
    )


def get_company_graph(
    ticker: str,
    *,
    include_paths: bool = False,
    include_inference: bool = True,
    rebuild: bool = False,
) -> dict[str, Any]:
    key = str(ticker or "").strip().upper()
    if not rebuild and key in _GRAPHS:
        return _serialize_graph(
            _GRAPHS[key], include_paths=include_paths, include_inference=include_inference
        )
    return build_graph_for_company(
        key, include_paths=include_paths, include_inference=include_inference
    )


def graph_company(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    ticker = str(body.get("ticker") or "").strip()
    include_paths = body.get("include_paths", False)
    include_inference = body.get("include_inference", True)
    if isinstance(include_paths, str):
        include_paths = include_paths.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(include_inference, str):
        include_inference = include_inference.strip().lower() in {"1", "true", "yes", "on"}
    return get_company_graph(
        ticker,
        include_paths=bool(include_paths),
        include_inference=bool(include_inference),
        rebuild=True,
    )
