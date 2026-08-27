"""Provider selector — best provider, fallbacks, authority, freshness, latency."""

from __future__ import annotations

from typing import Any

from acquisition_planner.api_registry import PROVIDERS, provider_authority_score


def _supports_need(provider: dict[str, Any], data_types: list[str]) -> bool:
    supports = set(provider.get("supports") or [])
    return any(dt in supports for dt in data_types)


def select_providers_for_evidence(
    *,
    evidence_item: dict[str, Any],
    min_authority_tier: int = 2,
    skip_providers: set[str] | None = None,
) -> dict[str, Any]:
    skip = skip_providers or set()
    preferred = list(evidence_item.get("preferred_providers") or [])
    data_types = list(evidence_item.get("data_types") or [])
    min_tier = int(evidence_item.get("min_tier") or min_authority_tier)

    candidates: list[dict[str, Any]] = []
    for pid, meta in PROVIDERS.items():
        if pid in skip:
            continue
        if meta.get("internal"):
            continue  # internals handled by cache reuse
        if meta.get("tier", 5) > min_tier and pid not in preferred:
            # still allow preferred even if slightly lower? keep strict for authority compliance
            if meta.get("tier", 5) > max(min_tier, min_authority_tier):
                continue
        if not _supports_need(meta, data_types) and pid not in preferred:
            continue
        score = provider_authority_score(pid)
        # boost preferred order
        prefer_boost = 0.0
        if pid in preferred:
            prefer_boost = 0.15 * (1.0 - preferred.index(pid) / max(len(preferred), 1))
        # prefer lower cost & latency
        cost_pen = float(meta.get("cost") or 1) * 0.02
        lat_pen = float(meta.get("latency_ms") or 100) / 10000.0
        total = score + prefer_boost - cost_pen - lat_pen
        candidates.append(
            {
                "provider": pid,
                "name": meta["name"],
                "tier": meta["tier"],
                "authority_score": round(score, 4),
                "freshness": meta.get("freshness"),
                "expected_latency_ms": meta.get("latency_ms"),
                "cost": meta.get("cost"),
                "reliability": meta.get("reliability"),
                "selection_score": round(total, 4),
                "fallback_providers": list(meta.get("fallback_providers") or []),
            }
        )

    # ensure preferred providers that support types are considered
    for pid in preferred:
        if pid in skip or pid in {c["provider"] for c in candidates}:
            continue
        meta = PROVIDERS.get(pid)
        if not meta or meta.get("internal"):
            continue
        if meta.get("tier", 5) > max(min_tier, min_authority_tier):
            continue
        score = provider_authority_score(pid)
        candidates.append(
            {
                "provider": pid,
                "name": meta["name"],
                "tier": meta["tier"],
                "authority_score": round(score, 4),
                "freshness": meta.get("freshness"),
                "expected_latency_ms": meta.get("latency_ms"),
                "cost": meta.get("cost"),
                "reliability": meta.get("reliability"),
                "selection_score": round(score + 0.2, 4),
                "fallback_providers": list(meta.get("fallback_providers") or []),
            }
        )

    candidates.sort(key=lambda c: (-c["selection_score"], c["tier"], c["cost"]))
    if not candidates:
        return {
            "evidence_key": evidence_item.get("evidence_key"),
            "primary": None,
            "fallbacks": [],
            "skipped": sorted(skip),
            "reason": "No compliant provider for evidence need",
        }

    primary = candidates[0]
    fallbacks = []
    # chain: remaining candidates + declared fallbacks
    seen = {primary["provider"]}
    for c in candidates[1:]:
        if c["provider"] in seen:
            continue
        seen.add(c["provider"])
        fallbacks.append(c)
    for fb in primary.get("fallback_providers") or []:
        if fb in seen or fb in skip:
            continue
        meta = PROVIDERS.get(fb)
        if not meta or meta.get("internal"):
            continue
        if meta.get("tier", 5) > max(min_tier, min_authority_tier):
            continue
        seen.add(fb)
        fallbacks.append(
            {
                "provider": fb,
                "name": meta["name"],
                "tier": meta["tier"],
                "authority_score": round(provider_authority_score(fb), 4),
                "freshness": meta.get("freshness"),
                "expected_latency_ms": meta.get("latency_ms"),
                "cost": meta.get("cost"),
                "reliability": meta.get("reliability"),
                "selection_score": round(provider_authority_score(fb), 4),
                "fallback_providers": list(meta.get("fallback_providers") or []),
            }
        )

    return {
        "evidence_key": evidence_item.get("evidence_key"),
        "label": evidence_item.get("label"),
        "primary": primary,
        "fallbacks": fallbacks[:4],
        "authority_compliant": primary["tier"] <= max(min_tier, min_authority_tier),
        "research_purpose": evidence_item.get("research_purpose"),
    }
