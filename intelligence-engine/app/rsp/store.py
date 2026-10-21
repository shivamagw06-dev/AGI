"""In-memory store for ReasoningPackages and evidence lookups."""

from __future__ import annotations

from threading import RLock

from app.rsp.models import EvidenceStatement, ReasoningPackage


class RspStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self.packages: dict[str, ReasoningPackage] = {}
        self.evidence: dict[str, EvidenceStatement] = {}

    def put(self, pkg: ReasoningPackage) -> None:
        with self._lock:
            self.packages[pkg.reasoning_id] = pkg
            for e in pkg.evidence:
                self.evidence[e.evidence_id] = e

    def get(self, reasoning_id: str) -> ReasoningPackage | None:
        with self._lock:
            return self.packages.get(reasoning_id)

    def get_evidence(self, evidence_id: str) -> EvidenceStatement | None:
        with self._lock:
            return self.evidence.get(evidence_id)

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "reasoning_packages": len(self.packages),
                "evidence_statements": len(self.evidence),
            }
