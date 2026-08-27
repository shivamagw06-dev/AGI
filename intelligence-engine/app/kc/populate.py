"""Corpus population orchestration — compounds KF without redesigning it."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from app.aws.adapters import dump, soft
from app.kc.broker import apply_broker_knowledge, is_broker_doc
from app.kc.earnings import apply_earnings_memory, earnings_company_keys, is_earnings_doc
from app.kc.gaps import detect_gaps
from app.kc.learning import build_learning_digest
from app.kc.models import CorpusMetrics
from app.kc.quality import (
    average_quality,
    score_company,
    score_macro,
    score_sector,
    score_theme,
)
from app.kc.universes import (
    NIFTY_50,
    NIFTY_NEXT_50,
    all_universe_rows,
    nifty50_tickers,
    nifty_next50_tickers,
    nifty500_path_tickers,
)


class CorpusPopulator:
    def __init__(self, kf: Any, *, kip: Any | None = None) -> None:
        self.kf = kf
        self.kip = kip if kip is not None else getattr(kf, "kip", None)
        self.last_populated_at: str | None = None
        self.broker_count = 0
        self.earnings_count = 0
        self._quality_cache: list = []
        self._gaps_cache: list = []

    def ensure_universe_objects(self) -> dict[str, int]:
        """Phase 1 — permanent company intelligence objects for Nifty path."""
        self.kf.pipeline.ensure_seeded()
        created = 0
        for row in all_universe_rows():
            t = row["ticker"].upper()
            if t not in self.kf.store.companies:
                self.kf.pipeline._seed_company(
                    {
                        "ticker": t,
                        "name": row.get("name") or t,
                        "sector": row.get("sector") or "",
                        "industry": row.get("sector") or "",
                    }
                )
                created += 1
        return {
            "created": created,
            "companies": len(self.kf.store.companies),
            "nifty_50": len(NIFTY_50),
            "nifty_next_50": len(NIFTY_NEXT_50),
            "nifty_500_path": len(all_universe_rows()),
        }

    def populate(self, *, rebuild_kip: bool = True) -> dict[str, Any]:
        """Full corpus refresh: universe → KIP docs → dossiers → quality/gaps."""
        universe = self.ensure_universe_objects()
        doc_stats = {"documents": 0, "research": 0, "broker": 0, "earnings": 0}
        if rebuild_kip and self.kip is not None:
            doc_stats = self.ingest_all_kip_documents()

        # Build living dossiers for Nifty 50 first, then broaden.
        built_companies = 0
        for t in sorted(nifty500_path_tickers()):
            try:
                self.kf.pipeline.build_company(t)
                built_companies += 1
            except Exception:
                continue

        built_sectors = 0
        for sid in list(self.kf.store.sectors.keys()):
            try:
                self.kf.pipeline.build_sector(sid)
                built_sectors += 1
            except Exception:
                continue

        built_themes = 0
        for tid in list(self.kf.store.themes.keys()):
            try:
                self.kf.pipeline.build_theme(tid)
                built_themes += 1
            except Exception:
                continue

        built_macros = 0
        for mid in list(self.kf.store.macros.keys()):
            try:
                self.kf.pipeline.build_macro(mid)
                built_macros += 1
            except Exception:
                continue

        self.kf.pipeline._recompute_relationships()
        self._quality_cache = self.compute_quality()
        self._gaps_cache = detect_gaps(self.kf, earnings_keys=earnings_company_keys(self.kf))
        self.last_populated_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
        return {
            "universe": universe,
            "documents": doc_stats,
            "built": {
                "companies": built_companies,
                "sectors": built_sectors,
                "themes": built_themes,
                "macros": built_macros,
            },
            "quality_objects": len(self._quality_cache),
            "gaps": len(self._gaps_cache),
            "metrics": self.metrics().model_dump(mode="json"),
        }

    def ingest_all_kip_documents(self) -> dict[str, int]:
        store = getattr(self.kip, "store", None)
        documents = getattr(store, "documents", None) if store is not None else None
        stats = {"documents": 0, "research": 0, "broker": 0, "earnings": 0}
        if not isinstance(documents, dict):
            return stats
        for doc in documents.values():
            stats["documents"] += 1
            result = self.on_document(doc)
            if result.get("broker"):
                stats["broker"] += 1
            elif result.get("earnings"):
                stats["earnings"] += 1
            elif result.get("research"):
                stats["research"] += 1
        self.broker_count = stats["broker"]
        self.earnings_count = stats["earnings"]
        return stats

    def on_document(self, doc: Any) -> dict[str, Any]:
        """Every new document must improve AGI — extract structured knowledge."""
        self.kf.pipeline.ensure_seeded()
        out: dict[str, Any] = {"accepted": False}
        try:
            if is_broker_doc(doc):
                br = apply_broker_knowledge(self.kf, doc)
                out.update({"accepted": br.get("accepted"), "broker": True, "detail": br})
                return out
            if is_earnings_doc(doc):
                er = apply_earnings_memory(self.kf, doc)
                out.update({"accepted": er.get("accepted"), "earnings": True, "detail": er})
                return out
            # Default AGI / institutional research → KF extract + merge
            ok = self.kf.pipeline.ingest_document(doc)
            out.update({"accepted": ok, "research": True})
            return out
        except Exception as exc:
            return {"accepted": False, "error": str(exc)}

    def compute_quality(self) -> list:
        scores = []
        for co in self.kf.store.companies.values():
            scores.append(score_company(co))
        for sec in self.kf.store.sectors.values():
            scores.append(score_sector(sec))
        for th in self.kf.store.themes.values():
            scores.append(score_theme(th))
        for m in self.kf.store.macros.values():
            scores.append(score_macro(m))
        self._quality_cache = scores
        return scores

    def gaps(self) -> list:
        self._gaps_cache = detect_gaps(self.kf, earnings_keys=earnings_company_keys(self.kf))
        return self._gaps_cache

    def learning(self) -> Any:
        return build_learning_digest(self.kf)

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Knowledge Corpus first — objects before documents."""
        hits = self.kf.search(query, limit=limit)
        quality = {f"{s.object_kind}:{s.object_key}": s.overall_quality for s in (self._quality_cache or self.compute_quality())}
        enriched = []
        for h in hits.get("hits") or []:
            key = f"{h.get('kind')}:{h.get('key')}"
            enriched.append({**h, "quality": quality.get(key, h.get("confidence"))})
        enriched.sort(key=lambda x: (-float(x.get("quality") or 0), -float(x.get("score") or 0)))
        return {
            "answer_policy": "knowledge_corpus_before_documents",
            "query": query,
            "hits": enriched[:limit],
            "count": len(enriched[:limit]),
            "primary_source_of_truth": "knowledge_objects",
        }

    def metrics(self) -> CorpusMetrics:
        store = self.kf.store
        n50 = nifty50_tickers()
        nn50 = nifty_next50_tickers()
        n500 = nifty500_path_tickers()

        def covered(universe: set[str]) -> tuple[int, int, float]:
            have = 0
            for t in universe:
                co = store.companies.get(t)
                if co and (co.latest_thesis or co.business_description or co.related_research or co.meta.version > 1):
                    have += 1
                elif co:
                    have += 1  # seeded object counts as covered shell; quality tracks depth
            total = len(universe)
            pct = round(have / total, 4) if total else 0.0
            return have, total, pct

        c50, t50, p50 = covered(n50)
        c_n50, t_n50, p_n50 = covered(nn50)
        c500, t500, p500 = covered(n500)

        scores = self._quality_cache or self.compute_quality()
        gaps = self._gaps_cache or self.gaps()
        needs = [g for g in gaps if g.severity in {"critical", "high"}]

        # Heatmap by sector for Nifty 50
        heatmap: list[dict[str, Any]] = []
        sector_map: dict[str, list[str]] = {}
        for row in NIFTY_50:
            sector_map.setdefault(row.get("sector") or "Other", []).append(row["ticker"].upper())
        for sector, tickers in sorted(sector_map.items()):
            present = sum(1 for t in tickers if t in store.companies)
            avg_q = []
            for t in tickers:
                co = store.companies.get(t)
                if co:
                    avg_q.append(score_company(co).overall_quality)
            heatmap.append(
                {
                    "sector": sector,
                    "companies": len(tickers),
                    "covered": present,
                    "coverage": round(present / len(tickers), 4) if tickers else 0.0,
                    "avg_quality": round(sum(avg_q) / len(avg_q), 4) if avg_q else 0.0,
                }
            )

        recently: list[dict[str, Any]] = []
        for co in store.companies.values():
            recently.append(
                {
                    "kind": "company",
                    "key": co.ticker,
                    "label": co.company_name,
                    "updated_at": co.meta.updated_at.isoformat() if co.meta.updated_at else None,
                    "confidence": co.meta.confidence,
                    "freshness": co.meta.freshness,
                }
            )
        recently.sort(key=lambda r: r.get("updated_at") or "", reverse=True)

        confs = [float(c.meta.confidence) for c in store.companies.values()]
        fresh = [float(c.meta.freshness) for c in store.companies.values()]
        broker_reports = self.broker_count
        if broker_reports == 0:
            broker_reports = sum(1 for ex in store.extracts.values() if "broker" in " ".join(ex.meta.sources or []).lower())

        kf_cov = soft(self.kf.coverage) or {}
        if not isinstance(kf_cov, dict):
            kf_cov = dump(kf_cov) or {}

        return CorpusMetrics(
            nifty_50_coverage=p50,
            nifty_50_covered=c50,
            nifty_50_total=t50,
            nifty_next_50_coverage=p_n50,
            nifty_next_50_covered=c_n50,
            nifty_500_path_coverage=p500,
            nifty_500_path_covered=c500,
            nifty_500_path_total=t500,
            companies_covered=len(store.companies),
            sector_coverage=len(store.sectors),
            theme_coverage=len(store.themes),
            macro_coverage=len(store.macros),
            research_notes=len(store.extracts),
            broker_reports=broker_reports,
            predictions=len(store.predictions),
            knowledge_objects=(
                len(store.companies)
                + len(store.sectors)
                + len(store.themes)
                + len(store.macros)
                + len(store.predictions)
                + len(store.extracts)
            ),
            relationships=int(getattr(store, "relationships", 0) or 0),
            avg_freshness=round(sum(fresh) / len(fresh), 4) if fresh else float(kf_cov.get("avg_freshness") or 0),
            avg_confidence=round(sum(confs) / len(confs), 4) if confs else float(kf_cov.get("avg_confidence") or 0),
            avg_quality=average_quality(scores),
            research_structured=len(store.extracts),
            predictions_structured=len(store.predictions),
            gaps_open=len(gaps),
            needs_attention=len(needs),
            recently_updated=recently[:15],
            coverage_heatmap=heatmap,
            last_populated_at=self.last_populated_at,
        )
