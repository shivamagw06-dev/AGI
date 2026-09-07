"""Decision Justification Graph (DJG).

Every conclusion produces a structured, traversable reasoning graph:

    Question → Applicability → Framework → Evidence → Conflict
      → Decision Policy → Committee → Conclusion

Built for AGIB itself (machine-checkable explainability), not for prose.
Soft helper under institutional_reasoning — no engine replaced.
"""

from __future__ import annotations

from typing import Any

DJG_VERSION = "decision-justification-graph-v1.0.0"

NODE_KINDS = (
    "question",
    "classification",
    "entity",
    "contract",
    "applicability",
    "framework",
    "evidence",
    "conflict",
    "decision_policy",
    "committee",
    "conclusion",
)

EDGE_KINDS = (
    "CLASSIFIED_AS",
    "RESOLVED_TO",
    "GOVERNED_BY",
    "SCORED_BY",
    "SELECTED",
    "REJECTED",
    "CONSUMED",
    "MISSING",
    "CONFLICTS_WITH",
    "WEIGHTED_BY",
    "SUPPORTS",
    "WITHHOLDS",
    "CONCLUDES",
)


def _node(node_id: str, kind: str, label: str, **attrs: Any) -> dict[str, Any]:
    return {"id": node_id, "kind": kind, "label": label, "attrs": attrs}


def _edge(src: str, kind: str, dst: str, **attrs: Any) -> dict[str, Any]:
    return {"source": src, "kind": kind, "target": dst, "attrs": attrs}


