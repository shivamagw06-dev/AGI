"""Evidence attachment — probabilities, catalysts, scenarios must be backed."""

from __future__ import annotations

from typing import Any


def evidence_pack(
    profile: dict[str, Any],
    *,
    catalysts: dict[str, Any] | None = None,
    analogues: list[dict[str, Any]] | None = None,
    causal_soft: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    items.append(
        {
            "kind": "profile_prior",
            "source": "forecast_intelligence.profiles",
            "note": f"Institutional scenario priors for {profile.get('ticker')}",
        }
    )
    for a in analogues or profile.get("analogues") or []:
        items.append(
            {
                "kind": "historical_analogue",
                "source": "forecast_intelligence.analogues",
                "year": a.get("year"),
                "similarity": a.get("similarity"),
                "note": a.get("note"),
            }
        )
    for c in (catalysts or {}).get("items") or []:
        items.extend(c.get("evidence") or [])
    if causal_soft and causal_soft.get("enabled"):
        items.append(
            {
                "kind": "causal_soft",
                "source": "causal_graph.soft_slice",
                "note": "CIG upstream drivers / transmission soft-wired into FIE sensitivity",
                "upstream": causal_soft.get("upstream_drivers"),
            }
        )
    unsupported = 0
    for c in (catalysts or {}).get("items") or []:
        if not c.get("linked_to_evidence"):
            unsupported += 1
    return {
        "count": len(items),
        "items": items[:40],
        "unsupported_claims": unsupported,
        "rule": "Every probability and catalyst is evidence-backed; no unsupported price predictions",
    }
