"""Institutional Scenario Intelligence engine — Bull / Base / Bear from Forecast Bundles."""

from __future__ import annotations

import time
from typing import Any

from institutional_forecast_intelligence.production import bundle as ifi_bundle
from institutional_scenario_intelligence import traces
from institutional_scenario_intelligence.schema import (
    ISI_VERSION,
    PROGRAMME,
    InstitutionalScenario,
    ScenarioComparison,
    ScenarioReport,
    ScenarioScope,
    ScenarioType,
)
from institutional_scenario_intelligence.store import METRICS
from institutional_scenario_intelligence.templates import (
    drivers_for,
    narratives_for,
    qualitative_confidence,
)
from institutional_scenario_intelligence.validation import assert_publishable


class InstitutionalScenarioEngine:
    """Consumes IFI Forecast Bundles only — never live Yahoo / NSE."""

    def company_report(self, ticker: str, *, question: str | None = None) -> dict[str, Any]:
        fb = ifi_bundle(scope="company", entity=ticker.upper(), question=question)
        return self.from_forecast_bundle(fb, scope=ScenarioScope.COMPANY)

    def sector_report(self, sector: str, *, question: str | None = None) -> dict[str, Any]:
        fb = ifi_bundle(scope="sector", entity=sector, question=question)
        return self.from_forecast_bundle(fb, scope=ScenarioScope.SECTOR)

    def market_report(self, *, question: str | None = None) -> dict[str, Any]:
        fb = ifi_bundle(scope="market", question=question)
        return self.from_forecast_bundle(fb, scope=ScenarioScope.MARKET)

    def macro_report(self, *, question: str | None = None) -> dict[str, Any]:
        fb = ifi_bundle(scope="macro", question=question)
        return self.from_forecast_bundle(fb, scope=ScenarioScope.MACRO)

    def report(
        self,
        *,
        scope: str,
        entity: str | None = None,
        question: str | None = None,
        forecast_bundle: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if forecast_bundle:
            scope_enum = ScenarioScope(scope.lower())
            return self.from_forecast_bundle(forecast_bundle, scope=scope_enum)
        scope_l = scope.lower()
        if scope_l == "company":
            return self.company_report(entity or "INFY", question=question)
        if scope_l == "sector":
            return self.sector_report(entity or "information_technology", question=question)
        if scope_l == "market":
            return self.market_report(question=question)
        if scope_l == "macro":
            return self.macro_report(question=question)
        return {"error": "unknown_scope", "providers_queried": [], "version": ISI_VERSION}

    def dashboard(self) -> dict[str, Any]:
        metrics = METRICS.dashboard()
        return {
            "board": "Institutional Scenario Intelligence",
            "programme": PROGRAMME,
            "version": ISI_VERSION,
            "principles": {
                "plausible_outcomes_not_single_forecast": True,
                "contradictions_preserved": True,
                "no_buy_sell_or_target_price": True,
                "no_probabilities_until_pci": True,
                "consumes_ifi_forecast_bundles_only": True,
                "no_live_providers": True,
            },
            **metrics,
            "retrieval_performance": {"traces": traces.recent(40)},
        }

    def from_forecast_bundle(
        self,
        forecast_bundle: dict[str, Any],
        *,
        scope: ScenarioScope,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        entity = str(forecast_bundle.get("entity") or "").upper() if scope == ScenarioScope.COMPANY else str(
            forecast_bundle.get("entity") or ""
        )
        span = traces.begin(
            "scenario_generation",
            meta={"scope": scope.value, "entity": entity, "bundle_id": forecast_bundle.get("bundle_id")},
        )
        scenarios = [
            self._build_scenario(ScenarioType.BULL, forecast_bundle, scope=scope, entity=entity),
            self._build_scenario(ScenarioType.BASE, forecast_bundle, scope=scope, entity=entity),
            self._build_scenario(ScenarioType.BEAR, forecast_bundle, scope=scope, entity=entity),
        ]
        traces.end(span, output={"count": len(scenarios), "types": [s.type.value for s in scenarios]})

        contradictions = self._collect_contradictions(scenarios, forecast_bundle)
        comparison = self._compare(scenarios, forecast_bundle, contradictions)

        cspan = traces.begin("scenario_comparison", meta={"entity": entity})
        traces.end(
            cspan,
            output={
                "conflicting_drivers": len(comparison.conflicting_drivers),
                "common_drivers": len(comparison.common_drivers),
            },
        )

        vspan = traces.begin("scenario_validation", meta={"entity": entity})
        thesis = None
        ck = forecast_bundle.get("current_knowledge") or {}
        thesis = ck.get("investment_thesis")
        report = ScenarioReport(
            scope=scope,
            entity=entity,
            entity_label=forecast_bundle.get("entity_label") or ck.get("name") or entity,
            forecast_bundle_id=forecast_bundle.get("bundle_id"),
            scenarios=scenarios,
            comparison=comparison,
            contradictions=contradictions,
            investment_thesis=thesis,
            monitoring_events=list(forecast_bundle.get("monitoring_events") or []),
            completeness={
                "bundle": forecast_bundle.get("completeness") or {},
                "missing_evidence": list(comparison.missing_evidence),
            },
            freshness=forecast_bundle.get("knowledge_freshness") or {},
            provenance={
                "gateway": "ISI",
                "version": ISI_VERSION,
                "forecast_bundle_id": forecast_bundle.get("bundle_id"),
                "ifi_sources": (forecast_bundle.get("provenance") or {}).get("sources") or [],
                "providers_hidden": True,
                "probabilities": False,
            },
            providers_queried=[],
        )
        assert_publishable(report)
        traces.end(vspan, output={"valid": True})

        pspan = traces.begin("scenario_publication", meta={"report_id": report.report_id})
        out = report.to_public_dict()
        out["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        out["forecast_bundle_tip"] = {
            "bundle_id": forecast_bundle.get("bundle_id"),
            "completeness": (forecast_bundle.get("completeness") or {}).get("overall"),
            "analogue_count": len(forecast_bundle.get("historical_analogues") or []),
            "relationship_count": len(forecast_bundle.get("relationship_intelligence") or []),
        }
        METRICS.record(
            scope=scope.value,
            entity=entity,
            scenario_types=[s.type.value for s in scenarios],
            contradictions=len(contradictions),
            ok=True,
        )
        traces.end(pspan, output={"report_id": report.report_id, "published": True})
        return out

    def _build_scenario(
        self,
        scenario_type: ScenarioType,
        bundle: dict[str, Any],
        *,
        scope: ScenarioScope,
        entity: str,
    ) -> InstitutionalScenario:
        narrative = narratives_for(scope.value, entity, scenario_type)
        drivers = drivers_for(scenario_type, scope=scope.value, entity=entity)
        catalysts = self._select_catalysts(bundle, scenario_type)
        risks = self._select_risks(bundle, scenario_type)
        evidence = self._supporting_evidence(bundle, scenario_type)
        analogues = list(bundle.get("historical_analogues") or [])[:5]
        # Per-scenario contradictions tip (full set attached at report level too)
        local_contra = [
            e
            for e in (bundle.get("contradictory_evidence") or [])
            if scenario_type != ScenarioType.BEAR or True
        ][:5]
        completeness = ((bundle.get("completeness") or {}).get("overall")) or "Partial"
        return InstitutionalScenario(
            type=scenario_type,
            narrative=narrative,
            drivers=drivers,
            catalysts=catalysts,
            risks=risks,
            supporting_evidence=evidence,
            historical_analogues=analogues,
            contradictions=local_contra if scenario_type != ScenarioType.BASE else list(
                bundle.get("contradictory_evidence") or []
            )[:3],
            confidence=qualitative_confidence(bundle, scenario_type),
            completeness=str(completeness),
            probability=None,
        )

    def _select_catalysts(self, bundle: dict[str, Any], scenario_type: ScenarioType) -> list[dict[str, Any]]:
        items = list(bundle.get("catalysts") or [])
        if scenario_type == ScenarioType.BULL:
            picked = [c for c in items if c.get("polarity") == "positive"] or items[:2]
        elif scenario_type == ScenarioType.BEAR:
            picked = [c for c in items if c.get("polarity") == "negative"] or items[-2:]
        else:
            picked = items[:3] or [{"catalyst": "Guidance delivery", "polarity": "neutral", "evidence": "Base path"}]
        # Enrich from relationships for bull rate-cut / AI themes
        for rel in bundle.get("relationship_intelligence") or []:
            rtype = str(rel.get("type") or rel.get("relationship_type") or "")
            if scenario_type == ScenarioType.BULL and "Positive" in rtype:
                picked.append(
                    {
                        "catalyst": f"{rel.get('source')} → {rel.get('target')}",
                        "polarity": "positive",
                        "evidence": "Historical relationship",
                    }
                )
            if scenario_type == ScenarioType.BEAR and ("Negative" in rtype or "Pressure" in rtype):
                picked.append(
                    {
                        "catalyst": f"{rel.get('source')} → {rel.get('target')}",
                        "polarity": "negative",
                        "evidence": "Historical relationship",
                    }
                )
        # Dedup by catalyst text
        seen: set[str] = set()
        out = []
        for c in picked:
            key = str(c.get("catalyst"))
            if key in seen:
                continue
            seen.add(key)
            out.append(c)
        return out[:6]

    def _select_risks(self, bundle: dict[str, Any], scenario_type: ScenarioType) -> list[dict[str, Any]]:
        risks = list(bundle.get("risks") or [])
        if scenario_type == ScenarioType.BULL:
            # Bull still carries residual risks (institutional honesty)
            return risks[:2] or [{"risk": "Execution lag on optimistic path", "severity": "Medium"}]
        if scenario_type == ScenarioType.BEAR:
            return risks or [{"risk": "Demand / margin downside", "severity": "High"}]
        return risks[:3] or [{"risk": "Guidance miss vs base path", "severity": "Medium"}]

    def _supporting_evidence(self, bundle: dict[str, Any], scenario_type: ScenarioType) -> list[dict[str, Any]]:
        evidence = []
        # Current
        ck = bundle.get("current_knowledge") or {}
        if ck:
            evidence.append(
                {
                    "kind": "current_evidence",
                    "summary": ck.get("investment_thesis") or ck.get("business_profile") or str(ck.get("ticker") or ck),
                    "source": "current_knowledge",
                }
            )
        # Historical
        hi = bundle.get("historical_intelligence") or {}
        if hi:
            evidence.append(
                {
                    "kind": "historical_evidence",
                    "summary": str(hi.get("cycles") or hi.get("timelines") or hi.get("coverage") or "historical intelligence present"),
                    "source": "historical_intelligence",
                }
            )
        # Research
        ri = bundle.get("research_intelligence") or {}
        if ri:
            tip = ri.get("company_research_office") or ri.get("sector_research_office") or ri.get("macro_research_office")
            evidence.append({"kind": "research_evidence", "summary": str(tip or ri), "source": "research_intelligence"})
        # Analogues — more weight on bull/bear extremes
        for a in (bundle.get("historical_analogues") or [])[:2]:
            evidence.append(
                {
                    "kind": "historical_analogue",
                    "summary": f"{a.get('matched_period')}: {a.get('label') or a.get('matched_label')}",
                    "score": a.get("similarity_score"),
                    "source": "historical_analogues",
                }
            )
        # Bundle supporting list
        for e in (bundle.get("supporting_evidence") or [])[:3]:
            evidence.append({**e, "kind": e.get("kind") or "bundle_evidence"})
        # Scenario-type tag for traceability
        for e in evidence:
            e.setdefault("scenario_type", scenario_type.value)
        return evidence

    def _collect_contradictions(
        self,
        scenarios: list[InstitutionalScenario],
        bundle: dict[str, Any],
    ) -> list[dict[str, Any]]:
        bull = next(s for s in scenarios if s.type == ScenarioType.BULL)
        bear = next(s for s in scenarios if s.type == ScenarioType.BEAR)
        contradictions = [
            {
                "dimension": "Margins",
                "bull": bull.drivers.margins,
                "bear": bear.drivers.margins,
                "why_both_plausible": (
                    "Margin recovery requires utilisation / pricing improvement; "
                    "compression remains plausible if demand stays weak — neither path is invalidated by current evidence."
                ),
            },
            {
                "dimension": "Revenue / Growth",
                "bull": bull.drivers.revenue or bull.drivers.growth,
                "bear": bear.drivers.revenue or bear.drivers.growth,
                "why_both_plausible": (
                    "AI / policy catalysts support upside while analogue slowdown periods keep downside live."
                ),
            },
        ]
        for e in bundle.get("contradictory_evidence") or []:
            contradictions.append(
                {
                    "dimension": "Bundle contradiction",
                    "detail": e,
                    "why_both_plausible": "Contradictory catalysts are preserved for Investment Office review.",
                }
            )
        return contradictions

    def _compare(
        self,
        scenarios: list[InstitutionalScenario],
        bundle: dict[str, Any],
        contradictions: list[dict[str, Any]],
    ) -> ScenarioComparison:
        bull = next(s for s in scenarios if s.type == ScenarioType.BULL)
        base = next(s for s in scenarios if s.type == ScenarioType.BASE)
        bear = next(s for s in scenarios if s.type == ScenarioType.BEAR)

        strongest = []
        for s in scenarios:
            if s.supporting_evidence:
                strongest.append(
                    {
                        "scenario": s.type.value,
                        "evidence": s.supporting_evidence[0],
                        "confidence": s.confidence,
                    }
                )

        weakest = [
            {
                "scenario": "Bull",
                "assumption": bull.narrative[0] if bull.narrative else "Upside conversion",
                "note": "Depends on catalyst conversion that is not yet confirmed",
            },
            {
                "scenario": "Bear",
                "assumption": bear.narrative[0] if bear.narrative else "Downside demand",
                "note": "Depends on sustained demand weakness; may be invalidated by deal/AI evidence",
            },
        ]

        missing = list(((bundle.get("completeness") or {}).get("missing_evidence")) or [])
        if (bundle.get("pattern_intelligence") or {}).get("deferred"):
            if "pattern_intelligence" not in missing:
                missing.append("pattern_intelligence")

        common = [
            d
            for d in ("sector", "macro", "competition", "valuation")
            if getattr(bull.drivers, d) and getattr(base.drivers, d) and getattr(bear.drivers, d)
        ]

        conflicting = [
            {
                "driver": c.get("dimension"),
                "bull": c.get("bull"),
                "bear": c.get("bear"),
            }
            for c in contradictions
            if c.get("bull") or c.get("bear")
        ]

        why = [
            "Current evidence supports multiple transmission paths (relationships + analogues).",
            "No single catalyst has confirmed or invalidated Bull or Bear.",
            "Institutional practice keeps contradictory paths open until evidence resolves them.",
        ]
        for c in contradictions[:3]:
            if c.get("why_both_plausible"):
                why.append(str(c["why_both_plausible"]))

        return ScenarioComparison(
            strongest_evidence=strongest,
            weakest_assumptions=weakest,
            missing_evidence=missing,
            common_drivers=common,
            conflicting_drivers=conflicting,
            why_all_remain_plausible=why,
        )
