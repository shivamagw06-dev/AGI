"""KCV1 service facade — Knowledge Corpus over Knowledge Foundation."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.kc.flags import KcFlags
from app.kc.populate import CorpusPopulator


class KcService:
    """Populate and continuously improve KF knowledge objects.

    Reads/writes via KF public surface + store. Does not redesign KF.
    """

    def __init__(
        self,
        *,
        kf: Any | None = None,
        kip: Any | None = None,
        flags: KcFlags | None = None,
    ) -> None:
        self.flags = flags or KcFlags.from_settings(get_settings())
        self.kf = kf
        self.kip = kip if kip is not None else getattr(kf, "kip", None)
        self.populator = CorpusPopulator(kf, kip=self.kip) if kf is not None else None

    def health(self) -> dict[str, Any]:
        metrics = {}
        if self.flags.kc and self.populator is not None:
            try:
                metrics = self.populator.metrics().model_dump(mode="json")
            except Exception:
                metrics = {}
        return {
            "status": "ok" if self.flags.kc and self.kf is not None else "disabled",
            "layer": "Knowledge Corpus",
            "programme": "KCV1",
            "version": "kc-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "populate_improve_knowledge_foundation",
            "depends_on": ["KF1", "KIP"],
            "no_redesign": ["architecture", "engines", "kip", "kf", "irp", "rsp"],
            "flags": self.flags.as_dict(),
            "metrics": metrics,
            "phases": [
                "company_dossiers",
                "sector_dossiers",
                "theme_dossiers",
                "macro_library",
                "research_extraction",
                "broker_knowledge",
                "earnings_memory",
                "daily_learning",
                "gap_detection",
                "knowledge_quality",
            ],
        }

    def populate(self, *, rebuild_kip: bool = True) -> dict[str, Any]:
        self._require()
        return self.populator.populate(rebuild_kip=rebuild_kip)

    def ensure_universe(self) -> dict[str, Any]:
        self._require()
        return self.populator.ensure_universe_objects()

    def metrics(self) -> dict[str, Any]:
        self._require()
        return self.populator.metrics().model_dump(mode="json")

    def dashboard(self) -> dict[str, Any]:
        """Executive dashboard payload."""
        self._require()
        metrics = self.populator.metrics().model_dump(mode="json")
        gaps = [g.model_dump(mode="json") for g in self.populator.gaps()[:40]]
        learning = self.populator.learning().model_dump(mode="json")
        quality = [
            q.model_dump(mode="json")
            for q in sorted(self.populator.compute_quality(), key=lambda s: -s.overall_quality)[:40]
        ]
        weak = [
            q.model_dump(mode="json")
            for q in sorted(self.populator.compute_quality(), key=lambda s: s.overall_quality)[:20]
        ]
        return {
            "programme": "KCV1",
            "architecture_status": "v1.0.1 LOCKED",
            "metrics": metrics,
            "gaps": gaps,
            "needs_attention": [g for g in gaps if g.get("severity") in {"critical", "high"}],
            "learning": learning,
            "top_quality": quality[:15],
            "weak_quality": weak,
            "answer_policy": "knowledge_corpus_before_documents",
        }

    def gaps(self) -> dict[str, Any]:
        self._require()
        if not self.flags.kc_gaps:
            raise RuntimeError("KC gaps disabled")
        items = [g.model_dump(mode="json") for g in self.populator.gaps()]
        return {"count": len(items), "tasks": items}

    def learning(self) -> dict[str, Any]:
        self._require()
        if not self.flags.kc_learning:
            raise RuntimeError("KC learning disabled")
        return self.populator.learning().model_dump(mode="json")

    def quality(self, *, kind: str | None = None, key: str | None = None) -> dict[str, Any]:
        self._require()
        if not self.flags.kc_quality:
            raise RuntimeError("KC quality disabled")
        scores = self.populator.compute_quality()
        if kind:
            scores = [s for s in scores if s.object_kind == kind]
        if key:
            scores = [s for s in scores if s.object_key.lower() == key.lower()]
        return {
            "count": len(scores),
            "avg_quality": round(sum(s.overall_quality for s in scores) / len(scores), 4) if scores else 0.0,
            "scores": [s.model_dump(mode="json") for s in scores[:200]],
        }

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        self._require()
        out = self.populator.consult(query, limit=limit)
        if not isinstance(out, dict):
            out = {"result": out}
        try:
            from academy.fapi.production import attach_for_engine

            attached = attach_for_engine("kcv", query, payload={"limit": limit})
            out["finance_academy"] = attached.get("finance_academy") or {}
        except Exception:
            out["finance_academy"] = {}
        return out

    def on_document(self, doc: Any) -> dict[str, Any]:
        """Soft corpus learning hook after KF/KIP ingest."""
        self._require()
        if not self.flags.kc_auto_populate:
            return {"accepted": False, "reason": "KC_AUTO_POPULATE=false"}
        from app.aws.adapters import dump
        from app.kc.broker import is_broker_doc
        from app.kc.earnings import is_earnings_doc

        # Plain research: KF already extracted — avoid duplicate merges.
        if not is_broker_doc(doc) and not is_earnings_doc(doc):
            d = dump(doc) if not isinstance(doc, dict) else doc
            document = d.get("document") if isinstance(d, dict) and isinstance(d.get("document"), dict) else {}
            doc_id = str((d or {}).get("document_id") or document.get("document_id") or "")
            if doc_id and doc_id in self.kf.store.extracts:
                return {"accepted": True, "research": True, "already_in_kf": True}
        return self.populator.on_document(doc)

    def _require(self) -> None:
        if not self.flags.kc:
            raise RuntimeError("KC is disabled (KC=false)")
        if self.kf is None or self.populator is None:
            raise RuntimeError("KC requires KF service")
