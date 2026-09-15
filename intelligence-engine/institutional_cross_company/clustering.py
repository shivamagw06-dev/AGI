"""CCI-01 Cluster Engine — deterministic institutional groupings."""

from __future__ import annotations

from typing import Any

from institutional_cross_company.models import Cluster
from institutional_cross_company.schema import ECOSYSTEMS


def build_clusters(*, kind: str = "sector") -> list[Cluster]:
    clusters: list[Cluster] = []
    for key, eco in ECOSYSTEMS.items():
        members = tuple(str(m).upper() for m in (eco.get("members") or ()))
        clusters.append(
            Cluster(
                cluster_id=f"cluster-{key}",
                label=str(eco.get("cluster") or eco.get("industry") or key),
                members=members,
                kind=kind,
            )
        )
    return clusters


def cluster_for_ticker(ticker: str) -> list[Cluster]:
    t = str(ticker or "").upper()
    return [c for c in build_clusters() if t in c.members]


def clusters_pack() -> dict[str, Any]:
    rows = build_clusters()
    return {
        "clusters": [c.to_dict() for c in rows],
        "count": len(rows),
        "kinds_available": ["sector"],
        "kinds_future": ["high_quality_compounders", "high_leverage", "turnaround", "deep_value"],
        "owns_graph": False,
    }
