"""EVE service facade — evidence, trust, conflicts, timeline, verification."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.eve.flags import EveFlags
from app.eve.health import compute_company_health, recompute_all_health
from app.eve.ingest import EveIngestPipeline
from app.eve.jobs import run_daily_verification
from app.eve.sources import seed_sources
from app.eve.store import EveStore
from app.eve.timeline import company_timeline
from app.eve.versioning import fact_history


class EveService:
    """Evidence & Verification Engine — between AOI and KCV/KF."""

    def __init__(
        self,
        *,
        flags: EveFlags | None = None,
        store: EveStore | None = None,
        aoi: Any | None = None,
        kc: Any | None = None,
        kf: Any | None = None,
    ) -> None:
        self.flags = flags or EveFlags.from_settings(get_settings())
        self.store = store or EveStore()
        self.aoi = aoi
        self.kc = kc
        self.kf = kf
        self.pipeline = EveIngestPipeline(self.store)
        if self.flags.eve and not self.store.sources:
            seed_sources(self.store)

    def health(self) -> dict[str, Any]:
        snap = self.store.snapshot() if self.flags.eve else {}
        return {
            "status": "ok" if self.flags.eve else "disabled",
            "layer": "Evidence & Verification Engine",
            "programme": "EVE",
            "version": "eve-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "between_aoi_and_kcv_kf",
            "no_redesign": ["kf1", "kcv1", "aoi", "kip", "irp", "rsp", "ask_agi"],
            "flags": self.flags.as_dict(),
            "snapshot": snap,
            "metrics": self.store.metrics.model_dump(mode="json"),
        }

    def ingest_aoi_artifact(self, artifact: Any, facts: list[Any], *, company_symbol: str = "") -> dict[str, Any]:
        """Extension point for AOI soft publish — verify before institutional memory."""
        self._require()
        if not self.flags.eve_auto_verify:
            return {"accepted": False, "reason": "EVE_AUTO_VERIFY=false"}
        return self.pipeline.ingest_aoi_artifact(artifact, facts, company_symbol=company_symbol)

    def dashboard(self) -> dict[str, Any]:
        self._require()
        health_rows = sorted(self.store.health.values(), key=lambda h: -h.trust_score)
        open_conflicts = [c for c in self.store.conflicts.values() if c.status == "open"]
        tasks = [t for t in self.store.tasks if t.status == "open"]
        return {
            "programme": "EVE",
            "architecture_status": "v1.0.1 LOCKED",
            "metrics": self.store.metrics.model_dump(mode="json"),
            "snapshot": self.store.snapshot(),
            "knowledge_health": [h.model_dump(mode="json") for h in health_rows[:50]],
            "confidence_heatmap": [
                {
                    "company_id": h.company_id,
                    "symbol": h.company_symbol,
                    "trust": h.trust_score,
                    "confidence": h.average_confidence,
                    "conflicts": h.conflicts,
                    "verification_pct": h.verification_pct,
                }
                for h in health_rows[:50]
            ],
            "conflicts": [c.model_dump(mode="json") for c in open_conflicts[:40]],
            "verification_queue": [t.model_dump(mode="json") for t in tasks[-40:]],
            "sources": [s.model_dump(mode="json") for s in self.store.sources.values()],
            "recent_evidence": [
                e.model_dump(mode="json")
                for e in sorted(self.store.active_evidence(), key=lambda x: x.created_at, reverse=True)[:25]
            ],
            "audit": [a.model_dump(mode="json") for a in self.store.audit[-30:]],
        }

    def list_evidence(
        self,
        *,
        company_id: str | None = None,
        fact_key: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        self._require()
        rows = self.store.active_evidence(company_id=company_id, fact_key=fact_key)
        rows = sorted(rows, key=lambda e: (-float(e.confidence), e.created_at), reverse=False)
        rows = sorted(rows, key=lambda e: -float(e.confidence))[:limit]
        return {"count": len(rows), "evidence": [e.model_dump(mode="json") for e in rows]}

    def get_evidence(self, evidence_id: str) -> dict[str, Any]:
        self._require()
        ev = self.store.evidence.get(evidence_id)
        if not ev or ev.soft_deleted:
            raise KeyError(f"Evidence '{evidence_id}' not found")
        related = self.store.active_evidence(company_id=ev.company_id, fact_key=ev.fact_key)
        history = fact_history(self.store, company_id=ev.company_id, fact_key=ev.fact_key)
        return {
            "evidence": ev.model_dump(mode="json"),
            "supporting": [e.model_dump(mode="json") for e in related if e.evidence_id != evidence_id][:12],
            "versions": [v.model_dump(mode="json") for v in history][-20:],
            "source": self.store.sources.get(ev.provenance.source_id).model_dump(mode="json")
            if self.store.sources.get(ev.provenance.source_id)
            else {},
        }

    def company_pack(self, company_key: str) -> dict[str, Any]:
        self._require()
        company_id = company_key
        symbol = ""
        # Resolve via AOI registry if available
        if self.aoi is not None:
            try:
                co = self.aoi.registry.resolve(company_key)
                if co:
                    company_id = co.company_id
                    symbol = co.nse_symbol
            except Exception:
                pass
        if company_id not in self.store.health:
            compute_company_health(self.store, company_id, symbol=symbol)
        evidence = self.store.active_evidence(company_id=company_id)
        evidence_sorted = sorted(evidence, key=lambda e: -float(e.confidence))
        conflicts = [c for c in self.store.conflicts.values() if c.company_id == company_id]
        return {
            "company_id": company_id,
            "symbol": symbol,
            "health": self.store.health.get(company_id).model_dump(mode="json")
            if self.store.health.get(company_id)
            else {},
            "evidence": [e.model_dump(mode="json") for e in evidence_sorted[:100]],
            "conflicts": [c.model_dump(mode="json") for c in conflicts],
            "timeline": [e.model_dump(mode="json") for e in company_timeline(self.store, company_id)[:50]],
            "versions": [
                v.model_dump(mode="json")
                for v in self.store.versions
                if v.company_id == company_id
            ][-40:],
            "answer_policy": "highest_confidence_evidence_first",
        }

    def conflicts(self, *, status: str = "open") -> dict[str, Any]:
        self._require()
        rows = [c for c in self.store.conflicts.values() if not status or c.status == status]
        return {"count": len(rows), "conflicts": [c.model_dump(mode="json") for c in rows]}

    def timeline(self, *, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        rows = company_timeline(self.store, company_id) if company_id else sorted(
            self.store.timeline, key=lambda e: e.event_date or e.created_at or "", reverse=True
        )
        return {"count": min(len(rows), limit), "events": [e.model_dump(mode="json") for e in rows[:limit]]}

    def trust(self) -> dict[str, Any]:
        self._require()
        if not self.store.health:
            recompute_all_health(self.store)
        rows = sorted(self.store.health.values(), key=lambda h: -h.trust_score)
        return {
            "count": len(rows),
            "average_trust": round(sum(h.trust_score for h in rows) / len(rows), 2) if rows else 0.0,
            "companies": [h.model_dump(mode="json") for h in rows],
        }

    def list_sources(self) -> dict[str, Any]:
        self._require()
        return {
            "count": len(self.store.sources),
            "sources": [s.model_dump(mode="json") for s in sorted(self.store.sources.values(), key=lambda s: s.name)],
        }

    def verification_queue(self) -> dict[str, Any]:
        self._require()
        open_tasks = [t for t in self.store.tasks if t.status == "open"]
        return {"count": len(open_tasks), "tasks": [t.model_dump(mode="json") for t in open_tasks[-100:]]}

    def run_verification_jobs(self) -> dict[str, Any]:
        self._require()
        if not self.flags.eve_daily_jobs:
            raise RuntimeError("EVE daily jobs disabled")
        return run_daily_verification(self.store)

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        q = (query or "").lower().strip()
        hits: list[dict[str, Any]] = []
        if not q:
            return {"query": query, "hits": [], "count": 0}
        for e in self.store.active_evidence():
            blob = f"{e.fact_key} {e.value_text} {e.company_symbol} {e.raw_field}".lower()
            if q in blob or any(tok in blob for tok in q.split() if len(tok) > 2):
                hits.append(
                    {
                        "kind": "evidence",
                        "id": e.evidence_id,
                        "label": f"{e.company_symbol or e.company_id or 'macro'} · {e.fact_key}",
                        "score": float(e.confidence),
                        "confidence": e.confidence,
                        "verification_status": e.verification_status,
                        "snippet": e.value_text[:200],
                    }
                )
        for c in self.store.conflicts.values():
            if c.status != "open":
                continue
            blob = f"{c.fact_key} {c.left_value} {c.right_value}".lower()
            if q in blob:
                hits.append(
                    {
                        "kind": "conflict",
                        "id": c.conflict_id,
                        "label": f"Conflict · {c.fact_key}",
                        "score": 0.5,
                        "snippet": f"{c.left_value[:80]} vs {c.right_value[:80]}",
                    }
                )
        hits.sort(key=lambda h: -float(h.get("score") or 0))
        return {"query": query, "hits": hits[:limit], "count": len(hits[:limit])}

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Ask AGI soft retrieval — highest-confidence evidence first; surface conflicts."""
        self._require()
        search = self.search(query, limit=limit)
        company_pack = None
        # Prefer AOI registry resolution
        if self.aoi is not None:
            try:
                co = self.aoi.registry.resolve(query)
                if co:
                    company_pack = self.company_pack(co.company_id)
            except Exception:
                company_pack = None
        if company_pack is None:
            # try symbol-like token
            for tok in (query or "").upper().split():
                if self.aoi is not None:
                    try:
                        co = self.aoi.registry.by_symbol(tok)
                        if co:
                            company_pack = self.company_pack(co.company_id)
                            break
                    except Exception:
                        pass

        evidence_hits = [h for h in search["hits"] if h.get("kind") == "evidence"]
        conflict_hits = [h for h in search["hits"] if h.get("kind") == "conflict"]
        low_confidence = [h for h in evidence_hits if float(h.get("confidence") or 0) < 0.55]
        # FAPI — Academy accounting intelligence for verification (additive)
        finance_academy: dict = {}
        try:
            from academy.fapi.production import attach_for_engine

            finance_academy = attach_for_engine("eve", query).get("finance_academy") or {}
        except Exception:
            finance_academy = {}
        return {
            "answer_policy": "verified_evidence_before_raw_facts",
            "query": query,
            "hits": search["hits"],
            "company": company_pack,
            "conflicts": conflict_hits,
            "low_confidence": low_confidence,
            "guidance": {
                "use_highest_confidence_first": True,
                "present_conflicts": bool(conflict_hits),
                "avoid_hallucinated_certainty": True,
                "inform_reasoning_if_low_confidence": bool(low_confidence),
                "academy_accounting_rules": True,
            },
            "primary_source_of_truth": "verified_evidence",
            "finance_academy": finance_academy,
        }

    def audit_logs(self, *, limit: int = 50) -> dict[str, Any]:
        self._require()
        rows = self.store.audit[-limit:]
        return {"count": len(rows), "audit": [a.model_dump(mode="json") for a in reversed(rows)]}

    def _require(self) -> None:
        if not self.flags.eve:
            raise RuntimeError("EVE is disabled (EVE=false)")
