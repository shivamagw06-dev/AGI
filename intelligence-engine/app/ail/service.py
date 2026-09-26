"""AIL service facade — living institutional intelligence; soft-wire only."""

from __future__ import annotations

from typing import Any

from app.ail.cache import AilCache
from app.ail.catalog import resolve_ticker
from app.ail.flags import AilFlags
from app.ail.pipeline import AilPipeline
from app.ail.store import AilStore
from app.core.config import get_settings


class AilService:
    """AGIB Intelligence Layer V2 — CDE/EDE/TE/PE/CME/EL."""

    def __init__(
        self,
        *,
        flags: AilFlags | None = None,
        store: AilStore | None = None,
        fre: Any | None = None,
        faa: Any | None = None,
        cae: Any | None = None,
    ) -> None:
        self.flags = flags or AilFlags.from_settings(get_settings())
        self.store = store or AilStore()
        self.pipeline = AilPipeline(self.store)
        self.pipeline.bind(fre=fre, faa=faa, cae=cae)
        self.cache = AilCache(redis_enabled=self.flags.ail_redis_cache)

    def bind(self, **engines: Any) -> None:
        self.pipeline.bind(**engines)

    def _require(self) -> None:
        if not self.flags.ail:
            raise RuntimeError("AIL disabled")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.ail else "disabled",
            "programme": "AIL",
            "layer": "AGIB Intelligence Layer V2",
            "version": "ail-v2.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "after_faa_fre_before_cae_ask_agi",
            "systems": ["CDE", "EDE", "TE", "PE", "CME", "EL", "TIMELINE", "KG", "AUDIT"],
            "does_not_redesign": ["faa", "fre", "cae", "ask_agi"],
            "invariants": [
                "incremental_dossiers",
                "immutable_predictions",
                "evidence_ids_required",
                "explainable_thesis_updates",
                "continuous_monitoring",
            ],
            "flags": self.flags.as_dict(),
            "store": self.store.snapshot(),
            "ledger": self.pipeline.ledger.snapshot(),
            "cache": self.cache.stats(),
            "fre_bound": self.pipeline.fre is not None,
            "faa_bound": self.pipeline.faa is not None,
            "cae_bound": self.pipeline.cae is not None,
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        return {
            "programme": "AIL",
            "architecture_status": "v1.0.1 LOCKED",
            "store": self.store.snapshot(),
            "monitor": self.pipeline.monitor.status(),
            "covered_tickers": sorted(self.store.dossiers.keys()),
        }

    def analyse(self, query: str, *, ticker: str | None = None) -> dict[str, Any]:
        self._require()
        t = ticker or resolve_ticker(query)
        cache_key = f"analyse:{(t or query).upper()}"
        cached = self.cache.get(cache_key)
        # Always compute for freshness of audit trail; cache only dossier snapshot helpers
        pack = self.pipeline.analyse(query, ticker=t)
        if pack.get("ticker"):
            self.cache.set(cache_key, {"ticker": pack["ticker"], "at": pack.get("audit_trail", {}).get("created_at")})
        return pack

    def package_for_ask_agi(self, question: str, *, ticker: str | None = None) -> dict[str, Any]:
        if not self.flags.ail or not self.flags.ail_ask_agi:
            return {"enabled": False, "bypassed": True}
        # Architecture: Ask never calls faa.acquire — only cached FRE/FAA snapshots.
        pack = self.analyse(question, ticker=ticker, pull_faa=False)
        if pack.get("error"):
            return {"enabled": True, "error": pack.get("error"), "programme": "AIL"}
        return {
            "enabled": True,
            "programme": "AIL",
            "architecture_status": "v1.0.1 LOCKED",
            "ticker": pack.get("ticker"),
            "company": pack.get("company"),
            "dossier": pack.get("dossier"),
            "events": (pack.get("events") or [])[:10],
            "timeline": pack.get("timeline"),
            "thesis": pack.get("thesis"),
            "forecast": {
                "prediction_id": (pack.get("forecast") or {}).get("prediction_id"),
                "confidence": pack.get("prediction_confidence"),
                "scenario": (pack.get("forecast") or {}).get("scenario"),
                "distributions": (pack.get("forecast") or {}).get("distributions"),
            },
            "supporting_evidence_ids": pack.get("supporting_evidence_ids"),
            "contradictory_evidence_ids": pack.get("contradictory_evidence_ids"),
            "knowledge_graph": pack.get("knowledge_graph"),
            "audit_trail": pack.get("audit_trail"),
            "ask_agi_hints": [
                f"Living dossier v{(pack.get('dossier') or {}).get('version')} for {pack.get('ticker')}",
                f"Thesis bull/base/bear = {(pack.get('thesis') or {}).get('bull', {}).get('probability')}/"
                f"{(pack.get('thesis') or {}).get('base', {}).get('probability')}/"
                f"{(pack.get('thesis') or {}).get('bear', {}).get('probability')}",
                f"Forecast confidence {(pack.get('prediction_confidence') or 0):.2f}",
            ],
        }

    # --- REST resource helpers ---
    def dossier(self, ticker: str) -> dict[str, Any]:
        self._require()
        self.pipeline.bootstrap_company(ticker)
        return self.pipeline.dossier.get(ticker)

    def timeline(self, ticker: str, *, limit: int = 100) -> dict[str, Any]:
        self._require()
        self.pipeline.bootstrap_company(ticker)
        return self.pipeline.timeline.get(ticker, limit=limit)

    def events(self, ticker: str, *, limit: int = 50) -> dict[str, Any]:
        self._require()
        self.analyse(f"Monitor {ticker}", ticker=ticker)
        return {"programme": "EDE", "ticker": ticker.upper(), "events": self.pipeline.events.list_for(ticker, limit=limit)}

    def thesis(self, ticker: str) -> dict[str, Any]:
        self._require()
        self.analyse(f"Thesis {ticker}", ticker=ticker)
        return self.pipeline.thesis.get(ticker)

    def forecast(self, ticker: str) -> dict[str, Any]:
        self._require()
        self.analyse(f"Forecast {ticker}", ticker=ticker)
        return self.pipeline.predictions.get(ticker)

    def ledger(self, ticker: str) -> dict[str, Any]:
        self._require()
        self.pipeline.bootstrap_company(ticker)
        rows = [e.to_dict() for e in self.pipeline.ledger.for_ticker(ticker)]
        return {"programme": "EL", "ticker": ticker.upper(), "evidence": rows, "count": len(rows)}

    def monitor(self, ticker: str) -> dict[str, Any]:
        self._require()
        pack = self.analyse(f"Monitor {ticker}", ticker=ticker)
        return {
            "programme": "CME",
            "ticker": ticker.upper(),
            "status": self.pipeline.monitor.status(),
            "latest": {
                "dossier_version": (pack.get("dossier") or {}).get("version"),
                "thesis_id": (pack.get("thesis") or {}).get("thesis_id"),
                "prediction_id": (pack.get("forecast") or {}).get("prediction_id"),
                "events": len(pack.get("events") or []),
            },
        }

    def event(self, event_id: str) -> dict[str, Any]:
        self._require()
        row = self.pipeline.events.get(event_id)
        if not row:
            raise KeyError(event_id)
        return row

    def evidence(self, evidence_id: str) -> dict[str, Any]:
        self._require()
        row = self.pipeline.ledger.get(evidence_id)
        if not row:
            raise KeyError(evidence_id)
        return row.to_dict()

    def prediction(self, prediction_id: str) -> dict[str, Any]:
        self._require()
        row = self.pipeline.predictions.get_by_id(prediction_id)
        if not row:
            raise KeyError(prediction_id)
        return row

    def run_monitor(self, *, watchlist: str = "default") -> dict[str, Any]:
        self._require()

        def _fn(ticker: str) -> dict[str, Any]:
            pack = self.analyse(f"Continuous monitor {ticker}", ticker=ticker)
            return {
                "dossier_version": (pack.get("dossier") or {}).get("version"),
                "thesis_id": (pack.get("thesis") or {}).get("thesis_id"),
                "prediction_id": (pack.get("forecast") or {}).get("prediction_id"),
                "events": len(pack.get("events") or []),
            }

        return self.pipeline.monitor.run(_fn, watchlist=watchlist)
