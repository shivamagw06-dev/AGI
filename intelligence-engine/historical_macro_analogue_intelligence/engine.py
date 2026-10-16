"""Historical Macro Analogue Engine — rank similar macro environments."""

from __future__ import annotations

from typing import Any

from historical_macro_analogue_intelligence import traces
from historical_macro_analogue_intelligence.query_builder import build_search_query
from historical_macro_analogue_intelligence.regimes import (
    build_current_regime,
    build_historical_regimes,
    soft_mri_relationships_for_dims,
)
from historical_macro_analogue_intelligence.schema import (
    HMAI_VERSION,
    NO_HMAI_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    HistoricalMacroAnalogue,
    SupportingEvidence,
    stable_analogue_id,
)
from historical_macro_analogue_intelligence.similarity import (
    confidence_for,
    explainability_bundle,
    key_differences,
    score_dimensions,
)
from historical_macro_analogue_intelligence.store import STORE


class HistoricalMacroAnalogueIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": HMAI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_HMAI_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "consumes": ["CMKP", "HMIP", "MRI", "Macro Research tips"],
            "feeds": ["Forecast Intelligence (Sprint 10.5)"],
            "phase": "10.4",
            "preceded_by": ["CMKP 10.1", "HMIP 10.2", "MRI 10.3"],
            "similarity_dimensions": [
                "interest_rate",
                "inflation",
                "gdp",
                "liquidity",
                "fiscal",
                "currency",
                "bond_yield",
                "global_growth",
                "commodity",
            ],
        }

    def run(self, *, country: str = "India", enrich_hmip: bool = True, top_k: int = 10) -> dict[str, Any]:
        """Ops rebuild — score & publish ranked analogues. Never Ask."""
        STORE.clear()
        current = build_current_regime(country=country)
        STORE.set_current_regime(current)
        historical = build_historical_regimes(country=country, enrich_hmip=enrich_hmip)
        STORE.set_regime_history(historical)

        ranked = self._rank(
            current,
            historical,
            top_k=top_k,
            min_score=0.0,
            target_period=None,
        )
        published = 0
        for ana in ranked:
            STORE.publish(ana)
            published += 1

        summary = {
            "ok": True,
            "country": country,
            "current_period": current.period,
            "historical_regimes": len(historical),
            "published": published,
            "top_similarity": ranked[0].similarity_score if ranked else None,
            "ask_triggered": False,
            "providers_queried": [],
            "coverage": STORE.coverage(),
        }
        STORE.record_run(summary)
        return summary

    def _rank(
        self,
        current,
        historical,
        *,
        top_k: int,
        min_score: float,
        target_period: str | None,
    ) -> list[HistoricalMacroAnalogue]:
        span = traces.begin(
            "macro_analogue_search",
            meta={
                "country": current.country,
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
            else:
                # keep all but boost exact year later via filter note
                pass
        traces.end(span, output={"candidates": len(candidates)})

        scored: list[HistoricalMacroAnalogue] = []
        for hist in candidates:
            # Skip comparing current period to itself when labels collide
            if hist.period == current.period and hist.label == current.label:
                continue

            sspan = traces.begin(
                "macro_similarity_scoring",
                meta={"matched_period": hist.period, "label": hist.label},
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
            rels = soft_mri_relationships_for_dims(hist.features)
            diffs = key_differences(details)
            explain = explainability_bundle(overall, details)
            ana = HistoricalMacroAnalogue(
                analogue_id=stable_analogue_id(
                    current.country, current.period, hist.period
                ),
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
                key_differences=diffs,
                relevant_relationships=rels,
                supporting_evidence=evidence,
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
                    "hmip_overlay": (hist.provenance or {}).get("hmip_overlay_keys"),
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
            "macro_analogue_ranking", meta={"n": len(scored), "top_k": top_k}
        )
        scored.sort(key=lambda a: a.similarity_score, reverse=True)
        # If user asked for a specific year that wasn't the only candidate, surface it first if present
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
                kind="historical_macro",
                summary=f"Historical regime {hist.period}: {hist.label}",
                period=hist.period,
                source_refs=list(hist.timeline_refs)[:4],
                weight=1.0,
            ),
            SupportingEvidence(
                kind="continuous_macro",
                summary=f"Current regime from CMKP tip ({current.period})",
                period=current.period,
                source_refs=["CMKP_KRIG"],
                weight=1.0,
            ),
        ]
        if hist.timeline_refs:
            evidence.append(
                SupportingEvidence(
                    kind="timeline",
                    summary="HMIP / institutional timeline anchors",
                    period=hist.period,
                    source_refs=list(hist.timeline_refs),
                    weight=0.8,
                )
            )
        if hist.research_refs:
            evidence.append(
                SupportingEvidence(
                    kind="research",
                    summary="Macro research office notes",
                    period=hist.period,
                    source_refs=list(hist.research_refs),
                    weight=0.7,
                )
            )
        if "HMIP" in (hist.source_layers or []):
            evidence.append(
                SupportingEvidence(
                    kind="historical_macro",
                    summary="HMIP series overlay confirmed catalog features",
                    period=hist.period,
                    source_refs=["HMIP_KRIG"],
                    weight=1.0,
                )
            )
        return evidence

    def search(
        self,
        *,
        country: str = "India",
        question: str | None = None,
        target_period: str | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
        persist: bool = False,
    ) -> dict[str, Any]:
        """Score analogues from soft-consumed knowledge — never collects."""
        q = build_search_query(
            country=country,
            question=question,
            target_period=target_period,
            top_k=top_k,
            min_score=min_score,
        )
        current = STORE.current_regime() or build_current_regime(country=country)
        historical = STORE.regime_history() or build_historical_regimes(
            country=country, enrich_hmip=True
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
            STORE.set_regime_history(historical)
            for ana in ranked:
                STORE.publish(ana)

        out = {
            "country": country,
            "question": question,
            "query": q,
            "current_regime": {
                "period": current.period,
                "label": current.label,
                "features": current.features,
                "source_layers": current.source_layers,
            },
            "n": len(ranked),
            "analogues": [a.to_public_dict() for a in ranked],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMAI_KRIG",
            "similarity_explainable": True,
        }
        return out

    def analogues(self, *, country: str | None = None, limit: int = 20) -> dict[str, Any]:
        span = traces.begin(
            "macro_analogue_retrieval", meta={"scope": "list", "country": country}
        )
        rows = STORE.list_all(limit=limit, country=country)
        # Soft compute if store empty (read path still never collects)
        if not rows:
            computed = self.search(country=country or "India", top_k=limit, persist=False)
            traces.end(span, output={"n": computed["n"], "mode": "computed"})
            return {
                **computed,
                "mode": "computed",
                "coverage": STORE.coverage(),
            }
        out = {
            "n": len(rows),
            "analogues": [r.to_public_dict() for r in rows],
            "current_regime": (
                {
                    "period": STORE.current_regime().period,
                    "label": STORE.current_regime().label,
                    "features": STORE.current_regime().features,
                }
                if STORE.current_regime()
                else None
            ),
            "coverage": STORE.coverage(),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMAI_KRIG",
            "mode": "published",
            "similarity_explainable": True,
        }
        traces.end(span, output={"n": out["n"], "mode": "published"})
        return out

    def analogues_for_country(self, country: str, *, limit: int = 20) -> dict[str, Any]:
        out = self.analogues(country=country, limit=limit)
        out["country"] = country
        return out

    def current_regime(self, *, country: str = "India") -> dict[str, Any]:
        span = traces.begin("macro_analogue_retrieval", meta={"scope": "current_regime"})
        regime = STORE.current_regime() or build_current_regime(country=country)
        out = {
            "country": country,
            "regime": regime.model_dump(mode="json"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMAI_KRIG",
        }
        traces.end(span, output={"period": regime.period})
        return out

    def regime_history(self, *, country: str = "India", limit: int = 50) -> dict[str, Any]:
        span = traces.begin("macro_analogue_retrieval", meta={"scope": "regime_history"})
        rows = STORE.regime_history(limit=limit) or build_historical_regimes(
            country=country, enrich_hmip=True
        )
        out = {
            "country": country,
            "n": len(rows),
            "regimes": [r.model_dump(mode="json") for r in rows[:limit]],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "HMAI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def forecast_tip(self, *, country: str = "India", top_k: int = 5) -> dict[str, Any]:
        """Bundle for Forecast Intelligence — store-only, no external APIs."""
        pack = self.search(country=country, top_k=top_k, persist=False)
        return {
            "gateway": "HMAI_KRIG",
            "collected_on_request": False,
            "providers_queried": [],
            "country": country,
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
                    "key_differences": a.get("key_differences"),
                    "timeline_refs": a.get("timeline_refs"),
                    "relevant_relationships": (a.get("relevant_relationships") or [])[:5],
                    "explainability": a.get("explainability"),
                }
                for a in pack.get("analogues") or []
            ],
            "n": pack.get("n"),
            "feeds_sprint": "10.5",
        }

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        rows = STORE.list_all(limit=20)
        if not rows:
            # Soft board from computed search without requiring prior run
            tip = self.search(country="India", top_k=5, persist=False)
            rows_pub = tip.get("analogues") or []
            current = tip.get("current_regime")
        else:
            rows_pub = [r.to_public_dict() for r in rows]
            cr = STORE.current_regime()
            current = (
                {"period": cr.period, "label": cr.label, "features": cr.features}
                if cr
                else None
            )
        return {
            "board": "Historical Macro Analogue",
            "programme": PROGRAMME,
            "version": HMAI_VERSION,
            "principles": {
                "deterministic_similarity": True,
                "explainable_scores": True,
                "evidence_linked": True,
                "ask_never_fetches": True,
                "providers_queried_always_empty": True,
                "no_forecasting_in_10_4": True,
            },
            "does_not": list(NO_HMAI_ACTIONS),
            "current_macro_regime": current,
            "top_analogue_matches": rows_pub[:8],
            "similarity_distribution": cov.get("similarity_distribution"),
            "confidence_distribution": cov.get("confidence_distribution"),
            "historical_coverage": {
                "matched_periods": cov.get("matched_periods"),
                "historical_regimes": cov.get("historical_regimes")
                or len(build_historical_regimes(enrich_hmip=False)),
                "total_analogues": cov.get("total_analogues") or len(rows_pub),
            },
            "analogue_freshness": {
                "seconds_since_publish": cov.get("analogue_freshness_seconds"),
                "ingestion_idle": cov.get("total_analogues", 0) == 0,
            },
            "retrieval_performance": {"traces": traces.recent(40)},
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": cov.get("total_analogues", 0) == 0,
            "providers_queried": [],
        }
