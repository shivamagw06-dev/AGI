"""DVC validation orchestration — multi-provider sample → consensus → quality."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dvc.conflicts import conflict_summary, detect_conflicts
from dvc.consensus import consensus_for_field
from dvc.learning import record_consensus_outcome, record_fetch
from dvc.priority import provider_priority
from dvc.quality import compute_quality, grade_from_quality, missing_fields
from dvc.schema import DVC_VERSION, FUNDAMENTAL_FIELDS, QUOTE_FIELDS
from dvc import store as dvc_store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_quote_obs(provider_id: str, quote: Any) -> Dict[str, Any]:
    data = quote.model_dump(mode="json") if hasattr(quote, "model_dump") else dict(quote or {})
    out: Dict[str, Any] = {}
    for field in QUOTE_FIELDS:
        if data.get(field) is not None:
            out[field] = {
                "provider": provider_id,
                "value": data.get(field),
                "timestamp": (data.get("provenance") or {}).get("pulled_at") or _now(),
            }
    # Alias common names
    if data.get("last") is None and data.get("price") is not None:
        out["last"] = {"provider": provider_id, "value": data.get("price"), "timestamp": _now()}
    return out


def _extract_fund_obs(provider_id: str, fund: Any) -> Dict[str, Any]:
    data = fund.model_dump(mode="json") if hasattr(fund, "model_dump") else dict(fund or {})
    metrics = data.get("metrics") if isinstance(data.get("metrics"), dict) else data
    out: Dict[str, Any] = {}
    for field in FUNDAMENTAL_FIELDS:
        if metrics.get(field) is not None:
            out[field] = {
                "provider": provider_id,
                "value": metrics.get(field),
                "timestamp": (data.get("provenance") or {}).get("pulled_at") or _now(),
            }
    return out


async def _sample_providers(
    client: Any,
    symbol: str,
    *,
    capability: str,
) -> tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """Sample all configured providers for a capability; return observations + fetch meta."""
    providers = list(client.registry.providers_for(capability))  # type: ignore[attr-defined]
    # Sort by DVC priority (not just registry order)
    providers = sorted(providers, key=lambda p: provider_priority(p.provider_id))
    observations: Dict[str, List[Dict[str, Any]]] = {}
    meta: Dict[str, Any] = {"providers_tried": [], "errors": {}}

    for provider in providers:
        pid = provider.provider_id
        meta["providers_tried"].append(pid)
        t0 = time.perf_counter()
        stats = dvc_store.get_provider_stats(pid)
        try:
            if capability == "quote":
                result = await provider.get_quote(symbol)
                field_obs = _extract_quote_obs(pid, result)
            else:
                result = await provider.get_fundamentals(symbol)
                field_obs = _extract_fund_obs(pid, result)
            latency = (time.perf_counter() - t0) * 1000.0
            missing_n = 0
            expected = QUOTE_FIELDS if capability == "quote" else FUNDAMENTAL_FIELDS
            for f in expected:
                if f not in field_obs:
                    missing_n += 1
            stats = record_fetch(stats, ok=True, latency_ms=latency, missing_fields=missing_n)
            dvc_store.save_provider_stats(stats)
            for field, obs in field_obs.items():
                observations.setdefault(field, []).append({**obs, "latency_ms": latency})
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - t0) * 1000.0
            stats = record_fetch(stats, ok=False, latency_ms=latency)
            dvc_store.save_provider_stats(stats)
            meta["errors"][pid] = str(exc)[:200]
    return observations, meta


def build_consensus_package(
    symbol: str,
    observations_by_field: Dict[str, List[Dict[str, Any]]],
    *,
    kind: str = "combined",
    previous_package: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run consensus + conflicts + quality for a set of field observations."""
    prev_fields = dict((previous_package or {}).get("validated_fields") or {})
    validated: Dict[str, Any] = {}
    winner_counts: Dict[str, int] = {}

    for field, obs in observations_by_field.items():
        prev_val = None
        old = prev_fields.get(field)
        if isinstance(old, dict):
            prev_val = old.get("value")
        vf = consensus_for_field(field, obs, symbol=symbol, previous_value=prev_val)
        # Prefer adjusted learning confidence when available
        try:
            stats = dvc_store.get_provider_stats(str(vf.get("provider") or ""))
            adj = float(stats.get("adjusted_confidence") or 0)
            if adj and vf.get("value") is not None:
                # Soft blend learned reliability into field confidence
                vf = dict(vf)
                vf["confidence"] = round(min(0.995, (float(vf.get("confidence") or 0) * 0.7) + (adj * 0.3)), 4)
        except Exception:
            pass
        # Preserve consensus history
        if isinstance(old, dict):
            history = list(old.get("consensus_history") or [])
            history.append(
                {
                    "at": vf.get("verified_at"),
                    "value": vf.get("value"),
                    "provider": vf.get("provider"),
                    "confidence": vf.get("confidence"),
                }
            )
            vf["consensus_history"] = history[-30:]
        validated[field] = vf
        wp = str(vf.get("provider") or "")
        if wp and vf.get("value") is not None:
            winner_counts[wp] = winner_counts.get(wp, 0) + 1

        # Learning: win / conflict outcomes
        for o in obs:
            pid = str(o.get("provider") or "")
            if not pid:
                continue
            stats = dvc_store.get_provider_stats(pid)
            won = pid == wp
            conflicted = pid in (vf.get("rejected_providers") or [])
            stats = record_consensus_outcome(stats, won=won, conflicted=conflicted)
            dvc_store.save_provider_stats(stats)

    conflicts = detect_conflicts(observations_by_field, company_id=symbol)
    quality = compute_quality(
        validated,
        conflicts=conflicts,
        observations_by_field=observations_by_field,
        kind=kind,
    )
    grades = grade_from_quality(quality)
    missing = missing_fields(validated)
    needs_refresh = float(quality.get("freshness") or 0) < 0.85 or float(quality.get("coverage") or 0) < 0.85
    winning_summary = sorted(winner_counts.items(), key=lambda x: (-x[1], provider_priority(x[0])))
    top_winner = winning_summary[0][0] if winning_summary else None

    package = {
        "company_id": symbol.upper(),
        "symbol": symbol.upper(),
        "validated_fields": validated,
        "conflicts": conflicts,
        "conflict_summary": conflict_summary(conflicts),
        "quality": quality,
        "grades": grades,
        "missing_fields": missing,
        "needs_refresh": needs_refresh,
        "recommended_refresh": "multi_provider_resync" if needs_refresh else None,
        "winning_provider_summary": top_winner,
        "provider_win_counts": dict(winner_counts),
        "kind": kind,
        "validated_at": _now(),
        "dvc_version": DVC_VERSION,
        "self_healing": {
            "higher_priority_available": False,
            "action": None,
        },
    }
    return package


