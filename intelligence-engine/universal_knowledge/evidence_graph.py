"""Universal Evidence Graph — merge provider results into one consumable graph.

The composer reads the graph, never individual providers. Each node carries
source, authority, confidence, freshness and the raw facts the provider returned.
"""

from __future__ import annotations

from typing import Any, Optional

from universal_knowledge.registry import DEPENDENCY_ORDER, capability


def build_evidence_graph(
    provider_results: list[Any],
    *,
    ticker: Optional[str] = None,
    family: str = "company",
) -> dict[str, Any]:
    """Collapse provider results into a role-ordered evidence graph."""
    nodes: list[dict[str, Any]] = []
    by_role: dict[str, list[dict[str, Any]]] = {role: [] for role in DEPENDENCY_ORDER}
    facts: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    why: list[str] = []
    attributions: list[dict[str, Any]] = []

    for result in provider_results or []:
        pid = getattr(result, "provider_id", None) or (result.get("provider_id") if isinstance(result, dict) else None)
        if not pid:
            continue
        ok = bool(getattr(result, "ok", False) if not isinstance(result, dict) else result.get("ok"))
        empty = bool(getattr(result, "empty", True) if not isinstance(result, dict) else result.get("empty", True))
        if not ok or empty:
            continue

        cap = capability(pid)
        role = cap.role if cap else "memory"
        summary = getattr(result, "summary", None) if not isinstance(result, dict) else result.get("summary")
        conf = getattr(result, "confidence", None) if not isinstance(result, dict) else result.get("confidence")
        result_why = list(getattr(result, "why", None) or []) if not isinstance(result, dict) else list(result.get("why") or [])
        result_facts = list(getattr(result, "facts", None) or []) if not isinstance(result, dict) else list(result.get("facts") or [])
        result_evidence = list(getattr(result, "evidence", None) or []) if not isinstance(result, dict) else list(result.get("evidence") or [])

        node = {
            "provider": pid,
            "role": role,
            "authority": cap.authority if cap else "institutional",
            "freshness": cap.freshness if cap else "batch",
            "summary": summary or "",
            "confidence": conf,
            "fact_count": len(result_facts),
            "evidence_count": len(result_evidence),
            "why": result_why[:6],
            "facts": result_facts[:20],
            "entity": ticker,
        }
        nodes.append(node)
        by_role.setdefault(role, []).append(node)
        facts.extend({**f, "provider": pid, "role": role} for f in result_facts[:20] if isinstance(f, dict))
        evidence.extend({**e, "provider": pid} for e in result_evidence[:10] if isinstance(e, dict))
        why.extend(result_why[:4])
        attributions.append(
            {
                "provider": pid,
                "role": role,
                "contribution": (summary or "")[:240],
                "evidence_count": len(result_evidence),
                "fact_count": len(result_facts),
                "confidence": conf,
                "weight": round(float(conf or 0.5), 3),
            }
        )

    # Deduplicate why lines while preserving order.
    seen: set[str] = set()
    unique_why: list[str] = []
    for line in why:
        key = str(line).strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique_why.append(line)

    return {
        "ok": True,
        "family": family,
        "entity": ticker,
        "nodes": nodes,
        "by_role": {role: by_role.get(role, []) for role in DEPENDENCY_ORDER if by_role.get(role)},
        "facts": facts,
        "evidence": evidence,
        "why": unique_why,
        "attributions": attributions,
        "node_count": len(nodes),
        "fact_count": len(facts),
        "evidence_count": len(evidence),
    }
