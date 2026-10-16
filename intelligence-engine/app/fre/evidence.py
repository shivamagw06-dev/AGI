"""Steps 12–13 — Evidence extraction + cross-validation."""

from __future__ import annotations

import re
from typing import Any

from app.fre.models import FreEvidence, extract_claim_candidates
from app.fre.store import FreStore

_CONFLICT_PAIRS = [
    (re.compile(r"(?i)increased|grew|rose|up\s+\d"), re.compile(r"(?i)declined|fell|decreased|down\s+\d")),
    (re.compile(r"(?i)margin\s+(expanded|improved)"), re.compile(r"(?i)margin\s+(compressed|declined|pressure)")),
]


def extract_evidence(hits: list[dict[str, Any]], *, limit: int = 20) -> list[FreEvidence]:
    out: list[FreEvidence] = []
    for h in hits[:limit]:
        claims = extract_claim_candidates(str(h.get("text") or ""), limit=2)
        for claim in claims:
            conf = float(h.get("rerank_score") or h.get("score") or h.get("confidence") or 0.5)
            conf = max(0.35, min(0.99, conf + (int(h.get("authority") or 2) / 50.0)))
            out.append(
                FreEvidence(
                    claim=claim,
                    source=str(h.get("source") or h.get("title") or "unknown"),
                    document_id=str(h.get("document_id") or ""),
                    chunk_id=str(h.get("chunk_id") or ""),
                    page=h.get("page"),
                    section=str(h.get("section") or h.get("heading") or ""),
                    company=h.get("company"),
                    symbol=h.get("symbol"),
                    document_type=str(h.get("document_type") or "unknown"),
                    published_at=h.get("published_at"),
                    confidence=round(conf, 4),
                    authority=int(h.get("authority") or 2),
                    supporting_chunk_ids=[str(h.get("chunk_id"))] if h.get("chunk_id") else [],
                    validation_status="unvalidated",
                )
            )
    return out


def cross_validate(store: FreStore, evidence: list[FreEvidence]) -> list[FreEvidence]:
    """Compare claims across document types; flag contradictions; boost multi-source agreement."""
    by_company: dict[str, list[FreEvidence]] = {}
    for ev in evidence:
        key = (ev.symbol or ev.company or "global").lower()
        by_company.setdefault(key, []).append(ev)

    for group in by_company.values():
        for i, a in enumerate(group):
            supporters = []
            contradictors = []
            for j, b in enumerate(group):
                if i == j:
                    continue
                # same-ish metric language
                if _similar_topic(a.claim, b.claim):
                    if _conflicts(a.claim, b.claim):
                        contradictors.append(b.evidence_id)
                    elif a.document_type != b.document_type or a.source != b.source:
                        supporters.append(b.evidence_id)
            a.supporting_chunk_ids = list(dict.fromkeys(a.supporting_chunk_ids + _chunk_ids(store, supporters)))
            a.contradictory_evidence_ids = contradictors
            if contradictors:
                a.validation_status = "conflict"
                a.confidence = max(0.25, a.confidence - 0.15)
            elif supporters:
                a.validation_status = "corroborated"
                a.confidence = min(0.99, a.confidence + 0.08)
            else:
                a.validation_status = "single_source"
    store.put_evidence(evidence)
    return evidence


def _chunk_ids(store: FreStore, evidence_ids: list[str]) -> list[str]:
    out = []
    for eid in evidence_ids:
        ev = store.evidence.get(eid)
        if ev and ev.chunk_id:
            out.append(ev.chunk_id)
    return out


def _similar_topic(a: str, b: str) -> bool:
    keys = ("revenue", "margin", "guidance", "growth", "eps", "profit", "capex", "debt")
    al, bl = a.lower(), b.lower()
    return any(k in al and k in bl for k in keys)


def _conflicts(a: str, b: str) -> bool:
    for pos, neg in _CONFLICT_PAIRS:
        if (pos.search(a) and neg.search(b)) or (neg.search(a) and pos.search(b)):
            return True
    return False
