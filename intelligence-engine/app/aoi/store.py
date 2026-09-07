"""Process-local AOI store — versioned, append-friendly, immutable history."""

from __future__ import annotations

from typing import Any

from app.aoi.models import (
    AuditEvent,
    CompanyQualityScore,
    DailyLearningDigest,
    DocumentArtifact,
    ExtractedFact,
    GapTask,
    GraphEdge,
    KnowledgeVersion,
    ObservabilitySnapshot,
    StructuredDiff,
)


class AoiStore:
    def __init__(self) -> None:
        self.artifacts: dict[str, DocumentArtifact] = {}
        self.checksum_index: dict[str, str] = {}  # checksum -> artifact_id
        self.facts: dict[str, ExtractedFact] = {}
        self.fact_history: list[ExtractedFact] = []  # immutable append log
        self.versions: dict[str, list[KnowledgeVersion]] = {}
        self.diffs: list[StructuredDiff] = []
        self.edges: dict[str, GraphEdge] = {}
        self.quality: dict[str, CompanyQualityScore] = {}
        self.gaps: list[GapTask] = []
        self.digests: list[DailyLearningDigest] = []
        self.audit: list[AuditEvent] = []
        self.metrics = ObservabilitySnapshot()
        self.queue: list[str] = []

    def known_checksums(self) -> set[str]:
        return set(self.checksum_index.keys())

    def upsert_artifact(self, art: DocumentArtifact) -> DocumentArtifact:
        if art.checksum and art.checksum in self.checksum_index:
            existing_id = self.checksum_index[art.checksum]
            existing = self.artifacts.get(existing_id)
            if existing:
                self.metrics.download_success += 0  # unchanged
                return existing
        self.artifacts[art.artifact_id] = art
        if art.checksum:
            self.checksum_index[art.checksum] = art.artifact_id
        return art

    def add_facts(self, facts: list[ExtractedFact]) -> int:
        n = 0
        for f in facts:
            self.facts[f.fact_id] = f
            self.fact_history.append(f)
            n += 1
        self.metrics.knowledge_growth_facts += n
        return n

    def add_version(self, version: KnowledgeVersion) -> None:
        self.versions.setdefault(version.company_id, []).append(version)

    def add_diff(self, diff: StructuredDiff) -> None:
        self.diffs.append(diff)

    def add_edge(self, edge: GraphEdge) -> None:
        key = f"{edge.src}|{edge.rel}|{edge.dst}"
        self.edges[key] = edge

    def audit_event(self, action: str, *, object_kind: str = "", object_id: str = "", detail: str = "") -> None:
        self.audit.append(
            AuditEvent(action=action, object_kind=object_kind, object_id=object_id, detail=detail)
        )

    def coverage_counts(self) -> dict[str, Any]:
        companies = {a.company_id for a in self.artifacts.values() if a.company_id}
        return {
            "artifacts": len(self.artifacts),
            "facts": len(self.facts),
            "fact_history": len(self.fact_history),
            "companies_with_docs": len(companies),
            "versions": sum(len(v) for v in self.versions.values()),
            "diffs": len(self.diffs),
            "edges": len(self.edges),
            "gaps": len(self.gaps),
            "digests": len(self.digests),
        }
