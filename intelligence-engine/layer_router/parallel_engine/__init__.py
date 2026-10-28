"""Identify parallel execution groups among independent layers."""

from __future__ import annotations

from typing import Any

from layer_router.registry import LAYER_DEFS


def build_parallel_groups(
    execution_order: list[str],
    dependency_edges: list[dict[str, str]],
) -> dict[str, Any]:
    preds: dict[str, set[str]] = {p: set() for p in execution_order}
    for e in dependency_edges:
        if e["from"] in preds and e["to"] in preds:
            preds[e["to"]].add(e["from"])

    # Levelize: level = 1 + max(pred levels)
    level: dict[str, int] = {}
    for node in execution_order:
        if not preds[node]:
            level[node] = 0
        else:
            level[node] = 1 + max(level.get(p, 0) for p in preds[node])

    groups_map: dict[int, list[str]] = {}
    for node, lv in level.items():
        groups_map.setdefault(lv, []).append(node)

    parallel_groups = []
    for lv in sorted(groups_map):
        members = groups_map[lv]
        # Prefer registry parallel_group labels when same level
        parallel_groups.append(
            {
                "level": lv,
                "layers": members,
                "parallel": len(members) > 1,
                "registry_groups": sorted(
                    {
                        (LAYER_DEFS.get(m) or {}).get("parallel_group") or "?"
                        for m in members
                    }
                ),
            }
        )

    parallelizable = sum(1 for g in parallel_groups if g["parallel"])
    return {
        "parallel_groups": parallel_groups,
        "parallel_group_count": len(parallel_groups),
        "parallelizable_levels": parallelizable,
        "max_width": max((len(g["layers"]) for g in parallel_groups), default=1),
    }