async def validate_symbol(
    client: Any,
    symbol: str,
    *,
    include_quote: bool = True,
    include_fundamentals: bool = True,
    persist: bool = True,
) -> Dict[str, Any]:
    """Full DVC validation for a symbol via MarketDataClient provider registry."""
    sym = (symbol or "").strip().upper()
    if not sym:
        return {"enabled": False, "reason": "no_symbol", "dvc_version": DVC_VERSION}

    observations: Dict[str, List[Dict[str, Any]]] = {}
    fetch_meta: Dict[str, Any] = {"quote": {}, "fundamentals": {}}

    if include_quote:
        q_obs, q_meta = await _sample_providers(client, sym, capability="quote")
        for k, v in q_obs.items():
            observations.setdefault(k, []).extend(v)
        fetch_meta["quote"] = q_meta

    if include_fundamentals:
        f_obs, f_meta = await _sample_providers(client, sym, capability="fundamental")
        for k, v in f_obs.items():
            observations.setdefault(k, []).extend(v)
        fetch_meta["fundamentals"] = f_meta

    prev = dvc_store.get_company(sym)
    kind = "combined" if include_quote and include_fundamentals else ("quote" if include_quote else "fundamentals")
    package = build_consensus_package(sym, observations, kind=kind, previous_package=prev)
    package["fetch_meta"] = fetch_meta

    # Self-healing signal: if a higher-priority provider succeeded after a lower one won previously
    if prev and package.get("winning_provider_summary"):
        old_w = prev.get("winning_provider_summary")
        new_w = package.get("winning_provider_summary")
        if old_w and new_w and provider_priority(str(new_w)) < provider_priority(str(old_w)):
            package["self_healing"] = {
                "higher_priority_available": True,
                "action": "auto_refresh_consensus",
                "from_provider": old_w,
                "to_provider": new_w,
            }

    if persist:
        try:
            package = dvc_store.upsert_company_validation(sym, package)
        except Exception as exc:  # noqa: BLE001
            dvc_store.record_validation_error(sym, "persist_failed", str(exc)[:200])

    return {"enabled": True, "dvc_version": DVC_VERSION, **package}


