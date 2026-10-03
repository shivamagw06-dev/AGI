"""Lightweight analysis history for admin coverage/version views."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FimlMetrics:
    analyses: int = 0
    by_domain: dict[str, int] = field(default_factory=dict)
    decisions: int = 0
    refuses: int = 0

    def observe(self, domain: str, result: dict[str, Any]) -> None:
        self.analyses += 1
        self.by_domain[domain] = self.by_domain.get(domain, 0) + 1
        if domain == "decision":
            self.decisions += 1
            if (result.get("label") or "") == "refuse_insufficient_data":
                self.refuses += 1

    def model_dump(self) -> dict[str, Any]:
        return {
            "analyses": self.analyses,
            "by_domain": dict(self.by_domain),
            "decisions": self.decisions,
            "refuses": self.refuses,
        }


class FimlStore:
    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []
        self.metrics = FimlMetrics()

    def add(self, domain: str, result: dict[str, Any]) -> None:
        self.metrics.observe(domain, result)
        self.history.append({"domain": domain, "result": result})
        self.history = self.history[-1000:]

    def snapshot(self) -> dict[str, Any]:
        return {"history": len(self.history), "domains": sorted(self.metrics.by_domain.keys())}
