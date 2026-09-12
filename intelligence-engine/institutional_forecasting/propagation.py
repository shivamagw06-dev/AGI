"""Propagation engine — assumptions walk the Knowledge Graph deterministically."""

from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from institutional_forecasting.assumptions import ScenarioAssumption
from institutional_forecasting.forecast_graph import (
    ForecastEdge,
    ForecastGraph,
    ForecastImpact,
    ForecastNode,
)
from institutional_forecasting.schema import FORECAST_GRAPH_VERSION, PROPAGATION_VERSION
from institutional_graph.graph import InstitutionalKnowledgeGraph


# Edge kind → sign applied to propagated shock when traversing source → target
_KIND_SIGN = {
    "positive": 1.0,
    "supports": 1.0,
    "derived": 1.0,
    "evidences": 1.0,
    "impacts": 1.0,
    "monitors": 0.0,  # structural, not causal for forecast
    "belongs_to": 0.0,
    "negative": -1.0,
    "pressures": -1.0,
}


@dataclass
class PropagationResult:
    node_impacts: Dict[str, float]
    changed_nodes: List[dict[str, Any]]
    propagated_impacts: List[dict[str, Any]]
    forecast_graph: ForecastGraph
    graph_changes: List[str]
    attenuation_paths: Dict[str, List[str]]
    elapsed_ms: float


def _resolve_assumption_node(
    graph: InstitutionalKnowledgeGraph,
    assumption: ScenarioAssumption,
) -> Optional[str]:
    key = str(assumption.node_key or "").strip().lower()
    meta = graph.meta or {}
    metric_ids = meta.get("metric_ids") or {}
    if key in metric_ids:
        return metric_ids[key]
    if key in {"rbi_rate", "rbi", "repo", "repo_rate"}:
        return meta.get("rbi_node_id")
    if key in {"valuation", "val"}:
        return meta.get("valuation_node_id")
    if key == "risk":
        risks = graph.nodes_by_type("Risk")
        return risks[0].id if risks else None
    # Fuzzy label match
    for node in graph.nodes.values():
        label = str(node.label or "").lower()
        attrs = node.attributes or {}
        if key and (key == str(attrs.get("metric_key") or "").lower() or key in label):
            return node.id
        if assumption.variable and assumption.variable.lower() in label:
            return node.id
    return None


