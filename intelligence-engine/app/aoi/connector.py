"""Pluggable source connector interface — zero cross-connector dependencies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.aoi.models import DocumentArtifact, ExtractedFact
from app.aoi.registry import CompanyRegistry


class SourceConnector(ABC):
    """Every connector implements the same contract.

    Adding a connector must require zero changes elsewhere beyond registration.
    """

    connector_id: str = "base"
    name: str = "Base Connector"
    category: str = "public"  # company | exchange | macro | government | optional

    def __init__(self, *, config: dict[str, Any] | None = None, live_fetch: bool = False) -> None:
        self.config = config or {}
        self.live_fetch = live_fetch

    @abstractmethod
    def discover(self, registry: CompanyRegistry) -> list[DocumentArtifact]:
        """Discover candidate documents / releases."""

    def fetch_updates(self, registry: CompanyRegistry, *, known_checksums: set[str]) -> list[DocumentArtifact]:
        """Return only new/changed artifacts (idempotent incremental)."""
        found = self.discover(registry)
        out: list[DocumentArtifact] = []
        for art in found:
            if art.checksum and art.checksum in known_checksums:
                art.status = "skipped"
                continue
            out.append(art)
        return out

    def download(self, artifact: DocumentArtifact) -> DocumentArtifact:
        """Download bytes/text; default synthesizes offline-safe content."""
        return artifact

    def parse(self, artifact: DocumentArtifact) -> DocumentArtifact:
        return artifact

    def extract(self, artifact: DocumentArtifact) -> list[ExtractedFact]:
        return []

    def validate(self, facts: list[ExtractedFact], artifact: DocumentArtifact) -> list[ExtractedFact]:
        return [f for f in facts if 0.0 <= float(f.confidence) <= 1.0 and (f.value_text or f.value is not None)]

    def transform(self, facts: list[ExtractedFact], artifact: DocumentArtifact) -> list[ExtractedFact]:
        return facts

    def publish(self, facts: list[ExtractedFact], artifact: DocumentArtifact) -> dict[str, Any]:
        """Connectors do not publish directly — pipeline owns publish. Hook retained for interface completeness."""
        return {"accepted": False, "reason": "pipeline_owned"}

    def health_check(self) -> dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "status": "ok",
            "live_fetch": self.live_fetch,
            "config_keys": sorted(self.config.keys()),
        }
