"""Institutional Forecast Preparation Engine — Forecast Bundles only."""

from __future__ import annotations

import time
from typing import Any

from institutional_forecast_intelligence import traces
from institutional_forecast_intelligence.completeness import assess_completeness
from institutional_forecast_intelligence.hip_bridge import HipForecastBridge
from institutional_forecast_intelligence.knowledge_catalog import (
    ANALOGUE_TIPS,
    CATALYSTS,
    COMPANY_KNOWLEDGE,
    HISTORICAL_TIPS,
    MACRO_INTELLIGENCE,
    MARKET_INTELLIGENCE,
    MONITORING_EVENTS,
    RELATIONSHIP_TIPS,
    RESEARCH_TIPS,
    RISKS,
    SECTOR_INTELLIGENCE,
    THEME_INTELLIGENCE,
)
from institutional_forecast_intelligence.schema import (
    IFI_VERSION,
    ForecastBundle,
    ForecastScope,
    PROGRAMME,
)
from institutional_forecast_intelligence.store import METRICS


class InstitutionalForecastEngine:
    def __init__(self, *, hip_base_url: str | None = None) -> None:
        self.hip = HipForecastBridge(hip_base_url)

    # ----- Public surfaces -----

    def company_bundle(self, ticker: str, *, question: str | None = None) -> dict[str, Any]:
        return self._generate(ForecastScope.COMPANY, ticker.upper(), question=question)

    def sector_bundle(self, sector: str, *, question: str | None = None) -> dict[str, Any]:
        key = sector.lower().replace(" ", "_")
        return self._generate(ForecastScope.SECTOR, key, question=question)

    def market_bundle(self, *, question: str | None = None) -> dict[str, Any]:
        return self._generate(ForecastScope.MARKET, "nifty", question=question)

    def macro_bundle(self, *, question: str | None = None) -> dict[str, Any]:
        return self._generate(ForecastScope.MACRO, "india", question=question)

    def theme_bundle(self, theme: str = "artificial_intelligence", *, question: str | None = None) -> dict[str, Any]:
        key = theme.lower().replace(" ", "_")
        return self._generate(ForecastScope.THEME, key, question=question)

    def bundle(
        self,
        *,
        scope: str,
        entity: str | None = None,
        question: str | None = None,
    ) -> dict[str, Any]:
        scope_l = scope.lower()
        if scope_l == "company":
            return self.company_bundle(entity or "INFY", question=question)
        if scope_l == "sector":
            return self.sector_bundle(entity or "information_technology", question=question)
        if scope_l == "market":
            return self.market_bundle(question=question)
        if scope_l == "macro":
            return self.macro_bundle(question=question)
        if scope_l == "theme":
            return self.theme_bundle(entity or "artificial_intelligence", question=question)
        return {
            "error": "unknown_scope",
            "providers_queried": [],
            "version": IFI_VERSION,
        }

    def dashboard(self) -> dict[str, Any]:
        metrics = METRICS.dashboard()
        provider_board = {}
        try:
            from forecast_provider_integration.production import provider_health

            provider_board = provider_health()
        except Exception:
            provider_board = {}
        return {
            "board": "Institutional Forecast Intelligence",
            "programme": PROGRAMME,
            "version": IFI_VERSION,
            "principles": {
                "no_uncontrolled_provider_calls_on_forecast_path": True,
                "no_live_providers_on_forecast_path": True,  # legacy alias — stale snapshot refresh only
                "stale_market_snapshot_refresh_only": True,
                "reasons_over_agi_knowledge": True,
                "no_price_prediction": True,
                "no_bull_base_bear_selection": True,
                "no_probabilities": True,
                "scenario_engine_consumes_bundles_only": True,
                "india_first_providers": True,
            },
            **metrics,
            "provider_health": {
                "groww": provider_board.get("groww_connection_status"),
                "yahoo": provider_board.get("yahoo_finance_status"),
                "nse": provider_board.get("nse_collector_status"),
                "bse": provider_board.get("bse_collector_status"),
                "company_ir": provider_board.get("company_ir_collector_status"),
                "forecast_may_call_providers_directly": False,
            },
            "retrieval_performance": {"traces": traces.recent(40)},
            "sample_entities": list(COMPANY_KNOWLEDGE.keys()),
        }

    # ----- Core generation -----

    def _generate(
        self,
        scope: ForecastScope,
        entity: str,
        *,
        question: str | None = None,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        span = traces.begin(
            "forecast_bundle_generation",
            meta={"scope": scope.value, "entity": entity, "question": question},
        )
        try:
            retrieved = self._retrieve_knowledge(scope, entity, question=question)
            prepared = self._prepare_context(scope, entity, retrieved)
            bundle = self._publish(scope, entity, prepared)
            latency = (time.perf_counter() - t0) * 1000
            METRICS.record(
                scope=scope.value,
                entity=entity,
                completeness_score=bundle.completeness.score,
                latency_ms=latency,
                ok=True,
            )
            out = bundle.to_public_dict()
            out["latency_ms"] = round(latency, 2)
            traces.end(
                span,
                output={
                    "bundle_id": bundle.bundle_id,
                    "completeness": bundle.completeness.overall.value,
                    "score": bundle.completeness.score,
                },
            )
            return out
        except Exception as exc:  # pragma: no cover
            latency = (time.perf_counter() - t0) * 1000
            METRICS.record(
                scope=scope.value,
                entity=entity,
                completeness_score=0.0,
                latency_ms=latency,
                ok=False,
            )
            traces.end(span, ok=False, output={"error": str(exc)})
            raise

    def _retrieve_knowledge(
        self,
        scope: ForecastScope,
        entity: str,
        *,
        question: str | None,
    ) -> dict[str, Any]:
        rspan = traces.begin(
            "forecast_knowledge_retrieval",
            meta={"scope": scope.value, "entity": entity, "hip": self.hip.enabled},
        )
        out: dict[str, Any] = {
            "providers_queried": [],
            "sources": ["agi_knowledge_catalog"],
        }

        if scope == ForecastScope.COMPANY:
            out.update(self._retrieve_company(entity, question=question))
        elif scope == ForecastScope.SECTOR:
            out.update(self._retrieve_sector(entity))
        elif scope == ForecastScope.MARKET:
            out.update(self._retrieve_market())
        elif scope == ForecastScope.MACRO:
            out.update(self._retrieve_macro())
        elif scope == ForecastScope.THEME:
            out.update(self._retrieve_theme(entity))

        # Soft Knowledge Platform enrichment — live snapshot only when stale
        out = self._enrich_from_knowledge_platform(scope, entity, out)

        traces.end(rspan, output={"sources": out.get("sources"), "keys": list(out.keys())})
        return out

    def _enrich_from_knowledge_platform(
        self,
        scope: ForecastScope,
        entity: str,
        retrieved: dict[str, Any],
    ) -> dict[str, Any]:
        """Consume AGI-owned knowledge; never call Groww/Yahoo/NSE/BSE directly here."""
        try:
            from forecast_provider_integration.production import enrich_for_forecast
        except Exception:
            return retrieved

        tip = enrich_for_forecast(
            scope=scope.value,
            entity=entity,
            catalog_current=retrieved.get("current_knowledge"),
            catalog_market=retrieved.get("market_intelligence"),
        )
        sources = list(retrieved.get("sources") or [])
        for s in tip.get("sources_added") or []:
            if s not in sources:
                sources.append(s)
        merged = {
            **retrieved,
            "current_knowledge": tip.get("current_knowledge") or retrieved.get("current_knowledge"),
            "market_intelligence": tip.get("market_intelligence") or retrieved.get("market_intelligence"),
            "market_snapshot": tip.get("market_snapshot"),
            "company_knowledge_object": tip.get("company_knowledge_object"),
            "providers_queried": [],  # forecast path never records raw provider calls
            "sources": sources,
            "provider_refresh": tip.get("refresh"),
            "forbidden_direct_calls": tip.get("forbidden_direct_calls") or [],
        }
        # Merge freshness tips
        kf = dict(retrieved.get("knowledge_freshness") or {})
        kf.update(tip.get("knowledge_freshness") or {})
        merged["knowledge_freshness"] = kf
        return merged

    def _retrieve_company(self, ticker: str, *, question: str | None) -> dict[str, Any]:
        current = dict(COMPANY_KNOWLEDGE.get(ticker) or {"ticker": ticker, "missing": True})
        sector_key = current.get("sector_key") or "information_technology"
        sector = dict(SECTOR_INTELLIGENCE.get(str(sector_key)) or {"missing": True})
        historical = dict(HISTORICAL_TIPS.get(ticker) or {})
        analogues = list(ANALOGUE_TIPS.get(ticker) or [])
        relationships = list(RELATIONSHIP_TIPS.get(ticker) or [])
        research = dict(RESEARCH_TIPS.get(ticker) or RESEARCH_TIPS.get("INFY") or {})
        monitoring = list(MONITORING_EVENTS.get(ticker) or MONITORING_EVENTS.get("INFY") or [])
        catalysts = list(CATALYSTS.get(ticker) or CATALYSTS.get("INFY") or [])
        risks = list(RISKS.get(ticker) or RISKS.get("INFY") or [])
        sources = ["agi_knowledge_catalog"]

        # Soft enrich from HIP when configured (still no live Yahoo)
        if self.hip.enabled:
            sources.append("hip_hko")
            hist = self.hip.company_history(ticker)
            if hist and hist.get("providers_queried") == []:
                historical = {
                    **historical,
                    "hip_timeline": hist.get("timeline") or [],
                    "hip_financials_tip": (hist.get("financials") or [])[-3:],
                    "hip_coverage": hist.get("coverage"),
                    "entity": hist.get("entity"),
                }
                if hist.get("entity"):
                    current = {**current, "entity_from_hip": hist.get("entity"), "missing": False}
            tl = self.hip.company_timeline(ticker)
            if tl:
                historical["timeline_narrative"] = tl.get("narrative") or tl.get("timeline")
            rel = self.hip.company_relationships(ticker)
            if rel and rel.get("relationships"):
                relationships = list(rel["relationships"])
                sources.append("hip_hri")
            ana = self.hip.company_analogues(ticker, question=question)
            if ana and ana.get("analogues"):
                analogues = list(ana["analogues"])
                sources.append("hip_hai")

        return {
            "current_knowledge": current,
            "historical_intelligence": historical or {"missing": True},
            "historical_analogues": analogues,
            "relationship_intelligence": relationships,
            "sector_intelligence": sector,
            "market_intelligence": dict(MARKET_INTELLIGENCE),
            "macro_intelligence": dict(MACRO_INTELLIGENCE),
            "research_intelligence": research,
            "monitoring_events": monitoring,
            "catalysts": catalysts,
            "risks": risks,
            "pattern_intelligence": {
                "deferred": True,
                "sprint": "8.5",
                "note": "Pattern & Cycle Intelligence not yet published — completeness reduced, not invented.",
            },
            "outlook_dimensions": [
                "Revenue Outlook",
                "Margin Outlook",
                "Cash Flow Outlook",
                "Valuation Outlook",
                "Risk Outlook",
            ],
            "sources": sources,
            "providers_queried": [],
        }

    def _retrieve_sector(self, sector_key: str) -> dict[str, Any]:
        sector = dict(SECTOR_INTELLIGENCE.get(sector_key) or {"sector_key": sector_key, "missing": True})
        sources = ["agi_knowledge_catalog"]
        # Soft consume published CSKP knowledge — never construct / collect
        cskp_tip = self._soft_cskp_sector(sector_key)
        if cskp_tip:
            sector = {**sector, "cskp_published": cskp_tip}
            sources.append("cskp_sector_knowledge_store")
        hsip_tip = self._soft_hsip_sector(sector_key)
        historical = {
            "sector_learning": sector.get("sector_learning"),
            "cycles": ["crisis", "digital", "covid_surge", "ai_boom"]
            if sector_key == "information_technology"
            else ["credit", "rate", "liquidity"],
        }
        if hsip_tip:
            historical = {**historical, "hsip_timeline": hsip_tip}
            sources.append("hsip_sector_history_store")
        sri_tip = self._soft_sri_sector(sector_key)
        relationship_intelligence: list[dict[str, Any]] = [
            {"source": sector_key, "target": "USDINR", "type": "Revenue Sensitivity"}
        ] if sector_key == "information_technology" else [
            {"source": "rbi_rate_cut", "target": "banks", "type": "Positive Historical Impact"}
        ]
        if sri_tip:
            relationship_intelligence = list(sri_tip.get("relationships") or relationship_intelligence)
            sources.append("sri_sector_relationship_store")
        hsai_tip = self._soft_hsai_analogues(sector_key)
        historical_analogues: list[dict[str, Any]] = [
            {
                "matched_period": "2022-2023",
                "label": "Post-pandemic demand air-pocket",
                "similarity_score": 80.0,
            }
        ] if sector_key == "information_technology" else [
            {"matched_period": "2020", "label": "COVID credit cycle", "similarity_score": 78.0}
        ]
        if hsai_tip and hsai_tip.get("top_analogues"):
            historical_analogues = list(hsai_tip["top_analogues"])
            sources.append("hsai_sector_analogue_store")
        sfi_tip = self._soft_sfi_forecast(sector_key)
        forecast_intelligence: dict[str, Any] | None = None
        if sfi_tip:
            forecast_intelligence = sfi_tip
            sources.append("sfi_sector_forecast_store")
            if sfi_tip.get("scenarios"):
                catalysts = [
                    c
                    for s in sfi_tip["scenarios"]
                    for c in (s.get("catalysts") or [])
                ][:6] or [{"catalyst": "Demand inflection", "polarity": "mixed"}]
                risks = [
                    r
                    for s in sfi_tip["scenarios"]
                    for r in (s.get("risks") or [])
                ][:6] or [{"risk": "Global demand shock", "severity": "High"}]
            else:
                catalysts = [{"catalyst": "Demand inflection", "polarity": "mixed"}]
                risks = [{"risk": "Global demand shock", "severity": "High"}]
        else:
            catalysts = [{"catalyst": "Demand inflection", "polarity": "mixed"}]
            risks = [{"risk": "Global demand shock", "severity": "High"}]
        return {
            "current_knowledge": {
                "sector_key": sector_key,
                "label": sector.get("label") or (cskp_tip or {}).get("label"),
            },
            "sector_intelligence": sector,
            "historical_intelligence": historical,
            "historical_analogues": historical_analogues,
            "relationship_intelligence": relationship_intelligence,
            "forecast_intelligence": forecast_intelligence,
            "market_intelligence": dict(MARKET_INTELLIGENCE),
            "macro_intelligence": dict(MACRO_INTELLIGENCE),
            "research_intelligence": {
                "sector_research_office": sector.get("outlook")
                or (cskp_tip or {}).get("current_outlook"),
                "macro_research_office": MACRO_INTELLIGENCE.get("rbi"),
            },
            "monitoring_events": [{"event": "Sector earnings season", "status": "Watching"}],
            "catalysts": catalysts,
            "risks": risks,
            "pattern_intelligence": {"deferred": True, "sprint": "8.5"},
            "outlook_dimensions": list(
                sector.get("outlook_dimensions")
                or ["Growth Outlook", "Margin Outlook", "Valuation Outlook"]
            ),
            "sources": sources,
            "providers_queried": [],
        }

    def _soft_cskp_sector(self, sector_key: str) -> dict[str, Any] | None:
        """Read-only CSKP gateway — never triggers builders."""
        try:
            from continuous_sector_knowledge.production import sector as cskp_sector
            from continuous_sector_knowledge.schema import canonicalize

            # Map IFI keys → CSKP keys
            alias = {
                "information_technology": "it_services",
                "financials": "banking",
                "energy": "oil_gas",
            }.get(sector_key, sector_key)
            key = canonicalize(alias) or alias
            pack = cskp_sector(key)
            if pack.get("found") and pack.get("latest"):
                tip = dict(pack["latest"])
                tip["gateway"] = "CSKP_KRIG"
                tip["collected_on_request"] = False
                tip["constructed_on_request"] = False
                tip["providers_queried"] = []
                return tip
            return None
        except Exception:
            return None

    def _soft_hsip_sector(self, sector_key: str) -> dict[str, Any] | None:
        """Read-only HSIP gateway — never triggers historical collectors."""
        try:
            from continuous_sector_knowledge.schema import canonicalize
            from historical_sector_intelligence.production import sector as hsip_sector

            alias = {
                "information_technology": "it_services",
                "financials": "banking",
                "energy": "oil_gas",
            }.get(sector_key, sector_key)
            key = canonicalize(alias) or alias
            pack = hsip_sector(key, limit=40)
            if pack.get("found"):
                return {
                    "sector": key,
                    "n": pack.get("n"),
                    "timeline": pack.get("timeline"),
                    "valuation_timeline": pack.get("valuation_timeline"),
                    "sample_periods": [
                        o.get("period") for o in (pack.get("observations") or [])[:8]
                    ],
                    "gateway": "HSIP_KRIG",
                    "collected_on_request": False,
                    "providers_queried": [],
                    "immutable": True,
                }
            return None
        except Exception:
            return None

    def _soft_sri_sector(self, sector_key: str) -> dict[str, Any] | None:
        """Read-only SRI gateway — never rebuilds the relationship graph."""
        try:
            from continuous_sector_knowledge.schema import canonicalize
            from sector_relationship_intelligence.production import for_sector as sri_for_sector

            alias = {
                "information_technology": "IT Services",
                "financials": "Banking",
                "energy": "Oil & Gas",
            }.get(sector_key)
            if not alias:
                key = canonicalize(sector_key) or sector_key
                alias = key.replace("_", " ").title()
            pack = sri_for_sector(alias, limit=20)
            if pack.get("n"):
                return {
                    "sector": alias,
                    "n": pack.get("n"),
                    "relationships": [
                        {
                            "source": r.get("source"),
                            "target": r.get("target"),
                            "type": r.get("relationship"),
                            "direction": r.get("direction"),
                            "confidence_pct": r.get("confidence_pct"),
                            "average_lag": r.get("average_lag"),
                            "kind": r.get("kind"),
                        }
                        for r in (pack.get("relationships") or [])[:8]
                    ],
                    "gateway": "SRI_KRIG",
                    "collected_on_request": False,
                    "providers_queried": [],
                }
            return None
        except Exception:
            return None

    def _soft_hsai_analogues(self, sector_key: str) -> dict[str, Any] | None:
        """Read-only HSAI gateway — never rebuilds analogue rankings."""
        try:
            from historical_sector_analogue_intelligence.production import forecast_tip

            alias = {
                "information_technology": "IT Services",
                "financials": "Banking",
                "energy": "Oil & Gas",
                "consumer_staples": "FMCG",
                "automobiles": "Auto",
                "industrials": "Capital Goods",
                "health_care": "Pharma",
                "pharmaceuticals": "Pharma",
            }.get(sector_key, sector_key.replace("_", " ").title())
            tip = forecast_tip(sector=alias, top_k=5)
            if tip.get("n"):
                tip = dict(tip)
                tip["collected_on_request"] = False
                tip["providers_queried"] = []
                return tip
            return None
        except Exception:
            return None

    def _soft_sfi_forecast(self, sector_key: str) -> dict[str, Any] | None:
        """Read-only SFI gateway — never rebuilds forecast reports."""
        try:
            from sector_forecast_intelligence.production import forecast as sfi_forecast

            alias = {
                "information_technology": "IT Services",
                "financials": "Banking",
                "energy": "Oil & Gas",
                "consumer_staples": "FMCG",
                "automobiles": "Auto",
                "industrials": "Capital Goods",
                "health_care": "Pharma",
                "pharmaceuticals": "Pharma",
            }.get(sector_key, sector_key.replace("_", " ").title())
            pack = sfi_forecast(sector=alias)
            if pack.get("scenarios"):
                return {
                    "sector": alias,
                    "probability_distribution": pack.get("probability_distribution"),
                    "confidence": pack.get("confidence"),
                    "scenarios": [
                        {
                            "scenario": s.get("scenario"),
                            "probability_pct": s.get("probability_pct"),
                            "confidence_pct": s.get("confidence_pct"),
                            "revenue_growth": s.get("revenue_growth"),
                            "earnings_growth": s.get("earnings_growth"),
                            "expected_relative_performance": s.get(
                                "expected_relative_performance"
                            ),
                            "catalysts": s.get("catalysts"),
                            "risks": s.get("risks"),
                            "narrative": (s.get("narrative") or [])[:3],
                        }
                        for s in (pack.get("scenarios") or [])
                    ],
                    "company_impact_matrix": pack.get("company_impact_matrix"),
                    "macro_inheritance": pack.get("macro_inheritance"),
                    "gateway": "SFI_KRIG",
                    "collected_on_request": False,
                    "providers_queried": [],
                    "predicts_single_path": False,
                }
            return None
        except Exception:
            return None

    def _retrieve_market(self) -> dict[str, Any]:
        market = dict(MARKET_INTELLIGENCE)
        sources = ["agi_knowledge_catalog"]
        cmktp_tip = self._soft_cmktp_market()
        if cmktp_tip:
            market = {**market, "cmktp_published": cmktp_tip}
            sources.append("cmktp_market_knowledge_store")
            if cmktp_tip.get("market_regime"):
                market["regime"] = cmktp_tip["market_regime"]
            if cmktp_tip.get("risk_sentiment"):
                market["risk_sentiment"] = cmktp_tip["risk_sentiment"]
            if cmktp_tip.get("health_score") is not None:
                market["health_score"] = cmktp_tip["health_score"]
            if cmktp_tip.get("breadth"):
                market["breadth"] = cmktp_tip["breadth"]
            if cmktp_tip.get("leadership"):
                market["leadership"] = cmktp_tip["leadership"]
        historical = {
            "regimes": [
                "2016 Demonetisation",
                "2020 COVID Crash",
                "2021 Liquidity Rally",
                "2022 Inflation",
            ]
        }
        hmkip_tip = self._soft_hmkip_market()
        if hmkip_tip:
            historical = {**historical, "hmkip_timeline": hmkip_tip}
            sources.append("hmkip_market_history_store")
        relationship_intelligence: list[dict[str, Any]] = [
            {"source": "RBI", "target": "Liquidity", "type": "Transmission"},
            {"source": "Liquidity", "target": "Banks", "type": "Positive Historical Impact"},
        ]
        mkri_tip = self._soft_mkri_market()
        if mkri_tip:
            relationship_intelligence = list(
                mkri_tip.get("relationships") or relationship_intelligence
            )
            sources.append("mkri_market_relationship_store")
        historical_analogues: list[dict[str, Any]] = [
            {
                "matched_period": "2021 Liquidity Rally",
                "similarity_score": 76.0,
                "label": "Liquidity abundant",
            }
        ]
        hmkai_tip = self._soft_hmkai_analogues()
        if hmkai_tip and hmkai_tip.get("top_analogues"):
            historical_analogues = list(hmkai_tip["top_analogues"])
            sources.append("hmkai_market_analogue_store")
        mkfi_tip = self._soft_mkfi_forecast()
        forecast_intelligence: dict[str, Any] | None = None
        if mkfi_tip:
            forecast_intelligence = mkfi_tip
            sources.append("mkfi_market_forecast_store")
            if mkfi_tip.get("scenarios"):
                catalysts = [
                    c
                    for s in mkfi_tip["scenarios"]
                    for c in (s.get("catalysts") or [])
                ][:6] or [{"catalyst": "Policy liquidity impulse", "polarity": "positive"}]
                risks = [
                    r
                    for s in mkfi_tip["scenarios"]
                    for r in (s.get("risks") or [])
                ][:6] or [{"risk": "Valuation compression", "severity": "High"}]
            else:
                catalysts = [{"catalyst": "Policy liquidity impulse", "polarity": "positive"}]
                risks = [{"risk": "Valuation compression", "severity": "High"}]
        else:
            catalysts = [{"catalyst": "Policy liquidity impulse", "polarity": "positive"}]
            risks = [{"risk": "Valuation compression", "severity": "High"}]
        return {
            "current_knowledge": {"market": "NIFTY"},
            "market_intelligence": market,
            "historical_intelligence": historical,
            "historical_analogues": historical_analogues,
            "relationship_intelligence": relationship_intelligence,
            "forecast_intelligence": forecast_intelligence,
            "macro_intelligence": dict(MACRO_INTELLIGENCE),
            "sector_intelligence": {"note": "Cross-sector breadth mixed"},
            "research_intelligence": {"market_research_office": "Regime watch — valuation elevated"},
            "monitoring_events": [{"event": "FII flows / liquidity", "status": "Watching"}],
            "catalysts": catalysts,
            "risks": risks,
            "pattern_intelligence": {"deferred": True, "sprint": "8.5"},
            "outlook_dimensions": list(market.get("outlook_dimensions") or []),
            "sources": sources,
            "providers_queried": [],
        }

    def _soft_cmktp_market(self) -> dict[str, Any] | None:
        """Read-only CMKTP gateway — never triggers market builders or live feeds."""
        try:
            from continuous_market_knowledge.production import market as cmktp_market

            pack = cmktp_market()
            if pack.get("found") and pack.get("market"):
                tip = dict(pack["market"])
                tip["gateway"] = "CMKTP_KRIG"
                tip["collected_on_request"] = False
                tip["constructed_on_request"] = False
                tip["providers_queried"] = []
                return tip
            return None
        except Exception:
            return None

    def _soft_hmkip_market(self) -> dict[str, Any] | None:
        """Read-only HMKIP gateway — never triggers historical collectors."""
        try:
            from historical_market_intelligence.production import market as hmkip_market

            pack = hmkip_market("india_equity", limit=40)
            if pack.get("found"):
                return {
                    "market": pack.get("market"),
                    "n": pack.get("n"),
                    "timeline": pack.get("timeline"),
                    "sample_events": [
                        {
                            "period": o.get("period"),
                            "regime": o.get("market_regime"),
                            "events": o.get("major_events"),
                        }
                        for o in (pack.get("observations") or [])[:8]
                    ],
                    "gateway": "HMKIP_KRIG",
                    "collected_on_request": False,
                    "providers_queried": [],
                }
            return None
        except Exception:
            return None

    def _soft_mkri_market(self) -> dict[str, Any] | None:
        """Read-only MKRI gateway — never rebuilds the market relationship graph."""
        try:
            from market_relationship_intelligence.production import for_indicator
            from market_relationship_intelligence.production import relationships as mkri_all

            pack = for_indicator("Repo Rate", limit=20)
            if not pack.get("n"):
                pack = mkri_all(limit=20)
            if pack.get("n"):
                return {
                    "n": pack.get("n"),
                    "relationships": [
                        {
                            "source": r.get("source"),
                            "target": r.get("target"),
                            "type": r.get("relationship"),
                            "direction": r.get("direction"),
                            "confidence_pct": r.get("confidence_pct"),
                            "average_lag": r.get("average_lag"),
                            "kind": r.get("kind"),
                        }
                        for r in (pack.get("relationships") or [])[:20]
                    ],
                    "gateway": "MKRI_KRIG",
                    "collected_on_request": False,
                    "providers_queried": [],
                }
            return None
        except Exception:
            return None

    def _soft_hmkai_analogues(self) -> dict[str, Any] | None:
        """Read-only HMKAI gateway — never rebuilds analogue catalogues."""
        try:
            from historical_market_analogue_intelligence.production import forecast_tip

            tip = forecast_tip(market="India", top_k=5)
            if tip.get("n"):
                tip["gateway"] = "HMKAI_KRIG"
                tip["collected_on_request"] = False
                tip["providers_queried"] = []
                return tip
            return None
        except Exception:
            return None

    def _soft_mkfi_forecast(self) -> dict[str, Any] | None:
        """Read-only MKFI gateway — never rebuilds market forecast reports."""
        try:
            from market_forecast_intelligence.production import forecast as mkfi_forecast

            pack = mkfi_forecast(market="India", horizon="6 Months")
            if pack.get("scenarios"):
                return {
                    "market": pack.get("market") or "India",
                    "horizon": pack.get("horizon") or "6 Months",
                    "probability_distribution": pack.get("probability_distribution"),
                    "confidence": pack.get("confidence"),
                    "current_outlook": pack.get("current_outlook"),
                    "scenarios": [
                        {
                            "scenario": s.get("scenario"),
                            "probability_pct": s.get("probability_pct"),
                            "confidence_pct": s.get("confidence_pct"),
                            "market_direction": s.get("market_direction"),
                            "breadth": s.get("breadth"),
                            "liquidity": s.get("liquidity"),
                            "volatility": s.get("volatility"),
                            "sector_leadership": s.get("sector_leadership"),
                            "catalysts": s.get("catalysts"),
                            "risks": s.get("risks"),
                            "invalidators": s.get("invalidators"),
                            "narrative": (s.get("narrative") or [])[:3],
                        }
                        for s in (pack.get("scenarios") or [])
                    ],
                    "sector_leadership_forecast": pack.get("sector_leadership_forecast"),
                    "macro_inheritance": pack.get("macro_inheritance"),
                    "gateway": "MKFI_KRIG",
                    "collected_on_request": False,
                    "providers_queried": [],
                    "predicts_single_path": False,
                }
            return None
        except Exception:
            return None

    def _retrieve_macro(self) -> dict[str, Any]:
        macro = dict(MACRO_INTELLIGENCE)
        sources = ["agi_knowledge_catalog"]
        # Soft consume published CMKP knowledge — never collect
        cmkp_tip = self._soft_cmkp_macro()
        if cmkp_tip:
            macro = {**macro, "cmkp_published": cmkp_tip}
            sources.append("cmkp_macro_knowledge_store")
        # Soft consume HMAI analogue bundle — never collect / no external APIs
        hmai_tip = self._soft_hmai_analogues()
        analogues = [
            {"matched_period": "2015-2017 easing", "similarity_score": 84.0},
            {"matched_period": "2025 Rate-Cut Optionality", "similarity_score": 90.0},
        ]
        if hmai_tip and hmai_tip.get("top_analogues"):
            analogues = list(hmai_tip["top_analogues"])
            sources.append("hmai_macro_analogue_store")
            macro = {**macro, "hmai_analogues": hmai_tip}
        return {
            "current_knowledge": {"region": "India"},
            "macro_intelligence": macro,
            "historical_intelligence": {
                "cycles": ["RBI easing", "Inflation shock 2022", "COVID policy response"],
                "current_regime": (hmai_tip or {}).get("current_regime"),
            },
            "historical_analogues": analogues,
            "relationship_intelligence": [
                {
                    "source": "RBI Rate Cut",
                    "target": "Banks",
                    "type": "Positive Historical Impact",
                    "chain": ["Housing", "Autos", "Consumption"],
                }
            ],
            "market_intelligence": dict(MARKET_INTELLIGENCE),
            "sector_intelligence": {"beneficiaries": ["financials", "autos", "housing"]},
            "research_intelligence": {"macro_research_office": macro.get("rbi")},
            "monitoring_events": [
                {"event": "CPI print", "status": "Scheduled"},
                {"event": "RBI MPC", "status": "Scheduled"},
            ],
            "catalysts": [{"catalyst": "Confirmed rate cut", "polarity": "positive"}],
            "risks": [{"risk": "Inflation surprise", "severity": "High"}],
            "pattern_intelligence": {"deferred": True, "sprint": "8.5"},
            "outlook_dimensions": list(macro.get("outlook_dimensions") or []),
            "sources": sources,
            "providers_queried": [],
        }

    def _soft_hmai_analogues(self) -> dict[str, Any] | None:
        """Read-only HMAI gateway — never triggers collectors or external APIs."""
        try:
            from historical_macro_analogue_intelligence.production import forecast_tip

            tip = forecast_tip(country="India", top_k=5)
            if tip.get("n"):
                return tip
            return None
        except Exception:
            return None

    def _soft_cmkp_macro(self) -> dict[str, Any] | None:
        """Read-only CMKP + HMIP gateways — never triggers collectors."""
        try:
            from continuous_macro_knowledge.production import india as cmkp_india
            from continuous_macro_knowledge.production import indicator as cmkp_indicator

            bundle = cmkp_india(limit=40)
            tip: dict[str, Any] = {
                "collected_on_request": False,
                "gateway": "CMKP_KRIG",
            }
            if bundle.get("n"):
                repo = cmkp_indicator("Repo Rate", country="India")
                cpi = cmkp_indicator("CPI", country="India")
                tip.update(
                    {
                        "published_count": bundle.get("n"),
                        "by_category": {
                            k: len(v) for k, v in (bundle.get("by_category") or {}).items()
                        },
                        "repo_rate": (repo.get("latest") or {}).get("current_value")
                        if repo.get("found")
                        else None,
                        "cpi": (cpi.get("latest") or {}).get("current_value")
                        if cpi.get("found")
                        else None,
                    }
                )
            # Soft historical memory tip from HMIP (store-only)
            try:
                from historical_macro_intelligence.production import indicator as hmip_indicator

                hist_repo = hmip_indicator("Repo Rate", country="India")
                if hist_repo.get("found"):
                    tip["historical_repo_timeline"] = {
                        "n": hist_repo.get("n"),
                        "completeness_pct": (hist_repo.get("timeline") or {}).get(
                            "completeness_pct"
                        ),
                        "years_span": (hist_repo.get("timeline") or {}).get("years_span"),
                        "gateway": "HMIP_KRIG",
                        "providers_queried": [],
                    }
            except Exception:
                pass
            # Soft relationship tip from MRI (store-only)
            try:
                from macroeconomic_relationship_intelligence.production import (
                    for_indicator as mri_for_indicator,
                )

                mri_repo = mri_for_indicator("Repo Rate")
                if mri_repo.get("n"):
                    tip["macro_relationships"] = {
                        "indicator": "Repo Rate",
                        "n": mri_repo.get("n"),
                        "sample_targets": [
                            r.get("target") for r in (mri_repo.get("relationships") or [])[:5]
                        ],
                        "gateway": "MRI_KRIG",
                        "providers_queried": [],
                    }
            except Exception:
                pass
            return (
                tip
                if tip.get("published_count")
                or tip.get("historical_repo_timeline")
                or tip.get("macro_relationships")
                else None
            )
        except Exception:
            return None

    def _retrieve_theme(self, theme_key: str) -> dict[str, Any]:
        base = THEME_INTELLIGENCE.get(theme_key) or THEME_INTELLIGENCE["artificial_intelligence"]
        theme = {**base, "theme_key": theme_key}
        return {
            "current_knowledge": {"theme": theme.get("theme") or theme_key},
            "research_intelligence": {"theme_research_office": theme},
            "sector_intelligence": {"sector_impact": theme.get("sector_impact")},
            "historical_intelligence": {"theme_history": "Digital → Cloud → AI spending sequence"},
            "historical_analogues": [
                {"matched_period": "2014 Digital Transformation", "similarity_score": 70.0}
            ],
            "relationship_intelligence": [
                {"source": "AI Spending", "target": "INFY", "type": "Demand Driver"}
            ],
            "market_intelligence": dict(MARKET_INTELLIGENCE),
            "macro_intelligence": dict(MACRO_INTELLIGENCE),
            "monitoring_events": [{"event": "Enterprise AI budget revisions", "status": "Watching"}],
            "catalysts": [{"catalyst": "Production AI conversions", "polarity": "positive"}],
            "risks": list(
                {"risk": r, "severity": "Medium"} for r in (theme.get("risks") or [])
            ),
            "pattern_intelligence": {"deferred": True, "sprint": "8.5"},
            "outlook_dimensions": list(theme.get("outlook_dimensions") or []),
            "sources": ["agi_knowledge_catalog"],
            "providers_queried": [],
            "theme": theme,
        }

    def _prepare_context(
        self, scope: ForecastScope, entity: str, retrieved: dict[str, Any]
    ) -> dict[str, Any]:
        pspan = traces.begin(
            "forecast_context_preparation",
            meta={"scope": scope.value, "entity": entity},
        )
        supporting = []
        contradictory = []
        for c in retrieved.get("catalysts") or []:
            if c.get("polarity") == "negative":
                contradictory.append(
                    {"kind": "catalyst", "summary": c.get("catalyst"), "evidence": c.get("evidence")}
                )
            else:
                supporting.append(
                    {"kind": "catalyst", "summary": c.get("catalyst"), "evidence": c.get("evidence")}
                )
        for a in retrieved.get("historical_analogues") or []:
            supporting.append(
                {
                    "kind": "historical_analogue",
                    "summary": f"{a.get('matched_period')}: {a.get('label') or a.get('matched_label')}",
                    "score": a.get("similarity_score"),
                }
            )
        for r in retrieved.get("relationship_intelligence") or []:
            supporting.append(
                {
                    "kind": "relationship",
                    "summary": f"{r.get('source')} → {r.get('target')} ({r.get('type') or r.get('relationship_type')})",
                    "confidence": r.get("confidence"),
                }
            )

        completeness = assess_completeness(retrieved)
        freshness = {
            "catalog": "institutional_seed",
            "hip_enriched": "hip_hko" in (retrieved.get("sources") or []),
            "knowledge_platform": "agi_knowledge_platform" in (retrieved.get("sources") or []),
            "current_as_of": "bundle_preparation_time",
            "monitoring": "current" if retrieved.get("monitoring_events") else "missing",
            **(retrieved.get("knowledge_freshness") or {}),
        }
        confidence_inputs = {
            "completeness_score": completeness.score,
            "analogue_count": len(retrieved.get("historical_analogues") or []),
            "relationship_count": len(retrieved.get("relationship_intelligence") or []),
            "research_present": bool(retrieved.get("research_intelligence")),
            "pattern_intelligence_ready": not (
                (retrieved.get("pattern_intelligence") or {}).get("deferred")
            ),
            "rule": "Confidence inputs only — IFI does not assign scenario probabilities",
        }
        prepared = {
            **retrieved,
            "supporting_evidence": supporting,
            "contradictory_evidence": contradictory,
            "completeness": completeness,
            "knowledge_freshness": freshness,
            "knowledge_coverage": {
                "overall": completeness.overall.value,
                "missing_evidence": list(completeness.missing_evidence),
                "score": completeness.score,
            },
            "confidence_inputs": confidence_inputs,
            "market_snapshot": retrieved.get("market_snapshot"),
        }
        traces.end(
            pspan,
            output={
                "supporting": len(supporting),
                "contradictory": len(contradictory),
                "completeness": completeness.overall.value,
            },
        )
        return prepared

    def _publish(self, scope: ForecastScope, entity: str, prepared: dict[str, Any]) -> ForecastBundle:
        pspan = traces.begin(
            "forecast_publication",
            meta={"scope": scope.value, "entity": entity},
        )
        label = None
        ck = prepared.get("current_knowledge") or {}
        if scope == ForecastScope.COMPANY:
            label = ck.get("name") or entity
        elif scope == ForecastScope.SECTOR:
            label = (prepared.get("sector_intelligence") or {}).get("label") or entity
        elif scope == ForecastScope.MARKET:
            label = "NIFTY"
        elif scope == ForecastScope.MACRO:
            label = "India"
        elif scope == ForecastScope.THEME:
            label = ((prepared.get("theme") or {}).get("theme")) or entity

        # Embed market snapshot inside market_intelligence / current_knowledge (bundle contract)
        market_intel = dict(prepared.get("market_intelligence") or {})
        if prepared.get("market_snapshot") and "live_snapshot" not in market_intel:
            market_intel["live_snapshot"] = prepared.get("market_snapshot")

        bundle = ForecastBundle(
            scope=scope,
            entity=entity,
            entity_label=label,
            current_knowledge=prepared.get("current_knowledge") or {},
            historical_intelligence=prepared.get("historical_intelligence") or {},
            historical_analogues=list(prepared.get("historical_analogues") or []),
            relationship_intelligence=list(prepared.get("relationship_intelligence") or []),
            pattern_intelligence=prepared.get("pattern_intelligence") or {},
            research_intelligence=prepared.get("research_intelligence") or {},
            sector_intelligence=prepared.get("sector_intelligence") or {},
            market_intelligence=market_intel,
            macro_intelligence=prepared.get("macro_intelligence") or {},
            monitoring_events=list(prepared.get("monitoring_events") or []),
            catalysts=list(prepared.get("catalysts") or []),
            risks=list(prepared.get("risks") or []),
            contradictory_evidence=list(prepared.get("contradictory_evidence") or []),
            supporting_evidence=list(prepared.get("supporting_evidence") or []),
            outlook_dimensions=list(prepared.get("outlook_dimensions") or []),
            confidence_inputs=prepared.get("confidence_inputs") or {},
            knowledge_freshness=prepared.get("knowledge_freshness") or {},
            knowledge_coverage=prepared.get("knowledge_coverage") or {},
            completeness=prepared["completeness"],
            provenance={
                "gateway": "IFI",
                "version": IFI_VERSION,
                "sources": prepared.get("sources") or ["agi_knowledge_catalog"],
                "providers_hidden": True,
                "scenario_selection": False,
                "provider_architecture": "india_first",
                "controlled_refresh": "market_snapshot_when_stale",
                "forecast_direct_provider_calls": False,
                "provider_refresh": prepared.get("provider_refresh"),
            },
            providers_queried=[],
        )
        traces.end(pspan, output={"bundle_id": bundle.bundle_id, "published": True})
        return bundle
