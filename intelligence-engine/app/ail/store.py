"""In-memory AIL store — immutable versions, incremental dossiers."""

from __future__ import annotations

from typing import Any

from app.ail.models import (
    AuditRecord,
    CorporateEvent,
    DossierVersion,
    EvidenceRecord,
    GraphEdge,
    PredictionRecord,
    ThesisVersion,
    TimelineEntry,
)


class AilStore:
    def __init__(self) -> None:
        self.evidence: dict[str, EvidenceRecord] = {}
        self.evidence_by_hash: dict[str, str] = {}
        self.dossiers: dict[str, list[str]] = {}  # ticker -> [dossier_ids]
        self.dossier_versions: dict[str, DossierVersion] = {}
        self.events: dict[str, CorporateEvent] = {}
        self.events_by_ticker: dict[str, list[str]] = {}
        self.theses: dict[str, list[str]] = {}
        self.thesis_versions: dict[str, ThesisVersion] = {}
        self.predictions: dict[str, PredictionRecord] = {}
        self.predictions_by_ticker: dict[str, list[str]] = {}
        self.timeline: dict[str, list[TimelineEntry]] = {}
        self.graph_edges: dict[str, GraphEdge] = {}
        self.audits: dict[str, AuditRecord] = {}
        self.watchlists: dict[str, list[str]] = {"default": ["RELIANCE", "TCS", "INFY", "HDFCBANK"]}

    # --- Evidence ---
    def put_evidence(self, rec: EvidenceRecord) -> EvidenceRecord:
        existing_id = self.evidence_by_hash.get(rec.content_hash)
        if existing_id and existing_id in self.evidence:
            return self.evidence[existing_id]
        self.evidence[rec.evidence_id] = rec
        self.evidence_by_hash[rec.content_hash] = rec.evidence_id
        return rec

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        return self.evidence.get(evidence_id)

    # --- Dossier (incremental: new version only when fields change) ---
    def active_dossier(self, ticker: str) -> DossierVersion | None:
        ids = self.dossiers.get(ticker.upper()) or []
        if not ids:
            return None
        return self.dossier_versions.get(ids[-1])

    def put_dossier(self, dossier: DossierVersion) -> DossierVersion:
        t = dossier.ticker.upper()
        prior = self.active_dossier(t)
        if prior:
            dossier.version = prior.version + 1
            dossier.supersedes = prior.dossier_id
        self.dossier_versions[dossier.dossier_id] = dossier
        self.dossiers.setdefault(t, []).append(dossier.dossier_id)
        return dossier

    # --- Events ---
    def put_event(self, event: CorporateEvent) -> CorporateEvent:
        self.events[event.event_id] = event
        self.events_by_ticker.setdefault(event.ticker.upper(), []).append(event.event_id)
        return event

    def events_for(self, ticker: str) -> list[CorporateEvent]:
        ids = self.events_by_ticker.get(ticker.upper()) or []
        return [self.events[i] for i in ids if i in self.events]

    # --- Thesis ---
    def active_thesis(self, ticker: str) -> ThesisVersion | None:
        ids = self.theses.get(ticker.upper()) or []
        if not ids:
            return None
        return self.thesis_versions.get(ids[-1])

    def put_thesis(self, thesis: ThesisVersion) -> ThesisVersion:
        t = thesis.ticker.upper()
        prior = self.active_thesis(t)
        if prior:
            thesis.version = prior.version + 1
            thesis.supersedes = prior.thesis_id
        self.thesis_versions[thesis.thesis_id] = thesis
        self.theses.setdefault(t, []).append(thesis.thesis_id)
        return thesis

    # --- Predictions (immutable append) ---
    def put_prediction(self, pred: PredictionRecord) -> PredictionRecord:
        t = pred.ticker.upper()
        prior_ids = self.predictions_by_ticker.get(t) or []
        if prior_ids:
            prior = self.predictions.get(prior_ids[-1])
            if prior:
                pred.version = prior.version + 1
        self.predictions[pred.prediction_id] = pred
        self.predictions_by_ticker.setdefault(t, []).append(pred.prediction_id)
        return pred

    def active_prediction(self, ticker: str) -> PredictionRecord | None:
        ids = self.predictions_by_ticker.get(ticker.upper()) or []
        if not ids:
            return None
        return self.predictions.get(ids[-1])

    def get_prediction(self, prediction_id: str) -> PredictionRecord | None:
        return self.predictions.get(prediction_id)

    # --- Timeline / graph / audit ---
    def add_timeline(self, entry: TimelineEntry) -> TimelineEntry:
        self.timeline.setdefault(entry.ticker.upper(), []).append(entry)
        return entry

    def timeline_for(self, ticker: str) -> list[TimelineEntry]:
        return list(self.timeline.get(ticker.upper()) or [])

    def put_edge(self, edge: GraphEdge) -> GraphEdge:
        key = f"{edge.src}|{edge.rel}|{edge.dst}"
        for e in self.graph_edges.values():
            if f"{e.src}|{e.rel}|{e.dst}" == key:
                # merge evidence ids
                merged = list(dict.fromkeys([*e.evidence_ids, *edge.evidence_ids]))
                e.evidence_ids = merged
                return e
        self.graph_edges[edge.edge_id] = edge
        return edge

    def graph_for(self, ticker: str) -> list[GraphEdge]:
        t = ticker.upper()
        company = None
        d = self.active_dossier(t)
        if d:
            company = d.company
        out = []
        for e in self.graph_edges.values():
            if t in {e.src.upper(), e.dst.upper()} or (company and company in {e.src, e.dst}):
                out.append(e)
        return out

    def put_audit(self, audit: AuditRecord) -> AuditRecord:
        self.audits[audit.audit_id] = audit
        return audit

    def snapshot(self) -> dict[str, Any]:
        return {
            "evidence": len(self.evidence),
            "dossiers": sum(len(v) for v in self.dossiers.values()),
            "events": len(self.events),
            "theses": sum(len(v) for v in self.theses.values()),
            "predictions": len(self.predictions),
            "timeline_entries": sum(len(v) for v in self.timeline.values()),
            "graph_edges": len(self.graph_edges),
            "audits": len(self.audits),
            "watchlists": {k: list(v) for k, v in self.watchlists.items()},
        }