def build_justification_graph(record: dict[str, Any]) -> dict[str, Any]:
    """Derive the reasoning graph from a governance record.

    Nothing is invented: every node traces to a field already produced by
    classification, validation, framework execution, debate, or committee.
    """
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    run_id = str(record.get("run_id") or "run")
    path = str(record.get("path") or "research")
    qtype = str(record.get("question_type") or "")
    classification = record.get("classification") or {}
    entity = record.get("entity") or {}
    validation = record.get("validation") or {}
    committee = record.get("committee") or {}
    frameworks = record.get("frameworks") or []
    iki = record.get("iki") or {}
    applicability = iki.get("applicability") or {}
    debate = iki.get("debate") or {}

    q_id = "question"
    nodes.append(
        _node(q_id, "question", str(record.get("question") or "")[:240], run_id=run_id, path=path)
    )

    cls_id = "classification"
    nodes.append(
        _node(
            cls_id,
            "classification",
            qtype or "unclassified",
            confidence=classification.get("confidence"),
            reason=classification.get("reason"),
        )
    )
    edges.append(_edge(q_id, "CLASSIFIED_AS", cls_id))

    # Education path terminates early and legitimately.
    if path == "education":
        concl_id = "conclusion"
        nodes.append(
            _node(concl_id, "conclusion", "Academy explanation", mode="explain_academy", gated=False)
        )
        edges.append(_edge(cls_id, "CONCLUDES", concl_id, reason="education_bypass"))
        return _finalize(nodes, edges, record=record, terminal=concl_id)

    ent_id = "entity"
    nodes.append(
        _node(
            ent_id,
            "entity",
            str(entity.get("entity_id") or "unresolved"),
            entity_name=entity.get("entity_name"),
            entity_type=entity.get("entity_type"),
            confidence=entity.get("confidence"),
            source=entity.get("source"),
        )
    )
    edges.append(_edge(cls_id, "RESOLVED_TO", ent_id))

    if path == "clarification":
        concl_id = "conclusion"
        nodes.append(
            _node(
                concl_id,
                "conclusion",
                "Clarification required",
                gated=True,
                stance=committee.get("stance"),
            )
        )
        edges.append(
            _edge(
                ent_id,
                "WITHHOLDS",
                concl_id,
                reason=(record.get("clarification") or {}).get("reason"),
            )
        )
        return _finalize(nodes, edges, record=record, terminal=concl_id)

    contract = record.get("contract") or {}
    c_id = "contract"
    nodes.append(
        _node(
            c_id,
            "contract",
            f"{qtype} contract",
            required=list(contract.get("required") or []),
            version=record.get("contract_version"),
        )
    )
    edges.append(_edge(ent_id, "GOVERNED_BY", c_id))

    # Applicability node (Phase 3). Absent → legacy fixed mapping.
    app_id = "applicability"
    nodes.append(
        _node(
            app_id,
            "applicability",
            "Applicability scoring" if applicability else "Fixed framework mapping",
            sector=applicability.get("sector"),
            version=applicability.get("applicability_version"),
            n_scored=len(applicability.get("scores") or []),
        )
    )
    edges.append(_edge(c_id, "SCORED_BY", app_id))

    # Evidence nodes from validated field verdicts.
    for verdict in validation.get("field_verdicts") or []:
        field = str(verdict.get("field") or "")
        if not field:
            continue
        ev_id = f"evidence:{field}"
        nodes.append(
            _node(
                ev_id,
                "evidence",
                field,
                present=bool(verdict.get("present")),
                value=verdict.get("value"),
                provenance=verdict.get("provenance"),
                as_of=verdict.get("as_of"),
                entity_id=verdict.get("entity_id"),
                rejected_reason=verdict.get("rejected_reason"),
            )
        )
        # Contract governs which evidence is required.
        edges.append(
            _edge(
                c_id,
                "CONSUMED" if verdict.get("present") else "MISSING",
                ev_id,
                reason=verdict.get("rejected_reason"),
            )
        )

    # Framework nodes + evidence edges.
    app_scores = {
        str(s.get("framework_id")): s for s in (applicability.get("scores") or [])
    }
    for fw in frameworks:
        fid = str(fw.get("framework_id") or "")
        if not fid:
            continue
        f_id = f"framework:{fid}"
        score_row = app_scores.get(fid) or {}
        nodes.append(
            _node(
                f_id,
                "framework",
                str(fw.get("name") or fid),
                framework_id=fid,
                author=fw.get("author"),
                status=fw.get("status"),
                confidence=fw.get("confidence"),
                applicability_score=score_row.get("score"),
                applicability_reasons=score_row.get("reasons"),
                outputs=fw.get("outputs") or {},
            )
        )
        selected = fw.get("status") in {"executed", "insufficient_evidence"}
        edges.append(
            _edge(
                app_id,
                "SELECTED" if selected else "REJECTED",
                f_id,
                score=score_row.get("score"),
                reason=(
                    "; ".join(score_row.get("reasons") or [])
                    or (fw.get("outputs") or {}).get("reason")
                ),
            )
        )
        for field in fw.get("required_evidence") or []:
            ev_id = f"evidence:{field}"
            if not any(n["id"] == ev_id for n in nodes):
                nodes.append(_node(ev_id, "evidence", str(field), present=False))
            missing = field in (fw.get("missing_evidence") or [])
            # Evidence flows into the framework that consumes it.
            edges.append(
                _edge(
                    ev_id,
                    "MISSING" if missing else "CONSUMED",
                    f_id,
                    reason=(fw.get("rejection_reasons") or {}).get(field) if missing else None,
                )
            )

    # Conflict nodes from debate.
    for i, conflict in enumerate(debate.get("conflicts") or []):
        k_id = f"conflict:{i + 1}"
        left = str(conflict.get("left") or "")
        right = str(conflict.get("right") or "")
        nodes.append(
            _node(
                k_id,
                "conflict",
                f"{left} vs {right}",
                conflict_type=conflict.get("type"),
                explanation=conflict.get("explanation"),
                evidence_shown=conflict.get("evidence_shown"),
            )
        )
        for side in (left, right):
            f_id = f"framework:{side}"
            if any(n["id"] == f_id for n in nodes):
                edges.append(_edge(f_id, "CONFLICTS_WITH", k_id))
            else:
                # Author-level conflict — attach to applicability as the reasoning origin
                a_id = f"author:{side}"
                if not any(n["id"] == a_id for n in nodes):
                    nodes.append(_node(a_id, "framework", side, author=side, status="mental_model"))
                    edges.append(_edge(app_id, "SELECTED", a_id, reason="author mental model"))
                edges.append(_edge(a_id, "CONFLICTS_WITH", k_id))

    # Decision policy node.
    policy = debate.get("policy") or (iki.get("decision_policy") or {})
    p_id = "decision_policy"
    nodes.append(
        _node(
            p_id,
            "decision_policy",
            f"{qtype} policy",
            weights=(policy or {}).get("weights"),
            dominant_lens=debate.get("dominant_lens"),
            dominant_framework=debate.get("dominant_framework"),
        )
    )
    # Spine edge: the policy always descends from applicability, so the
    # conclusion stays traceable to the question even when no framework ran.
    edges.append(_edge(app_id, "WEIGHTED_BY", p_id, reason="policy_applies_to_scored_frameworks"))
    for n in list(nodes):
        if n["kind"] == "conflict":
            edges.append(_edge(n["id"], "WEIGHTED_BY", p_id))
    executed_ids = [
        f"framework:{fw.get('framework_id')}"
        for fw in frameworks
        if fw.get("status") == "executed"
    ]
    for f_id in executed_ids:
        edges.append(_edge(f_id, "WEIGHTED_BY", p_id))

    # Committee node.
    com_id = "committee"
    nodes.append(
        _node(
            com_id,
            "committee",
            str(committee.get("stance") or "no stance"),
            executed_count=committee.get("executed_count"),
            insufficient_count=committee.get("insufficient_count"),
            not_applicable_count=committee.get("not_applicable_count"),
            can_conclude=committee.get("can_conclude"),
            disagreements=committee.get("disagreements"),
        )
    )
    edges.append(_edge(p_id, "SUPPORTS", com_id))

    # Blocked frameworks reach the committee as withholding reasons, so a gated
    # conclusion is traceable to the specific evidence that was absent.
    for fw in frameworks:
        status = fw.get("status")
        if status not in {"insufficient_evidence", "not_applicable"}:
            continue
        f_id = f"framework:{fw.get('framework_id')}"
        edges.append(
            _edge(
                f_id,
                "WITHHOLDS",
                com_id,
                reason=(
                    ", ".join(fw.get("missing_evidence") or [])
                    or (fw.get("outputs") or {}).get("reason")
                ),
                status=status,
            )
        )

    # Conclusion node.
    concl_id = "conclusion"
    gated = not bool(record.get("narrative_allowed"))
    nodes.append(
        _node(
            concl_id,
            "conclusion",
            str(committee.get("conclusion") or "")[:400],
            gated=gated,
            editorial_mode=record.get("editorial_mode"),
            missing_evidence=record.get("missing_evidence") or [],
            stance=committee.get("stance"),
        )
    )
    edges.append(
        _edge(
            com_id,
            "WITHHOLDS" if gated else "CONCLUDES",
            concl_id,
            reason="contract_incomplete" if gated else "frameworks_executed",
        )
    )

    return _finalize(nodes, edges, record=record, terminal=concl_id)


