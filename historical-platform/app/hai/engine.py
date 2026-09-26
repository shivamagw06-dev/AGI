"""Historical Analogue Engine — ranked similar situations from store-only history."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.contracts.models import (
    AnalogueConfidence,
    AnalogueQuery,
    AnalogueScope,
    HistoricalAnalogue,
)
from app.hai import traces
from app.hai.query_builder import (
    build_company_query,
    build_macro_query,
    build_market_query,
    build_sector_query,
    features_from_financial_row,
)
from app.hai.similarity import (
    COMPANY_WEIGHTS,
    MACRO_WEIGHTS,
    MARKET_WEIGHTS,
    SECTOR_WEIGHTS,
    confidence_for,
    outcome_from_next,
    score_dimensions,
)
from app.storage.db import HipStore

# Seeded historical situation vectors (evidence-backed by timelines / macro catalog)
SECTOR_SITUATIONS: list[dict[str, Any]] = [
    {
        "period": "2008",
        "label": "Financial Crisis — demand shock",
        "features": {"demand_stress": 0.95, "fx_sensitivity": 0.5, "margin_pressure": 0.9, "cycle_phase": 0.2},
        "outcome": "IT Services demand contracted; multi-year pricing pressure",
        "timeline": "information_technology:2008:Financial Crisis",
    },
    {
        "period": "2014",
        "label": "Digital Transformation wave",
        "features": {"demand_stress": 0.35, "fx_sensitivity": 0.55, "margin_pressure": 0.4, "cycle_phase": 0.7},
        "outcome": "Mix shift toward digital; growth re-accelerated",
        "timeline": "information_technology:2014:Digital Transformation",
    },
    {
        "period": "2020",
        "label": "COVID Demand Surge",
        "features": {"demand_stress": 0.3, "fx_sensitivity": 0.65, "margin_pressure": 0.35, "cycle_phase": 0.85},
        "outcome": "Cloud / digital acceleration lifted IT Services",
        "timeline": "information_technology:2020:COVID Demand Surge",
    },
    {
        "period": "2022-2023",
        "label": "Post-pandemic deal slowdown + AI setup",
        "features": {"demand_stress": 0.75, "fx_sensitivity": 0.7, "margin_pressure": 0.8, "cycle_phase": 0.55},
        "outcome": "Margin defence then AI spending boom narrative",
        "timeline": "information_technology:2023:AI Spending Boom",
    },
]

MACRO_SITUATIONS: list[dict[str, Any]] = [
    {
        "period": "2015-2017 easing",
        "label": "RBI easing / disinflation window",
        "features": {"policy_stance": -1.0, "inflation_direction": -0.6, "growth_direction": 0.2},
        "outcome": "Private banks and rate-sensitive sectors historically supported",
        "timeline": "india:rbi_rate_cycle",
    },
    {
        "period": "2020 COVID Policy Response",
        "label": "Emergency easing + liquidity",
        "features": {"policy_stance": -1.0, "inflation_direction": -0.3, "growth_direction": -0.9},
        "outcome": "Liquidity rally followed; banks as transmission node",
        "timeline": "india:2020:COVID Policy Response",
    },
    {
        "period": "2022 Inflation Cycle",
        "label": "Tightening / inflation shock",
        "features": {"policy_stance": 1.0, "inflation_direction": 0.9, "growth_direction": -0.2},
        "outcome": "NIM up for banks; growth assets under pressure",
        "timeline": "india:2022:Inflation Cycle",
    },
    {
        "period": "2025 Rate-Cut Optionality",
        "label": "Easing bias returning",
        "features": {"policy_stance": -0.7, "inflation_direction": -0.5, "growth_direction": -0.3},
        "outcome": "Early beneficiaries: banks, housing, autos (relationship graph)",
        "timeline": "india:2025:Rate-Cut Optionality",
    },
]

MARKET_SITUATIONS: list[dict[str, Any]] = [
    {
        "period": "2016 Demonetisation",
        "label": "Liquidity / consumption shock",
        "features": {"valuation_regime": 0.45, "volatility": 0.7, "liquidity": 0.25, "risk_appetite": 0.3},
        "outcome": "Near-term risk-off; later normalisation",
        "timeline": "nifty:2016:Demonetisation",
    },
    {
        "period": "2020 COVID Crash",
        "label": "Risk-off collapse",
        "features": {"valuation_regime": 0.25, "volatility": 0.95, "liquidity": 0.2, "risk_appetite": 0.1},
        "outcome": "Policy response → liquidity rally",
        "timeline": "nifty:2020:COVID Crash",
    },
    {
        "period": "2021 Liquidity Rally",
        "label": "Abundant liquidity / elevated risk appetite",
        "features": {"valuation_regime": 0.85, "volatility": 0.25, "liquidity": 0.9, "risk_appetite": 0.9},
        "outcome": "Broad risk-on; valuations expanded",
        "timeline": "nifty:2021:Liquidity Rally",
    },
    {
        "period": "2022 Inflation",
        "label": "Tightening / inflation regime",
        "features": {"valuation_regime": 0.5, "volatility": 0.65, "liquidity": 0.4, "risk_appetite": 0.35},
        "outcome": "Multiple compression; style rotation",
        "timeline": "nifty:2022:Inflation",
    },
]


class HistoricalAnalogueEngine:
    def __init__(self, store: HipStore) -> None:
        self.store = store

    # ----- Public APIs -----

    def company_analogues(
        self,
        symbol: str,
        *,
        question: str | None = None,
        as_of_period: str | None = None,
        situation: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        span = traces.begin(
            "historical_analogue_search",
            meta={"scope": "company", "symbol": symbol, "question": question},
        )
        periods = self._company_period_features(symbol)
        if not periods:
            traces.end(span, ok=False, output={"error": "no_financial_history"})
            return {
                "company_symbol": symbol.upper(),
                "providers_queried": [],
                "analogues": [],
                "note": "No historical financial periods in store.",
            }

        current_idx, current_feats, as_of = self._resolve_company_current(
            periods, as_of_period=as_of_period, situation=situation, question=question
        )
        query = build_company_query(
            symbol,
            features=current_feats,
            question=question,
            as_of_period=as_of,
            situation=situation,
            top_k=top_k,
        )
        analogues = self._rank_company(query, periods, current_idx=current_idx)
        out = self._bundle(
            query,
            analogues,
            latency_ms=(time.perf_counter() - t0) * 1000,
            extra={
                "company_symbol": symbol.upper(),
                "entity": self.store.get_entity(symbol),
                "current_features": current_feats,
                "current_period": as_of,
            },
        )
        traces.end(span, output={"count": len(analogues), "top_score": analogues[0].similarity_score if analogues else None})
        return out

    def sector_analogues(
        self,
        sector: str,
        *,
        question: str | None = None,
        situation: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        span = traces.begin("historical_analogue_search", meta={"scope": "sector", "sector": sector})
        query = build_sector_query(sector, question=question, situation=situation, top_k=top_k)
        analogues = self._rank_seeded(query, SECTOR_SITUATIONS, weights=SECTOR_WEIGHTS)
        out = self._bundle(
            query,
            analogues,
            latency_ms=(time.perf_counter() - t0) * 1000,
            extra={"sector_key": query.entity_key},
        )
        traces.end(span, output={"count": len(analogues)})
        return out

    def macro_analogues(
        self,
        *,
        question: str | None = None,
        situation: str | None = None,
        top_k: int = 5,
        features: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        span = traces.begin("historical_analogue_search", meta={"scope": "macro"})
        query = build_macro_query(question=question, situation=situation, features=features, top_k=top_k)
        analogues = self._rank_seeded(query, MACRO_SITUATIONS, weights=MACRO_WEIGHTS)
        out = self._bundle(query, analogues, latency_ms=(time.perf_counter() - t0) * 1000, extra={"macro": "India"})
        traces.end(span, output={"count": len(analogues)})
        return out

    def market_analogues(
        self,
        *,
        question: str | None = None,
        situation: str | None = None,
        top_k: int = 5,
        features: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        span = traces.begin("historical_analogue_search", meta={"scope": "market"})
        query = build_market_query(question=question, situation=situation, features=features, top_k=top_k)
        analogues = self._rank_seeded(query, MARKET_SITUATIONS, weights=MARKET_WEIGHTS)
        out = self._bundle(query, analogues, latency_ms=(time.perf_counter() - t0) * 1000, extra={"market": "NIFTY"})
        traces.end(span, output={"count": len(analogues)})
        return out

    def search(
        self,
        *,
        scope: str,
        entity: str | None = None,
        question: str | None = None,
        situation: str | None = None,
        as_of_period: str | None = None,
        top_k: int = 5,
        features: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        scope_l = scope.lower()
        if scope_l == "company":
            return self.company_analogues(
                entity or "INFY",
                question=question,
                as_of_period=as_of_period,
                situation=situation,
                top_k=top_k,
            )
        if scope_l == "sector":
            return self.sector_analogues(
                entity or "information_technology",
                question=question,
                situation=situation,
                top_k=top_k,
            )
        if scope_l == "macro":
            return self.macro_analogues(question=question, situation=situation, top_k=top_k, features=features)
        if scope_l == "market":
            return self.market_analogues(question=question, situation=situation, top_k=top_k, features=features)
        return {"error": "unknown_scope", "providers_queried": [], "analogues": []}

    # ----- Company ranking -----

    def _company_period_features(self, symbol: str) -> list[dict[str, Any]]:
        rows = self.store.list_financials(symbol, period_kind="annual", limit=50)
        # Dedup by period keeping highest version (list already version desc within date — re-sort ASC)
        by_period: dict[str, dict[str, Any]] = {}
        for row in rows:
            period = row.get("effective_date") or ""
            if not period:
                continue
            prev = by_period.get(period)
            if prev is None or int(row.get("version") or 0) >= int(prev.get("version") or 0):
                by_period[period] = row
        ordered = [by_period[p] for p in sorted(by_period.keys())]
        out: list[dict[str, Any]] = []
        for i, row in enumerate(ordered):
            prev = ordered[i - 1] if i else None
            feats = features_from_financial_row(row, prev=prev, sector_alignment=1.0)
            out.append(
                {
                    "period": row.get("effective_date"),
                    "row": row,
                    **feats,
                }
            )
        return out

    def _resolve_company_current(
        self,
        periods: list[dict[str, Any]],
        *,
        as_of_period: str | None,
        situation: str | None,
        question: str | None,
    ) -> tuple[int, dict[str, float], str]:
        sit = situation
        if not sit and question:
            from app.hai.query_builder import detect_situation

            sit = detect_situation(question)

        if as_of_period:
            for i, p in enumerate(periods):
                if p["period"] == as_of_period:
                    return i, self._feature_dict(p), as_of_period

        # Slowdown questions: use latest tip features but bias growth/margins toward compression,
        # then find historical periods that looked like that — OR use FY2022 if present as reference tip.
        if sit == "slowdown":
            # Prefer matching against a synthetic current slowdown profile derived from latest tip
            tip = periods[-1]
            tip_feats = self._feature_dict(tip)
            # Represent "this type of slowdown": low growth + compressed margins + modest PE
            current = {
                "revenue_growth": min(float(tip_feats.get("revenue_growth") or 8.0), 6.0),
                "pat_margin": min(float(tip_feats.get("pat_margin") or 0.2), 0.185),
                "pe": float(tip_feats.get("pe") or 18.0) * 0.85,
                "sector_alignment": 1.0,
            }
            return len(periods) - 1, current, tip["period"]

        tip = periods[-1]
        return len(periods) - 1, self._feature_dict(tip), tip["period"]

    def _rank_company(
        self,
        query: AnalogueQuery,
        periods: list[dict[str, Any]],
        *,
        current_idx: int,
    ) -> list[HistoricalAnalogue]:
        sspan = traces.begin("similarity_scoring", meta={"entity": query.entity_key, "n": len(periods)})
        scored: list[HistoricalAnalogue] = []
        timeline = self.store.get_timeline("company", query.entity_key)
        rels = self.store.list_relationships(company_symbol=query.entity_key)

        for i, period in enumerate(periods):
            if i == current_idx and query.situation != "slowdown":
                # Skip comparing the tip to itself for generic queries
                continue
            # For slowdown, still skip exact tip period if features were synthetic — allow FY2022 etc.
            if period["period"] == query.as_of_period and query.situation != "slowdown":
                continue
            hist_feats = self._feature_dict(period)
            # Need overlapping numeric dims
            if "revenue_growth" not in hist_feats and "revenue_growth" in query.features:
                continue
            overall, details, matching, non_matching = score_dimensions(
                query.features, hist_feats, COMPANY_WEIGHTS
            )
            evidence = self._company_evidence(query.entity_key, period, timeline, rels)
            if overall < 50 or not evidence:
                continue
            conf = confidence_for(overall, evidence_n=len(evidence))
            outcome = outcome_from_next(periods, i)
            # Timeline narrative outcome overlay
            year = _year(period["period"])
            tl_hit = next((t for t in timeline if int(t.get("year") or 0) == year), None)
            if tl_hit and not outcome:
                outcome = f"Timeline: {tl_hit.get('title')} — {tl_hit.get('description') or ''}".strip()
            elif tl_hit:
                outcome = f"{outcome}; timeline anchor: {tl_hit.get('title')}"

            scored.append(
                HistoricalAnalogue(
                    scope=AnalogueScope.COMPANY,
                    current_entity=query.entity_key,
                    matched_period=period["period"],
                    matched_label=tl_hit.get("title") if tl_hit else period["period"],
                    similarity_score=overall,
                    confidence=conf,
                    matching_dimensions=matching,
                    non_matching_dimensions=non_matching,
                    dimension_scores=details,
                    historical_outcome=outcome,
                    supporting_evidence=evidence,
                    timeline_refs=[f"{query.entity_key}:{year}:{tl_hit.get('title')}" ] if tl_hit else [],
                    relationship_refs=[r.get("relationship_id") for r in rels[:5] if r.get("relationship_id")],
                    features=hist_feats,
                )
            )
        traces.end(sspan, output={"candidates": len(scored)})
        return self._rank(scored, top_k=query.top_k)

    # ----- Seeded sector/macro/market -----

    def _rank_seeded(
        self,
        query: AnalogueQuery,
        situations: list[dict[str, Any]],
        *,
        weights: dict[str, float],
    ) -> list[HistoricalAnalogue]:
        sspan = traces.begin("similarity_scoring", meta={"scope": query.scope.value, "n": len(situations)})
        scored: list[HistoricalAnalogue] = []
        for sit in situations:
            overall, details, matching, non_matching = score_dimensions(
                query.features, sit["features"], weights, scales={k: 1.2 for k in weights}
            )
            if overall < 45:
                continue
            evidence = [
                {
                    "kind": "historical_cycle",
                    "summary": sit["label"],
                    "period": sit["period"],
                    "source_refs": [sit.get("timeline") or ""],
                },
                {
                    "kind": "institutional_catalog",
                    "summary": sit.get("outcome") or sit["label"],
                    "period": sit["period"],
                    "source_refs": [sit.get("timeline") or ""],
                },
            ]
            # Attach live timeline/relationship evidence when present
            if query.scope == AnalogueScope.SECTOR:
                tl = self.store.get_timeline("sector", query.entity_key)
                evidence.append(
                    {
                        "kind": "timeline",
                        "summary": f"{len(tl)} sector timeline events in store",
                        "period": sit["period"],
                        "source_refs": [e.get("event_id") for e in tl[:3] if e.get("event_id")],
                    }
                )
            conf = confidence_for(overall, evidence_n=len(evidence))
            scored.append(
                HistoricalAnalogue(
                    scope=query.scope,
                    current_entity=query.entity_key,
                    matched_period=sit["period"],
                    matched_label=sit["label"],
                    similarity_score=overall,
                    confidence=conf,
                    matching_dimensions=matching,
                    non_matching_dimensions=non_matching,
                    dimension_scores=details,
                    historical_outcome=sit.get("outcome"),
                    supporting_evidence=evidence,
                    timeline_refs=[sit.get("timeline")] if sit.get("timeline") else [],
                    features=sit["features"],
                )
            )
        traces.end(sspan, output={"candidates": len(scored)})
        return self._rank(scored, top_k=query.top_k)

    def _rank(self, items: list[HistoricalAnalogue], *, top_k: int) -> list[HistoricalAnalogue]:
        rspan = traces.begin("analogue_ranking", meta={"n": len(items), "top_k": top_k})
        ranked = sorted(items, key=lambda a: (a.similarity_score, len(a.supporting_evidence)), reverse=True)
        # Drop analogues without evidence (integrity)
        ranked = [a for a in ranked if a.supporting_evidence and a.similarity_score > 0]
        out = ranked[: max(1, top_k)]
        traces.end(rspan, output={"returned": len(out)})
        return out

    def _bundle(
        self,
        query: AnalogueQuery,
        analogues: list[HistoricalAnalogue],
        *,
        latency_ms: float,
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        rspan = traces.begin("analogue_retrieval", meta={"scope": query.scope.value, "entity": query.entity_key})
        payload = [a.model_dump(mode="json") for a in analogues]
        avg = round(sum(a.similarity_score for a in analogues) / len(analogues), 2) if analogues else None
        search_id = str(uuid4())
        self.store.insert_analogue_search(
            search_id=search_id,
            scope=query.scope.value,
            entity_key=query.entity_key,
            question=query.question,
            situation=query.situation,
            as_of_period=query.as_of_period,
            features=query.features,
            top_k=query.top_k,
            result_count=len(payload),
            avg_similarity=avg,
            latency_ms=round(latency_ms, 2),
            results=payload,
        )
        # Compose IE bundle
        timeline = []
        relationships = []
        if query.scope == AnalogueScope.COMPANY:
            timeline = [
                {"year": e.get("year"), "title": e.get("title")}
                for e in self.store.get_timeline("company", query.entity_key)
            ]
            relationships = self.store.list_relationships(company_symbol=query.entity_key)[:10]

        out = {
            **extra,
            "providers_queried": [],
            "search_id": search_id,
            "question": query.question,
            "situation": query.situation,
            "query_features": query.features,
            "analogues": payload,
            "top_k": query.top_k,
            "bundle": {
                "current_company_knowledge": extra.get("entity") or extra.get("current_features"),
                "historical_timeline": timeline,
                "historical_relationships": relationships,
                "top_historical_analogues": payload,
                "evidence": [e for a in payload for e in (a.get("supporting_evidence") or [])],
            },
            "latency_ms": round(latency_ms, 2),
            "note": "Analogue reasoning only — not a forecast. Judgment remains in the Intelligence Engine.",
        }
        traces.end(rspan, output={"search_id": search_id, "count": len(payload)})
        return out

    def _company_evidence(
        self,
        symbol: str,
        period: dict[str, Any],
        timeline: list[dict[str, Any]],
        rels: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        evidence = [
            {
                "kind": "historical_financials",
                "summary": f"{symbol} {period['period']} revenue_growth={period.get('revenue_growth')} pe={period.get('pe')}",
                "period": period["period"],
                "source_refs": [f"hko:{symbol}:financials:{period['period']}"],
            }
        ]
        year = _year(period["period"])
        for t in timeline:
            if int(t.get("year") or 0) == year:
                evidence.append(
                    {
                        "kind": "timeline",
                        "summary": f"{t.get('title')}: {t.get('description') or ''}".strip(),
                        "period": period["period"],
                        "source_refs": [t.get("event_id") or f"timeline:{symbol}:{year}:{t.get('title')}"],
                    }
                )
        if rels:
            evidence.append(
                {
                    "kind": "relationships",
                    "summary": f"{len(rels)} published historical relationships for {symbol}",
                    "period": period["period"],
                    "source_refs": [r.get("relationship_id") for r in rels[:3] if r.get("relationship_id")],
                }
            )
        return evidence

    @staticmethod
    def _feature_dict(period: dict[str, Any]) -> dict[str, float]:
        out: dict[str, float] = {}
        for key in ("revenue_growth", "pat_margin", "pe", "sector_alignment"):
            if key in period and period[key] is not None:
                out[key] = float(period[key])
        return out


def _year(period: str | None) -> int | None:
    if not period:
        return None
    raw = str(period)
    if raw.startswith("FY") and len(raw) >= 6:
        try:
            return int(raw[2:6])
        except ValueError:
            return None
    try:
        return int(raw[:4])
    except ValueError:
        return None
