"""Module 1 — Knowledge Source Registry."""

from __future__ import annotations

from typing import Any, Optional

from knowledge_unification.providers import ALL_PROVIDERS
from knowledge_unification.providers.base import KnowledgeProvider
from knowledge_unification.schema import ProviderSpec


class KnowledgeRegistry:
    def __init__(self, providers: Optional[list[KnowledgeProvider]] = None) -> None:
        self._providers: dict[str, KnowledgeProvider] = {}
        for cls in providers or ALL_PROVIDERS:
            inst = cls() if isinstance(cls, type) else cls
            self._providers[inst.spec.id] = inst

    def get(self, provider_id: str) -> Optional[KnowledgeProvider]:
        return self._providers.get(provider_id)

    def all(self) -> list[KnowledgeProvider]:
        return list(self._providers.values())

    def specs(self) -> list[ProviderSpec]:
        return [p.spec for p in self._providers.values()]

    def refresh_health(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for pid, p in self._providers.items():
            try:
                status = p.health_check()
            except Exception:
                status = "error"
            p.spec.health = status
            out[pid] = status
        return out

    def dashboard(self) -> dict[str, Any]:
        health = self.refresh_health()
        return {
            "provider_count": len(self._providers),
            "providers": [
                {**p.spec.to_dict(), "health": health.get(p.spec.id, p.spec.health)}
                for p in sorted(self._providers.values(), key=lambda x: x.spec.priority)
            ],
        }


_REGISTRY: Optional[KnowledgeRegistry] = None


def get_registry() -> KnowledgeRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = KnowledgeRegistry()
    return _REGISTRY
