"""Connector abstraction — search / fetch / validate / health / priority."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.faa.http_client import HttpClient
from app.faa.models import CandidateDocument, DiscoveryTask, FetchedDocument


class AcquisitionConnector(ABC):
    connector_id: str = "base"
    name: str = "Base"
    tier: int = 6
    max_per_minute: int = 30
    timeout_seconds: float = 25.0
    document_types: list[str] = ["unknown"]

    def __init__(self, *, live_fetch: bool = False, config: dict[str, Any] | None = None) -> None:
        self.live_fetch = live_fetch
        self.config = config or {}
        self.failures = 0
        self.successes = 0
        self.last_error: str | None = None
        self.last_success_at: str | None = None

    # --- required interface ---
    @abstractmethod
    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        """Discover candidate public documents for a task."""

    def discover(self, task: DiscoveryTask) -> list[CandidateDocument]:
        """Backward-compatible alias used by DiscoveryService."""
        return self.search(task)

    def fetch(self, candidate: CandidateDocument, client: HttpClient) -> FetchedDocument | None:
        """Optional connector-specific fetch. Return None to use generic FetchService."""
        return None

    def validate(self, fetched: FetchedDocument) -> tuple[bool, str | None]:
        if fetched.error:
            return False, fetched.error
        if fetched.skipped:
            return True, fetched.skip_reason
        if not (fetched.content_text or "").strip() and fetched.content_bytes_len <= 0:
            return False, "empty_content"
        if fetched.live_fetch and fetched.metadata.get("http_status", 200) >= 400:
            # allow thin provenance pages
            if (fetched.content_text or "").strip():
                return True, "thin_live_page"
            return False, f"http_{fetched.metadata.get('http_status')}"
        return True, None

    def health(self) -> dict[str, Any]:
        status = "ok"
        if self.failures > 0 and self.successes == 0:
            status = "degraded"
        if self.last_error and self.successes == 0:
            status = "error"
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "tier": self.tier,
            "priority": self.priority(),
            "live_fetch": self.live_fetch,
            "status": status,
            "supported_document_types": self.supported_document_types(),
            "max_per_minute": self.max_per_minute,
            "timeout_seconds": self.timeout_seconds,
            "successes": self.successes,
            "failures": self.failures,
            "last_error": self.last_error,
            "last_success_at": self.last_success_at,
        }

    def priority(self) -> int:
        # lower number = higher priority (Tier-aligned)
        return int(self.tier)

    def supported_document_types(self) -> list[str]:
        return list(self.document_types)

    def mark_success(self, at: str | None = None) -> None:
        self.successes += 1
        self.last_success_at = at
        self.last_error = None

    def mark_failure(self, error: str) -> None:
        self.failures += 1
        self.last_error = error[:240]
