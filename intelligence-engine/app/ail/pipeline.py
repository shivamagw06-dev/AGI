"""AIL pipeline — evidence → ledger → dossier → events → thesis → forecast → graph/timeline."""

from __future__ import annotations

from typing import Any

from app.ail.catalog import COMPANIES, resolve_ticker
from app.ail.dossier import CompanyDossierEngine
from app.ail.events import EventDetectionEngine
from app.ail.graph import KnowledgeGraphEngine
from app.ail.ledger import EvidenceLedger
from app.ail.models import AuditRecord, EvidenceRecord, utc_now
from app.ail.monitor import ContinuousMonitoringEngine
from app.ail.prediction_engine import PredictionEngine
from app.ail.store import AilStore
from app.ail.thesis_engine import ThesisEngine
from app.ail.timeline import TimelineEngine


class AilPipeline:
    def __init__(self, store: AilStore | None = None) -> None:
        self.store = store or AilStore()
        self.ledger = EvidenceLedger(self.store)
        self.dossier = CompanyDossierEngine(self.store)
        self.events = EventDetectionEngine(self.store)
        self.thesis = ThesisEngine(self.store)
        self.predictions = PredictionEngine(self.store)
        self.timeline = TimelineEngine(self.store)
        self.graph = KnowledgeGraphEngine(self.store)
        self.monitor = ContinuousMonitoringEngine(self.store)
        self.fre: Any | None = None
        self.faa: Any | None = None
        self.cae: Any | None = None

    def bind(self, **engines: Any) -> None:
        for k, v in engines.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def bootstrap_company(self, ticker: str) -> list[EvidenceRecord]:
        t = ticker.upper()
        profile = COMPANIES.get(t)
        if not profile:
            # minimal synthetic ledger entry so CAE path still has provenance
            rec = self.ledger.register(
                claim=f"Coverage initialized for {t}.",
                source="AIL bootstrap",
                url=None,
                company=t,
                ticker=t,
                section="bootstrap",
                connector="ail",
                authority_score=3,
                confidence=0.4,
            )
            self.dossier.ensure_base(t)
            self.timeline.ensure_seed(t, evidence_ids=[rec.evidence_id])
            self.graph.ensure_company(t, evidence_ids=[rec.evidence_id])
            return [rec]

        registered: list[EvidenceRecord] = []
        for claim in profile.get("seed_claims") or []:
            rec = self.ledger.register(
                claim=str(claim["claim"]),
                source=str(claim.get("source") or "IR"),
                url=claim.get("url"),
                company=profile["company"],
                ticker=t,
                page=claim.get("page"),
                section=claim.get("section"),
                connector=str(claim.get("connector") or "company_ir"),
                authority_score=int(claim.get("authority") or 8),
                confidence=0.8,
                metadata={"field": claim.get("field"), "bootstrap": True},
            )
            registered.append(rec)
            field = str(claim.get("field") or "company_overview")
            self.dossier.apply_claim(
                t,
                field=field,
                value=claim["claim"],
                evidence_ids=[rec.evidence_id],
                confidence=0.8,
            )
        eids = [r.evidence_id for r in registered]
        self.timeline.ensure_seed(t, evidence_ids=eids)
        self.graph.ensure_company(t, evidence_ids=eids)
        return registered

    def soft_pull_upstream(
        self,
        query: str,
        ticker: str,
        *,
        pull_faa: bool = False,
    ) -> list[EvidenceRecord]:
        """Soft-consume cached FAA/FRE evidence — never call ``faa.acquire``.

        ``pull_faa`` is ignored (kept for API compatibility). Live acquisition
        belongs exclusively to the FAA background collector / ``/v1/faa/*``.
        """
        del pull_faa  # Ask path must never trigger live FAA/Playwright.
        out: list[EvidenceRecord] = []

        # Read-only FAA snapshot (filled by background collector) — no acquire.
        if self.faa is not None:
            try:
                snap = {}
                if hasattr(self.faa, "store") and hasattr(self.faa.store, "snapshot"):
                    snap = self.faa.store.snapshot() or {}
                for d in (snap.get("latest") or [])[:8]:
                    if not isinstance(d, dict):
                        continue
                    claim = str(d.get("title") or d.get("claim") or d.get("url") or "")[:280]
                    if not claim:
                        continue
                    out.append(
                        self.ledger.register(
                            claim=claim,
                            source=str(d.get("connector_id") or d.get("source") or "faa_snapshot"),
                            url=d.get("url"),
                            company=d.get("company") or COMPANIES.get(ticker, {}).get("company"),
                            ticker=ticker,
                            section=d.get("document_type") or d.get("section"),
                            connector="faa_snapshot",
                            authority_score=int(d.get("authority") or 6),
                            confidence=0.6,
                            document_version=d.get("document_id") or d.get("checksum"),
                            metadata={"upstream": "faa_snapshot", "live_acquire": False},
                        )
                    )
            except Exception:
                pass

        # FRE index/search only (acquire=False). Never fre.query (that can FAA-acquire).
        if self.fre is not None:
            try:
                if hasattr(self.fre, "search"):
                    pack = self.fre.search(query, limit=8) or {}
                elif hasattr(self.fre, "consult"):
                    pack = self.fre.consult(query, limit=8) or {}
                else:
                    pack = {}
                evidence_rows = (
                    pack.get("evidence")
                    or pack.get("top_evidence")
                    or pack.get("hits")
                    or []
                )
                for e in evidence_rows[:8]:
                    if not isinstance(e, dict):
                        continue
                    claim = str(
                        e.get("claim")
                        or e.get("label")
                        or e.get("text")
                        or e.get("title")
                        or ""
                    )[:280]
                    if not claim:
                        continue
                    out.append(
                        self.ledger.register(
                            claim=claim,
                            source=str(e.get("source") or "fre"),
                            url=e.get("url"),
                            company=e.get("company"),
                            ticker=ticker,
                            page=e.get("page"),
                            section=e.get("section") or e.get("heading"),
                            connector=str(e.get("source") or "fre"),
                            authority_score=int(e.get("authority") or 6),
                            confidence=float(e.get("confidence") or e.get("score") or 0.65),
                            metadata={"upstream": "fre_index", "evidence_ref": e.get("evidence_id") or e.get("id")},
                        )
                    )
            except Exception:
                pass
        return out

    def ingest_evidence_records(self, ticker: str, records: list[EvidenceRecord]) -> dict[str, Any]:
        detected_events = []
        for rec in records:
            field = (rec.metadata or {}).get("field") or "company_overview"
            self.dossier.apply_claim(
                ticker,
                field=str(field),
                value=rec.claim,
                evidence_ids=[rec.evidence_id],
                confidence=rec.confidence,
            )
            evts = self.events.detect_from_evidence(rec)
            for evt in evts:
                self.timeline.add_from_event(evt)
                self.graph.update_from_event(evt)
            detected_events.extend(evts)
            self.graph.update_from_evidence(rec)

        thesis = self.thesis.update_with_evidence(ticker, records, detected_events)
        eids = [r.evidence_id for r in records]
        pred = self.predictions.forecast(
            ticker,
            company=thesis.company,
            evidence_ids=eids,
            thesis=thesis,
        )
        # link forecast + thesis summaries into dossier
        self.dossier.apply_claim(
            ticker,
            field="current_investment_thesis",
            value={
                "bull": thesis.bull.probability,
                "base": thesis.base.probability,
                "bear": thesis.bear.probability,
                "thesis_id": thesis.thesis_id,
            },
            evidence_ids=eids,
            confidence=thesis.base.confidence,
        )
        self.dossier.apply_claim(
            ticker,
            field="forecast",
            value={"prediction_id": pred.prediction_id, "confidence": pred.confidence},
            evidence_ids=eids,
            confidence=pred.confidence,
        )
        return {
            "events": [e.to_dict() for e in detected_events],
            "thesis_id": thesis.thesis_id,
            "prediction_id": pred.prediction_id,
        }

    def analyse(
        self,
        query: str,
        *,
        ticker: str | None = None,
        pull_faa: bool = False,
    ) -> dict[str, Any]:
        t = (ticker or resolve_ticker(query) or "").upper()
        if not t:
            return {
                "programme": "AIL",
                "architecture_status": "v1.0.1 LOCKED",
                "error": "ticker_unresolved",
                "query": query,
                "hint": "Provide a listed company name or ticker (e.g. Reliance Industries / RELIANCE).",
            }

        # Bootstrap living state once, then incrementally update
        existing = self.ledger.for_ticker(t)
        first_seen = not existing
        if first_seen:
            boot = self.bootstrap_company(t)
            ingest_meta = self.ingest_evidence_records(t, boot)
        else:
            boot = existing
            ingest_meta = {"events": [], "thesis_id": None, "prediction_id": None}

        upstream = self.soft_pull_upstream(query, t, pull_faa=pull_faa)
        if upstream:
            ingest_meta = self.ingest_evidence_records(t, upstream)

        if not self.store.active_thesis(t):
            self.thesis.ensure(t)
        if not self.store.active_prediction(t):
            th = self.store.active_thesis(t)
            self.predictions.forecast(t, thesis=th, evidence_ids=[r.evidence_id for r in boot])
        ingest_meta["first_seen"] = first_seen

        dossier = self.dossier.get(t)
        thesis = self.thesis.get(t)
        forecast = self.predictions.get(t)
        events = self.events.list_for(t, limit=30)
        timeline = self.timeline.get(t, limit=80)
        graph = self.graph.get(t)
        ledger = [e.to_dict() for e in self.ledger.for_ticker(t)]

        supporting = list((thesis.get("bull") or {}).get("supporting_evidence") or [])
        supporting += list((thesis.get("base") or {}).get("supporting_evidence") or [])
        supporting = list(dict.fromkeys(supporting))[:20]
        contradicting = list((thesis.get("bull") or {}).get("contradicting_evidence") or [])
        contradicting += list((thesis.get("bear") or {}).get("supporting_evidence") or [])
        contradicting = list(dict.fromkeys(contradicting))[:20]
        if not supporting:
            supporting = [e["evidence_id"] for e in ledger if e.get("evidence_id")][:12]

        audit = AuditRecord(
            query=query,
            ticker=t,
            evidence_ids=[e["evidence_id"] for e in ledger][:40],
            thesis_version=thesis.get("thesis_id"),
            prediction_version=forecast.get("prediction_id"),
            dossier_version=dossier.get("dossier_id"),
            reasoning_inputs={
                "systems": ["CDE", "EDE", "TE", "PE", "CME", "EL", "TIMELINE", "KG"],
                "upstream_faa": self.faa is not None,
                "upstream_fre": self.fre is not None,
                "ingest": ingest_meta,
            },
            confidence=float(forecast.get("confidence") or thesis.get("base", {}).get("confidence") or 0.5),
            created_at=utc_now(),
        )
        self.store.put_audit(audit)

        return {
            "programme": "AIL",
            "layer": "AGIB Intelligence Layer V2",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "after_faa_fre_before_cae_ask_agi",
            "does_not_redesign": ["faa", "fre", "cae", "ask_agi"],
            "query": query,
            "ticker": t,
            "company": dossier.get("company"),
            "dossier": dossier,
            "events": events,
            "timeline": timeline,
            "thesis": thesis,
            "forecast": forecast,
            "prediction_confidence": forecast.get("confidence"),
            "supporting_evidence_ids": supporting,
            "contradictory_evidence_ids": contradicting,
            "knowledge_graph": graph,
            "ledger": ledger[:60],
            "audit_trail": audit.to_dict(),
            "monitor": self.monitor.status(),
        }
