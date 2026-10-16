"""IIE store — versioned analytical objects; never overwrite history."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.iie.models import (
    Catalyst,
    CompanyDna,
    CompanyIntelligenceProfile,
    ComparisonResult,
    InvestmentThesis,
    MacroImpact,
    MonitoringChecklist,
    OpportunityItem,
    RelationshipEdge,
    RiskItem,
    ScenarioSet,
    SectorIntelligence,
    ThemeIntelligence,
    VersionedAnalysis,
    now_iso,
)


@dataclass
class IieMetrics:
    companies_analysed: int = 0
    analytical_updates: int = 0
    scenario_updates: int = 0
    risk_changes: int = 0
    catalyst_detections: int = 0
    theme_memberships: int = 0
    comparisons_generated: int = 0
    failures: int = 0
    last_latency_ms: float = 0.0

    def model_dump(self, mode: str = "json") -> dict[str, Any]:
        return {
            "companies_analysed": self.companies_analysed,
            "analytical_updates": self.analytical_updates,
            "scenario_updates": self.scenario_updates,
            "risk_changes": self.risk_changes,
            "catalyst_detections": self.catalyst_detections,
            "theme_memberships": self.theme_memberships,
            "comparisons_generated": self.comparisons_generated,
            "failures": self.failures,
            "last_latency_ms": self.last_latency_ms,
        }


@dataclass
class AuditEntry:
    action: str
    object_kind: str = ""
    object_id: str = ""
    detail: str = ""
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "object_kind": self.object_kind,
            "object_id": self.object_id,
            "detail": self.detail,
            "created_at": self.created_at,
        }


class IieStore:
    def __init__(self) -> None:
        self.profiles: dict[str, CompanyIntelligenceProfile] = {}
        self.dna: dict[str, CompanyDna] = {}
        self.sectors: dict[str, SectorIntelligence] = {}
        self.themes: dict[str, ThemeIntelligence] = {}
        self.macro_impacts: dict[str, MacroImpact] = {}
        self.catalysts: dict[str, Catalyst] = {}
        self.risks: dict[str, RiskItem] = {}
        self.opportunities: dict[str, OpportunityItem] = {}
        self.scenarios: dict[str, ScenarioSet] = {}  # by company_id
        self.theses: dict[str, InvestmentThesis] = {}  # by company_id (latest)
        self.monitors: dict[str, MonitoringChecklist] = {}
        self.relationships: dict[str, RelationshipEdge] = {}
        self.comparisons: dict[str, ComparisonResult] = {}
        self.history: list[VersionedAnalysis] = []  # append-only evolution
        self.audit: list[AuditEntry] = []
        self.metrics = IieMetrics()

    def put_profile(self, profile: CompanyIntelligenceProfile) -> CompanyIntelligenceProfile:
        existing = self.profiles.get(profile.company_id)
        if existing:
            self._archive(
                object_type="company_profile",
                entity_id=profile.company_id,
                version=existing.version,
                assessment="prior_profile",
                confidence=existing.confidence,
                reasoning_summary=existing.explainability.reasoning_summary,
                supporting_evidence=existing.explainability.supporting_evidence,
                payload=existing.to_dict(),
            )
            profile.version = existing.version + 1
            profile.created_at = existing.created_at
        profile.updated_at = now_iso()
        self.profiles[profile.company_id] = profile
        self.metrics.companies_analysed = len(self.profiles)
        self.metrics.analytical_updates += 1
        self.audit_event("put_profile", object_kind="company_profile", object_id=profile.company_id)
        return profile

    def put_dna(self, dna: CompanyDna) -> CompanyDna:
        existing = self.dna.get(dna.company_id)
        if existing:
            dna.version = existing.version + 1
        dna.updated_at = now_iso()
        self.dna[dna.company_id] = dna
        self.metrics.analytical_updates += 1
        return dna

    def put_sector(self, sector: SectorIntelligence) -> SectorIntelligence:
        existing = self.sectors.get(sector.sector_id)
        if existing:
            self._archive(
                object_type="sector",
                entity_id=sector.sector_id,
                version=existing.version,
                assessment=existing.demand_outlook or existing.name,
                confidence=existing.confidence,
                reasoning_summary=existing.explainability.reasoning_summary,
                supporting_evidence=existing.explainability.supporting_evidence,
                payload=existing.to_dict(),
            )
            sector.version = existing.version + 1
        sector.updated_at = now_iso()
        self.sectors[sector.sector_id] = sector
        self.metrics.analytical_updates += 1
        return sector

    def put_theme(self, theme: ThemeIntelligence) -> ThemeIntelligence:
        existing = self.themes.get(theme.theme_id)
        if existing:
            theme.version = existing.version + 1
            # merge memberships
            theme.company_ids = sorted(set(existing.company_ids) | set(theme.company_ids))
            theme.sector_ids = sorted(set(existing.sector_ids) | set(theme.sector_ids))
        theme.updated_at = now_iso()
        self.themes[theme.theme_id] = theme
        self.metrics.theme_memberships = sum(len(t.company_ids) for t in self.themes.values())
        return theme

    def put_macro(self, impact: MacroImpact) -> MacroImpact:
        self.macro_impacts[impact.impact_id] = impact
        return impact

    def put_catalyst(self, cat: Catalyst) -> Catalyst:
        existing = self.catalysts.get(cat.catalyst_id)
        if existing:
            cat.version = existing.version + 1
        cat.updated_at = now_iso()
        self.catalysts[cat.catalyst_id] = cat
        self.metrics.catalyst_detections = len(self.catalysts)
        return cat

    def put_risk(self, risk: RiskItem) -> RiskItem:
        existing = self.risks.get(risk.risk_id)
        if existing:
            self._archive(
                object_type="risk",
                entity_id=risk.company_id,
                version=existing.version,
                assessment=existing.title,
                confidence=existing.confidence,
                reasoning_summary=existing.explainability.reasoning_summary,
                supporting_evidence=existing.explainability.supporting_evidence,
                payload=existing.to_dict(),
            )
            risk.version = existing.version + 1
        risk.updated_at = now_iso()
        self.risks[risk.risk_id] = risk
        self.metrics.risk_changes += 1
        return risk

    def put_opportunity(self, opp: OpportunityItem) -> OpportunityItem:
        existing = self.opportunities.get(opp.opportunity_id)
        if existing:
            opp.version = existing.version + 1
        opp.updated_at = now_iso()
        self.opportunities[opp.opportunity_id] = opp
        return opp

    def put_scenario(self, scenario: ScenarioSet) -> ScenarioSet:
        existing = self.scenarios.get(scenario.company_id)
        if existing:
            self._archive(
                object_type="scenario",
                entity_id=scenario.company_id,
                version=existing.version,
                assessment="prior_scenarios",
                confidence=existing.explainability.confidence,
                reasoning_summary=existing.explainability.reasoning_summary,
                supporting_evidence=existing.explainability.supporting_evidence,
                payload=existing.to_dict(),
            )
            scenario.version = existing.version + 1
            scenario.scenario_id = existing.scenario_id
        scenario.updated_at = now_iso()
        self.scenarios[scenario.company_id] = scenario
        self.metrics.scenario_updates += 1
        return scenario

    def put_thesis(self, thesis: InvestmentThesis) -> InvestmentThesis:
        existing = self.theses.get(thesis.company_id)
        if existing:
            self._archive(
                object_type="thesis",
                entity_id=thesis.company_id,
                version=existing.version,
                assessment=existing.investment_thesis[:120],
                confidence=existing.confidence,
                reasoning_summary=existing.explainability.reasoning_summary,
                supporting_evidence=existing.evidence_references,
                payload=existing.to_dict(),
            )
            thesis.version = existing.version + 1
            thesis.thesis_id = existing.thesis_id
            thesis.created_at = existing.created_at
        thesis.updated_at = now_iso()
        self.theses[thesis.company_id] = thesis
        self.metrics.analytical_updates += 1
        return thesis

    def put_monitor(self, checklist: MonitoringChecklist) -> MonitoringChecklist:
        existing = self.monitors.get(checklist.company_id)
        if existing:
            checklist.version = existing.version + 1
        checklist.updated_at = now_iso()
        self.monitors[checklist.company_id] = checklist
        return checklist

    def put_relationship(self, edge: RelationshipEdge) -> RelationshipEdge:
        key = f"{edge.from_id}|{edge.relation_type}|{edge.to_id}"
        self.relationships[key] = edge
        return edge

    def put_comparison(self, comp: ComparisonResult) -> ComparisonResult:
        self.comparisons[comp.comparison_id] = comp
        self.metrics.comparisons_generated = len(self.comparisons)
        return comp

    def _archive(
        self,
        *,
        object_type: str,
        entity_id: str,
        version: int,
        assessment: str,
        confidence: float,
        reasoning_summary: str,
        supporting_evidence: list[dict[str, Any]],
        payload: dict[str, Any],
        conflicting_evidence: list[dict[str, Any]] | None = None,
    ) -> None:
        from app.iie.models import new_id

        self.history.append(
            VersionedAnalysis(
                object_id=new_id("hist"),
                object_type=object_type,
                entity_id=entity_id,
                version=version,
                assessment=assessment,
                confidence=confidence,
                reasoning_summary=reasoning_summary,
                supporting_evidence=list(supporting_evidence or []),
                conflicting_evidence=list(conflicting_evidence or []),
                payload=payload,
                superseded=True,
            )
        )

    def evolution(
        self,
        *,
        entity_id: str | None = None,
        object_type: str | None = None,
        limit: int = 50,
    ) -> list[VersionedAnalysis]:
        rows = self.history
        if entity_id:
            rows = [h for h in rows if h.entity_id == entity_id]
        if object_type:
            rows = [h for h in rows if h.object_type == object_type]
        return list(reversed(rows[-limit:]))

    def audit_event(self, action: str, *, object_kind: str = "", object_id: str = "", detail: str = "") -> None:
        self.audit.append(
            AuditEntry(action=action, object_kind=object_kind, object_id=object_id, detail=detail)
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "profiles": len(self.profiles),
            "dna": len(self.dna),
            "sectors": len(self.sectors),
            "themes": len(self.themes),
            "macro_impacts": len(self.macro_impacts),
            "catalysts": len(self.catalysts),
            "risks": len(self.risks),
            "opportunities": len(self.opportunities),
            "scenarios": len(self.scenarios),
            "theses": len(self.theses),
            "monitors": len(self.monitors),
            "relationships": len(self.relationships),
            "comparisons": len(self.comparisons),
            "history": len(self.history),
            "audit": len(self.audit),
        }

    def confidence_distribution(self) -> dict[str, int]:
        buckets = {"low": 0, "medium": 0, "high": 0}
        for p in self.profiles.values():
            c = float(p.confidence or 0)
            if c < 0.45:
                buckets["low"] += 1
            elif c < 0.7:
                buckets["medium"] += 1
            else:
                buckets["high"] += 1
        return buckets
