"""IEG Mission Control soft board."""

from __future__ import annotations

from typing import Any

from institutional_evidence_graph.schema import ENTITY_DOMAINS, IEG_VERSION, MODULE_CODE, PROGRAMME
from institutional_evidence_graph import store


def evidence_graph_dashboard() -> dict[str, Any]:
    recent = store.list_rows(limit=20)
    avg_cov = 0
    if recent:
        avg_cov = int(
            round(sum(int(r.get("domain_coverage_pct") or 0) for r in recent) / len(recent))
        )
    return {
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "ieg_version": IEG_VERSION,
        "entity_domains": list(ENTITY_DOMAINS),
        "n_domains": len(ENTITY_DOMAINS),
        "recent_n": len(recent),
        "recent_graphs": recent,
        "avg_domain_coverage_pct": avg_cov,
        "soft_wire_only": True,
        "guides_evidence": True,
        "fabricated": False,
    }
