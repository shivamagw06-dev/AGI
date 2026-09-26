"""Historical Sector Analogue Engine — rank similar sector environments."""

from __future__ import annotations

from typing import Any

from historical_sector_analogue_intelligence import traces
from historical_sector_analogue_intelligence.query_builder import build_search_query
from historical_sector_analogue_intelligence.regimes import (
    build_current_regime,
    build_historical_regimes,
    normalize_sector,
    soft_sri_relationships,
    supported_sectors,
)
from historical_sector_analogue_intelligence.schema import (
    HSAI_VERSION,
    NO_HSAI_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    SIMILARITY_DIMENSIONS,
    HistoricalSectorAnalogue,
    SupportingEvidence,
    stable_analogue_id,
)
from historical_sector_analogue_intelligence.similarity import (
    confidence_for,
    explainability_bundle,
    key_differences,
    score_dimensions,
)
from historical_sector_analogue_intelligence.store import STORE


class HistoricalSectorAnalogueIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HSAI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_HSAI_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "consumes": ["CSKP", "HSIP", "SRI", "HMIP tips"],
            "feeds": ["Sector Forecast Intelligence (Sprint 11.5)"],
            "phase": "11.4",
            "preceded_by": ["CSKP 11.1", "HSIP 11.2", "SRI 11.3"],
            "supported_sectors": supported_sectors(),
            "similarity_dimensions": list(SIMILARITY_DIMENSIONS),
        }

    def run(
        self,
        *,
        sector: str | None = None,
        enrich_hsip: bool = True,
        enrich_cskp: bool = True,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Ops rebuild — score & publish ranked analogues. Never Ask."""
        rspan = traces.begin(
            "sector_analogue_refresh",
            meta={"sector": sector, "enrich_hsip": enrich_hsip},
        )
        sectors = [normalize_sector(sector) or sector] if sector else supported_sectors()
        STORE.clear()
        published = 0
        per_sector: dict[str, Any] = {}

        for sec in sectors:
            if not sec:
                continue
            current = build_current_regime(sector=sec, enrich_cskp=enrich_cskp)
            STORE.set_current_regime(current)
            historical = build_historical_regimes(sector=sec, enrich_hsip=enrich_hsip)
            STORE.set_regime_history(sec, historical)
            ranked = self._rank(
                current,
                historical,
                top_k=top_k,
                min_score=0.0,
                target_period=None,
            )
            for ana in ranked:
                STORE.publish(ana)
                published += 1
            per_sector[sec] = {
                "current_period": current.period,
                "historical_regimes": len(historical),
                "published": len(ranked),
                "top_similarity": ranked[0].similarity_score if ranked else None,
            }

        summary = {
            "ok": True,
            "sectors": list(per_sector.keys()),
            "published": published,
            "per_sector": per_sector,
            "ask_triggered": False,
            "providers_queried": [],
            "coverage": STORE.coverage(),
        }
        STORE.record_run(summary)
        traces.end(rspan, output={"published": published, "sectors": len(per_sector)})
        return summary

    def _rank(
        self,
        current,
        historical,
        *,
        top_k: int,
        min_score: float,
        target_period: str | None,
    ) -> list[HistoricalSectorAnalogue]:
        span = traces.begin(
            "sector_analogue_search",
            meta={
                "sector": current.sector,
                "current_period": current.period,
                "candidates": len(historical),
                "target_period": target_period,
            },
        )
        candidates = list(historical)
        if target_period:
            focused = [h for h in candidates if h.period == str(target_period)]
            if focused:
                candidates = focused
        traces.end(span, output={"candidates": len(candidates)})

        scored: list[HistoricalSectorAnalogue] = []
        for hist in candidates:
            if hist.period == current.period and hist.label == current.label:
                continue

            sspan = traces.begin(
                "sector_similarity_scoring",
                meta={"matched_period": hist.period, "label": hist.label, "sector": current.sector},
            )
            overall, details, matching, non_matching = score_dimensions(
                current.features, hist.features
            )
            evidence = self._evidence_for(current, hist)
            dims_scored = sum(
                1
                for d in details
                if d.current_value is not None and d.historical_value is not None
            )
            conf = confidence_for(
                overall, evidence_n=len(evidence), dimensions_scored=dims_scored
            )
            rels = soft_sri_relationships(current.sector)
            diffs = key_differences(details)
            explain = explainability_bundle(overall, details)
            ana = HistoricalSectorAnalogue(
                analogue_id=stable_analogue_id(
                    current.sector, current.period, hist.period
                ),
                sector=current.sector,
                sector_key=current.sector_key,
                country=current.country,
                current_regime=current.label,
                current_period=current.period,
                matched_period=hist.period,
                matched_label=hist.label,
                similarity_score=overall,
                confidence=conf,
                matching_dimensions=matching,
                non_matching_dimensions=non_matching,
                dimension_scores=details,
                historical_outcome=hist.outcome,
                equity_outcome=hist.equity_outcome,
                historical_outcome_bundle=dict(hist.historical_outcome_bundle or {}),
                key_differences=diffs,
                relevant_relationships=rels,
                supporting_evidence=evidence,
                supporting_research=list(
                    dict.fromkeys([*current.research_refs, *hist.research_refs])
                ),
                timeline_refs=list(
                    dict.fromkeys([*current.timeline_refs, *hist.timeline_refs])
                ),
                research_refs=list(
                    dict.fromkeys([*current.research_refs, *hist.research_refs])
                ),
                explainability=explain,
                provenance={
                    "current_layers": current.source_layers,
                    "historical_layers": hist.source_layers,
                    "hsip_overlay": (hist.provenance or {}).get("hsip_soft_confirmed"),
                },
            )
            traces.end(
                sspan,
                output={
                    "similarity_score": overall,
                    "confidence": conf,
                    "matching": matching,
                    "dimensions_scored": dims_scored,
                },
            )
            if overall >= min_score:
                scored.append(ana)

        rspan = traces.begin(
            "sector_analogue_ranking", meta={"n": len(scored), "top_k": top_k}
        )
        scored.sort(key=lambda a: a.similarity_score, reverse=True)
        if target_period:
            exact = [a for a in scored if a.matched_period == str(target_period)]
            rest = [a for a in scored if a.matched_period != str(target_period)]
            scored = exact + rest
        for i, ana in enumerate(scored[:top_k], start=1):
            ana.rank = i
        ranked = scored[:top_k]
        traces.end(
            rspan,
            output={
                "ranked": len(ranked),
                "top_score": ranked[0].similarity_score if ranked else None,
                "top_period": ranked[0].matched_period if ranked else None,
            },
        )
        return ranked

    def _evidence_for(self, current, hist) -> list[SupportingEvidence]:
        evidence: list[SupportingEvidence] = [
            SupportingEvidence(
                kind="historical_sector",
                summary=f"Historical sector regime {hist.period}: {hist.label}",
                period=hist.period,
                source_refs=list(hist.timeline_refs)[:4],
                weight=1.0,
            ),
            SupportingEvidence(
                kind="continuous_sector",
                summary=f"Current sector regime from CSKP tip ({current.period})",
                period=current.period,
                source_refs=["CSKP_KRIG"],
                weight=1.0,
            ),
        ]
        if hist.timeline_refs:
            evidence.append(
                SupportingEvidence(
                    kind="timeline",
                    summary="HSIP / institutional sector timeline anchors",
                    period=hist.period,
                    source_refs=list(hist.timeline_refs),
                    weight=0.8,
                )
            )
        if hist.research_refs:
            evidence.append(
                SupportingEvidence(
                    kind="research",
                    summary="Sector research office notes",
                    period=hist.period,
                    source_refs=list(hist.research_refs),
                    weight=0.7,
                )
            )
        if "HSIP" in (hist.source_layers or []):
            evidence.append(
                SupportingEvidence(
                    kind="historical_sector",
                    summary="HSIP timeline soft-confirmed catalog features",
                    period=hist.period,
                    source_refs=["HSIP_KRIG"],
                    weight=1.0,
                )
            )
        return evidence

    def search(
        self,
        *,
        sector: str | None = None,
        question: str | None = None,
        target_period: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
        persist: bool = False,
    ) -> dict[str, Any]:
        """Score analogues from soft-consumed knowledge — never collects."""
        q = build_search_query(
            sector=sector,
            question=question,
            target_period=target_period,
            top_k=top_k,
            min_score=min_score,
        )
        sec = q["sector"]
        current = STORE.current_regime(sec) or build_current_regime(sector=sec)
        historical = STORE.regime_history(sec) or build_historical_regimes(
            sector=sec, enrich_hsip=True
        )
        ranked = self._rank(
            current,
            historical,
            top_k=int(q["top_k"]),
            min_score=float(q["min_score"]),
            target_period=q.get("target_period"),
        )
        if persist:
            STORE.set_current_regime(current)
            STORE.set_regime_history(sec, historical)
            for ana in ranked:
                STORE.publish(ana)

        out = {
            "sector": sec,
            "question": question,
            "query": q,
            "current_regime": {
                "sector": current.sector,
                "period": current.period,
                "label": current.label,
                "features": current.features,
                "source_layers": current.source_layers,
            },
            "n": len(ranked),
            "analogues": [a.to_public_dict() for a in ranked],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HSAI_KRIG",
            "similarity_explainable": True,
        }
        return out

    def analogues(self, *, sector: str | None = None, limit: int = 20) -> dict[str, Any]:
        span = traces.begin(
            "sector_analogue_retrieval", meta={"scope": "list", "sector": sector}
        )
        sec = normalize_sector(sector) if sector else None
        rows = STORE.list_all(limit=limit, sector=sec)
        if not rows:
            computed = self.search(sector=sec or "Banking", top_k=limit, persist=False)
            traces.end(span, output={"n": computed["n"], "mode": "computed"})
            return {
                **computed,
                "mode": "computed",
                "coverage": STORE.coverage(),
            }
        cr = STORE.current_regime(sec) if sec else None
        out = {
            "sector": sec,
            "n": len(rows),
            "analogues": [r.to_public_dict() for r in rows],
            "current_regime": (
                {
                    "sector": cr.sector,
                    "period": cr.period,
                    "label": cr.label,
                    "features": cr.features,
                }
                if cr
                else None
            ),
            "coverage": STORE.coverage(),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HSAI_KRIG",
            "mode": "published",
            "similarity_explainable": True,
        }
        traces.end(span, output={"n": out["n"], "mode": "published"})
        return out

    def analogues_for_sector(self, sector: str, *, limit: int = 20) -> dict[str, Any]:
        sec = normalize_sector(sector) or sector
        out = self.analogues(sector=sec, limit=limit)
        out["sector"] = sec
        return out

    def current_regime(self, *, sector: str = "Banking") -> dict[str, Any]:
        span = traces.begin("sector_analogue_retrieval", meta={"scope": "current_regime"})
        sec = normalize_sector(sector) or sector
        regime = STORE.current_regime(sec) or build_current_regime(sector=sec)
        out = {
            "sector": sec,
            "regime": regime.model_dump(mode="json"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HSAI_KRIG",
        }
        traces.end(span, output={"period": regime.period, "sector": sec})
        return out

    def regime_history(self, *, sector: str = "Banking", limit: int = 50) -> dict[str, Any]:
        span = traces.begin("sector_analogue_retrieval", meta={"scope": "regime_history"})
        sec = normalize_sector(sector) or sector
        rows = STORE.regime_history(sec, limit=limit) or build_historical_regimes(
            sector=sec, enrich_hsip=True
        )
        out = {
            "sector": sec,
            "n": len(rows),
            "regimes": [r.model_dump(mode="json") for r in rows[:limit]],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HSAI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def forecast_tip(self, *, sector: str = "Banking", top_k: int = 5) -> dict[str, Any]:
        """Bundle for Sector Forecast Intelligence — store-only, no external APIs."""
        sec = normalize_sector(sector) or sector
        pack = self.search(sector=sec, top_k=top_k, persist=False)
        return {
            "gateway": "HSAI_KRIG",
            "collected_on_request": False,
            "providers_queried": [],
            "sector": sec,
            "current_regime": pack.get("current_regime"),
            "top_analogues": [
                {
                    "matched_period": a.get("matched_period"),
                    "matched_label": a.get("matched_label"),
                    "similarity_score": a.get("similarity_score"),
                    "confidence": a.get("confidence"),
                    "matching_dimensions": a.get("matching_dimensions"),
                    "non_matching_dimensions": a.get("non_matching_dimensions"),
                    "historical_outcome": a.get("historical_outcome"),
                    "equity_outcome": a.get("equity_outcome"),
                    "historical_outcome_bundle": a.get("historical_outcome_bundle"),
                    "key_differences": a.get("key_differences"),
                    "timeline_refs": a.get("timeline_refs"),
                    "supporting_research": a.get("supporting_research"),
                    "relevant_relationships": (a.get("relevant_relationships") or [])[:5],
                    "explainability": a.get("explainability"),
                }
                for a in pack.get("analogues") or []
            ],
            "n": pack.get("n"),
            "feeds_sprint": "11.5",
        }

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        rows = STORE.list_all(limit=40)
        if not rows:
            tip = self.search(sector="Banking", top_k=5, persist=False)
            rows_pub = tip.get("analogues") or []
            current = tip.get("current_regime")
        else:
            rows_pub = [r.to_public_dict() for r in rows]
            # Prefer Banking current if present
            cr = STORE.current_regime("Banking") or STORE.current_regime()
            current = (
                {
                    "sector": cr.sector,
                    "period": cr.period,
                    "label": cr.label,
                    "features": cr.features,
                }
                if cr
                else None
            )
        return {
            "board": "Historical Sector Analogue",
            "programme": PROGRAMME,
            "version": HSAI_VERSION,
            "principles": {
                "deterministic_similarity": True,
                "explainable_scores": True,
                "evidence_linked": True,
                "ask_never_fetches": True,
                "providers_queried_always_empty": True,
                "no_forecasting_in_11_4": True,
            },
            "does_not": list(NO_HSAI_ACTIONS),
            "current_sector_regime": current,
            "top_analogue_matches": rows_pub[:10],
            "similarity_distribution": cov.get("similarity_distribution"),
            "confidence_distribution": cov.get("confidence_distribution"),
            "coverage_by_sector": {
                "sectors_covered": cov.get("sectors_covered") or supported_sectors(),
                "supported_sectors": supported_sectors(),
            },
            "historical_coverage": {
                "matched_periods": cov.get("matched_periods"),
                "historical_regimes": cov.get("historical_regimes"),
                "total_analogues": cov.get("total_analogues") or len(rows_pub),
            },
            "analogue_freshness": {
                "seconds_since_publish": cov.get("analogue_freshness_seconds"),
                "ingestion_idle": cov.get("total_analogues", 0) == 0,
            },
            "retrieval_performance": {"traces": traces.recent(40)},
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": cov.get("total_analogues", 0) == 0,
            "phase": "11.4",
            "providers_queried": [],
            "note": "Read APIs never rebuild catalogues. Use POST /v1/sector/analogues/run.",
        }
