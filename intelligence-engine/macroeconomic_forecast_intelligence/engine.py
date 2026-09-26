"""Macroeconomic Forecast Intelligence engine — Bull/Base/Bear from AGI knowledge."""

from __future__ import annotations

from typing import Any

from macroeconomic_forecast_intelligence import traces
from macroeconomic_forecast_intelligence.bundle import assemble_bundle
from macroeconomic_forecast_intelligence.impacts import (
    company_impacts_for,
    impact_matrices,
    sector_impacts_for,
)
from macroeconomic_forecast_intelligence.probability import assign_probabilities, score_confidence
from macroeconomic_forecast_intelligence.schema import (
    MFI_VERSION,
    NO_MFI_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    MacroForecastReport,
    MacroIndicatorForecast,
    MacroScenario,
    ScenarioType,
)
from macroeconomic_forecast_intelligence.store import STORE
from macroeconomic_forecast_intelligence.templates import (
    UNITS,
    drivers_for,
    narratives_for,
    path_deltas,
    risks_for,
)


class MacroeconomicForecastIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": MFI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_MFI_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "consumes": ["CMKP", "HMIP", "MRI", "HMAI", "Macro Research tips"],
            "feeds": ["Investment Office", "Company / Sector research"],
            "phase": "10.5",
            "preceded_by": ["CMKP 10.1", "HMIP 10.2", "MRI 10.3", "HMAI 10.4"],
            "predicts_single_path": False,
            "forecast_dimensions": [
                "monetary_policy",
                "inflation",
                "growth",
                "fiscal",
                "external_sector",
                "financial_markets",
            ],
        }

    def run(self, *, country: str = "India", region: str = "India") -> dict[str, Any]:
        """Ops publish — assemble + generate + publish report. Never Ask."""
        report = self.generate_report(country=country, region=region, persist=True)
        summary = {
            "ok": True,
            "report_id": report.report_id,
            "version": report.version,
            "country": country,
            "region": region,
            "probability_distribution": report.probability_distribution,
            "confidence_pct": (report.confidence or {}).get("overall_pct"),
            "ask_triggered": False,
            "providers_queried": [],
            "scenarios": [s.scenario for s in report.scenarios],
        }
        STORE.record_run(summary)
        return summary

    def generate_report(
        self,
        *,
        country: str = "India",
        region: str = "India",
        persist: bool = False,
    ) -> MacroForecastReport:
        bundle = assemble_bundle(country=country, region=region)
        scenarios = self._generate_scenarios(bundle)
        dist = self._assign_probability(scenarios, bundle)
        confidence = self._score_confidence(scenarios, bundle)
        sector_matrix, company_matrix = impact_matrices(scenarios)

        contradictions = self._contradictions(scenarios, bundle)
        report = MacroForecastReport(
            country=country,
            region=region,
            horizon=bundle.horizon,
            bundle_id=bundle.bundle_id,
            current_regime=bundle.current_regime,
            scenarios=scenarios,
            probability_distribution=dist,
            confidence=confidence,
            sector_impact_matrix=sector_matrix,
            company_impact_matrix=company_matrix,
            key_catalysts=self._catalysts(bundle, scenarios),
            upcoming_events=list(bundle.monitoring)[:15],
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
                "macro_forecast_publication",
                meta={"country": country, "bundle_id": bundle.bundle_id},
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

    def _generate_scenarios(self, bundle) -> list[MacroScenario]:
        span = traces.begin(
            "macro_scenario_generation",
            meta={"country": bundle.country, "horizon": bundle.horizon},
        )
        tips = dict((bundle.current_macro or {}).get("tips") or {})
        # Sensible defaults if CMKP empty (still labelled as catalog fill)
        defaults = {
            "Repo Rate": 6.50,
            "CPI": 3.65,
            "GDP": 7.4,
            "Fiscal Deficit": 5.1,
            "USDINR": 83.45,
            "Banking Liquidity": 1.2,
            "Credit Growth": 14.2,
            "WPI": 2.1,
            "G-Sec 10Y": 6.85,
            "Core Inflation": 3.9,
            "IIP": 4.2,
            "Forex Reserves": 692.0,
            "GVA": 7.2,
        }
        base_levels = {**defaults, **{k: v for k, v in tips.items() if v is not None}}

        scenarios: list[MacroScenario] = []
        for stype in ("Bull", "Base", "Bear"):
            scenario_type: ScenarioType = stype  # type: ignore[assignment]
            deltas = path_deltas(scenario_type)
            indicators: list[MacroIndicatorForecast] = []
            for name, delta in deltas.items():
                level = float(base_levels.get(name, defaults.get(name, 0.0))) + float(delta)
                # Round policy-ish figures
                if name in {"Repo Rate", "CPI", "GDP", "Fiscal Deficit", "WPI", "Core Inflation", "GVA", "IIP", "G-Sec 10Y", "Credit Growth"}:
                    level = round(level, 2)
                elif name == "USDINR":
                    level = round(level, 1)
                else:
                    level = round(level, 2)
                indicators.append(
                    MacroIndicatorForecast(
                        indicator=name,
                        unit=UNITS.get(name, ""),
                        value=level,
                        note=f"{stype} path delta {delta:+}",
                    )
                )

            # Evidence
            evidence = [
                {
                    "kind": "continuous_macro",
                    "summary": "Current macro tip from CMKP",
                    "refs": ["CMKP_KRIG"],
                },
                {
                    "kind": "research",
                    "summary": (bundle.research or {}).get("macro_research_office", {}).get("stance")
                    or "Macro research tip",
                    "refs": ["Macro_Research_Tip"],
                },
            ]
            analogues = []
            for a in bundle.analogues[:4]:
                analogues.append(
                    {
                        "matched_period": a.get("matched_period"),
                        "similarity_score": a.get("similarity_score"),
                        "label": a.get("matched_label"),
                        "outcome": a.get("historical_outcome"),
                    }
                )
                evidence.append(
                    {
                        "kind": "historical_analogue",
                        "summary": f"Analogue {a.get('matched_period')}: {a.get('matched_label')}",
                        "refs": a.get("timeline_refs") or ["HMAI_KRIG"],
                    }
                )
            if bundle.historical_tip.get("available"):
                evidence.append(
                    {
                        "kind": "historical_macro",
                        "summary": "HMIP series / timeline coverage",
                        "refs": ["HMIP_KRIG"],
                    }
                )

            rel_sample = [
                {
                    "source": r.get("source"),
                    "target": r.get("target"),
                    "relationship": r.get("relationship"),
                    "confidence_pct": r.get("confidence_pct"),
                }
                for r in bundle.relationships[:8]
            ]

            sspan = traces.begin("macro_sector_impact", meta={"scenario": stype})
            sectors = sector_impacts_for(scenario_type, relationships=bundle.relationships)
            traces.end(sspan, output={"n": len(sectors)})

            cspan = traces.begin("macro_company_impact", meta={"scenario": stype})
            companies = company_impacts_for(
                scenario_type, sectors, relationships=bundle.relationships
            )
            traces.end(cspan, output={"n": len(companies)})

            catalysts = [
                {
                    "catalyst": "Confirmed RBI rate cut",
                    "polarity": "positive" if stype == "Bull" else "mixed",
                },
                {
                    "catalyst": "CPI print vs target",
                    "polarity": "positive" if stype != "Bear" else "negative",
                },
                {
                    "catalyst": "Oil / commodity shock",
                    "polarity": "negative" if stype == "Bear" else "watch",
                },
            ]

            scenarios.append(
                MacroScenario(
                    scenario=scenario_type,
                    country=bundle.country,
                    forecast_horizon=bundle.horizon,
                    indicators=indicators,
                    narrative=narratives_for(scenario_type),
                    drivers=drivers_for(scenario_type),
                    catalysts=catalysts,
                    risks=risks_for(scenario_type),
                    supporting_evidence=evidence,
                    historical_analogues=analogues,
                    relationships=rel_sample,
                    sector_impacts=sectors,
                    company_impacts=companies,
                    provenance={"base_levels_source": "CMKP" if tips else "catalog_defaults"},
                )
            )

        traces.end(
            span,
            output={
                "scenarios": [s.scenario for s in scenarios],
                "indicators_per": len(scenarios[0].indicators) if scenarios else 0,
            },
        )
        return scenarios

    def _assign_probability(self, scenarios, bundle) -> dict[str, int]:
        span = traces.begin("macro_probability", meta={"n": len(scenarios)})
        dist = assign_probabilities(scenarios, bundle)
        traces.end(span, output={"distribution": dist, "sum": sum(dist.values())})
        return dist

    def _score_confidence(self, scenarios, bundle) -> dict[str, Any]:
        span = traces.begin("macro_confidence", meta={"completeness": bundle.completeness_pct})
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
        b_repo = bull.indicator_map().get("Repo Rate")
        r_repo = bear.indicator_map().get("Repo Rate")
        if b_repo is not None and r_repo is not None and b_repo < r_repo:
            out.append("Bull assumes lower repo than Bear — policy path is the key fork")
        b_cpi = bull.indicator_map().get("CPI")
        r_cpi = bear.indicator_map().get("CPI")
        if b_cpi is not None and r_cpi is not None and r_cpi > b_cpi + 1.0:
            out.append("Bear inflation path materially above Bull — commodity/FX shock risk")
        if bundle.analogues:
            top = bundle.analogues[0]
            if float(top.get("similarity_score") or 0) < 70:
                out.append("Top historical analogue similarity below 70 — regime match is imperfect")
        if bundle.completeness_pct < 70:
            out.append("Macro knowledge completeness below 70% — widen confidence bands")
        return out

    # --- Retrieval surfaces ---

    def forecast(self, *, country: str = "India", region: str | None = None) -> dict[str, Any]:
        region = region or ("Global" if country.lower() == "global" else "India")
        ctry = "India" if region == "India" else country
        latest = STORE.latest(country=ctry if region == "India" else "India")
        if latest and latest.region == region:
            return {
                **latest.to_public_dict(),
                "mode": "published",
                "gateway": "MFI_KRIG",
            }
        report = self.generate_report(country=ctry, region=region, persist=False)
        return {**report.to_public_dict(), "mode": "computed", "gateway": "MFI_KRIG"}

    def india(self) -> dict[str, Any]:
        return self.forecast(country="India", region="India")

    def global_forecast(self) -> dict[str, Any]:
        # Soft global tip: still India-anchored scenarios with global growth overlays in research
        report = self.generate_report(country="India", region="Global", persist=False)
        data = report.to_public_dict()
        data["region"] = "Global"
        data["note"] = (
            "Global path overlays WEO / Fed tips from CMKP; India remains the primary scenario anchor."
        )
        data["gateway"] = "MFI_KRIG"
        return data

    def scenarios(self, *, country: str = "India") -> dict[str, Any]:
        pack = self.forecast(country=country)
        return {
            "country": country,
            "n": len(pack.get("scenarios") or []),
            "scenarios": pack.get("scenarios") or [],
            "probability_distribution": pack.get("probability_distribution"),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "MFI_KRIG",
        }

    def probability(self, *, country: str = "India") -> dict[str, Any]:
        pack = self.forecast(country=country)
        return {
            "country": country,
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
            "gateway": "MFI_KRIG",
            "note": "Probability quantifies scenario likelihood; confidence quantifies assessment certainty.",
        }

    def report(self, *, country: str = "India", persist: bool = False) -> dict[str, Any]:
        if persist:
            r = self.generate_report(country=country, persist=True)
            return {**r.to_public_dict(), "mode": "published", "gateway": "MFI_KRIG"}
        return self.forecast(country=country)

    def history(self, *, country: str = "India", limit: int = 20) -> dict[str, Any]:
        rows = STORE.history(limit=limit, country=country)
        return {
            "country": country,
            "n": len(rows),
            "reports": [
                {
                    "report_id": r.report_id,
                    "version": r.version,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "probability_distribution": r.probability_distribution,
                    "confidence_pct": (r.confidence or {}).get("overall_pct"),
                }
                for r in rows
            ],
            "providers_queried": [],
            "gateway": "MFI_KRIG",
        }

    def dashboard(self) -> dict[str, Any]:
        latest = STORE.latest()
        if not latest:
            latest = self.generate_report(persist=False)
            published = False
        else:
            published = True
        pub = latest.to_public_dict()
        return {
            "board": "Macro Forecast Intelligence",
            "programme": PROGRAMME,
            "version": MFI_VERSION,
            "principles": {
                "agi_owned_knowledge_only": True,
                "no_external_providers": True,
                "no_single_path_prediction": True,
                "ask_never_fetches": True,
                "versioned_reports": True,
                "evidence_linked_scenarios": True,
            },
            "does_not": list(NO_MFI_ACTIONS),
            "current_macro_regime": pub.get("current_regime"),
            "bull_base_bear_scenarios": pub.get("scenarios"),
            "probability_distribution": pub.get("probability_distribution"),
            "confidence": pub.get("confidence"),
            "confidence_trend": [
                {
                    "version": r.version,
                    "overall_pct": (r.confidence or {}).get("overall_pct"),
                }
                for r in STORE.history(limit=10)
            ],
            "key_macro_catalysts": pub.get("key_catalysts"),
            "upcoming_macro_events": pub.get("upcoming_events"),
            "sector_impact_matrix": pub.get("sector_impact_matrix"),
            "company_impact_matrix": pub.get("company_impact_matrix"),
            "forecast_history": self.history(limit=10),
            "coverage": STORE.coverage(),
            "retrieval_performance": {"traces": traces.recent(40)},
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": not published and STORE.coverage()["total_reports"] == 0,
            "providers_queried": [],
            "published": published,
        }
