"""IIE analytical engines — transform verified evidence into investment intelligence."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.iie.config import (
    DNA_DIMENSIONS,
    FACT_TO_INTEL,
    MACRO_IMPACT_MAP,
    MONITOR_METRICS,
    SECTOR_CATALOG,
    THEME_CATALOG,
)
from app.iie.evidence import VerifiedEvidenceReader, evidence_ref
from app.iie.models import (
    Catalyst,
    CompanyDna,
    CompanyIntelligenceProfile,
    ComparisonResult,
    DnaDimension,
    Explainability,
    InvestmentThesis,
    MacroImpact,
    MonitorItem,
    MonitoringChecklist,
    OpportunityItem,
    RelationshipEdge,
    RiskItem,
    ScenarioCase,
    ScenarioSet,
    SectorIntelligence,
    ThemeIntelligence,
    new_id,
    now_iso,
)
from app.iie.store import IieStore

_RISK_KEYS = {"risks", "debt", "litigation", "governance", "fx", "commodity", "interest"}
_OPP_KEYS = {"opportunities", "guidance", "capex", "products", "revenue", "margins"}
_CATALYST_KEYS = {"guidance", "dividend", "buyback", "capex", "board", "products"}
_RELATION_PATTERNS = [
    (r"\bcustomer\b", "customer"),
    (r"\bsupplier\b", "supplier"),
    (r"\bcompetitor\b", "competitor"),
    (r"\bsubsidiary\b", "subsidiary"),
    (r"\bparent\b", "parent"),
    (r"\bjv\b|\bjoint venture\b", "jv"),
]


def _avg(vals: list[float]) -> float:
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _assessment_from_confidence(conf: float) -> str:
    if conf >= 0.75:
        return "strong"
    if conf >= 0.55:
        return "moderate"
    if conf >= 0.35:
        return "developing"
    return "uncertain"


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _facts_by_key(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for ev in evidence:
        key = (ev.get("fact_key") or "unknown").lower()
        out.setdefault(key, []).append(ev)
    return out


def _text_blob(evidence: list[dict[str, Any]]) -> str:
    return " ".join((ev.get("value_text") or "") for ev in evidence).lower()


def _sector_for_text(blob: str, symbol: str = "") -> str:
    for row in SECTOR_CATALOG:
        sid = row["sector_id"]
        label = row["label"].lower()
        if sid.replace("_", " ") in blob or label in blob:
            return sid
    # light heuristics
    if any(x in blob for x in ("bank", "nbfc", "credit")):
        return "banking"
    if any(x in blob for x in ("software", "it services", "digital")):
        return "it_services"
    if "defence" in blob or "defense" in blob:
        return "defence"
    if "renewable" in blob or "solar" in blob:
        return "renewables"
    return "capital_goods" if symbol else "infrastructure"


class IieAnalyser:
    def __init__(self, store: IieStore, reader: VerifiedEvidenceReader) -> None:
        self.store = store
        self.reader = reader

    def analyse_company(self, key: str) -> dict[str, Any]:
        company_id, symbol, name = self.reader.resolve_company(key)
        pack = self.reader.company_pack(company_id if company_id else key)
        evidence = pack.get("evidence") if isinstance(pack, dict) else None
        if not evidence:
            evidence = self.reader.list_for_company(company_id)
        else:
            evidence = self.reader._filter(evidence)
        conflicts = self.reader.conflicts_for_company(company_id)
        conflict_refs = [
            {
                "conflict_id": c.get("conflict_id"),
                "fact_key": c.get("fact_key"),
                "left": (c.get("left_value") or "")[:120],
                "right": (c.get("right_value") or "")[:120],
            }
            for c in conflicts
        ]

        profile = self._build_profile(company_id, name or symbol or company_id, evidence, conflict_refs)
        dna = self._build_dna(company_id, evidence, conflict_refs)
        sector_id = _sector_for_text(_text_blob(evidence), symbol)
        sector = self._touch_sector(sector_id, company_id, evidence)
        themes = self._classify_themes(company_id, sector_id, evidence)
        catalysts = self._build_catalysts(company_id, sector_id, evidence)
        risks = self._build_risks(company_id, evidence, conflict_refs)
        opps = self._build_opportunities(company_id, evidence)
        scenarios = self._build_scenarios(company_id, evidence, risks, opps, conflict_refs)
        thesis = self._build_thesis(company_id, profile, catalysts, risks, opps, evidence, conflict_refs)
        monitor = self._build_monitor(company_id, evidence)
        rels = self._infer_relationships(company_id, evidence)

        self.store.put_profile(profile)
        self.store.put_dna(dna)
        self.store.put_sector(sector)
        for t in themes:
            self.store.put_theme(t)
        for c in catalysts:
            self.store.put_catalyst(c)
        for r in risks:
            self.store.put_risk(r)
        for o in opps:
            self.store.put_opportunity(o)
        self.store.put_scenario(scenarios)
        self.store.put_thesis(thesis)
        self.store.put_monitor(monitor)
        for e in rels:
            self.store.put_relationship(e)

        return {
            "company_id": company_id,
            "symbol": symbol,
            "profile": profile.to_dict(),
            "dna": dna.to_dict(),
            "sector": sector.to_dict(),
            "themes": [t.to_dict() for t in themes],
            "catalysts": [c.to_dict() for c in catalysts],
            "risks": [r.to_dict() for r in risks],
            "opportunities": [o.to_dict() for o in opps],
            "scenarios": scenarios.to_dict(),
            "thesis": thesis.to_dict(),
            "monitor": monitor.to_dict(),
            "relationships": [e.to_dict() for e in rels],
            "evidence_count": len(evidence),
            "conflict_count": len(conflicts),
        }

    def _build_profile(
        self,
        company_id: str,
        company_name: str,
        evidence: list[dict[str, Any]],
        conflicts: list[dict[str, Any]],
    ) -> CompanyIntelligenceProfile:
        by_key = _facts_by_key(evidence)
        refs = [evidence_ref(e) for e in evidence[:20]]
        conf = _avg([float(e.get("confidence") or 0) for e in evidence])

        def section_from(keys: list[str], default: str) -> str:
            parts = []
            for k in keys:
                for ev in by_key.get(k, [])[:2]:
                    parts.append(ev.get("value_text") or "")
            text = " ".join(p for p in parts if p).strip()
            return text[:500] if text else default

        sections: dict[str, Any] = {
            "business_summary": section_from(["business_model", "products", "revenue"], "Insufficient verified evidence for business summary."),
            "business_model": section_from(["business_model"], "Not enough verified business-model evidence."),
            "revenue_mix": section_from(["revenue", "products"], "Revenue mix not yet evidenced."),
            "geographic_mix": section_from(["geography", "revenue"], "Geographic mix not yet evidenced."),
            "product_mix": section_from(["products"], "Product mix not yet evidenced."),
            "customer_base": section_from(["customers"], "Customer base not yet evidenced."),
            "supplier_dependencies": section_from(["suppliers"], "Supplier dependencies not yet evidenced."),
            "competitive_landscape": section_from(["products", "business_model"], "Competitive landscape inferred only from limited verified facts."),
            "market_share": section_from(["market_share"], "Market share not yet evidenced."),
            "industry_structure": section_from(["business_model"], "Industry structure pending sector analysis."),
            "economic_moat": section_from(["business_model", "margins"], "Moat assessment requires more verified evidence."),
            "capital_allocation_history": section_from(["capex", "dividend", "buyback"], "Capital allocation history sparse."),
            "management_quality": section_from(["management", "guidance", "board"], "Management quality assessed from limited guidance/board evidence."),
            "balance_sheet_strength": section_from(["debt", "cash"], "Balance sheet strength pending more verified financial facts."),
            "cash_flow_quality": section_from(["cash", "pat", "revenue"], "Cash-flow quality not fully evidenced."),
            "profitability": section_from(["margins", "pat"], "Profitability facts limited."),
            "growth_outlook": section_from(["guidance", "revenue", "opportunities"], "Growth outlook contingent on verified guidance."),
            "capital_requirements": section_from(["capex"], "Capex / capital requirements sparse."),
            "pricing_power": section_from(["margins", "products"], "Pricing power uncertain."),
            "operating_leverage": section_from(["margins", "revenue"], "Operating leverage not yet evidenced."),
            "technology_strategy": section_from(["products", "opportunities"], "Technology strategy not yet evidenced."),
            "ai_strategy": section_from(["opportunities", "products"], "AI strategy not yet evidenced."),
            "expansion_plans": section_from(["capex", "guidance"], "Expansion plans not yet evidenced."),
            "ma_history": section_from(["ma"], "M&A history not yet evidenced."),
            "corporate_governance": section_from(["board", "shareholding", "management"], "Governance assessed from shareholding/board evidence where available."),
            "esg_summary": section_from(["esg"], "ESG summary not yet evidenced."),
            "key_risks": [evidence_ref(e) for e in by_key.get("risks", [])[:5]],
            "investment_thesis": "",
            "bear_thesis": section_from(["risks", "debt"], "Bear case driven by verified risks where present."),
            "bull_thesis": section_from(["opportunities", "guidance"], "Bull case driven by verified opportunities/guidance where present."),
            "base_case": "Base case assumes continuation of currently verified operating trends without material new catalysts.",
            "catalysts": [],
            "monitoring_checklist": list(MONITOR_METRICS),
        }

        explain = Explainability(
            supporting_evidence=refs,
            reasoning_summary=(
                f"Profile synthesised from {len(evidence)} verified/pending EVE evidence items. "
                "No raw documents consumed. Uncertainty preserved where evidence is thin."
            ),
            confidence=conf,
            conflicting_evidence=conflicts,
            responsible_engine="iie.company_profile",
            version=1,
        )
        return CompanyIntelligenceProfile(
            company_id=company_id,
            company_name=company_name,
            sections=sections,
            confidence=conf,
            evidence_ids=[e.get("evidence_id") for e in evidence if e.get("evidence_id")],
            explainability=explain,
        )

    def _build_dna(
        self,
        company_id: str,
        evidence: list[dict[str, Any]],
        conflicts: list[dict[str, Any]],
    ) -> CompanyDna:
        by_key = _facts_by_key(evidence)
        prior = self.store.dna.get(company_id)
        dims: dict[str, DnaDimension] = {}
        mapping = {
            "business_quality": ["business_model", "margins", "revenue"],
            "moat": ["business_model", "margins", "products"],
            "execution_quality": ["guidance", "capex"],
            "innovation": ["products", "opportunities"],
            "capital_discipline": ["capex", "debt", "dividend"],
            "management_credibility": ["management", "guidance", "board"],
            "balance_sheet_quality": ["debt", "cash"],
            "industry_leadership": ["market_share", "products"],
            "scalability": ["revenue", "opportunities"],
            "margin_durability": ["margins"],
            "pricing_power": ["margins", "products"],
            "resilience": ["cash", "debt", "risks"],
            "commodity_sensitivity": ["commodity"],
            "interest_rate_sensitivity": ["interest", "debt"],
            "currency_sensitivity": ["fx"],
            "government_dependency": ["policy"],
            "customer_concentration": ["customers"],
            "supplier_risk": ["suppliers"],
        }
        for dim in DNA_DIMENSIONS:
            keys = mapping.get(dim, [])
            supporting = []
            for k in keys:
                supporting.extend(by_key.get(k, [])[:2])
            refs = [evidence_ref(e) for e in supporting[:4]]
            conf = _avg([float(e.get("confidence") or 0) for e in supporting]) if supporting else 0.2
            assessment = _assessment_from_confidence(conf) if supporting else "insufficient_evidence"
            hist: list[dict[str, Any]] = []
            if prior and dim in prior.dimensions:
                old = prior.dimensions[dim]
                if old.assessment != assessment:
                    hist = list(old.historical_evolution) + [
                        {
                            "as_of": old.last_updated,
                            "assessment": old.assessment,
                            "confidence": old.confidence,
                            "reason": "Updated from newer verified evidence",
                        }
                    ]
                    # archive evolution entry
                    self.store._archive(
                        object_type="dna_dimension",
                        entity_id=company_id,
                        version=old.version,
                        assessment=f"{dim}:{old.assessment}",
                        confidence=old.confidence,
                        reasoning_summary=f"Prior {dim} assessment",
                        supporting_evidence=old.supporting_evidence,
                        payload={"dimension": dim, **old.to_dict()},
                        conflicting_evidence=conflicts,
                    )
                else:
                    hist = list(old.historical_evolution)
            dims[dim] = DnaDimension(
                dimension=dim,
                assessment=assessment,
                confidence=conf,
                supporting_evidence=refs,
                historical_evolution=hist[-20:],
                version=(prior.dimensions[dim].version + 1) if prior and dim in prior.dimensions else 1,
            )
        return CompanyDna(company_id=company_id, dimensions=dims)

    def _touch_sector(self, sector_id: str, company_id: str, evidence: list[dict[str, Any]]) -> SectorIntelligence:
        label = next((s["label"] for s in SECTOR_CATALOG if s["sector_id"] == sector_id), sector_id)
        existing = self.store.sectors.get(sector_id)
        companies = list(existing.key_listed_companies) if existing else []
        if company_id not in companies:
            companies.append(company_id)
        by_key = _facts_by_key(evidence)
        risks = [evidence_ref(e)["claim_text"] for e in by_key.get("risks", [])[:5]]
        cats = [evidence_ref(e)["claim_text"] for e in by_key.get("guidance", [])[:5]]
        conf = _avg([float(e.get("confidence") or 0) for e in evidence])
        explain = Explainability(
            supporting_evidence=[evidence_ref(e) for e in evidence[:10]],
            reasoning_summary=f"Sector intelligence updated from verified company evidence for {company_id}.",
            confidence=conf,
            responsible_engine="iie.sector",
        )
        return SectorIntelligence(
            sector_id=sector_id,
            name=label,
            industry_structure=existing.industry_structure if existing else f"{label} industry structure inferred from covered companies.",
            growth_drivers=(existing.growth_drivers if existing else [])
            + [evidence_ref(e)["claim_text"] for e in by_key.get("opportunities", [])[:2]],
            competitive_intensity=existing.competitive_intensity if existing else "moderate",
            regulation=existing.regulation if existing else "See policy / SEBI / RBI verified evidence where available.",
            demand_outlook=existing.demand_outlook if existing else "Demand outlook contingent on verified sector catalysts.",
            supply_outlook=existing.supply_outlook if existing else "Supply outlook pending capacity evidence.",
            key_listed_companies=companies[:50],
            capacity_additions=existing.capacity_additions if existing else [],
            valuation_trends=existing.valuation_trends if existing else "Valuation trends reserved for IIE v2.",
            industry_risks=list(dict.fromkeys((existing.industry_risks if existing else []) + risks))[:20],
            industry_catalysts=list(dict.fromkeys((existing.industry_catalysts if existing else []) + cats))[:20],
            government_influence=existing.government_influence if existing else "Mapped via macro impact chains when policy evidence arrives.",
            global_comparisons=existing.global_comparisons if existing else "",
            confidence=conf,
            evidence_ids=[e.get("evidence_id") for e in evidence if e.get("evidence_id")],
            explainability=explain,
        )

    def _classify_themes(self, company_id: str, sector_id: str, evidence: list[dict[str, Any]]) -> list[ThemeIntelligence]:
        blob = _text_blob(evidence) + " " + sector_id
        themes: list[ThemeIntelligence] = []
        for row in THEME_CATALOG:
            kws = [k.lower() for k in row.get("keywords") or []]
            if any(k in blob for k in kws) or row["theme_id"] == sector_id:
                themes.append(
                    ThemeIntelligence(
                        theme_id=row["theme_id"],
                        name=row["label"],
                        description=f"Theme membership inferred from verified evidence keywords for {company_id}.",
                        company_ids=[company_id],
                        sector_ids=[sector_id],
                        confidence=_avg([float(e.get("confidence") or 0) for e in evidence[:5]]) or 0.4,
                        evidence_ids=[e.get("evidence_id") for e in evidence[:5] if e.get("evidence_id")],
                    )
                )
        return themes

    def _build_catalysts(self, company_id: str, sector_id: str, evidence: list[dict[str, Any]]) -> list[Catalyst]:
        by_key = _facts_by_key(evidence)
        out: list[Catalyst] = []
        for key in _CATALYST_KEYS:
            for ev in by_key.get(key, [])[:3]:
                cid = _stable_id("cat", company_id, key, ev.get("evidence_id") or ev.get("value_text", "")[:40])
                ctype = {
                    "guidance": "management_guidance",
                    "dividend": "dividend",
                    "buyback": "buyback",
                    "capex": "capacity_commissioning",
                    "board": "agm",
                    "products": "product_launch",
                }.get(key, "other")
                conf = float(ev.get("confidence") or 0)
                out.append(
                    Catalyst(
                        catalyst_id=cid,
                        title=(ev.get("value_text") or key)[:160],
                        catalyst_type=ctype,
                        expected_date=None,
                        probability=min(0.9, max(0.2, conf)),
                        potential_impact="moderate" if conf < 0.7 else "high",
                        affected_companies=[company_id],
                        affected_sectors=[sector_id],
                        confidence=conf,
                        evidence_ids=[ev.get("evidence_id")] if ev.get("evidence_id") else [],
                        explainability=Explainability(
                            supporting_evidence=[evidence_ref(ev)],
                            reasoning_summary=f"Catalyst derived from verified fact_key={key}.",
                            confidence=conf,
                            responsible_engine="iie.catalyst",
                        ),
                    )
                )
        return out

    def _build_risks(
        self,
        company_id: str,
        evidence: list[dict[str, Any]],
        conflicts: list[dict[str, Any]],
    ) -> list[RiskItem]:
        by_key = _facts_by_key(evidence)
        out: list[RiskItem] = []
        type_map = {
            "risks": "operational",
            "debt": "financial",
            "litigation": "regulatory",
            "board": "governance",
            "fx": "fx",
            "commodity": "commodity",
            "interest": "interest_rate",
        }
        for key in _RISK_KEYS:
            for ev in by_key.get(key, [])[:3]:
                rid = _stable_id("risk", company_id, key, ev.get("evidence_id") or "")
                conf = float(ev.get("confidence") or 0)
                out.append(
                    RiskItem(
                        risk_id=rid,
                        company_id=company_id,
                        risk_type=type_map.get(key, "operational"),
                        title=(ev.get("value_text") or key)[:160],
                        description=ev.get("value_text") or "",
                        severity="high" if conf >= 0.7 and key in {"debt", "litigation", "risks"} else "medium",
                        confidence=conf,
                        evidence_ids=[ev.get("evidence_id")] if ev.get("evidence_id") else [],
                        explainability=Explainability(
                            supporting_evidence=[evidence_ref(ev)],
                            reasoning_summary=f"Risk extracted from verified fact_key={key}.",
                            confidence=conf,
                            conflicting_evidence=conflicts if key in {c.get("fact_key") for c in conflicts} else [],
                            responsible_engine="iie.risk",
                        ),
                    )
                )
        # Conflicting evidence itself is a risk signal
        for c in conflicts[:3]:
            rid = _stable_id("risk", company_id, "conflict", c.get("conflict_id") or c.get("fact_key") or "")
            out.append(
                RiskItem(
                    risk_id=rid,
                    company_id=company_id,
                    risk_type="governance",
                    title=f"Evidence conflict on {c.get('fact_key')}",
                    description=f"{c.get('left')} vs {c.get('right')}",
                    severity="medium",
                    confidence=0.55,
                    explainability=Explainability(
                        supporting_evidence=[],
                        reasoning_summary="Open EVE conflict preserved; IIE does not silently resolve.",
                        confidence=0.55,
                        conflicting_evidence=[c],
                        responsible_engine="iie.risk",
                    ),
                )
            )
        return out

    def _build_opportunities(self, company_id: str, evidence: list[dict[str, Any]]) -> list[OpportunityItem]:
        by_key = _facts_by_key(evidence)
        out: list[OpportunityItem] = []
        type_map = {
            "opportunities": "industry_tailwind",
            "guidance": "demand_acceleration",
            "capex": "capacity_utilisation",
            "products": "technology_leadership",
            "revenue": "market_expansion",
            "margins": "margin_expansion",
        }
        for key in _OPP_KEYS:
            for ev in by_key.get(key, [])[:2]:
                oid = _stable_id("opp", company_id, key, ev.get("evidence_id") or "")
                conf = float(ev.get("confidence") or 0)
                out.append(
                    OpportunityItem(
                        opportunity_id=oid,
                        company_id=company_id,
                        opportunity_type=type_map.get(key, "industry_tailwind"),
                        title=(ev.get("value_text") or key)[:160],
                        description=ev.get("value_text") or "",
                        confidence=conf,
                        evidence_ids=[ev.get("evidence_id")] if ev.get("evidence_id") else [],
                        explainability=Explainability(
                            supporting_evidence=[evidence_ref(ev)],
                            reasoning_summary=f"Opportunity derived from verified fact_key={key}.",
                            confidence=conf,
                            responsible_engine="iie.opportunity",
                        ),
                    )
                )
        return out

    def _build_scenarios(
        self,
        company_id: str,
        evidence: list[dict[str, Any]],
        risks: list[RiskItem],
        opps: list[OpportunityItem],
        conflicts: list[dict[str, Any]],
    ) -> ScenarioSet:
        conf = _avg([float(e.get("confidence") or 0) for e in evidence])
        refs = [evidence_ref(e) for e in evidence[:8]]
        bull = ScenarioCase(
            case_type="bull",
            assumptions=["Verified opportunities materialise", "Guidance delivered"],
            key_drivers=[o.title for o in opps[:4]] or ["Upside drivers not yet evidenced"],
            risks=[r.title for r in risks[:2]],
            potential_triggers=[o.title for o in opps[:3]],
            probability=0.25,
            confidence=conf * 0.9,
            supporting_evidence=refs,
        )
        base = ScenarioCase(
            case_type="base",
            assumptions=["Current verified trends continue", "No material unresolved conflict dominates"],
            key_drivers=["Operating continuity from verified evidence"],
            risks=[r.title for r in risks[:3]],
            potential_triggers=["Quarterly results", "Management guidance updates"],
            probability=0.5,
            confidence=conf,
            supporting_evidence=refs,
        )
        bear = ScenarioCase(
            case_type="bear",
            assumptions=["Verified risks crystallise", "Conflicts indicate higher uncertainty"],
            key_drivers=[r.title for r in risks[:4]] or ["Downside drivers not yet evidenced"],
            risks=[r.title for r in risks[:5]],
            potential_triggers=[r.title for r in risks[:3]],
            probability=0.25,
            confidence=conf * 0.85,
            supporting_evidence=refs,
        )
        return ScenarioSet(
            scenario_id=new_id("scn"),
            company_id=company_id,
            bull=bull,
            base=base,
            bear=bear,
            evidence_ids=[e.get("evidence_id") for e in evidence if e.get("evidence_id")],
            explainability=Explainability(
                supporting_evidence=refs,
                reasoning_summary="Three scenarios constructed from verified opportunities/risks; probabilities are analytical priors, not forecasts.",
                confidence=conf,
                conflicting_evidence=conflicts,
                responsible_engine="iie.scenario",
            ),
        )

    def _build_thesis(
        self,
        company_id: str,
        profile: CompanyIntelligenceProfile,
        catalysts: list[Catalyst],
        risks: list[RiskItem],
        opps: list[OpportunityItem],
        evidence: list[dict[str, Any]],
        conflicts: list[dict[str, Any]],
    ) -> InvestmentThesis:
        conf = profile.confidence
        refs = [evidence_ref(e) for e in evidence[:12]]
        thesis_text = (
            f"Based on {len(evidence)} verified evidence items, {profile.company_name} presents "
            f"{'a constructive' if conf >= 0.55 else 'an uncertain'} investment setup. "
            "Thesis updates are versioned and never overwrite history."
        )
        profile.sections["investment_thesis"] = thesis_text
        profile.sections["catalysts"] = [c.title for c in catalysts[:8]]
        return InvestmentThesis(
            thesis_id=new_id("thesis"),
            company_id=company_id,
            business_overview=str(profile.sections.get("business_summary") or ""),
            investment_thesis=thesis_text,
            competitive_advantages=[str(profile.sections.get("economic_moat") or "")],
            growth_drivers=[o.title for o in opps[:6]],
            risks=[r.title for r in risks[:8]],
            valuation_considerations="Valuation engine reserved for IIE v2; use qualitative considerations only.",
            catalysts=[c.title for c in catalysts[:8]],
            monitoring_checklist=list(MONITOR_METRICS)[:12],
            evidence_references=refs,
            confidence=conf,
            explainability=Explainability(
                supporting_evidence=refs,
                reasoning_summary="Structured thesis from verified EVE evidence only.",
                confidence=conf,
                conflicting_evidence=conflicts,
                responsible_engine="iie.thesis",
            ),
        )

    def _build_monitor(self, company_id: str, evidence: list[dict[str, Any]]) -> MonitoringChecklist:
        by_key = _facts_by_key(evidence)
        items: list[MonitorItem] = []
        for metric in MONITOR_METRICS:
            # Map monitor metric to fact keys via FACT_TO_INTEL reverse-ish
            related = []
            for fk, intel in FACT_TO_INTEL.items():
                if metric in intel or metric.replace("_", "") in "".join(intel):
                    related.extend(by_key.get(fk, []))
            # also direct key match
            related.extend(by_key.get(metric, []))
            related = related[:2]
            status = "active" if related else "watch"
            last_value = (related[0].get("value_text") or "")[:120] if related else ""
            items.append(
                MonitorItem(
                    metric=metric,
                    status=status,
                    last_value=last_value,
                    notes="Tracked from verified evidence" if related else "Awaiting verified evidence",
                    evidence_ids=[e.get("evidence_id") for e in related if e.get("evidence_id")],
                )
            )
        return MonitoringChecklist(company_id=company_id, items=items)

    def _infer_relationships(self, company_id: str, evidence: list[dict[str, Any]]) -> list[RelationshipEdge]:
        out: list[RelationshipEdge] = []
        for ev in evidence:
            text = (ev.get("value_text") or "").lower()
            for pattern, rel in _RELATION_PATTERNS:
                if re.search(pattern, text):
                    eid = _stable_id("rel", company_id, rel, ev.get("evidence_id") or text[:30])
                    out.append(
                        RelationshipEdge(
                            edge_id=eid,
                            from_id=company_id,
                            to_id=f"inferred:{rel}",
                            relation_type=rel,
                            confidence=float(ev.get("confidence") or 0) * 0.7,
                            evidence_ids=[ev.get("evidence_id")] if ev.get("evidence_id") else [],
                        )
                    )
        return out[:20]

    def map_macro(self, macro_event: str, *, company_ids: list[str] | None = None) -> MacroImpact:
        key = (macro_event or "").strip().lower().replace(" ", "_")
        chain = list(MACRO_IMPACT_MAP.get(key) or MACRO_IMPACT_MAP.get(key.replace("-", "_")) or [])
        if not chain:
            # fuzzy: find any key contained
            for mk, ch in MACRO_IMPACT_MAP.items():
                if mk in key or key in mk:
                    key = mk
                    chain = list(ch)
                    break
        affected_sectors = chain
        affected_companies: list[str] = []
        for sid in affected_sectors:
            sec = self.store.sectors.get(sid)
            if sec:
                affected_companies.extend(sec.key_listed_companies)
        if company_ids:
            affected_companies = sorted(set(affected_companies) | set(company_ids))
        else:
            affected_companies = sorted(set(affected_companies))
        direct = [{"sector_id": s, "order": i, "impact": "direct" if i == 0 else "indirect"} for i, s in enumerate(chain)]
        impact = MacroImpact(
            impact_id=_stable_id("macro", key, ",".join(chain[:3])),
            macro_event=key,
            chain=chain,
            direct_impacts=[d for d in direct if d["impact"] == "direct"],
            indirect_impacts=[d for d in direct if d["impact"] == "indirect"],
            affected_companies=affected_companies,
            affected_sectors=affected_sectors,
            confidence=0.6 if chain else 0.2,
            evidence_ids=[],
        )
        self.store.put_macro(impact)
        return impact

    def compare(
        self,
        company_ids: list[str],
        *,
        dimensions: list[str] | None = None,
    ) -> ComparisonResult:
        dims = dimensions or [
            "management_quality",
            "capital_discipline",
            "balance_sheet_quality",
            "operating_leverage",
            "pricing_power",
            "moat",
            "growth_quality",
        ]
        matrix: dict[str, dict[str, Any]] = {}
        evidence_ids: list[str] = []
        for cid in company_ids:
            dna = self.store.dna.get(cid)
            profile = self.store.profiles.get(cid)
            row: dict[str, Any] = {}
            for d in dims:
                if dna and d in dna.dimensions:
                    dim = dna.dimensions[d]
                    row[d] = {
                        "assessment": dim.assessment,
                        "confidence": dim.confidence,
                        "evidence": dim.supporting_evidence[:2],
                    }
                    evidence_ids.extend(dim.supporting_evidence[i]["evidence_id"] for i in range(min(2, len(dim.supporting_evidence))) if dim.supporting_evidence[i].get("evidence_id"))
                elif profile and d.replace("_quality", "") in str(profile.sections):
                    row[d] = {
                        "assessment": "from_profile",
                        "confidence": profile.confidence,
                        "evidence": profile.explainability.supporting_evidence[:1],
                    }
                else:
                    row[d] = {"assessment": "insufficient_evidence", "confidence": 0.0, "evidence": []}
            matrix[cid] = row
        conf = _avg(
            [
                float(v.get("confidence") or 0)
                for row in matrix.values()
                for v in row.values()
            ]
        )
        result = ComparisonResult(
            comparison_id=new_id("cmp"),
            company_ids=list(company_ids),
            dimensions=dims,
            matrix=matrix,
            summary=f"Comparative intelligence across {len(company_ids)} companies on {len(dims)} dimensions from versioned DNA/profile objects.",
            confidence=conf,
            evidence_ids=list(dict.fromkeys(evidence_ids))[:40],
        )
        self.store.put_comparison(result)
        return result
