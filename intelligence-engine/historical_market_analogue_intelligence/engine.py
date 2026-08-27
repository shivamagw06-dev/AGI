"""Historical Market Analogue Engine — rank similar market environments."""

from __future__ import annotations

from typing import Any

from historical_market_analogue_intelligence import traces
from historical_market_analogue_intelligence.query_builder import build_search_query
from historical_market_analogue_intelligence.regimes import (
    build_current_regime,
    build_historical_regimes,
    normalize_market,
    soft_mkri_relationships,
    supported_markets,
)
from historical_market_analogue_intelligence.schema import (
    HMKAI_VERSION,
    NO_HMKAI_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    SIMILARITY_DIMENSIONS,
    HistoricalMarketAnalogue,
    SupportingEvidence,
    stable_analogue_id,
)
from historical_market_analogue_intelligence.similarity import (
    confidence_for,
    explainability_bundle,
    key_differences,
    score_dimensions,
)
from historical_market_analogue_intelligence.store import STORE


class HistoricalMarketAnalogueIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HMKAI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_HMKAI_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "consumes": ["CMKTP", "HMKIP", "MKRI", "HMIP tips", "HSIP tips"],
            "feeds": ["Market Forecast Intelligence (Sprint 12.5)"],
            "phase": "12.4",
            "preceded_by": ["CMKTP 12.1", "HMKIP 12.2", "MKRI 12.3"],
            "supported_markets": supported_markets(),
            "similarity_dimensions": list(SIMILARITY_DIMENSIONS),
            "note": "Programme short HMKAI avoids collision with Macro HMAI",
        }

    def run(
        self,
        *,
        market: str | None = None,
        enrich_hmkip: bool = True,
        enrich_cmktp: bool = True,
        top_k: int = 10,
    ) -> dict[str, Any]:
        """Ops rebuild — score & publish ranked analogues. Never Ask."""
        rspan = traces.begin(
            "market_analogue_refresh",
            meta={"market": market, "enrich_hmkip": enrich_hmkip},
        )
        markets = [normalize_market(market) or market] if market else supported_markets()
        STORE.clear()
        published = 0
        per_market: dict[str, Any] = {}

        for mkt in markets:
            if not mkt:
                continue
            current = build_current_regime(market=mkt, enrich_cmktp=enrich_cmktp)
            STORE.set_current_regime(current)
            historical = build_historical_regimes(market=mkt, enrich_hmkip=enrich_hmkip)
            STORE.set_regime_history(mkt, historical)
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
            per_market[mkt] = {
                "current_period": current.period,
                "historical_regimes": len(historical),
                "published": len(ranked),
                "top_similarity": ranked[0].similarity_score if ranked else None,
            }

        summary = {
            "ok": True,
            "markets": list(per_market.keys()),
            "published": published,
            "per_market": per_market,
            "ask_triggered": False,
            "providers_queried": [],
            "coverage": STORE.coverage(),
            "programme_short": PROGRAMME_SHORT,
        }
        STORE.record_run(summary)
        traces.end(rspan, output={"published": published, "markets": len(per_market)})
        return summary

    def _rank(
        self,
        current,
        historical,
        *,
        top_k: int,
        min_score: float,
        target_period: str | None,
    ) -> list[HistoricalMarketAnalogue]:
        span = traces.begin(
            "market_analogue_search",
            meta={
                "market": current.market,
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

        scored: list[HistoricalMarketAnalogue] = []
        for hist in candidates:
            if hist.period == current.period and hist.label == current.label:
                continue

            sspan = traces.begin(
                "market_similarity_scoring",
                meta={"matched_period": hist.period, "label": hist.label, "market": current.market},
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
            rels = soft_mkri_relationships(current.market)
            diffs = key_differences(details)
            explain = explainability_bundle(overall, details)
            ana = HistoricalMarketAnalogue(
                analogue_id=stable_analogue_id(
                    current.market, current.period, hist.period
                ),
                market=current.market,
                market_key=current.market_key,
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
                supporting_relationships=rels,
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
                    "hmkip_overlay": (hist.provenance or {}).get("hmkip_soft_confirmed"),
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
            "market_analogue_ranking", meta={"n": len(scored), "top_k": top_k}
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
                kind="historical_market",
                summary=f"Historical market regime {hist.period}: {hist.label}",
                period=hist.period,
                source_refs=list(hist.timeline_refs)[:4],
                weight=1.0,
            ),
            SupportingEvidence(
                kind="continuous_market",
                summary=f"Current market regime from CMKTP tip ({current.period})",
                period=current.period,
                source_refs=["CMKTP_KRIG"],
                weight=1.0,
            ),
        ]
        if hist.timeline_refs:
            evidence.append(
                SupportingEvidence(
                    kind="timeline",
                    summary="HMKIP / institutional market timeline anchors",
                    period=hist.period,
                    source_refs=list(hist.timeline_refs),
                    weight=0.8,
                )
            )
        if hist.research_refs:
            evidence.append(
                SupportingEvidence(
                    kind="research",
                    summary="Market research office notes",
                    period=hist.period,
                    source_refs=list(hist.research_refs),
                    weight=0.7,
                )
            )
        if "HMKIP" in (hist.source_layers or []):
            evidence.append(
                SupportingEvidence(
                    kind="historical_market",
                    summary="HMKIP timeline soft-confirmed catalog features",
                    period=hist.period,
                    source_refs=["HMKIP_KRIG"],
                    weight=1.0,
                )
            )
        return evidence

    def search(
        self,
        *,
        market: str | None = None,
        question: str | None = None,
        target_period: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
        persist: bool = False,
    ) -> dict[str, Any]:
        """Score analogues from soft-consumed knowledge — never collects."""
        q = build_search_query(
            market=market,
            question=question,
            target_period=target_period,
            top_k=top_k,
            min_score=min_score,
        )
        mkt = q["market"]
        current = STORE.current_regime(mkt) or build_current_regime(market=mkt)
        historical = STORE.regime_history(mkt) or build_historical_regimes(
            market=mkt, enrich_hmkip=True
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
            STORE.set_regime_history(mkt, historical)
            for ana in ranked:
                STORE.publish(ana)

        out = {
            "market": mkt,
            "question": question,
            "query": q,
            "current_regime": {
                "market": current.market,
                "period": current.period,
                "label": current.label,
                "regime_label": current.regime_label,
                "features": current.features,
                "source_layers": current.source_layers,
            },
            "n": len(ranked),
            "analogues": [a.to_public_dict() for a in ranked],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMKAI_KRIG",
            "similarity_explainable": True,
        }
        return out

    def analogues(self, *, market: str | None = None, limit: int = 20) -> dict[str, Any]:
        span = traces.begin(
            "market_analogue_retrieval", meta={"scope": "list", "market": market}
        )
        mkt = normalize_market(market) if market else None
        rows = STORE.list_all(limit=limit, market=mkt)
        if not rows:
            computed = self.search(market=mkt or "India", top_k=limit, persist=False)
            traces.end(span, output={"n": computed["n"], "mode": "computed"})
            return {
                **computed,
                "mode": "computed",
                "coverage": STORE.coverage(),
            }
        cr = STORE.current_regime(mkt) if mkt else None
        out = {
            "market": mkt,
            "n": len(rows),
            "analogues": [r.to_public_dict() for r in rows],
            "current_regime": (
                {
                    "market": cr.market,
                    "period": cr.period,
                    "label": cr.label,
                    "regime_label": cr.regime_label,
                    "features": cr.features,
                }
                if cr
                else None
            ),
            "coverage": STORE.coverage(),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMKAI_KRIG",
            "mode": "published",
            "similarity_explainable": True,
        }
        traces.end(span, output={"n": out["n"], "mode": "published"})
        return out

    def analogues_for_market(self, market: str, *, limit: int = 20) -> dict[str, Any]:
        mkt = normalize_market(market) or market
        out = self.analogues(market=mkt, limit=limit)
        out["market"] = mkt
        return out

    def current_regime(self, *, market: str = "India") -> dict[str, Any]:
        span = traces.begin("market_analogue_retrieval", meta={"scope": "current_regime"})
        mkt = normalize_market(market) or market
        regime = STORE.current_regime(mkt) or build_current_regime(market=mkt)
        out = {
            "market": mkt,
            "regime": regime.model_dump(mode="json"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMKAI_KRIG",
        }
        traces.end(span, output={"period": regime.period, "market": mkt})
        return out

    def regime_history(self, *, market: str = "India", limit: int = 50) -> dict[str, Any]:
        span = traces.begin("market_analogue_retrieval", meta={"scope": "regime_history"})
        mkt = normalize_market(market) or market
        rows = STORE.regime_history(mkt, limit=limit) or build_historical_regimes(
            market=mkt, enrich_hmkip=True
        )
        out = {
            "market": mkt,
            "n": len(rows),
            "regimes": [r.model_dump(mode="json") for r in rows[:limit]],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMKAI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def report(self, *, market: str = "India", top_k: int = 5) -> dict[str, Any]:
        """Institutional analogue report for Mission Control / Forecast."""
        pack = self.search(market=market, top_k=top_k, persist=False)
        return {
            "report": "Historical Market Analogue Report",
            "programme_short": PROGRAMME_SHORT,
            "market": pack.get("market"),
            "current_regime": pack.get("current_regime"),
            "top_analogues": pack.get("analogues"),
            "n": pack.get("n"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMKAI_KRIG",
            "feeds_sprint": "12.5",
        }

    def forecast_tip(self, *, market: str = "India", top_k: int = 5) -> dict[str, Any]:
        """Bundle for Market Forecast Intelligence — store-only, no external APIs."""
        mkt = normalize_market(market) or market
        pack = self.search(market=mkt, top_k=top_k, persist=False)
        return {
            "gateway": "HMKAI_KRIG",
            "collected_on_request": False,
            "providers_queried": [],
            "market": mkt,
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
                    "supporting_relationships": (a.get("supporting_relationships") or [])[:5],
                    "explainability": a.get("explainability"),
                }
                for a in pack.get("analogues") or []
            ],
            "n": pack.get("n"),
            "feeds_sprint": "12.5",
        }

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        rows = STORE.list_all(limit=40)
        if not rows:
            tip = self.search(market="India", top_k=5, persist=False)
            rows_pub = tip.get("analogues") or []
            current = tip.get("current_regime")
        else:
            rows_pub = [r.to_public_dict() for r in rows]
            cr = STORE.current_regime("India") or STORE.current_regime()
            current = (
                {
                    "market": cr.market,
                    "period": cr.period,
                    "label": cr.label,
                    "regime_label": cr.regime_label,
                    "features": cr.features,
                }
                if cr
                else None
            )
        return {
            "board": "Historical Market Analogue",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HMKAI_VERSION,
            "principles": {
                "deterministic_similarity": True,
                "explainable_scores": True,
                "evidence_linked": True,
                "ask_never_fetches": True,
                "providers_queried_always_empty": True,
                "no_forecasting_in_12_4": True,
            },
            "does_not": list(NO_HMKAI_ACTIONS),
            "current_market_regime": current,
            "top_analogue_matches": rows_pub[:10],
            "similarity_distribution": cov.get("similarity_distribution"),
            "confidence_distribution": cov.get("confidence_distribution"),
            "matching_dimensions_sample": [
                {
                    "matched_period": r.get("matched_period"),
                    "matching": r.get("matching_dimensions"),
                    "different": r.get("non_matching_dimensions"),
                }
                for r in rows_pub[:5]
            ],
            "key_differences_sample": [
                {"matched_period": r.get("matched_period"), "differences": r.get("key_differences")}
                for r in rows_pub[:5]
            ],
            "historical_outcomes_sample": [
                {
                    "matched_period": r.get("matched_period"),
                    "outcome": r.get("historical_outcome"),
                    "bundle": r.get("historical_outcome_bundle"),
                }
                for r in rows_pub[:5]
            ],
            "coverage_by_market": {
                "markets_covered": cov.get("markets_covered") or supported_markets(),
                "supported_markets": supported_markets(),
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
            "phase": "12.4",
            "providers_queried": [],
            "note": "Read APIs never rebuild catalogues. Use POST /v1/market/analogues/run.",
        }
