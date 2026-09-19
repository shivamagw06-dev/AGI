"""Fallback engine — automatic switch by authority ranking."""

from __future__ import annotations

from typing import Any

from acquisition_planner.api_registry import PROVIDERS, provider_authority_score


def build_fallback_chains(selections: list[dict[str, Any]]) -> dict[str, Any]:
    chains = []
    for sel in selections:
        primary = sel.get("primary") or {}
        fbs = sel.get("fallbacks") or []
        chain = []
        if primary.get("provider"):
            chain.append(
                {
                    "order": 1,
                    "provider": primary["provider"],
                    "name": primary.get("name"),
                    "authority_score": primary.get("authority_score"),
                    "role": "primary",
                }
            )
        for i, fb in enumerate(fbs, start=2):
            chain.append(
                {
                    "order": i,
                    "provider": fb.get("provider"),
                    "name": fb.get("name"),
                    "authority_score": fb.get("authority_score") or round(provider_authority_score(str(fb.get("provider"))), 4),
                    "role": "fallback",
                }
            )
        # ensure authority ranking (primary should be best or equal among chain start)
        ranked = sorted(chain, key=lambda x: (-(x.get("authority_score") or 0), x["order"]))
        chains.append(
            {
                "evidence_key": sel.get("evidence_key"),
                "chain": chain,
                "authority_ranked": [c["provider"] for c in ranked],
                "fallback_ready": len(chain) >= 2,
            }
        )
    success = all(c.get("fallback_ready") or (c.get("chain") and len(c["chain"]) >= 1) for c in chains) if chains else True
    return {
        "fallback_chains": chains,
        "fallback_providers": [
            {"evidence_key": c["evidence_key"], "providers": [x["provider"] for x in c["chain"][1:]]}
            for c in chains
        ],
        "fallback_coverage": success,
    }


def simulate_failover(chain: list[dict[str, Any]], unavailable: set[str]) -> dict[str, Any]:
    for item in chain:
        pid = str(item.get("provider") or "")
        if pid and pid not in unavailable and pid in PROVIDERS:
            return {"selected": pid, "success": True, "skipped_unavailable": sorted(unavailable)}
    return {"selected": None, "success": False, "skipped_unavailable": sorted(unavailable)}
