"""Knowledge selection for Ask and workflows."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_runtime.contradictions import list_contradictions


def select_assertions(
    pack: dict[str, Any],
    *,
    categories: list[str] | None = None,
    claim_types: list[str] | None = None,
    min_confidence: int = 0,
    include_unknowns: bool = True,
    limit: int = 20,
) -> dict[str, Any]:
    """Select relevant assertions from an IKR runtime pack."""
    assertions = pack.get("assertions") or []
    selected: list[dict[str, Any]] = []

    for a in assertions:
        if categories and str(a.get("category")) not in categories:
            continue
        if claim_types and str(a.get("claim_type")) not in claim_types:
            continue
        status = str(a.get("status") or "UNKNOWN")
        conf = int(a.get("confidence") or 0)
        if status == "UNKNOWN" and not include_unknowns:
            continue
        if status != "UNKNOWN" and conf < min_confidence:
            continue
        selected.append(a)

    selected.sort(key=lambda x: (-int(x.get("confidence") or 0), str(x.get("assertion_id") or "")))
    selected = selected[:limit]

    unknowns = pack.get("unknowns") or []
    if not include_unknowns:
        unknowns = []

    return {
        "assertions": selected,
        "evidence": {a["assertion_id"]: pack.get("evidence", {}).get(a["assertion_id"]) for a in selected if a.get("assertion_id")},
        "unknowns": unknowns,
        "contradictions": list_contradictions(assertions),
        "count": len(selected),
    }
