"""MEE pipeline — batch detection, verification and propagation jobs."""

from __future__ import annotations

import time
from typing import Any

from app.mee.engines import MeeEngines
from app.mee.store import MeeStore


class MeePipeline:
    def __init__(self, store: MeeStore, engines: MeeEngines) -> None:
        self.store = store
        self.engines = engines

    def run_detection_cycle(self, *, limit: int = 40) -> dict[str, Any]:
        t0 = time.perf_counter()
        eve_out = self.engines.ingest_from_eve(limit=limit)
        # Soft IIE recent profiles
        iie_created = 0
        if self.engines.iie:
            try:
                dash = self.engines.iie.dashboard()
                profiles = dash.get("recent_profiles") if isinstance(dash, dict) else []
                for p in (profiles or [])[: min(10, limit)]:
                    cid = p.get("company_id") if isinstance(p, dict) else None
                    if not cid:
                        continue
                    out = self.engines.ingest_from_iie(cid)
                    iie_created += out.get("created") or 0
            except Exception:
                pass
        # Process remaining queue
        verified = 0
        for eid in list(self.store.queue)[:limit]:
            try:
                self.engines.verify(eid)
                verified += 1
            except Exception:
                self.store.metrics.processing_failures += 1
        self.store.metrics.api_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        self.store.audit_event(
            "detection_cycle",
            detail=f"eve={eve_out.get('created')} iie={iie_created} verified={verified}",
        )
        return {
            "eve_events": eve_out.get("created") or 0,
            "iie_events": iie_created,
            "verified": verified,
            "queue_depth": len(self.store.queue),
            "latency_ms": self.store.metrics.api_latency_ms,
        }
