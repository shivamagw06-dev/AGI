"""KG-01 Institutional Knowledge Graph — single-company substrate."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from institutional_decision.models import InstitutionalDecision
from institutional_decision.recommendation_rules import business_quality_band_safe
from institutional_graph.entities import Entity, make_node
from institutional_graph.provenance import LINEAGE_CHAIN, build_provenance
from institutional_graph.relationships import Relationship, make_relationship
from institutional_graph.schema import GRAPH_ENGINE_VERSION, KG_VERSION
from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.reasoning import Reason

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _nid(ticker: str, kind: str, key: str) -> str:
    raw = f"{ticker}|{kind}|{key}".lower().replace(" ", "_")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return f"kg:{ticker.lower()}:{kind}:{digest}"


def _conf01(value: Any, default: float = 0.7) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if n > 1.0:
        n = n / 100.0
    return max(0.0, min(1.0, n))


@dataclass
class InstitutionalKnowledgeGraph:
    """In-memory directed graph for one company."""

    ticker: str
    graph_id: str
    version: str = KG_VERSION
    engine_version: str = GRAPH_ENGINE_VERSION
    generated_at: str = ""
    company_name: str = ""
    scope: str = "single_company"
    nodes: Dict[str, Entity] = field(default_factory=dict)
    relationships: Dict[str, Relationship] = field(default_factory=dict)
    decision_node_id: str = ""
    calibration_node_id: str = ""
    lineage: List[str] = field(default_factory=lambda: list(LINEAGE_CHAIN))
    inferred_relationship_ids: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Entity) -> Entity:
        self.nodes[node.id] = node
        return node

    def add_relationship(self, rel: Relationship) -> Relationship:
        if rel.source_id not in self.nodes or rel.target_id not in self.nodes:
            raise ValueError(f"relationship endpoints missing: {rel.id}")
        self.relationships[rel.id] = rel
        if rel.inferred:
            self.inferred_relationship_ids.append(rel.id)
        return rel

    def get(self, node_id: str) -> Optional[Entity]:
        return self.nodes.get(node_id)

    def neighbors(self, node_id: str, *, outbound: bool = True) -> List[Relationship]:
        if outbound:
            return [r for r in self.relationships.values() if r.source_id == node_id]
        return [r for r in self.relationships.values() if r.target_id == node_id]

    def nodes_by_type(self, node_type: str) -> List[Entity]:
        return [n for n in self.nodes.values() if n.type == node_type]

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "version": self.version,
            "engine_version": self.engine_version,
            "generated_at": self.generated_at,
            "scope": self.scope,
            "decision_node_id": self.decision_node_id,
            "calibration_node_id": self.calibration_node_id,
            "lineage": list(self.lineage),
            "entity_count": len(self.nodes),
            "relationship_count": len(self.relationships),
            "inference_count": len(self.inferred_relationship_ids),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "relationships": [r.to_dict() for r in self.relationships.values()],
            "inferred_relationship_ids": list(self.inferred_relationship_ids),
            "meta": dict(self.meta),
            "llm": False,
        }


def build_company_graph(
    evidence: InstitutionalReportInput,
    reasons: Sequence[Reason] | None = None,
    decision: InstitutionalDecision | None = None,
    *,
    as_of: str | None = None,
) -> InstitutionalKnowledgeGraph:
    """
    Build a deterministic single-company knowledge graph.

    Scope: one company → evidence → metrics → risks → valuation → reasons → decision.
    """
    ticker = str(evidence.ticker or "").strip().upper()
    ts = as_of or evidence.as_of or now_iso()
    snap = ""
    if decision is not None:
        snap = decision.evidence_snapshot_id
    if not snap:
        snap = hashlib.sha256(f"{ticker}|{ts}".encode()).hexdigest()[:12]
    graph_id = f"kg-{ticker.lower()}-{snap}"

    g = InstitutionalKnowledgeGraph(
        ticker=ticker,
        graph_id=graph_id,
        generated_at=ts,
        company_name=str(evidence.company_name or ""),
    )

    def prov(origin: str, evidence_ids: Iterable[str] = (), source_document: str = "") -> Any:
        return build_provenance(
            origin=origin,
            timestamp=ts,
            source_document=source_document,
            evidence_ids=evidence_ids,
            engine=GRAPH_ENGINE_VERSION,
            version=KG_VERSION,
        )

    # --- Core entities ---
    company = make_node(
        node_id=_nid(ticker, "company", ticker),
        node_type="Company",
        label=evidence.company_name or ticker,
        version=KG_VERSION,
        timestamp=ts,
        source="InstitutionalReportInput",
        confidence=1.0,
        ticker=ticker,
        attributes={"sector": evidence.sector},
        provenance=prov("report_input"),
    )
    g.add_node(company)

    sector = make_node(
        node_id=_nid(ticker, "sector", evidence.sector or "unknown"),
        node_type="Sector",
        label=str(evidence.sector or "Unknown"),
        version=KG_VERSION,
        timestamp=ts,
        source="InstitutionalReportInput",
        confidence=0.95,
        ticker=ticker,
        provenance=prov("report_input"),
    )
    g.add_node(sector)
    g.add_relationship(
        make_relationship(
            rel_id=_nid(ticker, "rel", f"belongs:{company.id}:{sector.id}"),
            source_id=company.id,
            target_id=sector.id,
            kind="belongs_to",
            strength=1.0,
            confidence=0.95,
            evidence_ids=tuple(e.evidence_id for e in evidence.evidence[:1]),
            version=KG_VERSION,
            timestamp=ts,
            label="company_in_sector",
            provenance=prov("report_input"),
        )
    )

    industry = make_node(
        node_id=_nid(ticker, "industry", evidence.sector or "banking"),
        node_type="Industry",
        label=str(evidence.sector or "Banking"),
        version=KG_VERSION,
        timestamp=ts,
        source="InstitutionalReportInput",
        confidence=0.9,
        ticker=ticker,
        provenance=prov("report_input"),
    )
    g.add_node(industry)
    g.add_relationship(
        make_relationship(
            rel_id=_nid(ticker, "rel", f"belongs:{company.id}:{industry.id}"),
            source_id=company.id,
            target_id=industry.id,
            kind="belongs_to",
            strength=0.9,
            confidence=0.9,
            version=KG_VERSION,
            timestamp=ts,
            label="company_in_industry",
            provenance=prov("report_input"),
        )
    )

    country = make_node(
        node_id=_nid(ticker, "country", "india"),
        node_type="Country",
        label="India",
        version=KG_VERSION,
        timestamp=ts,
        source="scope_default",
        confidence=0.99,
        ticker=ticker,
        provenance=prov("scope_default", source_document="NSE/India single-company scope"),
    )
    g.add_node(country)
    g.add_relationship(
        make_relationship(
            rel_id=_nid(ticker, "rel", f"belongs:{company.id}:{country.id}"),
            source_id=company.id,
            target_id=country.id,
            kind="belongs_to",
            strength=1.0,
            confidence=0.99,
            version=KG_VERSION,
            timestamp=ts,
            label="company_in_country",
            provenance=prov("scope_default"),
        )
    )

    bq_band = business_quality_band_safe(evidence.business_quality)
    management = make_node(
        node_id=_nid(ticker, "management", "franchise"),
        node_type="Management",
        label="Franchise / Management Quality",
        version=KG_VERSION,
        timestamp=ts,
        source="InstitutionalReportInput",
        confidence=0.8,
        ticker=ticker,
        attributes={"band": bq_band},
        provenance=prov("report_input", evidence_ids=[e.evidence_id for e in evidence.evidence]),
    )
    g.add_node(management)

    # --- Metrics ---
    metric_defs = [
        ("nim", "Net Interest Margin", "FinancialMetric", 0.75),
        ("credit_cost", "Credit Cost", "FinancialMetric", 0.72),
        ("roe", "Return on Equity", "FinancialMetric", 0.74),
        ("profitability", "Profitability", "FinancialMetric", 0.76),
        ("business_quality", "Business Quality", "FinancialMetric", 0.85),
        ("financial_quality", "Financial Quality", "FinancialMetric", 0.8),
    ]
    metric_ids: dict[str, str] = {}
    for key, label, typ, conf in metric_defs:
        node = make_node(
            node_id=_nid(ticker, "metric", key),
            node_type=typ,
            label=label,
            version=KG_VERSION,
            timestamp=ts,
            source="InstitutionalReportInput",
            confidence=conf,
            ticker=ticker,
            attributes={"metric_key": key, "financial_quality": evidence.financial_quality},
            provenance=prov("report_input", evidence_ids=[e.evidence_id for e in evidence.evidence]),
        )
        g.add_node(node)
        metric_ids[key] = node.id
        g.add_relationship(
            make_relationship(
                rel_id=_nid(ticker, "rel", f"company_metric:{key}"),
                source_id=company.id,
                target_id=node.id,
                kind="monitors",
                strength=0.8,
                confidence=conf,
                evidence_ids=tuple(e.evidence_id for e in evidence.evidence[:2]),
                version=KG_VERSION,
                timestamp=ts,
                label=f"company_monitors_{key}",
                provenance=prov("report_input"),
            )
        )

    valuation = make_node(
        node_id=_nid(ticker, "valuation", str(evidence.valuation or "unclear")),
        node_type="ValuationMetric",
        label=f"Valuation: {evidence.valuation}",
        version=KG_VERSION,
        timestamp=ts,
        source="InstitutionalReportInput",
        confidence=0.8,
        ticker=ticker,
        attributes={"band": str(evidence.valuation or "")},
        provenance=prov("report_input", evidence_ids=[e.evidence_id for e in evidence.evidence]),
    )
    g.add_node(valuation)

    # Macro (company-scoped — not a market-wide graph)
    rbi = make_node(
        node_id=_nid(ticker, "macro", "rbi_rate"),
        node_type="MacroVariable",
        label="RBI Policy Rate",
        version=KG_VERSION,
        timestamp=ts,
        source="banking_macro_link",
        confidence=0.7,
        ticker=ticker,
        attributes={"scope": "company_contextual"},
        provenance=prov("banking_macro_link", source_document="company-scoped macro context"),
    )
    g.add_node(rbi)

    # Structural banking relationships (deterministic institutional memory)
    structural = [
        (rbi.id, metric_ids["nim"], "negative", 0.7, "RBI rate pressures NIM"),
        (metric_ids["nim"], metric_ids["profitability"], "positive", 0.75, "NIM supports profitability"),
        (metric_ids["credit_cost"], metric_ids["profitability"], "negative", 0.8, "Credit cost pressures profitability"),
        (metric_ids["roe"], metric_ids["profitability"], "positive", 0.78, "ROE supports profitability"),
        (metric_ids["profitability"], metric_ids["business_quality"], "positive", 0.8, "Profitability supports business quality"),
        (metric_ids["financial_quality"], metric_ids["profitability"], "positive", 0.77, "Financial quality supports profitability"),
        (management.id, metric_ids["business_quality"], "positive", 0.7, "Management supports business quality"),
        (metric_ids["business_quality"], company.id, "supports", 0.85, "Business quality supports company thesis"),
    ]
    for src, tgt, kind, strength, label in structural:
        g.add_relationship(
            make_relationship(
                rel_id=_nid(ticker, "rel", f"struct:{label}"),
                source_id=src,
                target_id=tgt,
                kind=kind,
                strength=strength,
                confidence=strength,
                evidence_ids=tuple(e.evidence_id for e in evidence.evidence[:3]),
                version=KG_VERSION,
                timestamp=ts,
                label=label,
                provenance=prov("structural_banking_memory", evidence_ids=[e.evidence_id for e in evidence.evidence[:3]]),
            )
        )

    # Valuation → company
    val_kind = "pressures" if str(evidence.valuation).title() == "Expensive" else (
        "supports" if str(evidence.valuation).title() == "Cheap" else "impacts"
    )
    g.add_relationship(
        make_relationship(
            rel_id=_nid(ticker, "rel", "valuation_company"),
            source_id=valuation.id,
            target_id=company.id,
            kind=val_kind,
            strength=0.7,
            confidence=0.75,
            evidence_ids=tuple(e.evidence_id for e in evidence.evidence[:2]),
            version=KG_VERSION,
            timestamp=ts,
            label="valuation_impacts_company",
            provenance=prov("report_input"),
        )
    )

    # Risks / catalysts / forecast
    risk_ids: list[str] = []
    for i, risk in enumerate(evidence.risks or ()):
        node = make_node(
            node_id=_nid(ticker, "risk", f"{i}:{risk[:40]}"),
            node_type="Risk",
            label=str(risk),
            version=KG_VERSION,
            timestamp=ts,
            source="InstitutionalReportInput",
            confidence=0.7,
            ticker=ticker,
            provenance=prov("report_input", evidence_ids=[e.evidence_id for e in evidence.evidence]),
        )
        g.add_node(node)
        risk_ids.append(node.id)
        g.add_relationship(
            make_relationship(
                rel_id=_nid(ticker, "rel", f"risk_pressures:{i}"),
                source_id=node.id,
                target_id=company.id,
                kind="pressures",
                strength=0.65,
                confidence=0.7,
                version=KG_VERSION,
                timestamp=ts,
                label="risk_pressures_company",
                provenance=prov("report_input"),
            )
        )
        # Credit-related risks hit credit_cost / profitability
        if any(w in str(risk).lower() for w in ("credit", "npa", "asset quality", "slippage")):
            g.add_relationship(
                make_relationship(
                    rel_id=_nid(ticker, "rel", f"risk_credit:{i}"),
                    source_id=node.id,
                    target_id=metric_ids["credit_cost"],
                    kind="positive",
                    strength=0.7,
                    confidence=0.72,
                    version=KG_VERSION,
                    timestamp=ts,
                    label="risk_elevates_credit_cost",
                    provenance=prov("report_input"),
                )
            )

    for i, cat in enumerate(evidence.catalysts or ()):
        node = make_node(
            node_id=_nid(ticker, "catalyst", f"{i}:{cat[:40]}"),
            node_type="Catalyst",
            label=str(cat),
            version=KG_VERSION,
            timestamp=ts,
            source="InstitutionalReportInput",
            confidence=0.68,
            ticker=ticker,
            provenance=prov("report_input"),
        )
        g.add_node(node)
        g.add_relationship(
            make_relationship(
                rel_id=_nid(ticker, "rel", f"catalyst_supports:{i}"),
                source_id=node.id,
                target_id=company.id,
                kind="supports",
                strength=0.6,
                confidence=0.68,
                version=KG_VERSION,
                timestamp=ts,
                label="catalyst_supports_company",
                provenance=prov("report_input"),
            )
        )

    forecast = make_node(
        node_id=_nid(ticker, "forecast", "near_term"),
        node_type="Forecast",
        label="Near-term operating forecast",
        version=KG_VERSION,
        timestamp=ts,
        source="InstitutionalReportInput",
        confidence=0.65,
        ticker=ticker,
        attributes={"unknowns": list(evidence.unknowns or ())},
        provenance=prov("report_input"),
    )
    g.add_node(forecast)
    g.add_relationship(
        make_relationship(
            rel_id=_nid(ticker, "rel", "forecast_impacts_profitability"),
            source_id=forecast.id,
            target_id=metric_ids["profitability"],
            kind="impacts",
            strength=0.6,
            confidence=0.65,
            version=KG_VERSION,
            timestamp=ts,
            label="forecast_impacts_profitability",
            provenance=prov("report_input"),
        )
    )

    # Evidence nodes
    evidence_ids: list[str] = []
    for ev in evidence.evidence or ():
        node = make_node(
            node_id=_nid(ticker, "evidence", ev.evidence_id or ev.label),
            node_type="Evidence",
            label=ev.label or ev.evidence_id,
            version=KG_VERSION,
            timestamp=ts,
            source=ev.source_type or "EvidenceItem",
            confidence=0.85,
            ticker=ticker,
            attributes={
                "evidence_id": ev.evidence_id,
                "section_keys": list(ev.section_keys or ()),
            },
            provenance=prov(
                "evidence_item",
                evidence_ids=[ev.evidence_id] if ev.evidence_id else (),
                source_document=ev.label or "",
            ),
        )
        g.add_node(node)
        evidence_ids.append(node.id)
        g.add_relationship(
            make_relationship(
                rel_id=_nid(ticker, "rel", f"evidence_company:{ev.evidence_id}"),
                source_id=node.id,
                target_id=company.id,
                kind="evidences",
                strength=0.8,
                confidence=0.85,
                evidence_ids=(ev.evidence_id,) if ev.evidence_id else (),
                version=KG_VERSION,
                timestamp=ts,
                label="evidence_for_company",
                provenance=prov("evidence_item", evidence_ids=[ev.evidence_id] if ev.evidence_id else ()),
            )
        )

    # Reason nodes
    reason_list = list(reasons or [])
    reason_node_ids: list[str] = []
    for reason in reason_list:
        rid = _nid(ticker, "reason", reason.section_key or reason.title)
        node = make_node(
            node_id=rid,
            node_type="Reason",
            label=reason.title or reason.section_key,
            version=KG_VERSION,
            timestamp=ts,
            source="ReasonComposer",
            confidence=_conf01(reason.confidence, 0.67),
            ticker=ticker,
            attributes={
                "section_key": reason.section_key,
                "conclusion": reason.conclusion,
                "supporting_points": list(reason.supporting_points or ()),
                "contradicting_points": list(reason.contradicting_points or ()),
                "unknowns": list(reason.unknowns or ()),
                "supporting_evidence": list(reason.supporting_evidence or ()),
            },
            provenance=prov(
                "reason_composer",
                evidence_ids=list(reason.supporting_evidence or ()),
            ),
        )
        g.add_node(node)
        reason_node_ids.append(node.id)
        # Link evidence → reason
        for ev_ref in reason.supporting_evidence or ():
            for eid in evidence_ids:
                ev_node = g.get(eid)
                if ev_node and (
                    ev_ref == ev_node.attributes.get("evidence_id")
                    or ev_ref in (ev_node.label or "")
                ):
                    g.add_relationship(
                        make_relationship(
                            rel_id=_nid(ticker, "rel", f"ev_reason:{ev_ref}:{reason.section_key}"),
                            source_id=eid,
                            target_id=node.id,
                            kind="evidences",
                            strength=0.8,
                            confidence=_conf01(reason.confidence),
                            evidence_ids=(str(ev_ref),),
                            version=KG_VERSION,
                            timestamp=ts,
                            label="evidence_supports_reason",
                            provenance=prov("reason_composer", evidence_ids=[str(ev_ref)]),
                        )
                    )
        # Metric → reason for key sections
        section = reason.section_key
        metric_map = {
            "business_quality": "business_quality",
            "financial_quality": "financial_quality",
            "valuation": None,
            "risk_assessment": None,
            "bottom_line": "business_quality",
            "investment_thesis": "profitability",
        }
        mk = metric_map.get(section)
        if mk and mk in metric_ids:
            g.add_relationship(
                make_relationship(
                    rel_id=_nid(ticker, "rel", f"metric_reason:{mk}:{section}"),
                    source_id=metric_ids[mk],
                    target_id=node.id,
                    kind="supports",
                    strength=0.7,
                    confidence=_conf01(reason.confidence),
                    version=KG_VERSION,
                    timestamp=ts,
                    label=f"{mk}_supports_reason",
                    provenance=prov("reason_composer"),
                )
            )
        if section == "valuation":
            g.add_relationship(
                make_relationship(
                    rel_id=_nid(ticker, "rel", f"val_reason:{section}"),
                    source_id=valuation.id,
                    target_id=node.id,
                    kind="supports",
                    strength=0.75,
                    confidence=_conf01(reason.confidence),
                    version=KG_VERSION,
                    timestamp=ts,
                    label="valuation_supports_reason",
                    provenance=prov("reason_composer"),
                )
            )

    # Decision node
    if decision is not None:
        dnode = make_node(
            node_id=_nid(ticker, "decision", decision.decision_id or "latest"),
            node_type="Decision",
            label=f"Decision: {decision.recommendation}",
            version=str(decision.decision_version),
            timestamp=decision.generated_at or ts,
            source="InstitutionalDecision",
            confidence=_conf01(decision.confidence),
            ticker=ticker,
            attributes={
                "decision_id": decision.decision_id,
                "recommendation": decision.recommendation,
                "conviction": decision.conviction,
                "score": decision.score,
                "rule_path": decision.rule_path,
                "calibrated": bool(getattr(decision, "calibrated", False)),
            },
            provenance=prov(
                "decision_system",
                evidence_ids=list(decision.evidence_ids or ()),
            ),
        )
        g.add_node(dnode)
        g.decision_node_id = dnode.id
        for rid in reason_node_ids:
            g.add_relationship(
                make_relationship(
                    rel_id=_nid(ticker, "rel", f"reason_decision:{rid}"),
                    source_id=rid,
                    target_id=dnode.id,
                    kind="supports",
                    strength=0.8,
                    confidence=_conf01(decision.confidence),
                    evidence_ids=tuple(decision.evidence_ids or ()),
                    version=KG_VERSION,
                    timestamp=ts,
                    label="reason_supports_decision",
                    provenance=prov("decision_system", evidence_ids=list(decision.evidence_ids or ())),
                )
            )
        # Business quality → supports/pressures recommendation
        rec = str(decision.recommendation or "").upper()
        kind = "supports" if rec == "BUY" else ("pressures" if rec == "SELL" else "impacts")
        g.add_relationship(
            make_relationship(
                rel_id=_nid(ticker, "rel", "bq_decision"),
                source_id=metric_ids["business_quality"],
                target_id=dnode.id,
                kind=kind,
                strength=0.85,
                confidence=_conf01(decision.confidence),
                version=KG_VERSION,
                timestamp=ts,
                label="business_quality_to_recommendation",
                provenance=prov("decision_system"),
            )
        )
        g.add_relationship(
            make_relationship(
                rel_id=_nid(ticker, "rel", "val_decision"),
                source_id=valuation.id,
                target_id=dnode.id,
                kind=val_kind,
                strength=0.75,
                confidence=0.75,
                version=KG_VERSION,
                timestamp=ts,
                label="valuation_to_recommendation",
                provenance=prov("decision_system"),
            )
        )
        for risk_id in risk_ids[:4]:
            g.add_relationship(
                make_relationship(
                    rel_id=_nid(ticker, "rel", f"risk_decision:{risk_id}"),
                    source_id=risk_id,
                    target_id=dnode.id,
                    kind="pressures",
                    strength=0.6,
                    confidence=0.7,
                    version=KG_VERSION,
                    timestamp=ts,
                    label="risk_supports_caution",
                    provenance=prov("decision_system"),
                )
            )

        # Calibration node (if present)
        if getattr(decision, "calibrated", False) or getattr(decision, "calibration", None):
            cal = make_node(
                node_id=_nid(ticker, "calibration", decision.decision_id or "cal"),
                node_type="Calibration",
                label=f"Calibration: {decision.confidence}%",
                version=str(getattr(decision, "calibration_version", "") or KG_VERSION),
                timestamp=ts,
                source="InstitutionalCalibration",
                confidence=_conf01(decision.confidence),
                ticker=ticker,
                attributes={
                    "profile_version": getattr(decision, "calibration_profile_version", ""),
                    "final_confidence": decision.confidence,
                },
                provenance=prov("calibration_engine", evidence_ids=list(decision.evidence_ids or ())),
            )
            g.add_node(cal)
            g.calibration_node_id = cal.id
            g.add_relationship(
                make_relationship(
                    rel_id=_nid(ticker, "rel", "decision_calibration"),
                    source_id=dnode.id,
                    target_id=cal.id,
                    kind="impacts",
                    strength=0.9,
                    confidence=_conf01(decision.confidence),
                    version=KG_VERSION,
                    timestamp=ts,
                    label="decision_to_calibration",
                    provenance=prov("calibration_engine"),
                )
            )

    g.meta = {
        "metric_ids": metric_ids,
        "company_node_id": company.id,
        "valuation_node_id": valuation.id,
        "reason_node_ids": reason_node_ids,
        "evidence_node_ids": evidence_ids,
        "rbi_node_id": rbi.id,
    }
    return g
