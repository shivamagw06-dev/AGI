"""FLE pipeline — batch forecast generation and resolution jobs."""

from __future__ import annotations

import time
from typing import Any

from app.fle.engines import FleEngines
from app.fle.store import FleStore


class FlePipeline:
    def __init__(self, store: FleStore, engines: FleEngines) -> None:
        self.store = store
        self.engines = engines

    def generate_from_iie(self, company_key: str) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            created = self.engines.create_from_iie(company_key)
            self.store.metrics.forecast_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            self.store.audit_event(
                "generate_from_iie",
                object_kind="company",
                object_id=company_key,
                detail=str(len(created)),
            )
            return {
                "company": company_key,
                "created": len(created),
                "forecasts": [f.to_dict() for f in created],
            }
        except Exception as exc:
            self.store.metrics.forecast_failures += 1
            self.store.audit_event(
                "generate_from_iie_failed",
                object_kind="company",
                object_id=company_key,
                detail=str(exc)[:200],
            )
            raise

    def batch_from_iie_profiles(self, *, limit: int = 20) -> dict[str, Any]:
        if not self.engines.iie:
            return {"created": 0, "companies": []}
        try:
            dash = self.engines.iie.dashboard()
            profiles = dash.get("recent_profiles") if isinstance(dash, dict) else []
        except Exception:
            profiles = []
        companies = []
        total = 0
        for p in (profiles or [])[:limit]:
            cid = p.get("company_id") if isinstance(p, dict) else None
            if not cid:
                continue
            try:
                out = self.generate_from_iie(cid)
                total += out["created"]
                companies.append(cid)
            except Exception:
                continue
        return {"created": total, "companies": companies}

    def run_resolution_jobs(self, *, limit: int = 50) -> dict[str, Any]:
        self.engines.mark_review_due()
        result = self.engines.auto_resolve_from_evidence(limit=limit)
        self.store.audit_event("resolution_jobs", detail=str(result))
        return result
