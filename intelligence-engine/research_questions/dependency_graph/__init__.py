"""Question tree / dependency graph — logical chain of proof."""

from __future__ import annotations

from typing import Any

from research_questions.schema import TREE_LAYER_ORDER


def build_question_tree(
    *,
    hypothesis_id: str,
    hypothesis_statement: str,
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a dependency tree: Historical → Peer → Valuation → Forecast → Thesis."""
    by_layer: dict[str, list[str]] = {layer: [] for layer in TREE_LAYER_ORDER}
    other: list[str] = []
    nodes = []
    for q in questions:
        layer = str(q.get("tree_layer") or q.get("type") or "Peer")
        if layer not in by_layer:
            # Map question types into tree layers
            t = str(q.get("type") or "")
            if t in TREE_LAYER_ORDER:
                layer = t
            elif t in ("Verification", "Business", "Financial", "Management", "Accounting"):
                layer = "Historical" if not by_layer["Historical"] else "Peer"
            elif t in ("Contradiction", "Risk", "Macro", "Portfolio"):
                layer = "Forecast"
            else:
                layer = "Peer"
        qid = str(q.get("id"))
        if layer in by_layer:
            by_layer[layer].append(qid)
        else:
            other.append(qid)
        nodes.append(
            {
                "id": qid,
                "question": q.get("question"),
                "layer": layer,
                "priority": q.get("priority"),
                "decision_impact": q.get("decision_impact"),
                "analyst_owner": q.get("analyst_owner"),
            }
        )

    # Edges between consecutive populated layers + thesis root
    edges: list[dict[str, str]] = []
    root_id = f"HYP::{hypothesis_id}"
    prev_ids = [root_id]
    layers_present = []
    for layer in TREE_LAYER_ORDER:
        ids = by_layer.get(layer) or []
        if not ids:
            continue
        layers_present.append({"layer": layer, "question_ids": ids})
        for pid in prev_ids:
            for cid in ids:
                edges.append({"from": pid, "to": cid, "relation": "supports"})
        prev_ids = ids

    thesis_id = f"THESIS::{hypothesis_id}"
    for pid in prev_ids:
        if pid != root_id:
            edges.append({"from": pid, "to": thesis_id, "relation": "concludes"})

    # Attach dependency ids onto each question
    layer_index = {layer: i for i, layer in enumerate(TREE_LAYER_ORDER)}
    enriched = []
    for q in questions:
        layer = str(q.get("tree_layer") or "")
        deps: list[str] = []
        if layer in layer_index:
            idx = layer_index[layer]
            if idx > 0:
                prev_layer = TREE_LAYER_ORDER[idx - 1]
                deps = list(by_layer.get(prev_layer) or [])
        # Honour explicit depends_on from generator
        for d in q.get("depends_on") or []:
            if d not in deps:
                deps.append(d)
        enriched.append({**q, "dependencies": deps, "tree_layer": layer or q.get("type")})

    return {
        "hypothesis_id": hypothesis_id,
        "hypothesis": hypothesis_statement,
        "root": root_id,
        "thesis_node": thesis_id,
        "layers": layers_present,
        "nodes": nodes,
        "edges": edges,
        "layer_order": list(TREE_LAYER_ORDER),
        "proof_chain": " → ".join(["Hypothesis"] + [L["layer"] for L in layers_present] + ["Investment Thesis"]),
        "questions": enriched,
    }


def attach_trees(
    hypothesis_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out = []
    for block in hypothesis_blocks:
        tree = build_question_tree(
            hypothesis_id=str(block.get("hypothesis_id") or block.get("id") or "H1"),
            hypothesis_statement=str(block.get("hypothesis") or block.get("statement") or ""),
            questions=list(block.get("research_questions") or []),
        )
        out.append(
            {
                **block,
                "research_questions": tree["questions"],
                "question_tree": {
                    "proof_chain": tree["proof_chain"],
                    "layers": tree["layers"],
                    "edges": tree["edges"],
                    "root": tree["root"],
                    "thesis_node": tree["thesis_node"],
                    "layer_order": tree["layer_order"],
                },
            }
        )
    return out
