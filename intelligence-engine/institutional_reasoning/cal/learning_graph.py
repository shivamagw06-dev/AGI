"""Learning Graph — final AGIB graph.

Outcome Graph → Learning Proposal → Simulation → Approved Change → New Version
"""

from __future__ import annotations

from typing import Any

LG_VERSION = "learning-graph-v1.0.0"

NODE_KINDS = (
    "outcome_graph",
    "learning_proposal",
    "simulation",
    "approval",
    "version",
)

EDGE_KINDS = (
    "PROPOSES",
    "SIMULATED_BY",
    "APPROVED_BY",
    "REJECTED_BY",
    "DEPLOYED_AS",
    "REFERENCES_OG",
)


def _node(node_id: str, kind: str, label: str, **attrs: Any) -> dict[str, Any]:
    return {"id": node_id, "kind": kind, "label": label, "attrs": attrs}


def _edge(src: str, kind: str, dst: str, **attrs: Any) -> dict[str, Any]:
    return {"source": src, "kind": kind, "target": dst, "attrs": attrs}


def build_learning_graph(record: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    proposal = record.get("proposal") or {}
    simulation = record.get("simulation") or {}
    approval = record.get("approval") or {}
    deployment = record.get("deployment") or {}
    og_ref = record.get("outcome_ref") or proposal.get("source_outcome_id") or proposal.get("og_ref")

    n_og = "outcome_graph"
    nodes.append(_node(n_og, "outcome_graph", f"OG {og_ref}", reference=og_ref))

    n_prop = "learning_proposal"
    nodes.append(
        _node(
            n_prop,
            "learning_proposal",
            str(proposal.get("kind") or "proposal"),
            proposal_id=proposal.get("proposal_id"),
            target=proposal.get("target"),
            regime=proposal.get("regime"),
        )
    )
    edges.append(_edge(n_og, "PROPOSES", n_prop))
    if og_ref:
        edges.append(_edge(n_prop, "REFERENCES_OG", n_og))

    n_sim = "simulation"
    nodes.append(
        _node(
            n_sim,
            "simulation",
            "Sandbox",
            passed=simulation.get("passed"),
            ies_delta=simulation.get("ies_delta"),
            live_delta=simulation.get("live_delta"),
        )
    )
    edges.append(_edge(n_prop, "SIMULATED_BY", n_sim))

    approved = bool(approval.get("approved"))
    n_appr = "approval"
    nodes.append(
        _node(
            n_appr,
            "approval",
            "Approved" if approved else "Rejected",
            approved=approved,
            reason=approval.get("reason"),
            approver=approval.get("approver"),
        )
    )
    edges.append(_edge(n_sim, "APPROVED_BY" if approved else "REJECTED_BY", n_appr))

    n_ver = "version"
    version_id = deployment.get("version_id")
    nodes.append(
        _node(
            n_ver,
            "version",
            version_id or "not_deployed",
            planner_version=deployment.get("planner_version"),
            policy_version=deployment.get("policy_version"),
            reversible=True,
            source_overwritten=False,
        )
    )
    if deployment.get("deployed"):
        edges.append(_edge(n_appr, "DEPLOYED_AS", n_ver))
    else:
        edges.append(_edge(n_appr, "REJECTED_BY", n_ver))

    node_ids = {n["id"] for n in nodes}
    problems: list[str] = []
    for e in edges:
        if e["source"] not in node_ids or e["target"] not in node_ids:
            problems.append(f"dangling_edge:{e['source']}->{e['target']}")
    if not og_ref:
        problems.append("missing_og_link")
    if approved and deployment.get("deployed") and not version_id:
        problems.append("approved_without_version")

    return {
        "lg_version": LG_VERSION,
        "proposal_id": proposal.get("proposal_id"),
        "outcome_ref": og_ref,
        "nodes": nodes,
        "edges": edges,
        "terminal": n_ver,
        "node_kinds": sorted({n["kind"] for n in nodes}),
        "edge_kinds": sorted({e["kind"] for e in edges}),
        "counts": {"nodes": len(nodes), "edges": len(edges)},
        "integrity": {
            "valid": not problems,
            "problems": problems,
            "linked_to_og": bool(og_ref),
            "governed": True,
            "source_overwritten": False,
        },
    }
