"""CAE store — packages, cache, metrics, audit."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.cae.config import CACHE_TTL_SECONDS
from app.cae.models import AuditEntry, CacheEntry, ContextPackage


@dataclass
class CaeMetrics:
    assemblies: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_assembly_latency_ms: float = 0.0
    last_assembly_latency_ms: float = 0.0
    avg_context_tokens: float = 0.0
    avg_duplicates_removed: float = 0.0
    avg_compression_ratio: float = 1.0
    retrieval_failures: int = 0
    token_savings_estimate: float = 0.0

    _latency_sum: float = field(default=0.0, repr=False)
    _token_sum: float = field(default=0.0, repr=False)
    _dup_sum: float = field(default=0.0, repr=False)
    _comp_sum: float = field(default=0.0, repr=False)

    def observe(self, package: ContextPackage) -> None:
        self.assemblies += 1
        self.last_assembly_latency_ms = package.assembly_latency_ms
        self._latency_sum += package.assembly_latency_ms
        tokens = float((package.token_usage or {}).get("total_estimate") or 0)
        self._token_sum += tokens
        self._dup_sum += package.duplicates_removed
        self._comp_sum += package.compression_ratio
        n = max(1, self.assemblies)
        self.avg_assembly_latency_ms = round(self._latency_sum / n, 2)
        self.avg_context_tokens = round(self._token_sum / n, 2)
        self.avg_duplicates_removed = round(self._dup_sum / n, 2)
        self.avg_compression_ratio = round(self._comp_sum / n, 4)
        if package.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        # Rough savings vs unranked multi-engine dump (~2.2x raw)
        raw = tokens / max(0.2, package.compression_ratio)
        self.token_savings_estimate = round(max(0.0, raw - tokens), 2)

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        total = self.cache_hits + self.cache_misses
        return {
            "assemblies": self.assemblies,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hits / total, 4) if total else 0.0,
            "avg_assembly_latency_ms": self.avg_assembly_latency_ms,
            "last_assembly_latency_ms": self.last_assembly_latency_ms,
            "avg_context_tokens": self.avg_context_tokens,
            "avg_duplicates_removed": self.avg_duplicates_removed,
            "avg_compression_ratio": self.avg_compression_ratio,
            "retrieval_failures": self.retrieval_failures,
            "token_savings_estimate": self.token_savings_estimate,
        }


class CaeStore:
    def __init__(self) -> None:
        self.packages: dict[str, ContextPackage] = {}
        self.recent_ids: list[str] = []
        self.cache: dict[str, CacheEntry] = {}
        self.audit: list[AuditEntry] = []
        self.metrics = CaeMetrics()

    def put_package(self, package: ContextPackage) -> ContextPackage:
        self.packages[package.package_id] = package
        self.recent_ids.append(package.package_id)
        self.recent_ids = self.recent_ids[-200:]
        self.metrics.observe(package)
        self.audit_event("put_package", object_kind="package", object_id=package.package_id)
        return package

    def get_package(self, package_id: str) -> ContextPackage | None:
        return self.packages.get(package_id)

    def cache_get(self, key: str) -> dict[str, Any] | None:
        entry = self.cache.get(key)
        if not entry:
            return None
        if time.time() > entry.expires_at:
            del self.cache[key]
            return None
        entry.hits += 1
        return entry.package

    def cache_set(self, key: str, package: dict[str, Any], *, ttl: int = CACHE_TTL_SECONDS) -> None:
        now = time.time()
        self.cache[key] = CacheEntry(key=key, package=package, created_at=now, expires_at=now + ttl)

    def cache_clear(self) -> int:
        n = len(self.cache)
        self.cache.clear()
        return n

    def cache_stats(self) -> dict[str, Any]:
        now = time.time()
        alive = [c for c in self.cache.values() if c.expires_at >= now]
        return {
            "entries": len(alive),
            "expired_pending": len(self.cache) - len(alive),
            "keys": [c.to_dict() for c in alive[:50]],
        }

    def audit_event(self, action: str, *, object_kind: str = "", object_id: str = "", detail: str = "") -> None:
        self.audit.append(
            AuditEntry(action=action, object_kind=object_kind, object_id=object_id, detail=detail)
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "packages": len(self.packages),
            "cache_entries": len(self.cache),
            "audit": len(self.audit),
        }
