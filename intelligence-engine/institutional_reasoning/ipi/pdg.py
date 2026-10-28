"""Portfolio Decision Graph (PDG).

Traceability:

    Evidence → Research DJG → Portfolio Decision Graph → Final Portfolio Decision

Soft helper under institutional_reasoning/ipi — does not replace DJG.
"""

from __future__ import annotations

from typing import Any

PDG_VERSION = "portfolio-decision-graph-v1.0.0"

NODE_KINDS = (
    "research_package",
    "expected_return",
    "risk",
    "exposure",
    "scenario",
    "policy",
    "sizing",
    "committee",
    "decision",
)

EDGE_KINDS = (
    "DERIVES",
    "CONSTRAINED_BY",
    "STRESSED_BY",
    "GOVERNED_BY",
    "SIZED_BY",
    "DECIDED_BY",
    "REFERENCES_DJG",
    "WITHHOLDS",
    "CONCLUDES",
)


def _node(node_id: str, kind: str, label: str, **attrs: Any) -> dict[str, Any]:
    return {"id": node_id, "kind": kind, "label": label, "attrs": attrs}


def _edge(src: str, kind: str, dst: str, **attrs: Any) -> dict[str, Any]:
    return {"source": src, "kind": kind, "target": dst, "attrs": attrs}


def build_portfolio_decision_graph(decision: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    run_id = str(decision.get("run_id") or "pdg")
    entity = str(decision.get("entity_id") or "")
    djg_ref = decision.get("djg_reference")
    evidence = decision.get("portfolio_evidence") or {}
    risk = decision.get("risk") or {}
    exposure = decision.get("exposure") or {}
    scenarios = decision.get("scenarios") or {}
    policy = decision.get("policy") or {}
    sizing = decision.get("sizing") or {}
    committee = decision.get("committee") or {}
    withheld = bool(decision.get("withheld"))

    n_research = "research_package"
    nodes.append(
        _node(
            n_research,
            "research_package",
            f"Research package for {entity}",
            djg_reference=djg_ref,
            research_run_id=decision.get("research_run_id"),
            evidence_coverage=evidence.get("evidence_coverage"),
        )
    )
    if djg_ref:
        nodes.append(_node("djg_ref", "research_package", f"DJG {djg_ref}", reference=djg_ref))
        edges.append(_edge(n_research, "REFERENCES_DJG", "djg_ref"))

    n_ret = "expected_return"
    nodes.append(
        _node(
            n_ret,
            "expected_return",
            "Expected return",
            value=evidence.get("expected_return"),
            expected_downside=evidence.get("expected_downside"),
        )
    )
    edges.append(_edge(n_research, "DERIVES", n_ret))

    n_risk = "risk"
    nodes.append(
        _node(
            n_risk,
            "risk",
            "Risk intelligence",
            risk_contribution=risk.get("risk_contribution"),
            risk_budget=risk.get("risk_budget"),
            var=risk.get("var"),
        )
    )
    edges.append(_edge(n_ret, "CONSTRAINED_BY", n_risk))

    n_exp = "exposure"
    nodes.append(
        _node(
            n_exp,
            "exposure",
            "Exposure intelligence",
            rejected=exposure.get("rejected"),
            breaches=len(exposure.get("breaches") or []),
        )
    )
    edges.append(_edge(n_risk, "CONSTRAINED_BY", n_exp))

    n_scen = "scenario"
    nodes.append(
        _node(
            n_scen,
            "scenario",
            "Scenario intelligence",
            shock_count=len(scenarios.get("shocks") or []),
            has_base=bool((scenarios.get("scenarios") or {}).get("base")),
        )
    )
    edges.append(_edge(n_exp, "STRESSED_BY", n_scen))

    n_pol = "policy"
    nodes.append(
        _node(
            n_pol,
            "policy",
            "Portfolio policy",
            allowed=policy.get("allowed"),
            reasons=policy.get("reasons") or [],
        )
    )
    edges.append(_edge(n_scen, "GOVERNED_BY", n_pol))

    n_size = "sizing"
    nodes.append(
        _node(
            n_size,
            "sizing",
            "Position sizing",
            action=sizing.get("action"),
            target_weight=sizing.get("target_weight"),
            conviction=sizing.get("conviction"),
        )
    )
    edges.append(_edge(n_pol, "SIZED_BY", n_size))

    n_com = "committee"
    nodes.append(
        _node(
            n_com,
            "committee",
            "Portfolio committee",
            action=committee.get("action"),
            can_recommend=committee.get("can_recommend"),
        )
    )
    edges.append(_edge(n_size, "DECIDED_BY", n_com))

    n_dec = "decision"
    action = committee.get("action") or sizing.get("action") or "Withhold"
    nodes.append(
        _node(
            n_dec,
            "decision",
            action,
            target_weight=committee.get("target_weight"),
            withheld=withheld,
            conclusion=committee.get("conclusion"),
        )
    )
    if withheld or action == "Withhold":
        edges.append(_edge(n_com, "WITHHOLDS", n_dec))
    else:
        edges.append(_edge(n_com, "CONCLUDES", n_dec))

    # Integrity: every node reachable from research, terminal decision present
    node_ids = {n["id"] for n in nodes}
    problems: list[str] = []
    for e in edges:
        if e["source"] not in node_ids or e["target"] not in node_ids:
            problems.append(f"dangling_edge:{e['source']}->{e['target']}")
    required = {"research_package", "risk", "exposure", "scenario", "policy", "sizing", "committee", "decision"}
    missing = sorted(required - node_ids)
    if missing:
        problems.append(f"missing_nodes:{missing}")

    return {
        "pdg_version": PDG_VERSION,
        "run_id": run_id,
        "entity_id": entity or None,
        "djg_reference": djg_ref,
        "nodes": nodes,
        "edges": edges,
        "terminal": n_dec,
        "node_kinds": sorted({n["kind"] for n in nodes}),
        "edge_kinds": sorted({e["kind"] for e in edges}),
        "counts": {"nodes": len(nodes), "edges": len(edges)},
        "integrity": {
            "valid": not problems,
            "problems": problems,
            "explainable": not problems,
            "linked_to_djg": bool(djg_ref),
        },
    }
