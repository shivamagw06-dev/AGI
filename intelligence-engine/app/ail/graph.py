"""Knowledge graph extensions — company relationships updated by events/evidence."""

from __future__ import annotations

from typing import Any

from app.ail.catalog import COMPANIES
from app.ail.models import CorporateEvent, EvidenceRecord, GraphEdge
from app.ail.store import AilStore


class KnowledgeGraphEngine:
    def __init__(self, store: AilStore) -> None:
        self.store = store

    def ensure_company(self, ticker: str, *, evidence_ids: list[str] | None = None) -> None:
        t = ticker.upper()
        profile = COMPANIES.get(t) or {}
        company = str(profile.get("company") or t)
        eids = list(evidence_ids or [])
        for comp in profile.get("competitors") or []:
            self.store.put_edge(
                GraphEdge(src=t, rel="competes_with", dst=str(comp).upper(), evidence_ids=eids, weight=1.0)
            )
        for geo in profile.get("geographies") or []:
            self.store.put_edge(GraphEdge(src=t, rel="operates_in", dst=str(geo), evidence_ids=eids))
        self.store.put_edge(GraphEdge(src=t, rel="named", dst=company, evidence_ids=eids))
        # structural exposures
        self.store.put_edge(GraphEdge(src=t, rel="affected_by", dst="Interest Rates", evidence_ids=eids, weight=0.6))
        self.store.put_edge(GraphEdge(src=t, rel="affected_by", dst="FX", evidence_ids=eids, weight=0.5))
        self.store.put_edge(GraphEdge(src=t, rel="regulated_by", dst="Government", evidence_ids=eids, weight=0.8))

    def update_from_event(self, event: CorporateEvent) -> None:
        t = event.ticker.upper()
        eids = list(event.evidence_ids)
        if event.category in {"acquisition", "merger"}:
            self.store.put_edge(
                GraphEdge(src=t, rel="owns", dst=f"Target@{event.event_id}", evidence_ids=eids, weight=1.2)
            )
        if event.category in {"gov_approval", "regulatory_penalty", "macro_policy"}:
            self.store.put_edge(
                GraphEdge(src=t, rel="affected_by", dst="Policy", evidence_ids=eids, weight=1.0)
            )
        if event.category in {"capex"}:
            self.store.put_edge(
                GraphEdge(src=t, rel="affected_by", dst="Commodity", evidence_ids=eids, weight=0.7)
            )

    def update_from_evidence(self, evidence: EvidenceRecord) -> None:
        if not evidence.ticker:
            return
        text = (evidence.claim or "").lower()
        t = evidence.ticker.upper()
        eids = [evidence.evidence_id]
        if "subsidiar" in text:
            self.store.put_edge(GraphEdge(src=t, rel="owns", dst="Subsidiary", evidence_ids=eids))
        if "supplier" in text or "supplied by" in text:
            self.store.put_edge(GraphEdge(src=t, rel="supplied_by", dst="Supplier", evidence_ids=eids))

    def get(self, ticker: str) -> dict[str, Any]:
        self.ensure_company(ticker)
        edges = self.store.graph_for(ticker)
        return {
            "programme": "KG",
            "ticker": ticker.upper(),
            "relationships": [e.to_dict() for e in edges],
            "count": len(edges),
        }
