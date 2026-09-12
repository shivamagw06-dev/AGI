"""Evidence Ledger (EL) — immutable claim registry; nothing enters CAE without IDs."""

from __future__ import annotations

from typing import Any

from app.ail.models import EvidenceRecord, utc_now
from app.ail.store import AilStore


class EvidenceLedger:
    def __init__(self, store: AilStore) -> None:
        self.store = store

    def register(
        self,
        *,
        claim: str,
        source: str,
        url: str | None = None,
        company: str | None = None,
        ticker: str | None = None,
        page: int | None = None,
        section: str | None = None,
        connector: str = "ail",
        authority_score: int = 5,
        confidence: float = 0.7,
        document_version: str | None = None,
        verified_against: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceRecord:
        rec = EvidenceRecord(
            claim=claim.strip(),
            source=source,
            url=url,
            company=company,
            ticker=(ticker or "").upper() or None,
            page=page,
            section=section,
            connector=connector,
            authority_score=int(authority_score),
            confidence=float(confidence),
            document_version=document_version,
            validation_status="registered",
            verified_against=list(verified_against or []),
            metadata=metadata or {},
            retrieved_at=utc_now(),
        )
        return self.store.put_evidence(rec)

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        return self.store.get_evidence(evidence_id)

    def for_ticker(self, ticker: str) -> list[EvidenceRecord]:
        t = ticker.upper()
        return [e for e in self.store.evidence.values() if (e.ticker or "").upper() == t]

    def require_ids(self, evidence_ids: list[str]) -> list[str]:
        """Filter to ledger-registered IDs only."""
        return [eid for eid in evidence_ids if eid in self.store.evidence]

    def snapshot(self) -> dict[str, Any]:
        return {
            "programme": "EL",
            "records": len(self.store.evidence),
            "by_connector": _count_by(self.store.evidence.values(), "connector"),
            "by_authority": _count_by(self.store.evidence.values(), "authority_score"),
        }


def _count_by(items, attr: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        key = str(getattr(item, attr, "unknown"))
        out[key] = out.get(key, 0) + 1
    return out
