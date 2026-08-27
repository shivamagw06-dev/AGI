"""FLE service facade — forecast registry, outcomes, learning, Ask AGI consult."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.fle.engines import FleEngines
from app.fle.flags import FleFlags
from app.fle.pipeline import FlePipeline
from app.fle.store import FleStore


class FleService:
    """Forecasting & Learning Engine — after IIE, before reasoning."""

    def __init__(
        self,
        *,
        flags: FleFlags | None = None,
        store: FleStore | None = None,
        iie: Any | None = None,
        eve: Any | None = None,
        kf: Any | None = None,
        kc: Any | None = None,
        aoi: Any | None = None,
    ) -> None:
        self.flags = flags or FleFlags.from_settings(get_settings())
        self.store = store or FleStore()
        self.iie = iie
        self.eve = eve
        self.kf = kf
        self.kc = kc
        self.aoi = aoi
        self.engines = FleEngines(self.store, iie=iie, eve=eve)
        self.pipeline = FlePipeline(self.store, self.engines)

    def bind_iie(self, iie: Any) -> None:
        self.iie = iie
        self.engines.iie = iie

    def bind_eve(self, eve: Any) -> None:
        self.eve = eve
        self.engines.eve = eve

    def health(self) -> dict[str, Any]:
        snap = self.store.snapshot() if self.flags.fle else {}
        return {
            "status": "ok" if self.flags.fle else "disabled",
            "layer": "Forecasting & Learning Engine",
            "programme": "FLE",
            "version": "fle-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "after_iie_before_reasoning",
            "no_redesign": ["kf1", "kcv1", "aoi", "eve", "iie", "kip", "irp", "rsp", "ask_agi"],
            "inputs": ["iie", "eve_verified_evidence", "user_request", "scheduled_jobs"],
            "invariants": [
                "forecasts_immutable",
                "never_overwrite",
                "always_version",
                "assumptions_required",
                "evidence_required",
            ],
            "flags": self.flags.as_dict(),
            "snapshot": snap,
            "metrics": self.store.metrics.model_dump(),
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        self.engines.mark_review_due()
        forecasts = sorted(self.store.active_forecasts(), key=lambda f: f.created_at, reverse=True)
        pending = [f for f in forecasts if f.status in {"review_due", "pending"}]
        resolved = [
            self.store.outcomes[fid].to_dict()
            for fid in list(self.store.outcomes.keys())[-40:]
        ]
        learnings = sorted(self.store.learnings.values(), key=lambda l: l.created_at, reverse=True)
        cal = self.store.calibration_history[-1].to_dict() if self.store.calibration_history else {}
        acc = self.store.accuracy.get("global|all")
        heatmap = [
            {
                "company_id": h.company_id,
                "accuracy": h.forecast_accuracy,
                "coverage": h.forecast_coverage,
                "pending": h.pending_reviews,
                "confidence": h.average_confidence,
                "calibration": h.calibration_label,
                "learning_score": h.learning_score,
            }
            for h in sorted(self.store.health.values(), key=lambda x: -x.forecast_accuracy)[:50]
        ]
        return {
            "programme": "FLE",
            "architecture_status": "v1.0.1 LOCKED",
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
            "pending_reviews": [f.to_dict() for f in pending[:40]],
            "recent_forecasts": [f.to_dict() for f in forecasts[:40]],
            "resolved_forecasts": resolved[-40:],
            "accuracy": acc.to_dict() if acc else {},
            "calibration": cal,
            "learnings": [l.to_dict() for l in learnings[:30]],
            "heatmap": heatmap,
            "sector_accuracy": [
                s.to_dict() for k, s in self.store.accuracy.items() if k.startswith("sector|")
            ][:30],
            "macro_accuracy": [
                s.to_dict()
                for k, s in self.store.accuracy.items()
                if k.startswith("metric|") and s.scope_id in {"gdp", "inflation", "repo_rate", "oil", "usd_inr"}
            ],
            "expired": [
                f.to_dict()
                for f in self.store.forecasts.values()
                if f.status == "expired" or f.soft_deleted
            ][:20],
            "audit": [a.to_dict() for a in self.store.audit[-30:]],
        }

    def create_forecast(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require()
        fc = self.engines.create_forecast(
            metric=str(payload.get("metric") or ""),
            predicted_value=str(payload.get("predicted_value") or payload.get("value") or ""),
            company_id=str(payload.get("company_id") or ""),
            company_symbol=str(payload.get("company_symbol") or payload.get("symbol") or ""),
            sector_id=str(payload.get("sector_id") or ""),
            theme_ids=list(payload.get("theme_ids") or []),
            forecast_type=payload.get("forecast_type"),
            direction=str(payload.get("direction") or ""),
            confidence=float(payload.get("confidence") or 0.55),
            probability=float(payload.get("probability") or 0.5),
            origin=str(payload.get("origin") or "user_request"),
            assumptions=list(payload.get("assumptions") or []),
            evidence_ids=list(payload.get("evidence_ids") or []),
            evidence_links=list(payload.get("evidence_links") or []),
            horizon_days=int(payload.get("horizon_days") or 90),
            tags=list(payload.get("tags") or []),
            why=str(payload.get("why") or ""),
            risks=list(payload.get("risks") or []),
            thesis_id=str(payload.get("thesis_id") or ""),
            risk_ids=list(payload.get("risk_ids") or []),
            catalyst_ids=list(payload.get("catalyst_ids") or []),
            unit=str(payload.get("unit") or ""),
            predicted_numeric=payload.get("predicted_numeric"),
            priority=str(payload.get("priority") or "normal"),
        )
        return fc.to_dict()

    def get_forecast(self, forecast_id: str) -> dict[str, Any]:
        self._require()
        fc = self.store.forecasts.get(forecast_id)
        if not fc or fc.soft_deleted:
            raise KeyError(f"Forecast '{forecast_id}' not found")
        outcome = self.store.outcomes.get(forecast_id)
        learnings = [l.to_dict() for l in self.store.learnings.values() if l.forecast_id == forecast_id]
        versions = [
            f.to_dict()
            for f in self.store.forecasts.values()
            if f.forecast_id == forecast_id or f.parent_forecast_id == forecast_id or fc.parent_forecast_id == f.forecast_id
        ]
        return {
            "forecast": fc.to_dict(),
            "outcome": outcome.to_dict() if outcome else {},
            "learnings": learnings,
            "versions": versions,
        }

    def list_forecasts(
        self,
        *,
        company_id: str | None = None,
        sector_id: str | None = None,
        metric: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require()
        rows = self.store.active_forecasts(
            company_id=company_id, sector_id=sector_id, metric=metric, status=status
        )
        rows = sorted(rows, key=lambda f: f.created_at, reverse=True)[:limit]
        return {"count": len(rows), "forecasts": [f.to_dict() for f in rows]}

    def company(self, key: str, *, generate_if_empty: bool = True) -> dict[str, Any]:
        self._require()
        company_id = key
        # Resolve via IIE/AOI soft
        if self.iie:
            try:
                pack = self.iie.company(key, analyse_if_missing=False)
                if isinstance(pack, dict) and pack.get("company_id"):
                    company_id = pack["company_id"]
            except Exception:
                pass
        history = self.store.history_for_company(company_id)
        if not history and company_id != key:
            history = self.store.history_for_company(key)
        if not history and generate_if_empty and self.iie:
            try:
                self.pipeline.generate_from_iie(key)
                history = self.store.history_for_company(company_id) or self.store.history_for_company(key)
                if history:
                    company_id = history[0].company_id or company_id
            except Exception:
                pass
        pending = [f for f in history if f.status in {"active", "pending", "review_due"} and not f.soft_deleted]
        resolved = [f for f in history if f.forecast_id in self.store.outcomes]
        learnings = [l for l in self.store.learnings.values() if l.company_id in {company_id, key}]
        health = self.store.health.get(company_id) or self.store.health.get(key)
        acc = self.store.accuracy.get(f"company|{company_id}")
        return {
            "company_id": company_id,
            "historical_forecasts": [f.to_dict() for f in history[:50]],
            "pending_forecasts": [f.to_dict() for f in pending[:30]],
            "resolved_forecasts": [
                {
                    "forecast": f.to_dict(),
                    "outcome": self.store.outcomes[f.forecast_id].to_dict(),
                }
                for f in resolved[:30]
            ],
            "accuracy_trend": acc.to_dict() if acc else {},
            "confidence_trend": [
                {"forecast_id": f.forecast_id, "confidence": f.confidence, "created_at": f.created_at}
                for f in history[:30]
            ],
            "learning_history": [l.to_dict() for l in learnings[:30]],
            "version_history": [
                {"forecast_id": f.forecast_id, "version": f.version, "parent": f.parent_forecast_id, "status": f.status}
                for f in history
                if f.version > 1 or f.parent_forecast_id
            ][:30],
            "health": health.to_dict() if health else {},
        }

    def resolve(self, forecast_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require()
        if not self.flags.fle_auto_resolve and not payload.get("force"):
            # still allow explicit resolve
            pass
        return self.engines.resolve(
            forecast_id,
            actual_value=str(payload.get("actual_value") or payload.get("actual") or ""),
            actual_numeric=payload.get("actual_numeric"),
            notes=str(payload.get("notes") or ""),
            evidence_ids=list(payload.get("evidence_ids") or []),
        )

    def outcomes(self, *, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        rows = list(self.store.outcomes.values())
        if company_id:
            rows = [
                o
                for o in rows
                if (self.store.forecasts.get(o.forecast_id)
                    and (
                        self.store.forecasts[o.forecast_id].company_id == company_id
                        or self.store.forecasts[o.forecast_id].company_symbol == company_id
                    ))
            ]
        rows = sorted(rows, key=lambda o: o.resolution_date, reverse=True)[:limit]
        return {"count": len(rows), "outcomes": [o.to_dict() for o in rows]}

    def learning(self, *, q: str | None = None, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        if not self.flags.fle_learning:
            raise RuntimeError("FLE learning disabled")
        rows = list(self.store.learnings.values())
        if company_id:
            rows = [l for l in rows if l.company_id == company_id]
        if q:
            ql = q.lower()
            rows = [l for l in rows if ql in (l.searchable_text or "").lower() or ql in l.metric]
        rows = sorted(rows, key=lambda l: l.created_at, reverse=True)[:limit]
        return {"count": len(rows), "learnings": [l.to_dict() for l in rows]}

    def calibration(self) -> dict[str, Any]:
        self._require()
        if not self.flags.fle_calibration:
            raise RuntimeError("FLE calibration disabled")
        if not self.store.calibration_history:
            snap = self.engines.recompute_calibration()
        else:
            snap = self.store.calibration_history[-1]
        return {
            "current": snap.to_dict(),
            "history": [s.to_dict() for s in self.store.calibration_history[-20:]],
        }

    def scenarios(self, forecast_id: str) -> dict[str, Any]:
        self._require()
        if not self.flags.fle_scenarios:
            raise RuntimeError("FLE scenarios disabled")
        fc = self.store.forecasts.get(forecast_id)
        if not fc:
            raise KeyError(f"Forecast '{forecast_id}' not found")
        return {
            "forecast_id": forecast_id,
            "bull": fc.bull.to_dict(),
            "base": fc.base.to_dict(),
            "bear": fc.bear.to_dict(),
        }

    def accuracy(self, *, scope: str | None = None, scope_id: str | None = None) -> dict[str, Any]:
        self._require()
        if not self.store.accuracy:
            self.engines.recompute_accuracy()
        if scope and scope_id:
            row = self.store.accuracy.get(f"{scope}|{scope_id}")
            return {"accuracy": row.to_dict() if row else {}}
        return {
            "count": len(self.store.accuracy),
            "accuracy": [a.to_dict() for a in self.store.accuracy.values()],
        }

    def history(self, *, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        if company_id:
            rows = self.store.history_for_company(company_id)[:limit]
        else:
            rows = sorted(self.store.forecasts.values(), key=lambda f: f.created_at, reverse=True)[:limit]
        return {"count": len(rows), "history": [f.to_dict() for f in rows]}

    def generate(self, key: str) -> dict[str, Any]:
        self._require()
        return self.pipeline.generate_from_iie(key)

    def batch(self, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        return self.pipeline.batch_from_iie_profiles(limit=limit)

    def run_jobs(self) -> dict[str, Any]:
        self._require()
        return self.pipeline.run_resolution_jobs()

    def version(self, forecast_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require()
        fc = self.engines.version_forecast(forecast_id, **payload)
        return fc.to_dict()

    def compare(self, forecast_id: str) -> dict[str, Any]:
        self._require()
        fc = self.store.forecasts.get(forecast_id)
        if not fc:
            raise KeyError(f"Forecast '{forecast_id}' not found")
        prior = self.store.forecasts.get(fc.parent_forecast_id) if fc.parent_forecast_id else None
        similar = [
            f
            for f in self.store.active_forecasts(metric=fc.metric)
            if f.forecast_id != forecast_id and f.company_id == fc.company_id
        ][:5]
        acc = self.store.accuracy.get(f"metric|{fc.metric}")
        return {
            "current": fc.to_dict(),
            "previous": prior.to_dict() if prior else {},
            "historical_accuracy": acc.to_dict() if acc else {},
            "similar_internal": [f.to_dict() for f in similar],
            "consensus": {},  # reserved v2
            "analyst_views": {},  # reserved v2
            "version_delta": {
                "version": fc.version,
                "parent_forecast_id": fc.parent_forecast_id,
                "predicted_value_changed": bool(prior and prior.predicted_value != fc.predicted_value),
                "confidence_delta": round(fc.confidence - prior.confidence, 4) if prior else 0.0,
            },
        }

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        q = (query or "").lower().strip()
        hits: list[dict[str, Any]] = []
        if not q:
            return {"query": query, "hits": [], "count": 0}
        for f in self.store.forecasts.values():
            if f.soft_deleted:
                continue
            blob = f"{f.company_id} {f.company_symbol} {f.metric} {f.predicted_value} {' '.join(f.tags)}".lower()
            if q in blob or any(tok in blob for tok in q.split() if len(tok) > 2):
                hits.append(
                    {
                        "kind": "forecast",
                        "id": f.forecast_id,
                        "label": f"{f.company_symbol or f.company_id} · {f.metric}",
                        "score": float(f.confidence),
                        "status": f.status,
                        "snippet": f.predicted_value[:200],
                    }
                )
        for l in self.store.learnings.values():
            if q in (l.searchable_text or "").lower() or q in l.metric:
                hits.append(
                    {
                        "kind": "learning",
                        "id": l.learning_id,
                        "label": f"Learning · {l.metric} · {l.company_id}",
                        "score": 0.6,
                        "snippet": "; ".join(l.lessons_learned)[:200],
                    }
                )
        hits.sort(key=lambda h: -float(h.get("score") or 0))
        return {"query": query, "hits": hits[:limit], "count": len(hits[:limit])}

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Ask AGI soft retrieval — forecast history + calibration before reasoning."""
        self._require()
        search = self.search(query, limit=limit)
        company_pack = None
        # Resolve company
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
                    hist = self.store.history_for_company(tok)
                    if hist:
                        resolved = hist[0].company_id or tok
                        break
                    if self.iie is not None:
                        try:
                            pack = self.iie.company(tok, analyse_if_missing=False)
                            if isinstance(pack, dict) and pack.get("company_id"):
                                resolved = pack["company_id"]
                                break
                        except Exception:
                            pass
        if resolved:
            try:
                company_pack = self.company(resolved, generate_if_empty=True)
            except Exception:
                company_pack = None

        cal = self.store.calibration_history[-1] if self.store.calibration_history else None
        if cal is None and self.store.outcomes:
            cal = self.engines.recompute_calibration()

        # Surface poor historical performance / miscalibration
        uncertainty_flags: list[str] = []
        if company_pack and company_pack.get("accuracy_trend"):
            acc = company_pack["accuracy_trend"]
            if float(acc.get("mean_accuracy_score") or 1) < 0.45 and int(acc.get("resolved_count") or 0) >= 1:
                uncertainty_flags.append("historically_weak_on_similar_forecasts")
        if cal and cal.calibration_drift > 0.15:
            uncertainty_flags.append("overconfident_calibration_drift")
        if cal and cal.calibration_drift < -0.15:
            uncertainty_flags.append("underconfident_calibration_drift")

        reduce_certainty = bool(uncertainty_flags)
        finance_academy: dict = {}
        try:
            from academy.fapi.production import attach_for_engine

            finance_academy = attach_for_engine("fle", query).get("finance_academy") or {}
        except Exception:
            finance_academy = {}
        return {
            "answer_policy": "forecast_history_and_calibration_before_reasoning",
            "query": query,
            "hits": search["hits"],
            "company": company_pack,
            "current_predictions": (company_pack or {}).get("pending_forecasts") or [],
            "calibration": cal.to_dict() if cal else {},
            "learnings": (company_pack or {}).get("learning_history") or [],
            "uncertainty_flags": uncertainty_flags,
            "guidance": {
                "use_forecast_history_first": True,
                "surface_poor_historical_accuracy": "historically_weak_on_similar_forecasts" in uncertainty_flags,
                "reduce_certainty_if_miscalibrated": reduce_certainty,
                "never_forget_predictions": True,
                "immutable_forecasts": True,
                "academy_forecast_drivers": True,
            },
            "primary_source_of_truth": "forecast_registry",
            "finance_academy": finance_academy,
        }

    def _require(self) -> None:
        if not self.flags.fle:
            raise RuntimeError("FLE is disabled (FLE=false)")
