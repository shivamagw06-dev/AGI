"""Cache manager — check internal intelligence before external APIs."""

from __future__ import annotations

from typing import Any

from acquisition_planner.api_registry import INTERNAL_PROVIDERS, PROVIDERS

# Simulated internal inventory for planning (soft-wire; real FIL/PIL/etc. bind later)
DEFAULT_INTERNAL_INVENTORY: dict[str, dict[str, Any]] = {
    "fil": {"available": True, "covers": ["official_filings", "quarterly_results", "historical_financials"], "age_hours": 18},
    "pil": {"available": True, "covers": ["peer_metrics"], "age_hours": 12},
    "ikg": {"available": True, "covers": ["knowledge_graph_context", "portfolio_exposure"], "age_hours": 6},
    "eil": {"available": True, "covers": ["evidence_corpus", "press_flow"], "age_hours": 4},
    "ilm": {"available": True, "covers": ["knowledge_graph_context", "portfolio_exposure"], "age_hours": 24},
}


def inspect_internal_cache(
    *,
    required_data: list[dict[str, Any]],
    freshness_plan: dict[str, Any],
    inventory: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    inv = inventory or DEFAULT_INTERNAL_INVENTORY
    max_age = float(freshness_plan.get("max_age_hours") or 24)
    required_f = str(freshness_plan.get("required_freshness") or "daily")
    per_ev = {str(p.get("evidence_key")): str(p.get("required_freshness") or required_f) for p in (freshness_plan.get("per_evidence") or [])}

    reuse: list[dict[str, Any]] = []
    miss: list[str] = []

    for item in required_data:
        key = str(item.get("evidence_key") or "")
        need_f = per_ev.get(key, required_f)
        # Live prices never reuse stale cache in V1 planning inventory
        if key == "live_prices" and need_f in {"live", "intraday"}:
            miss.append(key)
            continue

        hit = None
        for provider_id, meta in inv.items():
            if not meta.get("available"):
                continue
            if key not in (meta.get("covers") or []):
                continue
            age = float(meta.get("age_hours") or 9999)
            if need_f == "existing_knowledge":
                fresh_ok = True
            elif need_f == "live":
                fresh_ok = age <= 0.25
            elif need_f == "intraday":
                fresh_ok = age <= max(max_age, 8)
            elif need_f == "quarterly":
                fresh_ok = age <= max(max_age, 24 * 45)
            else:
                fresh_ok = age <= max_age
            if not fresh_ok:
                continue
            hit = {
                "evidence_key": key,
                "provider": provider_id,
                "provider_name": PROVIDERS.get(provider_id, {}).get("name", provider_id),
                "age_hours": age,
                "action": "reuse",
                "reason": "Valid internal intelligence within freshness policy",
            }
            break
        if hit:
            reuse.append(hit)
        else:
            miss.append(key)

    return {
        "reuse_internal_layers": reuse,
        "cache_misses": miss,
        "reuse_count": len(reuse),
        "miss_count": len(miss),
        "checked_layers": sorted(INTERNAL_PROVIDERS),
    }
