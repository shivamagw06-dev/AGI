"""Market Forecast Intelligence engine — Bull/Base/Bear from AGI market knowledge."""

from __future__ import annotations

from typing import Any

from market_forecast_intelligence import traces
from market_forecast_intelligence.bundle import assemble_bundle, normalize_market
from market_forecast_intelligence.impacts import impact_matrices, sector_impacts_for
from market_forecast_intelligence.probability import assign_probabilities, score_confidence
from market_forecast_intelligence.schema import (
    FORECAST_DIMENSIONS,
    FORECAST_HORIZONS,
    MKFI_VERSION,
    NO_MKFI_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    SUPPORTED_MARKETS,
    DirectionLabel,
    MarketDimensionForecast,
    MarketForecastReport,
    MarketScenario,
    ScenarioType,
)
from market_forecast_intelligence.store import STORE
from market_forecast_intelligence.templates import (
    assumptions_for,
    catalysts_for,
    cross_asset_for,
    dimensions_for,
    drivers_for,
    invalidators_for,
    leadership_for,
    narratives_for,
    risks_for,
)


class MarketForecastIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "ok": True,
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": MKFI_VERSION,
            "mkfi_version": MKFI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_MKFI_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "consumes": [
                "CMKTP",
                "HMKIP",
                "MKRI",
                "HMKAI",
                "MFI (macro inheritance)",
                "SFI (sector inheritance)",
            ],
            "feeds": [
                "Sector Forecast Intelligence",
                "Company Intelligence",
                "Portfolio Intelligence",
                "Investment Office",
            ],
            "phase": "12.5",
            "preceded_by": ["CMKTP 12.1", "HMKIP 12.2", "MKRI 12.3", "HMKAI 12.4"],
            "predicts_single_path": False,
            "inherits_macro_from": "MFI",
            "supported_markets": list(SUPPORTED_MARKETS),
            "forecast_horizons": list(FORECAST_HORIZONS),
            "forecast_dimensions": list(FORECAST_DIMENSIONS),
            "langsmith_traces": list(traces.TRACE_NAMES),
            "note": "Programme short MKFI avoids collision with Macro MFI",
        }

    def run(
        self,
        *,
        market: str | None = None,
        horizon: str | None = None,
        country: str | None = None,
        markets: list[str] | None = None,
        horizons: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ops publish — assemble + generate + publish. Never Ask."""
        if markets:
            markets = [normalize_market(m) or m for m in markets if m]
        elif market:
            markets = [normalize_market(market) or market]
        else:
            markets = list(SUPPORTED_MARKETS)
        if horizons:
            horizons = [h for h in horizons if h]
        elif horizon:
            horizons = [horizon]
        else:
            horizons = list(FORECAST_HORIZONS)
        published = 0
        per: dict[str, Any] = {}
        for mkt in markets:
            if not mkt:
                continue
            for hz in horizons:
                report = self.generate_report(
                    market=mkt, horizon=hz, country=country, persist=True
                )
                published += 1
                key = f"{mkt}:{hz}"
                per[key] = {
                    "report_id": report.report_id,
                    "version": report.version,
                    "probability_distribution": report.probability_distribution,
                    "confidence_pct": (report.confidence or {}).get("overall_pct"),
                }
        summary = {
            "ok": True,
            "markets": [m for m in markets if m],
            "horizons": horizons,
            "published": published,
            "per_report": per,
            "ask_triggered": False,
            "providers_queried": [],
            "scenarios": ["Bull", "Base", "Bear"],
            "programme_short": PROGRAMME_SHORT,
        }
        STORE.record_run(summary)
        return summary

    def generate_report(
        self,
        *,
        market: str = "India",
        horizon: str = "6 Months",
        country: str | None = None,
        persist: bool = False,
    ) -> MarketForecastReport:
        mkt = normalize_market(market) or market
        bundle = assemble_bundle(market=mkt, horizon=horizon, country=country)
        scenarios = self._generate_scenarios(bundle)
        dist = self._assign_probability(scenarios, bundle)
        confidence = self._score_confidence(scenarios, bundle)
        leadership, sector_matrix = impact_matrices(scenarios)

        vspan = traces.begin(
            "market_forecast_validation",
            meta={"market": mkt, "horizon": horizon, "completeness": bundle.completeness_pct},
        )
        contradictions = self._contradictions(scenarios, bundle)
        traces.end(vspan, output={"contradictions": len(contradictions)})

        rspan = traces.begin("market_risk_engine", meta={"market": mkt})
        major_risks: list[dict[str, Any]] = []
        invalidators: list[str] = []
        seen: set[str] = set()
        for sc in scenarios:
            for r in sc.risks:
                key = str(r.get("risk"))
                if key in seen:
                    continue
                seen.add(key)
                major_risks.append({**r, "scenario_context": sc.scenario})
            for inv in sc.invalidators:
                if inv not in invalidators:
                    invalidators.append(inv)
        traces.end(rspan, output={"risks": len(major_risks), "invalidators": len(invalidators)})

        cspan = traces.begin("market_catalyst_engine", meta={"market": mkt})
        key_catalysts = self._catalysts(bundle, scenarios)
        traces.end(cspan, output={"catalysts": len(key_catalysts)})

        report = MarketForecastReport(
            market=mkt,
            country=bundle.country,
            horizon=horizon,
            bundle_id=bundle.bundle_id,
            current_outlook={
                "market": mkt,
                "regime": (bundle.current_market or {}).get("market_regime"),
                "risk_sentiment": (bundle.current_market or {}).get("risk_sentiment"),
                "health_score": (bundle.current_market or {}).get("health_score"),
                "completeness_pct": bundle.completeness_pct,
            },
            current_regime=bundle.current_regime,
            scenarios=scenarios,
            probability_distribution=dist,
            confidence=confidence,
            sector_leadership_forecast=leadership,
            sector_impact_matrix=sector_matrix,
            key_catalysts=key_catalysts,
            major_risks=major_risks[:12],
            invalidation_alerts=invalidators[:12],
            macro_inheritance={
                "gateway": "MFI_KRIG",
                "inherited": bool((bundle.macro_forecast_tip or {}).get("inherited")),
                "probability_distribution": (bundle.macro_forecast_tip or {}).get(
                    "probability_distribution"
                ),
                "scenarios": (bundle.macro_forecast_tip or {}).get("scenarios") or [],
            },
            sector_inheritance={
                "gateway": "SFI_KRIG",
                "inherited": bool((bundle.sector_forecast_tip or {}).get("inherited")),
                "probability_distribution": (bundle.sector_forecast_tip or {}).get(
                    "probability_distribution"
                ),
            },
            contradictions=contradictions,
            providers_queried=[],
            provenance={
                "sources": bundle.sources,
                "completeness_pct": bundle.completeness_pct,
                "analogue_n": len(bundle.analogues),
                "relationship_n": len(bundle.relationships),
            },
        )

        if persist:
            pspan = traces.begin(
                "market_forecast_publication",
                meta={"market": mkt, "horizon": horizon, "bundle_id": bundle.bundle_id},
            )
            published = STORE.publish(report)
            traces.end(
                pspan,
                output={
                    "report_id": published.report_id,
                    "version": published.version,
                    "distribution": published.probability_distribution,
                },
            )
            return published
        return report

    def _generate_scenarios(self, bundle) -> list[MarketScenario]:
        span = traces.begin(
            "market_scenario_generation",
            meta={"market": bundle.market, "horizon": bundle.horizon},
        )
        macro_scenarios = {
            s.get("scenario"): s
            for s in ((bundle.macro_forecast_tip or {}).get("scenarios") or [])
        }
        scenarios: list[MarketScenario] = []
        for stype in ("Bull", "Base", "Bear"):
            scenario_type: ScenarioType = stype  # type: ignore[assignment]
            dims = dimensions_for(scenario_type)
            lead = leadership_for(bundle.market, scenario_type)
            direction: DirectionLabel = dims["market_direction"]  # type: ignore[assignment]

            evidence = [
                {
                    "kind": "continuous_market",
                    "summary": "Current market tip from CMKTP",
                    "refs": ["CMKTP_KRIG"],
                },
                {
                    "kind": "research",
                    "summary": (bundle.research or {})
                    .get("market_research_office", {})
                    .get("stance")
                    or "Market research tip",
                    "refs": ["Market_Research_Tip"],
                },
                {
                    "kind": "macro_inheritance",
                    "summary": "Macro assumptions inherited from MFI",
                    "refs": ["MFI_KRIG"],
                },
                {
                    "kind": "sector_inheritance",
                    "summary": "Sector outlook tip inherited from SFI",
                    "refs": ["SFI_KRIG"],
                },
            ]
            analogues = []
            for a in bundle.analogues[:4]:
                analogues.append(
                    {
                        "matched_period": a.get("matched_period"),
                        "similarity_score": a.get("similarity_score"),
                        "label": a.get("matched_label") or a.get("label"),
                        "outcome": a.get("historical_outcome"),
                        "equity_outcome": a.get("equity_outcome"),
                        "historical_outcome_bundle": a.get("historical_outcome_bundle"),
                    }
                )
                evidence.append(
                    {
                        "kind": "historical_analogue",
                        "summary": f"Analogue {a.get('matched_period')}: {a.get('matched_label') or a.get('label')}",
                        "refs": a.get("timeline_refs") or ["HMKAI_KRIG"],
                    }
                )
            if not analogues:
                analogues = [
                    {
                        "matched_period": "2021 Liquidity Rally",
                        "similarity_score": 74.0,
                        "label": "Liquidity abundant",
                        "outcome": "Equities re-rated with improving breadth",
                    },
                    {
                        "matched_period": "2022 Inflation / Tightening",
                        "similarity_score": 68.0,
                        "label": "Policy restraint",
                        "outcome": "Multiple compression and risk-off leadership",
                    },
                ]
                evidence.append(
                    {
                        "kind": "historical_analogue",
                        "summary": "Catalog market analogues (HMKAI tip unavailable)",
                        "refs": ["HMKAI_catalog"],
                    }
                )
            if bundle.historical_tip.get("available"):
                evidence.append(
                    {
                        "kind": "historical_market",
                        "summary": "HMKIP series / timeline coverage",
                        "refs": ["HMKIP_KRIG"],
                    }
                )

            rel_sample = [
                {
                    "source": r.get("source"),
                    "target": r.get("target"),
                    "relationship": r.get("relationship") or r.get("type"),
                    "confidence_pct": r.get("confidence_pct"),
                    "kind": r.get("kind"),
                }
                for r in bundle.relationships[:8]
            ]
            if not rel_sample:
                rel_sample = [
                    {
                        "source": "Repo Rate",
                        "target": "Liquidity",
                        "relationship": "Transmission",
                        "confidence_pct": 82,
                        "kind": "policy",
                    },
                    {
                        "source": "Liquidity",
                        "target": "Equity Breadth",
                        "relationship": "Positive Historical Impact",
                        "confidence_pct": 78,
                        "kind": "market",
                    },
                    {
                        "source": "FII Flows",
                        "target": "Nifty",
                        "relationship": "Risk Appetite Channel",
                        "confidence_pct": 76,
                        "kind": "flows",
                    },
                ]

            sector_imps = sector_impacts_for(
                bundle.market, scenario_type, relationships=bundle.relationships
            )

            msc = macro_scenarios.get(stype) or {}
            macro_assumptions = []
            if msc:
                macro_assumptions = [
                    {"driver": "Repo Rate path", "value": msc.get("repo_rate"), "source": "MFI"},
                    {"driver": "CPI path", "value": msc.get("inflation"), "source": "MFI"},
                    {"driver": "GDP path", "value": msc.get("gdp"), "source": "MFI"},
                    {"driver": "USDINR path", "value": msc.get("usdinr"), "source": "MFI"},
                ]
            else:
                macro_assumptions = [
                    {"driver": a, "source": "MKFI_catalog_macro_neutrality"}
                    for a in assumptions_for(scenario_type)[:4]
                ]

            dimension_rows = [
                MarketDimensionForecast(dimension=k, value=v)
                for k, v in dims.items()
                if k != "market_direction"
            ]

            scenarios.append(
                MarketScenario(
                    scenario=scenario_type,
                    market=bundle.market,
                    country=bundle.country,
                    forecast_horizon=bundle.horizon,
                    market_regime=dims.get("market_regime"),
                    market_direction=direction,
                    breadth=dims.get("breadth", "Stable"),
                    liquidity=dims.get("liquidity", "Stable"),
                    volatility=dims.get("volatility", "Moderate"),
                    institutional_flows=dims.get("institutional_flows", "Balanced"),
                    sector_leadership=list(lead.get("leaders") or []),
                    weak_sectors=list(lead.get("weak") or []),
                    cross_asset_outlook=cross_asset_for(scenario_type),
                    dimensions=dimension_rows,
                    narrative=narratives_for(bundle.market, scenario_type),
                    drivers=drivers_for(bundle.market, scenario_type),
                    catalysts=catalysts_for(scenario_type),
                    risks=risks_for(scenario_type),
                    invalidators=invalidators_for(scenario_type),
                    key_assumptions=assumptions_for(scenario_type),
                    supporting_evidence=evidence,
                    historical_analogues=analogues,
                    supporting_relationships=rel_sample,
                    macro_assumptions=macro_assumptions,
                    sector_impacts=sector_imps,
                    provenance={
                        "macro_inherited": bool(msc),
                        "sources": bundle.sources,
                    },
                )
            )

        traces.end(
            span,
            output={
                "scenarios": [s.scenario for s in scenarios],
                "horizon": bundle.horizon,
            },
        )
        return scenarios

    def _assign_probability(self, scenarios, bundle) -> dict[str, int]:
        span = traces.begin(
            "market_probability", meta={"market": bundle.market, "horizon": bundle.horizon}
        )
        dist = assign_probabilities(scenarios, bundle)
        traces.end(span, output={"distribution": dist, "sum": sum(dist.values())})
        return dist

    def _score_confidence(self, scenarios, bundle) -> dict[str, Any]:
        span = traces.begin(
            "market_confidence", meta={"completeness": bundle.completeness_pct}
        )
        conf = score_confidence(scenarios, bundle)
        traces.end(span, output={"overall_pct": conf.get("overall_pct"), "label": conf.get("label")})
        return conf

    def _catalysts(self, bundle, scenarios) -> list[dict[str, Any]]:
        cats: list[dict[str, Any]] = []
        seen: set[str] = set()
        for sc in scenarios:
            for c in sc.catalysts:
                key = str(c.get("catalyst"))
                if key in seen:
                    continue
                seen.add(key)
                cats.append({**c, "scenario_context": sc.scenario})
        for m in bundle.monitoring[:5]:
            cats.append(
                {
                    "catalyst": m.get("event"),
                    "polarity": "watch",
                    "status": m.get("status"),
                    "importance": m.get("importance"),
                }
            )
        return cats[:12]

    def _contradictions(self, scenarios, bundle) -> list[str]:
        out: list[str] = []
        bull = next(s for s in scenarios if s.scenario == "Bull")
        bear = next(s for s in scenarios if s.scenario == "Bear")
        if bull.breadth == "Improving" and bear.breadth == "Weakening":
            out.append("Bull assumes breadth improvement while Bear assumes deterioration — participation is the key fork")
        if bull.liquidity == "Expanding" and bear.liquidity == "Contracting":
            out.append("Liquidity path is the primary regime fork between Bull and Bear")
        if bundle.analogues:
            top = bundle.analogues[0]
            if float(top.get("similarity_score") or 0) < 70:
                out.append("Top historical analogue similarity below 70 — regime match is imperfect")
        if bundle.completeness_pct < 70:
            out.append("Market knowledge completeness below 70% — widen confidence bands")
        if not (bundle.macro_forecast_tip or {}).get("inherited"):
            out.append("Macro Forecast tip unavailable — market scenarios use catalog macro neutrality")
        return out

    # --- Retrieval surfaces ---

    def forecast(
        self, *, market: str = "India", horizon: str = "6 Months"
    ) -> dict[str, Any]:
        mkt = normalize_market(market) or market
        latest = STORE.latest(market=mkt, horizon=horizon)
        if latest:
            return {
                **latest.to_public_dict(),
                "mode": "published",
                "gateway": "MKFI_KRIG",
            }
        report = self.generate_report(market=mkt, horizon=horizon, persist=False)
        return {**report.to_public_dict(), "mode": "computed", "gateway": "MKFI_KRIG"}

    def forecast_all(self, *, limit: int = 20) -> dict[str, Any]:
        rows = []
        for mkt in SUPPORTED_MARKETS:
            for hz in FORECAST_HORIZONS:
                if len(rows) >= limit:
                    break
                pack = self.forecast(market=mkt, horizon=hz)
                rows.append(
                    {
                        "market": mkt,
                        "horizon": hz,
                        "probability_distribution": pack.get("probability_distribution"),
                        "confidence_pct": (pack.get("confidence") or {}).get("overall_pct"),
                        "mode": pack.get("mode"),
                        "version": pack.get("version"),
                    }
                )
        return {
            "n": len(rows),
            "forecasts": rows,
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "MKFI_KRIG",
            "predicts_single_path": False,
        }

    def scenarios(
        self, *, market: str = "India", horizon: str = "6 Months"
    ) -> dict[str, Any]:
        pack = self.forecast(market=market, horizon=horizon)
        return {
            "market": normalize_market(market) or market,
            "horizon": horizon,
            "n": len(pack.get("scenarios") or []),
            "scenarios": pack.get("scenarios") or [],
            "probability_distribution": pack.get("probability_distribution"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "MKFI_KRIG",
        }

    def probability(
        self, *, market: str = "India", horizon: str = "6 Months"
    ) -> dict[str, Any]:
        pack = self.forecast(market=market, horizon=horizon)
        return {
            "market": normalize_market(market) or market,
            "horizon": horizon,
            "distribution": pack.get("probability_distribution") or {},
            "sum_pct": sum((pack.get("probability_distribution") or {}).values()),
            "confidence": pack.get("confidence"),
            "scenario_probabilities": [
                {
                    "scenario": s.get("scenario"),
                    "probability_pct": s.get("probability_pct"),
                    "confidence_pct": s.get("confidence_pct"),
                }
                for s in pack.get("scenarios") or []
            ],
            "providers_queried": [],
            "gateway": "MKFI_KRIG",
            "note": "Probability quantifies scenario likelihood; confidence quantifies assessment certainty.",
        }

    def catalysts(
        self, *, market: str = "India", horizon: str = "6 Months"
    ) -> dict[str, Any]:
        pack = self.forecast(market=market, horizon=horizon)
        return {
            "market": normalize_market(market) or market,
            "horizon": horizon,
            "n": len(pack.get("key_catalysts") or []),
            "catalysts": pack.get("key_catalysts") or [],
            "providers_queried": [],
            "gateway": "MKFI_KRIG",
        }

    def risks(
        self, *, market: str = "India", horizon: str = "6 Months"
    ) -> dict[str, Any]:
        pack = self.forecast(market=market, horizon=horizon)
        return {
            "market": normalize_market(market) or market,
            "horizon": horizon,
            "n": len(pack.get("major_risks") or []),
            "risks": pack.get("major_risks") or [],
            "invalidation_alerts": pack.get("invalidation_alerts") or [],
            "providers_queried": [],
            "gateway": "MKFI_KRIG",
        }

    def report(
        self,
        *,
        market: str = "India",
        horizon: str = "6 Months",
        persist: bool = False,
    ) -> dict[str, Any]:
        if persist:
            r = self.generate_report(market=market, horizon=horizon, persist=True)
            return {**r.to_public_dict(), "mode": "published", "gateway": "MKFI_KRIG"}
        return self.forecast(market=market, horizon=horizon)

    def history(
        self,
        *,
        market: str | None = None,
        horizon: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        mkt = normalize_market(market) if market else None
        rows = STORE.history(limit=limit, market=mkt, horizon=horizon)
        return {
            "market": mkt,
            "horizon": horizon,
            "n": len(rows),
            "reports": [
                {
                    "report_id": r.report_id,
                    "market": r.market,
                    "horizon": r.horizon,
                    "version": r.version,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "probability_distribution": r.probability_distribution,
                    "confidence_pct": (r.confidence or {}).get("overall_pct"),
                }
                for r in rows
            ],
            "providers_queried": [],
            "gateway": "MKFI_KRIG",
        }

    def dashboard(self) -> dict[str, Any]:
        latest = STORE.latest(market="India", horizon="6 Months") or STORE.latest()
        if not latest:
            latest = self.generate_report(market="India", horizon="6 Months", persist=False)
            published = False
        else:
            published = True
        pub = latest.to_public_dict()
        return {
            "board": "Market Forecast Intelligence",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": MKFI_VERSION,
            "principles": {
                "agi_owned_knowledge_only": True,
                "no_external_providers": True,
                "no_single_path_prediction": True,
                "ask_never_fetches": True,
                "versioned_reports": True,
                "evidence_linked_scenarios": True,
                "inherits_macro_from_mfi": True,
                "cascades_to_sector_company_portfolio": True,
            },
            "does_not": list(NO_MKFI_ACTIONS),
            "current_market_outlook": pub.get("current_outlook"),
            "bull_base_bear_scenarios": pub.get("scenarios"),
            "scenario_probabilities": pub.get("probability_distribution"),
            "probability_distribution": pub.get("probability_distribution"),
            "confidence": pub.get("confidence"),
            "confidence_trends": [
                {
                    "version": r.version,
                    "market": r.market,
                    "horizon": r.horizon,
                    "overall_pct": (r.confidence or {}).get("overall_pct"),
                }
                for r in STORE.history(limit=10)
            ],
            "forecast_horizons": list(FORECAST_HORIZONS),
            "key_catalysts": pub.get("key_catalysts"),
            "major_risks": pub.get("major_risks"),
            "invalidation_alerts": pub.get("invalidation_alerts"),
            "sector_leadership_forecast": pub.get("sector_leadership_forecast"),
            "market_health_trend": {
                "current_health": (pub.get("current_outlook") or {}).get("health_score"),
                "note": "Health path differs across Bull/Base/Bear via liquidity and breadth dimensions",
            },
            "macro_inheritance": pub.get("macro_inheritance"),
            "sector_inheritance": pub.get("sector_inheritance"),
            "forecast_revisions": self.history(limit=10),
            "forecast_accuracy_over_time": {
                "note": "Accuracy tracking reserved for post-publication outcome loops",
                "versions_tracked": STORE.coverage().get("latest_version"),
            },
            "accuracy_tracking": {
                "note": "Accuracy tracking reserved for post-publication outcome loops",
                "versions_tracked": STORE.coverage().get("latest_version"),
                "history_n": STORE.coverage().get("total_reports"),
            },
            "reports": [
                {
                    "market": r.market,
                    "horizon": r.horizon,
                    "version": r.version,
                    "probability_distribution": r.probability_distribution,
                    "confidence_pct": (r.confidence or {}).get("overall_pct"),
                }
                for r in STORE.history(limit=20)
            ],
            "coverage": STORE.coverage(),
            "retrieval_performance": {"traces": traces.recent(40)},
            "langsmith_traces": list(traces.TRACE_NAMES),
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": not published and STORE.coverage()["total_reports"] == 0,
            "phase": "12.5",
            "providers_queried": [],
            "published": published,
        }
