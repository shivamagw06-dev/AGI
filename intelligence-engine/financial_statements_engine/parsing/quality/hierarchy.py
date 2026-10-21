"""Hierarchical statement tree — preserve parent/child before flattening."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def build_statement_tree(
    fields: dict[str, Any],
    *,
    sections: list[str] | None = None,
    mapped_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a queryable hierarchy from extracted labels.

    If labels contain nested hints (e.g. 'Revenue > Domestic'), preserve chain.
    Otherwise group under detected sections. Flattened canonical metrics link via ``canonical``.
    """
    mapped_metrics = mapped_metrics or {}
    # Invert source_field → canonical
    source_to_canon = {}
    for canon, row in mapped_metrics.items():
        if isinstance(row, dict) and row.get("source_field"):
            source_to_canon[str(row["source_field"])] = canon

    roots: list[dict[str, Any]] = []
    section_nodes: dict[str, dict[str, Any]] = {}
    for sec in sections or ["unknown"]:
        node = {"label": sec, "canonical": None, "value": None, "children": [], "node_type": "section"}
        section_nodes[sec] = node
        roots.append(node)

    default_section = roots[0] if roots else {
        "label": "unknown",
        "canonical": None,
        "value": None,
        "children": [],
        "node_type": "section",
    }
    if not roots:
        roots.append(default_section)

    for label, payload in (fields or {}).items():
        parts = [p.strip() for p in str(label).split(">") if p.strip()]
        if len(parts) == 1:
            # Also support " / " nesting
            parts = [p.strip() for p in str(label).split("/") if p.strip()] if "/" in str(label) else parts

        value = payload.get("value") if isinstance(payload, dict) else payload
        parent = default_section
        # Attach income-ish labels under income_statement when present
        lab_l = str(label).lower()
        for sec_name, sec_node in section_nodes.items():
            if sec_name == "income_statement" and any(k in lab_l for k in ("revenue", "profit", "income", "pat", "ebit")):
                parent = sec_node
                break
            if sec_name == "balance_sheet" and any(k in lab_l for k in ("asset", "liabilit", "equity", "cash", "inventory")):
                parent = sec_node
                break
            if sec_name == "cash_flow" and any(k in lab_l for k in ("operating", "investing", "financing", "cash flow")):
                parent = sec_node
                break

        cursor = parent
        for i, part in enumerate(parts):
            existing = next((c for c in cursor["children"] if c.get("label") == part), None)
            if existing is None:
                existing = {
                    "label": part,
                    "canonical": source_to_canon.get(label) if i == len(parts) - 1 else source_to_canon.get(part),
                    "value": value if i == len(parts) - 1 else None,
                    "children": [],
                    "node_type": "metric" if i == len(parts) - 1 else "group",
                    "source_field": label if i == len(parts) - 1 else None,
                }
                cursor["children"].append(existing)
            elif i == len(parts) - 1:
                existing["value"] = value
                existing["canonical"] = source_to_canon.get(label)
                existing["source_field"] = label
            cursor = existing

    fingerprint = hashlib.sha256(
        json.dumps(_strip_for_fp(roots), sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    return {
        "statement_tree": roots,
        "hierarchy_fingerprint": fingerprint,
        "flattening_destroys_hierarchy": False,
        "layer": "hierarchical_statement_tree",
    }


def _strip_for_fp(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for n in nodes:
        out.append(
            {
                "label": n.get("label"),
                "canonical": n.get("canonical"),
                "value": n.get("value"),
                "children": _strip_for_fp(n.get("children") or []),
            }
        )
    return out


def hierarchy_preserved(tree: dict[str, Any]) -> bool:
    """True if tree exists and flattening flag is false."""
    return bool(tree.get("statement_tree")) and tree.get("flattening_destroys_hierarchy") is False
