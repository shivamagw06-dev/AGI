"""IPCI engine — Forecast Assessments from ISI Scenario Reports."""

from __future__ import annotations

import time
from typing import Any

from institutional_probability_confidence import traces
from institutional_probability_confidence.confidence import (
    calculate_confidence,
    per_scenario_confidence,
)
from institutional_probability_confidence.evidence_scoring import (
    extract_missing_evidence,
    score_analogue_strength,
    score_evidence_quality,
    soft_triggers_from_report,
)
from institutional_probability_confidence.probability import calculate_probabilities
from institutional_probability_confidence.schema import (
    IPCI_VERSION,
    PROGRAMME,
    ForecastAssessment,
    ScenarioAssessment,
)
from institutional_probability_confidence.store import METRICS
from institutional_scenario_intelligence.production import (
    company as isi_company,
    macro as isi_macro,
    market as isi_market,
    report as isi_report,
    sector as isi_sector,
)


class InstitutionalProbabilityConfidenceEngine:
    def company_assessment(self, ticker: str, *, question: str | None = None) -> dict[str, Any]:
        report = isi_company(ticker, question=question)
        return self.from_scenario_report(report)

    def sector_assessment(self, sector: str, *, question: str | None = None) -> dict[str, Any]:
        return self.from_scenario_report(isi_sector(sector, question=question))

    def probability_company(self, ticker: str, *, question: str | None = None) -> dict[str, Any]:
        full = self.company_assessment(ticker, question=question)
        return {
            "entity": full["entity"],
            "providers_queried": [],
            "probabilities": full["probabilities"],
            "probability_sum_pct": full["probability_sum_pct"],
            "distribution": {p["scenario"]: p["probability_pct"] for p in full["probabilities"]},
            "version": IPCI_VERSION,
            "note": "Probability only — see /v1/confidence or /v1/forecast/assessment for confidence",
        }

    def probability_sector(self, sector: str, *, question: str | None = None) -> dict[str, Any]:
        full = self.sector_assessment(sector, question=question)
        return {
            "entity": full["entity"],
            "providers_queried": [],
            "probabilities": full["probabilities"],
            "probability_sum_pct": full["probability_sum_pct"],
            "distribution": {p["scenario"]: p["probability_pct"] for p in full["probabilities"]},
            "version": IPCI_VERSION,
        }

    def confidence_company(self, ticker: str, *, question: str | None = None) -> dict[str, Any]:
        full = self.company_assessment(ticker, question=question)
        return {
            "entity": full["entity"],
            "providers_queried": [],
            "confidence": full["confidence"],
            "overall_forecast_quality_pct": full["overall_forecast_quality_pct"],
            "missing_evidence": full["missing_evidence"],
            "per_scenario_confidence": {
                a["scenario"]: a["confidence_pct"] for a in full["assessments"]
            },
            "version": IPCI_VERSION,
            "note": "Confidence is independent of probability mass",
        }

    def assessment(
        self,
        *,
        scope: str = "company",
        entity: str | None = None,
        question: str | None = None,
        scenario_report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if scenario_report:
            return self.from_scenario_report(scenario_report)
        scope_l = scope.lower()
        if scope_l == "company":
            return self.company_assessment(entity or "INFY", question=question)
        if scope_l == "sector":
            return self.sector_assessment(entity or "information_technology", question=question)
        if scope_l == "market":
            return self.from_scenario_report(isi_market(question=question))
        if scope_l == "macro":
            return self.from_scenario_report(isi_macro(question=question))
        return self.from_scenario_report(
            isi_report(scope=scope, entity=entity, question=question)
        )

    def dashboard(self) -> dict[str, Any]:
        metrics = METRICS.dashboard()
        return {
            "board": "Institutional Probability & Confidence Intelligence",
            "programme": PROGRAMME,
            "version": IPCI_VERSION,
            "principles": {
                "probability_ne_confidence": True,
                "probabilities_sum_to_100": True,
                "no_guessing": True,
                "no_trading_recommendations": True,
                "no_live_providers": True,
                "missing_evidence_explicit": True,
            },
            **metrics,
            "retrieval_performance": {"traces": traces.recent(40)},
        }

    def from_scenario_report(self, scenario_report: dict[str, Any]) -> dict[str, Any]:
        t0 = time.perf_counter()
        entity = str(scenario_report.get("entity") or "")
        span = traces.begin("forecast_assessment", meta={"entity": entity})

        espan = traces.begin("evidence_scoring", meta={"entity": entity})
        evidence_quality = score_evidence_quality(scenario_report)
        ana_pct, ana_count = score_analogue_strength(scenario_report)
        missing = extract_missing_evidence(scenario_report)
        triggers = soft_triggers_from_report(scenario_report)
        traces.end(
            espan,
            output={
                "evidence_quality": evidence_quality.get("score_pct"),
                "analogues": ana_count,
                "missing": len(missing),
            },
        )

        probabilities = calculate_probabilities(
            scenario_report,
            evidence_quality=evidence_quality,
            analogue_count=ana_count,
            triggers=triggers,
        )
        confidence = calculate_confidence(
            scenario_report,
            evidence_quality=evidence_quality,
            missing_evidence=missing,
            triggers=triggers,
        )

        scenarios = {s.get("type"): s for s in (scenario_report.get("scenarios") or [])}
        assessments: list[ScenarioAssessment] = []
        for p in probabilities:
            s = scenarios.get(p.scenario) or {}
            conf_pct = per_scenario_confidence(s, overall=confidence, scenario_name=p.scenario)
            assessments.append(
                ScenarioAssessment(
                    scenario=p.scenario,
                    probability_pct=p.probability_pct,
                    confidence_pct=conf_pct,
                    supporting_evidence=list(s.get("supporting_evidence") or []),
                    contradictions=[
                        c
                        for c in (scenario_report.get("contradictions") or [])
                        if p.scenario in {"Bull", "Bear"} or c.get("dimension") == "Bundle contradiction"
                    ][:5],
                    missing_evidence=missing,
                    catalysts=list(s.get("catalysts") or []),
                    triggers=[t for t in triggers if t.get("scenario") in {None, p.scenario}][:5]
                    or triggers[:3],
                    narrative=list(s.get("narrative") or []),
                )
            )

        # Overall forecast quality blends confidence with completeness / evidence
        quality = int(
            round(
                0.55 * confidence.overall_pct
                + 0.25 * float(evidence_quality.get("score_pct") or 70)
                + 0.20 * confidence.knowledge_freshness_pct
            )
        )
        quality = max(40, min(99, quality))

        assessment = ForecastAssessment(
            entity=entity,
            entity_label=scenario_report.get("entity_label"),
            scope=str(scenario_report.get("scope") or "company"),
            scenario_report_id=scenario_report.get("report_id"),
            forecast_bundle_id=scenario_report.get("forecast_bundle_id"),
            assessments=assessments,
            probabilities=probabilities,
            probability_sum_pct=sum(p.probability_pct for p in probabilities),
            confidence=confidence,
            overall_forecast_quality_pct=quality,
            missing_evidence=missing,
            contradictions_summary=list(scenario_report.get("contradictions") or [])[:8],
            provenance={
                "gateway": "IPCI",
                "version": IPCI_VERSION,
                "scenario_report_id": scenario_report.get("report_id"),
                "forecast_bundle_id": scenario_report.get("forecast_bundle_id"),
                "analogue_strength_pct": ana_pct,
                "providers_hidden": True,
            },
            providers_queried=[],
        )
        assert assessment.probability_sum_pct == 100

        out = assessment.to_public_dict()
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        METRICS.record(
            {
                "entity": entity,
                "scope": assessment.scope,
                "overall_confidence": confidence.overall_pct,
                "forecast_quality": quality,
                "distribution": {p.scenario: p.probability_pct for p in probabilities},
                "evidence_quality": evidence_quality.get("score_pct"),
                "missing_evidence_count": len(missing),
            }
        )
        traces.end(
            span,
            output={
                "sum": assessment.probability_sum_pct,
                "quality": quality,
                "confidence": confidence.overall_pct,
            },
        )
        return out