def _finalize(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    record: dict[str, Any],
    terminal: str,
) -> dict[str, Any]:
    graph = {
        "djg_version": DJG_VERSION,
        "run_id": record.get("run_id"),
        "question_type": record.get("question_type"),
        "path": record.get("path"),
        "nodes": nodes,
        "edges": edges,
        "terminal": terminal,
        "node_kinds": sorted({n["kind"] for n in nodes}),
        "edge_kinds": sorted({e["kind"] for e in edges}),
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "frameworks": len([n for n in nodes if n["kind"] == "framework"]),
            "evidence": len([n for n in nodes if n["kind"] == "evidence"]),
            "conflicts": len([n for n in nodes if n["kind"] == "conflict"]),
        },
    }
    graph["integrity"] = validate_graph(graph)
    return graph


# ---------------------------------------------------------------------------
# Traversal / integrity
# ---------------------------------------------------------------------------


def _incoming(graph: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    return [e for e in graph.get("edges") or [] if e["target"] == node_id]


def _outgoing(graph: dict[str, Any], node_id: str) -> list[dict[str, Any]]:
    return [e for e in graph.get("edges") or [] if e["source"] == node_id]


def node_by_id(graph: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for n in graph.get("nodes") or []:
        if n["id"] == node_id:
            return n
    return None


def ancestors(graph: dict[str, Any], node_id: str, *, max_depth: int = 12) -> list[str]:
    """All nodes that feed into node_id (breadth-first, cycle-safe)."""
    seen: set[str] = set()
    frontier = [node_id]
    depth = 0
    while frontier and depth < max_depth:
        nxt: list[str] = []
        for nid in frontier:
            for e in _incoming(graph, nid):
                src = e["source"]
                if src not in seen:
                    seen.add(src)
                    nxt.append(src)
        frontier = nxt
        depth += 1
    return sorted(seen)


def why(graph: dict[str, Any], node_id: str = "conclusion") -> dict[str, Any]:
    """Machine-readable justification for one node."""
    node = node_by_id(graph, node_id)
    if not node:
        return {"found": False, "node_id": node_id}
    supports = _incoming(graph, node_id)
    chain = ancestors(graph, node_id)
    return {
        "found": True,
        "node": node,
        "supported_by": [
            {
                "source": e["source"],
                "kind": e["kind"],
                "reason": (e.get("attrs") or {}).get("reason"),
            }
            for e in supports
        ],
        "reasoning_chain": chain,
        "evidence_used": [
            n["id"]
            for n in graph.get("nodes") or []
            if n["kind"] == "evidence" and n["id"] in chain and (n.get("attrs") or {}).get("present")
        ],
        "evidence_missing": [
            n["id"]
            for n in graph.get("nodes") or []
            if n["kind"] == "evidence"
            and n["id"] in chain
            and not (n.get("attrs") or {}).get("present")
        ],
        "frameworks_in_path": [
            n["id"] for n in graph.get("nodes") or [] if n["kind"] == "framework" and n["id"] in chain
        ],
    }


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """AGIB self-check: an ungated conclusion must trace to executed frameworks
    and present evidence. Orphan nodes and dangling edges are defects.
    """
    problems: list[str] = []
    node_ids = {n["id"] for n in graph.get("nodes") or []}

    for e in graph.get("edges") or []:
        if e["source"] not in node_ids:
            problems.append(f"dangling_edge_source:{e['source']}")
        if e["target"] not in node_ids:
            problems.append(f"dangling_edge_target:{e['target']}")

    terminal = str(graph.get("terminal") or "conclusion")
    concl = node_by_id(graph, terminal)
    if not concl:
        problems.append("missing_conclusion_node")
        return {
            "valid": False,
            "problems": problems,
            "explainable": False,
        }

    chain = ancestors(graph, terminal)
    if "question" not in chain and graph.get("path") != "education":
        problems.append("conclusion_not_traceable_to_question")

    gated = bool((concl.get("attrs") or {}).get("gated"))
    executed = [
        n
        for n in graph.get("nodes") or []
        if n["kind"] == "framework" and (n.get("attrs") or {}).get("status") == "executed"
    ]
    present_evidence = [
        n
        for n in graph.get("nodes") or []
        if n["kind"] == "evidence" and (n.get("attrs") or {}).get("present")
    ]

    if not gated and graph.get("path") == "research":
        if not executed:
            problems.append("ungated_conclusion_without_executed_framework")
        if not present_evidence:
            problems.append("ungated_conclusion_without_present_evidence")

    # A withheld conclusion must be traceable to a concrete withholding reason.
    if gated and graph.get("path") == "research":
        withheld_reasons = [
            e
            for e in graph.get("edges") or []
            if e["kind"] == "WITHHOLDS" and (e.get("attrs") or {}).get("reason")
        ]
        if not withheld_reasons:
            problems.append("gated_conclusion_without_withholding_reason")

    # Conflicts must carry explanations (Phase 3 requirement).
    for n in graph.get("nodes") or []:
        if n["kind"] == "conflict" and not (n.get("attrs") or {}).get("explanation"):
            problems.append(f"unexplained_conflict:{n['id']}")

    orphans = [
        n["id"]
        for n in graph.get("nodes") or []
        if n["id"] != "question"
        and not _incoming(graph, n["id"])
        and not _outgoing(graph, n["id"])
    ]
    problems.extend(f"orphan_node:{o}" for o in orphans)

    return {
        "valid": not problems,
        "problems": problems,
        "explainable": bool(chain) and terminal in node_ids,
        "executed_frameworks": [n["id"] for n in executed],
        "present_evidence": [n["id"] for n in present_evidence],
        "gated": gated,
    }


def render_ascii(graph: dict[str, Any]) -> str:
    """Debug rendering of the justification path (for AGIB logs, not users)."""
    order = (
        "question",
        "classification",
        "entity",
        "contract",
        "applicability",
        "framework",
        "evidence",
        "conflict",
        "decision_policy",
        "committee",
        "conclusion",
    )
    lines: list[str] = ["Decision Justification Graph"]
    for kind in order:
        rows = [n for n in graph.get("nodes") or [] if n["kind"] == kind]
        if not rows:
            continue
        lines.append("        |")
        lines.append("        v")
        for n in rows[:8]:
            attrs = n.get("attrs") or {}
            suffix = ""
            if kind == "framework":
                suffix = f" [{attrs.get('status')}, applicability={attrs.get('applicability_score')}]"
            elif kind == "evidence":
                suffix = f" [{'present' if attrs.get('present') else 'missing'}]"
            elif kind == "conclusion":
                suffix = f" [{'withheld' if attrs.get('gated') else 'issued'}]"
            lines.append(f"{kind}: {n['label']}{suffix}")
    integrity = graph.get("integrity") or {}
    lines.append("")
    lines.append(f"integrity: {'valid' if integrity.get('valid') else 'defects'}")
    if integrity.get("problems"):
        lines.append(f"problems: {', '.join(integrity['problems'][:6])}")
    return "\n".join(lines)


def graph_telemetry_row(graph: dict[str, Any], *, run_id: str | None = None) -> dict[str, Any]:
    integrity = graph.get("integrity") or {}
    return {
        "run_id": run_id or graph.get("run_id"),
        "djg_version": graph.get("djg_version"),
        "node_count": (graph.get("counts") or {}).get("nodes"),
        "edge_count": (graph.get("counts") or {}).get("edges"),
        "framework_count": (graph.get("counts") or {}).get("frameworks"),
        "evidence_count": (graph.get("counts") or {}).get("evidence"),
        "conflict_count": (graph.get("counts") or {}).get("conflicts"),
        "integrity_valid": integrity.get("valid"),
        "integrity_problems": integrity.get("problems") or [],
        "gated": integrity.get("gated"),
        "terminal": graph.get("terminal"),
    }
