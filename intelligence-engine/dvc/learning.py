"""Provider reliability learning — adjusts confidence over time."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dvc.priority import base_confidence, provider_priority
from dvc.schema import DVC_VERSION


def empty_provider_stats(provider: str) -> Dict[str, Any]:
    return {
        "provider": provider,
        "priority": provider_priority(provider),
        "base_confidence": base_confidence(provider),
        "successes": 0,
        "failures": 0,
        "latency_ms_sum": 0.0,
        "latency_samples": 0,
        "conflicts": 0,
        "wins": 0,
        "missing_fields": 0,
        "availability_ok": 0,
        "availability_fail": 0,
        "adjusted_confidence": base_confidence(provider),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "dvc_version": DVC_VERSION,
    }


def record_fetch(
    stats: Dict[str, Any],
    *,
    ok: bool,
    latency_ms: Optional[float] = None,
    missing_fields: int = 0,
) -> Dict[str, Any]:
    out = dict(stats)
    if ok:
        out["successes"] = int(out.get("successes") or 0) + 1
        out["availability_ok"] = int(out.get("availability_ok") or 0) + 1
    else:
        out["failures"] = int(out.get("failures") or 0) + 1
        out["availability_fail"] = int(out.get("availability_fail") or 0) + 1
    if latency_ms is not None:
        out["latency_ms_sum"] = float(out.get("latency_ms_sum") or 0) + float(latency_ms)
        out["latency_samples"] = int(out.get("latency_samples") or 0) + 1
    out["missing_fields"] = int(out.get("missing_fields") or 0) + int(missing_fields or 0)
    out["adjusted_confidence"] = compute_adjusted_confidence(out)
    out["updated_at"] = datetime.now(timezone.utc).isoformat()
    return out


def record_consensus_outcome(
    stats: Dict[str, Any],
    *,
    won: bool,
    conflicted: bool,
) -> Dict[str, Any]:
    out = dict(stats)
    if won:
        out["wins"] = int(out.get("wins") or 0) + 1
    if conflicted:
        out["conflicts"] = int(out.get("conflicts") or 0) + 1
    out["adjusted_confidence"] = compute_adjusted_confidence(out)
    out["updated_at"] = datetime.now(timezone.utc).isoformat()
    return out


def compute_adjusted_confidence(stats: Dict[str, Any]) -> float:
    base = float(stats.get("base_confidence") or base_confidence(str(stats.get("provider") or "")))
    successes = int(stats.get("successes") or 0)
    failures = int(stats.get("failures") or 0)
    total = successes + failures
    if total == 0:
        return round(base, 4)
    success_rate = successes / total
    wins = int(stats.get("wins") or 0)
    conflicts = int(stats.get("conflicts") or 0)
    win_rate = wins / max(1, wins + conflicts) if (wins + conflicts) else 0.5
    # Blend: base * 0.5 + success * 0.3 + win_rate * 0.2
    adj = base * 0.5 + success_rate * 0.3 + win_rate * 0.2
    # Cap within [0.35, 0.995]
    return round(max(0.35, min(0.995, adj)), 4)


def provider_health_row(stats: Dict[str, Any]) -> Dict[str, Any]:
    successes = int(stats.get("successes") or 0)
    failures = int(stats.get("failures") or 0)
    total = successes + failures
    samples = int(stats.get("latency_samples") or 0)
    avg_lat = (float(stats.get("latency_ms_sum") or 0) / samples) if samples else None
    return {
        "provider": stats.get("provider"),
        "priority": stats.get("priority"),
        "uptime_pct": round(100.0 * successes / total, 2) if total else None,
        "failure_rate": round(failures / total, 4) if total else 0.0,
        "avg_latency_ms": round(avg_lat, 2) if avg_lat is not None else None,
        "conflicts": int(stats.get("conflicts") or 0),
        "wins": int(stats.get("wins") or 0),
        "missing_fields": int(stats.get("missing_fields") or 0),
        "adjusted_confidence": float(stats.get("adjusted_confidence") or 0),
        "updated_at": stats.get("updated_at"),
    }