def propagate(
    graph: InstitutionalKnowledgeGraph,
    assumptions: Sequence[ScenarioAssumption],
    *,
    horizon: str = "12M",
    scenario_id: str = "",
    probability: float = 0.0,
    max_depth: int = 6,
    decay: float = 0.72,
) -> PropagationResult:
    """
    Propagate explicit assumption shocks through the company knowledge graph.

    Example:
      Repo Rate ↓ → Funding/NIM ↑ → Profitability ↑ → ROE ↑ → BQ ↑ → Decision score ↑
    """
    import time

    t0 = time.perf_counter()
    shocks: Dict[str, float] = defaultdict(float)
    seed_nodes: list[str] = []
    for assumption in assumptions:
        nid = _resolve_assumption_node(graph, assumption)
        if not nid:
            continue
        # Shock = magnitude * confidence (explicit, deterministic)
        shock = float(assumption.magnitude) * float(assumption.confidence)
        shocks[nid] += shock
        seed_nodes.append(nid)

    # BFS propagation
    impacts: Dict[str, float] = defaultdict(float)
    for nid, shock in shocks.items():
        impacts[nid] += shock

    paths: Dict[str, List[str]] = {nid: [nid] for nid in shocks}
    edges_used: List[Tuple[str, str, str, float, float]] = []  # src,tgt,kind,mag,conf
    q: deque[Tuple[str, float, int, List[str]]] = deque(
        (nid, shocks[nid], 0, [nid]) for nid in shocks
    )
    visited_depth: Dict[str, int] = {nid: 0 for nid in shocks}

    while q:
        cur, shock, depth, path = q.popleft()
        if depth >= max_depth or abs(shock) < 0.01:
            continue
        for rel in graph.neighbors(cur, outbound=True):
            sign = _KIND_SIGN.get(str(rel.kind or "").lower(), 0.0)
            if sign == 0.0:
                continue
            transmitted = shock * sign * float(rel.strength) * decay
            if abs(transmitted) < 0.01:
                continue
            tgt = rel.target_id
            impacts[tgt] += transmitted
            edges_used.append(
                (cur, tgt, rel.kind, transmitted, float(rel.confidence) * float(probability or 1.0))
            )
            next_depth = depth + 1
            if tgt not in visited_depth or next_depth < visited_depth[tgt]:
                visited_depth[tgt] = next_depth
                next_path = path + [tgt]
                paths[tgt] = next_path
                q.append((tgt, transmitted, next_depth, next_path))

    changed_nodes: list[dict[str, Any]] = []
    for nid, impact in sorted(impacts.items(), key=lambda x: -abs(x[1])):
        node = graph.get(nid)
        if node is None:
            continue
        changed_nodes.append(
            {
                "node_id": nid,
                "label": node.label,
                "type": node.type,
                "impact": round(impact, 4),
                "seed": nid in shocks,
            }
        )

    propagated = [
        {
            "node_id": row["node_id"],
            "label": row["label"],
            "impact": row["impact"],
            "path": paths.get(row["node_id"], []),
        }
        for row in changed_nodes
        if not row["seed"]
    ]

    # Build forecast graph
    f_nodes: list[ForecastNode] = []
    seen_nodes: set[str] = set()
    for nid, impact in impacts.items():
        node = graph.get(nid)
        if node is None or nid in seen_nodes:
            continue
        seen_nodes.add(nid)
        f_nodes.append(
            ForecastNode(
                id=nid,
                label=node.label,
                node_type=node.type,
                shock=float(shocks.get(nid, 0.0)),
                impact=float(impact),
                horizon=horizon,
                confidence=float(node.confidence),
            )
        )

    f_edges: list[ForecastEdge] = []
    seen_edges: set[str] = set()
    for src, tgt, kind, mag, conf in edges_used:
        eid = hashlib.sha256(f"{scenario_id}|{src}|{tgt}|{kind}".encode()).hexdigest()[:12]
        if eid in seen_edges:
            continue
        seen_edges.add(eid)
        f_edges.append(
            ForecastEdge(
                id=f"fg-e-{eid}",
                source_id=src,
                target_id=tgt,
                direction=kind,
                magnitude=float(mag),
                probability=float(probability),
                confidence=float(conf),
                time_horizon=horizon,
                label=f"{kind}:{src}->{tgt}",
            )
        )

    f_impacts = [
        ForecastImpact(
            node_id=p["node_id"],
            label=p["label"],
            impact=float(p["impact"]),
            path=tuple(p.get("path") or ()),
        )
        for p in propagated[:24]
    ]

    fg = ForecastGraph(
        scenario_id=scenario_id,
        horizon=horizon,
        nodes=f_nodes,
        edges=f_edges,
        impacts=f_impacts,
        version=FORECAST_GRAPH_VERSION,
    )

    graph_changes = [
        f"{row['label']}: {row['impact']:+.2f}"
        for row in changed_nodes[:16]
    ]

    elapsed = (time.perf_counter() - t0) * 1000.0
    return PropagationResult(
        node_impacts=dict(impacts),
        changed_nodes=changed_nodes,
        propagated_impacts=propagated,
        forecast_graph=fg,
        graph_changes=graph_changes,
        attenuation_paths=paths,
        elapsed_ms=elapsed,
    )


def score_delta_from_impacts(
    graph: InstitutionalKnowledgeGraph,
    node_impacts: Dict[str, float],
) -> Tuple[float, Dict[str, float]]:
    """
    Translate node impacts into a decision-score delta.

    Positive BQ / profitability / NIM / ROE lifts score.
    Rising credit cost / risk / expensive valuation lowers score.
    """
    meta = graph.meta or {}
    metric_ids = meta.get("metric_ids") or {}
    components: Dict[str, float] = {}

    def _impact(key: str) -> float:
        nid = metric_ids.get(key)
        return float(node_impacts.get(nid, 0.0)) if nid else 0.0

    components["nim"] = _impact("nim") * 2.2
    components["roe"] = _impact("roe") * 2.0
    components["profitability"] = _impact("profitability") * 2.4
    components["business_quality"] = _impact("business_quality") * 2.6
    components["financial_quality"] = _impact("financial_quality") * 2.0
    # Credit cost rising is bad → negative contribution from positive impact on credit_cost node
    components["credit_cost"] = -_impact("credit_cost") * 2.3

    val_id = meta.get("valuation_node_id")
    if val_id:
        # Negative shock on valuation node (more expensive) lowers score
        components["valuation"] = float(node_impacts.get(val_id, 0.0)) * 1.8

    rbi_id = meta.get("rbi_node_id")
    if rbi_id:
        # Rate up (positive shock on rbi) is typically negative for banks via NIM path;
        # residual direct macro drag
        components["macro"] = -float(node_impacts.get(rbi_id, 0.0)) * 0.8

    risk_drag = 0.0
    for node in graph.nodes_by_type("Risk"):
        risk_drag += float(node_impacts.get(node.id, 0.0))
    components["risk"] = -risk_drag * 1.5

    # Map continuous component sum into score delta roughly in [-4, +4]
    raw = sum(components.values())
    delta = max(-4.0, min(4.0, raw))
    return delta, components
