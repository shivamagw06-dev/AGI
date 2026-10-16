"""KF1 service facade — Knowledge Foundation V1."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.kf.flags import KfFlags
from app.kf.pipeline import KfPipeline
from app.kf.store import KfStore


class KfService:
    """Structured institutional knowledge layer over KIP.

    Does not redesign KIP / IRP / RSP / engines.
    """

    def __init__(
        self,
        *,
        kip: Any | None = None,
        flags: KfFlags | None = None,
        store: KfStore | None = None,
    ) -> None:
        self.flags = flags or KfFlags.from_settings(get_settings())
        self.kip = kip
        self.store = store or KfStore()
        self.pipeline = KfPipeline(self.store, kip=kip)
        if self.flags.kf:
            self.pipeline.ensure_seeded()

    def health(self) -> dict[str, Any]:
        seeded = self.pipeline.ensure_seeded() if self.flags.kf else {}
        cov = self.store.coverage(seeded=seeded) if self.flags.kf else None
        return {
            "status": "ok" if self.flags.kf else "disabled",
            "layer": "Knowledge Foundation",
            "programme": "KF1",
            "version": "kf-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "knowledge_objects_over_kip",
            "flags": self.flags.as_dict(),
            "coverage": cov.model_dump(mode="json") if cov else {},
            "priority": [
                "agi_research",
                "company_fundamentals",
                "sector_knowledge",
                "theme_knowledge",
                "macro_knowledge",
                "broker_research",
                "financial_news",
            ],
        }

    def seed(self) -> dict[str, Any]:
        self._require()
        counts = self.pipeline.seed()
        return {"seeded": counts, "coverage": self.coverage()}

    def coverage(self) -> dict[str, Any]:
        self._require()
        seeded = self.pipeline.ensure_seeded()
        return self.store.coverage(seeded=seeded).model_dump(mode="json")

    def rebuild(self) -> dict[str, Any]:
        self._require()
        stats = self.pipeline.rebuild_from_kip()
        return {"rebuild": stats, "coverage": self.coverage()}

    def on_document(self, doc: Any) -> dict[str, Any]:
        """Soft learning-pipeline hook after KIP ingest."""
        self._require()
        if not self.flags.kf_auto_build:
            return {"accepted": False, "reason": "KF_AUTO_BUILD=false"}
        ok = self.pipeline.ingest_document(doc)
        return {"accepted": ok, "coverage": self.coverage()}

    def get_company(self, ticker: str) -> dict[str, Any]:
        self._require()
        if not self.flags.kf_company:
            raise RuntimeError("KF company knowledge disabled")
        obj = self.pipeline.build_company(ticker)
        return obj.model_dump(mode="json")

    def get_sector(self, sector_id: str) -> dict[str, Any]:
        self._require()
        if not self.flags.kf_sector:
            raise RuntimeError("KF sector knowledge disabled")
        obj = self.pipeline.build_sector(sector_id)
        return obj.model_dump(mode="json")

    def get_theme(self, theme_id: str) -> dict[str, Any]:
        self._require()
        if not self.flags.kf_theme:
            raise RuntimeError("KF theme knowledge disabled")
        obj = self.pipeline.build_theme(theme_id)
        return obj.model_dump(mode="json")

    def get_macro(self, macro_id: str) -> dict[str, Any]:
        self._require()
        if not self.flags.kf_macro:
            raise RuntimeError("KF macro knowledge disabled")
        obj = self.pipeline.build_macro(macro_id)
        return obj.model_dump(mode="json")

    def list_companies(self) -> list[dict[str, Any]]:
        self._require()
        self.pipeline.ensure_seeded()
        return [
            {
                "ticker": c.ticker,
                "name": c.company_name,
                "sector": c.sector,
                "confidence": c.meta.confidence,
                "freshness": c.meta.freshness,
                "version": c.meta.version,
            }
            for c in sorted(self.store.companies.values(), key=lambda x: x.ticker)
        ]

    def list_sectors(self) -> list[dict[str, Any]]:
        self._require()
        self.pipeline.ensure_seeded()
        return [
            {
                "sector_id": s.sector_id,
                "label": s.label,
                "companies": len(s.major_companies),
                "confidence": s.meta.confidence,
                "freshness": s.meta.freshness,
                "current_agi_view": s.current_agi_view,
            }
            for s in sorted(self.store.sectors.values(), key=lambda x: x.label)
        ]

    def list_themes(self) -> list[dict[str, Any]]:
        self._require()
        self.pipeline.ensure_seeded()
        return [
            {
                "theme_id": t.theme_id,
                "label": t.label,
                "companies": len(t.companies),
                "confidence": t.meta.confidence,
                "freshness": t.meta.freshness,
            }
            for t in sorted(self.store.themes.values(), key=lambda x: x.label)
        ]

    def list_macros(self) -> list[dict[str, Any]]:
        self._require()
        self.pipeline.ensure_seeded()
        return [
            {
                "macro_id": m.macro_id,
                "label": m.label,
                "confidence": m.meta.confidence,
                "freshness": m.meta.freshness,
            }
            for m in sorted(self.store.macros.values(), key=lambda x: x.label)
        ]

    def list_predictions(self) -> list[dict[str, Any]]:
        self._require()
        if not self.flags.kf_predictions:
            raise RuntimeError("KF predictions disabled")
        self.pipeline.ensure_seeded()
        return [
            {
                "prediction_id": p.prediction_id,
                "prediction": p.prediction,
                "date": p.date,
                "company": p.company,
                "sector": p.sector,
                "theme": p.theme,
                "confidence": p.confidence,
                "status": p.status,
                "expected_timeline": p.expected_timeline,
                "expected_outcome": p.expected_outcome,
                "actual_outcome": p.actual_outcome,
            }
            for p in sorted(
                self.store.predictions.values(),
                key=lambda x: (x.date or "", x.prediction_id),
                reverse=True,
            )
        ]

    def list_extracts(self) -> list[dict[str, Any]]:
        self._require()
        self.pipeline.ensure_seeded()
        return [
            {
                "document_id": e.document_id,
                "title": e.title,
                "companies": e.companies,
                "sectors": e.sectors,
                "themes": e.themes,
                "confidence": e.confidence,
                "summary": e.summary[:240],
            }
            for e in sorted(self.store.extracts.values(), key=lambda x: x.document_id)
        ]

    def search(self, query: str, *, limit: int = 12) -> dict[str, Any]:
        """Prefer knowledge objects before raw documents."""
        self._require()
        hits = self.pipeline.search(query, limit=limit)
        hit_rows = [h.model_dump(mode="json") for h in hits]
        # FAPI — expose Finance Academy objects as first-class knowledge (additive)
        finance_academy: dict = {}
        try:
            from academy.fapi.production import attach_for_engine

            attached = attach_for_engine("kf", query, payload={"limit": limit})
            finance_academy = attached.get("finance_academy") or {}
            for c in (finance_academy.get("concepts") or [])[: max(1, min(limit, 8))]:
                hit_rows.append(
                    {
                        "kind": "finance_academy_concept",
                        "id": c.get("concept_id"),
                        "key": c.get("concept_id"),
                        "label": c.get("concept"),
                        "score": c.get("score"),
                        "snippet": (c.get("definition") or "")[:220],
                        "source": "finance_academy",
                        "course": c.get("course"),
                    }
                )
        except Exception:
            finance_academy = {}
        return {
            "query": query,
            "answer_policy": "knowledge_objects_before_documents",
            "hits": hit_rows[: max(limit + 8, limit)],
            "count": len(hit_rows[: max(limit + 8, limit)]),
            "finance_academy": finance_academy,
        }

    def _require(self) -> None:
        if not self.flags.kf:
            raise RuntimeError("KF is disabled (KF=false)")