def ask_agi_hints(package: Dict[str, Any]) -> List[str]:
    """Soft hints for Ask AGI when conflicts / quality issues exist."""
    hints: List[str] = []
    if not package or not package.get("enabled", True):
        return hints
    conflicts = package.get("conflicts") or []
    for c in conflicts[:3]:
        if not isinstance(c, dict):
            continue
        field = c.get("field")
        winner = c.get("winning_provider")
        sev = c.get("severity")
        if field == "market_cap":
            hints.append(
                f"Market capitalisation differs across providers. AGI currently uses {winner} "
                f"as the canonical source while monitoring discrepancies (severity={sev})."
            )
        elif field == "last":
            hints.append(
                f"Current price shows provider disagreement. Canonical value from {winner} "
                f"(severity={sev})."
            )
        else:
            hints.append(
                f"Field '{field}' differs across providers. Canonical source: {winner} "
                f"(severity={sev})."
            )
    grades = package.get("grades") or {}
    q = package.get("quality") or {}
    if grades.get("institutional"):
        hints.append(
            f"Data quality institutional — overall {round(float(q.get('overall') or 0) * 100)}% "
            f"(coverage {round(float(q.get('coverage') or 0) * 100)}%, "
            f"confidence {round(float(q.get('confidence') or 0) * 100)}%)."
        )
    elif q.get("overall") is not None:
        hints.append(
            f"Data Grade {grades.get('data_grade')} — overall "
            f"{round(float(q.get('overall') or 0) * 100)}%. "
            f"Missing: {', '.join((package.get('missing_fields') or [])[:5]) or 'none'}."
        )
    if package.get("self_healing", {}).get("higher_priority_available"):
        sh = package["self_healing"]
        hints.append(
            f"Self-healing: higher-priority provider {sh.get('to_provider')} refreshed consensus "
            f"(was {sh.get('from_provider')})."
        )
    return hints[:6]


def panel_for_company(package: Dict[str, Any]) -> Dict[str, Any]:
    """Internal company-page data quality panel payload."""
    q = package.get("quality") or {}
    grades = package.get("grades") or {}
    fields = package.get("validated_fields") or {}
    providers = sorted(
        {
            str(vf.get("provider"))
            for vf in fields.values()
            if isinstance(vf, dict) and vf.get("provider") and vf.get("value") is not None
        },
        key=provider_priority,
    )
    return {
        "research_grade": grades.get("research_grade"),
        "knowledge_grade": grades.get("knowledge_grade"),
        "data_grade": grades.get("data_grade"),
        "institutional": bool(grades.get("institutional")),
        "coverage": q.get("coverage"),
        "freshness": q.get("freshness"),
        "confidence": q.get("confidence"),
        "consistency": q.get("consistency"),
        "provider_agreement": q.get("provider_agreement"),
        "validation": q.get("validation"),
        "overall": q.get("overall"),
        "provider_sources": providers,
        "missing_information": package.get("missing_fields") or [],
        "recommended_refresh": package.get("recommended_refresh"),
        "conflicts_open": (package.get("conflict_summary") or {}).get("open", 0),
        "winning_provider": package.get("winning_provider_summary"),
        "dvc_version": DVC_VERSION,
    }
