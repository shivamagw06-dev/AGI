"""MEE service facade — canonical events, timelines, impact, Ask AGI consult."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.mee.engines import MeeEngines
from app.mee.flags import MeeFlags
from app.mee.pipeline import MeePipeline
from app.mee.store import MeeStore


class MeeService:
    """Market Event Engine — after FLE; event backbone for AGI."""

    def __init__(
        self,
        *,
        flags: MeeFlags | None = None,
        store: MeeStore | None = None,
        eve: Any | None = None,
        iie: Any | None = None,
        fle: Any | None = None,
        aoi: Any | None = None,
        kf: Any | None = None,
        kc: Any | None = None,
    ) -> None:
        self.flags = flags or MeeFlags.from_settings(get_settings())
        self.store = store or MeeStore()
        self.eve = eve
        self.iie = iie
        self.fle = fle
        self.aoi = aoi
        self.kf = kf
        self.kc = kc
        self.engines = MeeEngines(self.store, eve=eve, iie=iie, fle=fle)
        self.pipeline = MeePipeline(self.store, self.engines)

    def bind_eve(self, eve: Any) -> None:
        self.eve = eve
        self.engines.eve = eve

    def bind_iie(self, iie: Any) -> None:
        self.iie = iie
        self.engines.iie = iie

    def bind_fle(self, fle: Any) -> None:
        self.fle = fle
        self.engines.fle = fle

    def health(self) -> dict[str, Any]:
        snap = self.store.snapshot() if self.flags.mee else {}
        return {
            "status": "ok" if self.flags.mee else "disabled",
            "layer": "Market Event Engine",
            "programme": "MEE",
            "version": "mee-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "after_fle_before_reasoning_and_future_pmo_ime_ams",
            "no_redesign": ["kf1", "kcv1", "aoi", "eve", "iie", "fle", "kip", "irp", "rsp", "ask_agi"],
            "inputs": ["eve_verified_evidence", "iie", "fle"],
            "never_consumes": ["unverified_raw_documents"],
            "future_consumers": ["pmo", "ime", "ams"],
            "invariants": ["events_immutable", "never_overwrite", "always_version", "never_delete"],
            "flags": self.flags.as_dict(),
            "snapshot": snap,
            "event_health": self.store.health.to_dict(),
            "metrics": self.store.metrics.model_dump(),
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        recent = sorted(self.store.active_events(), key=lambda e: e.detected_at, reverse=True)
        props = sorted(self.store.propagations, key=lambda p: p.created_at, reverse=True)
        return {
            "programme": "MEE",
            "architecture_status": "v1.0.1 LOCKED",
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
            "event_health": self.store.health.to_dict(),
            "live_feed": [e.to_dict() for e in recent[:40]],
            "queue": list(self.store.queue)[:40],
            "severity_dashboard": self._severity_counts(),
            "propagations": [p.to_dict() for p in props[:30]],
            "duplicates": [
                e.to_dict() for e in self.store.events.values() if e.duplicate_of
            ][:20],
            "impacts": [g.to_dict() for g in list(self.store.impacts.values())[:20]],
            "audit": [a.to_dict() for a in self.store.audit[-30:]],
        }

    def create_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require()
        if not self.flags.mee_auto_detect and not payload.get("force"):
            pass
        ev = self.engines.create_event(
            event_type=str(payload.get("event_type") or payload.get("type") or ""),
            title=str(payload.get("title") or payload.get("summary") or ""),
            summary=str(payload.get("summary") or payload.get("title") or ""),
            company_ids=list(payload.get("company_ids") or ([payload["company_id"]] if payload.get("company_id") else [])),
            company_symbols=list(payload.get("company_symbols") or ([payload["symbol"]] if payload.get("symbol") else [])),
            sector_ids=list(payload.get("sector_ids") or ([payload["sector_id"]] if payload.get("sector_id") else [])),
            theme_ids=list(payload.get("theme_ids") or []),
            evidence_ids=list(payload.get("evidence_ids") or []),
            evidence_links=list(payload.get("evidence_links") or []),
            confidence=float(payload.get("confidence") or 0.55),
            origin=str(payload.get("origin") or "user"),
            effective_date=payload.get("effective_date"),
            event_time=payload.get("event_time"),
            forecast_ids=list(payload.get("forecast_ids") or []),
            risk_ids=list(payload.get("risk_ids") or []),
            catalyst_ids=list(payload.get("catalyst_ids") or []),
            tags=list(payload.get("tags") or []),
            status=str(payload.get("status") or "detected"),
            country=str(payload.get("country") or "IN"),
        )
        if ev is None:
            return {"created": False, "reason": "duplicate_or_low_confidence"}
        if payload.get("verify", True):
            self.engines.verify(ev.event_id)
            ev = self.store.events[ev.event_id]
        return ev.to_dict()

    def get_event(self, event_id: str) -> dict[str, Any]:
        self._require()
        ev = self.store.events.get(event_id)
        if not ev or ev.soft_deleted:
            raise KeyError(f"Event '{event_id}' not found")
        impact = self.store.impacts.get(event_id)
        similar = self.engines.find_similar(event_id, limit=5) if self.flags.mee_similar else []
        rels = [
            r.to_dict()
            for r in self.store.relationships.values()
            if r.from_id == event_id or r.to_id == event_id
        ]
        props = [p.to_dict() for p in self.store.propagations if p.event_id == event_id]
        return {
            "event": ev.to_dict(),
            "impact": impact.to_dict() if impact else {},
            "similar": similar,
            "relationships": rels,
            "propagations": props,
        }

    def list_events(
        self,
        *,
        company_id: str | None = None,
        sector_id: str | None = None,
        theme_id: str | None = None,
        category: str | None = None,
        event_type: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require()
        rows = self.store.active_events(
            company_id=company_id,
            sector_id=sector_id,
            theme_id=theme_id,
            category=category,
            event_type=event_type,
            status=status,
            severity=severity,
        )
        rows = sorted(rows, key=lambda e: e.detected_at, reverse=True)[:limit]
        return {"count": len(rows), "events": [e.to_dict() for e in rows]}

    def company(self, key: str, *, detect: bool = True) -> dict[str, Any]:
        self._require()
        company_id = key
        if self.iie:
            try:
                pack = self.iie.company(key, analyse_if_missing=False)
                if isinstance(pack, dict) and pack.get("company_id"):
                    company_id = pack["company_id"]
            except Exception:
                pass
        if detect and self.flags.mee_auto_detect:
            if self.iie:
                try:
                    self.engines.ingest_from_iie(key)
                except Exception:
                    pass
            if self.fle:
                try:
                    self.engines.ingest_from_fle(key)
                except Exception:
                    pass
        events = self.store.active_events(company_id=company_id)
        if not events and company_id != key:
            events = self.store.active_events(company_id=key)
        timeline = [
            t.to_dict()
            for t in self.store.timelines
            if t.scope == "company" and t.scope_id in {company_id, key}
        ]
        timeline = sorted(timeline, key=lambda t: t.get("effective_date") or "", reverse=True)
        return {
            "company_id": company_id,
            "events": [e.to_dict() for e in sorted(events, key=lambda e: e.detected_at, reverse=True)[:50]],
            "timeline": timeline[:50],
            "count": len(events),
        }

    def sector(self, sector_id: str) -> dict[str, Any]:
        self._require()
        events = self.store.active_events(sector_id=sector_id)
        # also include impact-chain membership
        for eid, graph in self.store.impacts.items():
            if sector_id in graph.chain and eid in self.store.events:
                ev = self.store.events[eid]
                if ev not in events and not ev.soft_deleted and not ev.duplicate_of:
                    events.append(ev)
        timeline = [
            t.to_dict()
            for t in self.store.timelines
            if t.scope == "sector" and t.scope_id == sector_id
        ]
        return {
            "sector_id": sector_id,
            "events": [e.to_dict() for e in sorted(events, key=lambda e: e.detected_at, reverse=True)[:50]],
            "timeline": sorted(timeline, key=lambda t: t.get("effective_date") or "", reverse=True)[:50],
            "count": len(events),
        }

    def theme(self, theme_id: str) -> dict[str, Any]:
        self._require()
        events = self.store.active_events(theme_id=theme_id)
        timeline = [
            t.to_dict()
            for t in self.store.timelines
            if t.scope == "theme" and t.scope_id == theme_id
        ]
        return {
            "theme_id": theme_id,
            "events": [e.to_dict() for e in sorted(events, key=lambda e: e.detected_at, reverse=True)[:50]],
            "timeline": sorted(timeline, key=lambda t: t.get("effective_date") or "", reverse=True)[:50],
            "count": len(events),
        }

    def timeline(
        self,
        *,
        scope: str = "company",
        scope_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require()
        rows = [t for t in self.store.timelines if t.scope == scope]
        if scope_id:
            rows = [t for t in rows if t.scope_id == scope_id]
        rows = sorted(rows, key=lambda t: t.effective_date or t.created_at, reverse=True)[:limit]
        return {"count": len(rows), "timeline": [t.to_dict() for t in rows]}

    def impact(self, event_id: str) -> dict[str, Any]:
        self._require()
        if not self.flags.mee_impact:
            raise RuntimeError("MEE impact disabled")
        graph = self.store.impacts.get(event_id)
        if not graph:
            graph = self.engines.build_impact(event_id)
        return graph.to_dict()

    def relationships(self, *, event_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        self._require()
        rows = list(self.store.relationships.values())
        if event_id:
            rows = [r for r in rows if r.from_id == event_id or r.to_id == event_id]
        return {"count": min(len(rows), limit), "relationships": [r.to_dict() for r in rows[:limit]]}

    def history(self, *, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        rows = list(self.store.events.values())
        if company_id:
            rows = [
                e
                for e in rows
                if company_id in e.company_ids or company_id in e.company_symbols
            ]
        rows = sorted(rows, key=lambda e: e.created_at, reverse=True)[:limit]
        return {"count": len(rows), "history": [e.to_dict() for e in rows]}

    def similar(self, event_id: str, *, limit: int = 8) -> dict[str, Any]:
        self._require()
        if not self.flags.mee_similar:
            raise RuntimeError("MEE similar disabled")
        return {"event_id": event_id, "similar": self.engines.find_similar(event_id, limit=limit)}

    def verify(self, event_id: str) -> dict[str, Any]:
        self._require()
        ev = self.engines.verify(event_id)
        return ev.to_dict()

    def version(self, event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require()
        ev = self.engines.version_event(event_id, **payload)
        return ev.to_dict()

    def run_cycle(self, *, limit: int = 40) -> dict[str, Any]:
        self._require()
        return self.pipeline.run_detection_cycle(limit=limit)

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        q = (query or "").lower().strip()
        hits: list[dict[str, Any]] = []
        if not q:
            return {"query": query, "hits": [], "count": 0}
        for e in self.store.active_events():
            blob = (
                f"{e.event_type} {e.category} {e.title} {e.summary} "
                f"{' '.join(e.company_ids)} {' '.join(e.company_symbols)} "
                f"{' '.join(e.sector_ids)} {' '.join(e.theme_ids)} {' '.join(e.tags)}"
            ).lower()
            if q in blob or any(tok in blob for tok in q.split() if len(tok) > 2):
                hits.append(
                    {
                        "kind": "event",
                        "id": e.event_id,
                        "label": f"{e.event_type} · {e.title[:60]}",
                        "score": float(e.confidence) + (0.2 if e.severity in {"critical", "high"} else 0),
                        "severity": e.severity,
                        "status": e.status,
                        "snippet": e.summary[:200],
                    }
                )
        hits.sort(key=lambda h: -float(h.get("score") or 0))
        return {"query": query, "hits": hits[:limit], "count": len(hits[:limit])}

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Ask AGI soft retrieval — what changed before reasoning."""
        self._require()
        search = self.search(query, limit=limit)
        company_pack = None
        resolved = None
        if self.aoi is not None:
            try:
                co = self.aoi.registry.resolve(query)
                if co:
                    resolved = co.company_id or co.nse_symbol
            except Exception:
                resolved = None
        if resolved is None:
            for tok in (query or "").upper().split():
                if len(tok) >= 2 and tok.isalpha():
                    evs = self.store.active_events(company_id=tok)
                    if evs:
                        resolved = evs[0].company_ids[0] if evs[0].company_ids else tok
                        break
        if resolved:
            try:
                company_pack = self.company(resolved, detect=True)
            except Exception:
                company_pack = None

        recent = sorted(self.store.active_events(), key=lambda e: e.detected_at, reverse=True)[:limit]
        similar_bundle = []
        if recent and self.flags.mee_similar:
            similar_bundle = self.engines.find_similar(recent[0].event_id, limit=5)

        return {
            "answer_policy": "what_changed_before_reasoning",
            "query": query,
            "hits": search["hits"],
            "recent_events": [e.to_dict() for e in recent],
            "company": company_pack,
            "historical_similar_events": similar_bundle,
            "affected_companies": list(
                {
                    cid
                    for e in recent
                    for cid in e.company_ids
                }
            )[:20],
            "guidance": {
                "always_ask_what_changed": True,
                "use_event_context_first": True,
                "link_to_forecasts_and_intelligence": True,
                "immutable_events": True,
            },
            "primary_source_of_truth": "canonical_event_registry",
        }

    def _severity_counts(self) -> dict[str, int]:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
        for e in self.store.active_events():
            counts[e.severity] = counts.get(e.severity, 0) + 1
        return counts

    def _require(self) -> None:
        if not self.flags.mee:
            raise RuntimeError("MEE is disabled (MEE=false)")
