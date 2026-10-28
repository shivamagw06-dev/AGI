"""Portfolio Knowledge Graph — Portfolio → Companies → Relationships."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from institutional_portfolio.allocation import build_allocations
from institutional_portfolio.concentration import compute_concentration, concentration_risks
from institutional_portfolio.correlations import average_correlation, compute_correlations
from institutional_portfolio.exposures import compute_exposures, exposures_by_dimension
from institutional_portfolio.portfolio_entities import (
    DecisionSummary,
    HoldingRecord,
    InstitutionalPortfolio,
    PortfolioEntity,
    PortfolioRelationship,
    make_entity,
    make_relationship,
)
from institutional_portfolio.schema import (
    LINEAGE_CHAIN,
    PKG_VERSION,
    PORTFOLIO_GRAPH_ENGINE_VERSION,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


@dataclass
class PortfolioKnowledgeGraph:
    """In-memory directed graph for one portfolio."""

    portfolio_id: str
    graph_id: str
    name: str = ""
    version: str = PKG_VERSION
    engine_version: str = PORTFOLIO_GRAPH_ENGINE_VERSION
    generated_at: str = ""
    scope: str = "single_portfolio"
    nodes: Dict[str, PortfolioEntity] = field(default_factory=dict)
    relationships: Dict[str, PortfolioRelationship] = field(default_factory=dict)
    portfolio_node_id: str = ""
    lineage: List[str] = field(default_factory=lambda: list(LINEAGE_CHAIN))
    institutional_portfolio: Optional[InstitutionalPortfolio] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: PortfolioEntity) -> PortfolioEntity:
        self.nodes[node.id] = node
        return node

    def add_relationship(self, rel: PortfolioRelationship) -> PortfolioRelationship:
        if rel.source_id not in self.nodes or rel.target_id not in self.nodes:
            raise ValueError(f"relationship endpoints missing: {rel.id}")
        self.relationships[rel.id] = rel
        return rel

    def nodes_by_type(self, node_type: str) -> List[PortfolioEntity]:
        return [n for n in self.nodes.values() if n.type == node_type]

    def to_dict(self) -> dict[str, Any]:
        ip = self.institutional_portfolio
        return {
            "graph_id": self.graph_id,
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "version": self.version,
            "engine_version": self.engine_version,
            "generated_at": self.generated_at,
            "scope": self.scope,
            "portfolio_node_id": self.portfolio_node_id,
            "lineage": list(self.lineage),
            "entity_count": len(self.nodes),
            "relationship_count": len(self.relationships),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "relationships": [r.to_dict() for r in self.relationships.values()],
            "institutional_portfolio": ip.to_dict() if ip else None,
            "meta": dict(self.meta or {}),
            "llm": False,
        }


def _graph_id(portfolio_id: str, tickers: Sequence[str]) -> str:
    raw = f"{portfolio_id}|{'|'.join(sorted(tickers))}|{PKG_VERSION}"
    return f"pkg-{portfolio_id.lower()}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def build_portfolio_graph(
    *,
    portfolio_id: str,
    name: str,
    holdings: Sequence[HoldingRecord],
    cash_weight: float = 0.0,
    base_currency: str = "INR",
    as_of: str | None = None,
) -> PortfolioKnowledgeGraph:
    """
    Build Portfolio → Company → Sector/Decision/Exposure graph.

    Deterministic. No LLM. No portfolio optimisation.
    """
    ts = as_of or now_iso()
    holds = tuple(sorted(holdings, key=lambda h: h.ticker))
    gid = _graph_id(portfolio_id, [h.ticker for h in holds])
    g = PortfolioKnowledgeGraph(
        portfolio_id=portfolio_id,
        graph_id=gid,
        name=name,
        generated_at=ts,
    )

    portfolio_node = make_entity(
        portfolio_id,
        "Portfolio",
        portfolio_id,
        name or portfolio_id,
        timestamp=ts,
        confidence=0.95,
        attributes={
            "holding_count": len(holds),
            "cash_weight": float(cash_weight),
            "base_currency": base_currency,
        },
    )
    g.add_node(portfolio_node)
    g.portfolio_node_id = portfolio_node.id

    if cash_weight > 0:
        cash_node = make_entity(
            portfolio_id,
            "Cash",
            "cash",
            f"Cash {cash_weight:.1%}",
            timestamp=ts,
            attributes={"weight": float(cash_weight), "currency": base_currency},
        )
        g.add_node(cash_node)
        g.add_relationship(
            make_relationship(
                portfolio_id,
                portfolio_node.id,
                cash_node.id,
                "allocates",
                label="cash allocation",
                weight=float(cash_weight),
                strength=float(cash_weight),
            )
        )

    company_nodes: dict[str, PortfolioEntity] = {}
    sector_nodes: dict[str, PortfolioEntity] = {}
    country_nodes: dict[str, PortfolioEntity] = {}
    decision_nodes: dict[str, PortfolioEntity] = {}

    for h in holds:
        company = make_entity(
            portfolio_id,
            "Company",
            h.ticker,
            h.company or h.ticker,
            timestamp=ts,
            confidence=max(0.5, min(0.99, (h.confidence or 70) / 100.0)),
            attributes=h.to_dict(),
        )
        g.add_node(company)
        company_nodes[h.ticker] = company

        holding_node = make_entity(
            portfolio_id,
            "Holding",
            h.ticker,
            f"{h.ticker} {h.weight:.1%}",
            timestamp=ts,
            attributes={"ticker": h.ticker, "weight": h.weight, "market_value": h.market_value},
        )
        g.add_node(holding_node)

        alloc_node = make_entity(
            portfolio_id,
            "Allocation",
            h.ticker,
            f"Allocation {h.ticker}",
            timestamp=ts,
            attributes={"ticker": h.ticker, "weight": h.weight},
        )
        g.add_node(alloc_node)

        g.add_relationship(
            make_relationship(
                portfolio_id,
                portfolio_node.id,
                holding_node.id,
                "holds",
                label=f"holds {h.ticker}",
                weight=h.weight,
                strength=h.weight,
            )
        )
        g.add_relationship(
            make_relationship(
                portfolio_id,
                holding_node.id,
                company.id,
                "belongs_to",
                label=f"{h.ticker} company",
                weight=h.weight,
                strength=0.9,
            )
        )
        g.add_relationship(
            make_relationship(
                portfolio_id,
                portfolio_node.id,
                alloc_node.id,
                "allocates",
                label=f"allocates {h.weight:.1%} to {h.ticker}",
                weight=h.weight,
                strength=h.weight,
            )
        )
        g.add_relationship(
            make_relationship(
                portfolio_id,
                alloc_node.id,
                company.id,
                "belongs_to",
                label=f"allocation → {h.ticker}",
                weight=h.weight,
                strength=0.85,
            )
        )

        if h.sector:
            if h.sector not in sector_nodes:
                sector_nodes[h.sector] = g.add_node(
                    make_entity(
                        portfolio_id,
                        "Sector",
                        h.sector,
                        h.sector,
                        timestamp=ts,
                        attributes={"sector": h.sector},
                    )
                )
            g.add_relationship(
                make_relationship(
                    portfolio_id,
                    company.id,
                    sector_nodes[h.sector].id,
                    "belongs_to",
                    label=f"{h.ticker} ∈ {h.sector}",
                    weight=h.weight,
                    strength=0.8,
                )
            )
            g.add_relationship(
                make_relationship(
                    portfolio_id,
                    portfolio_node.id,
                    sector_nodes[h.sector].id,
                    "exposes",
                    label=f"sector exposure {h.sector}",
                    weight=h.weight,
                    strength=h.weight,
                    inferred=True,
                )
            )

        if h.country:
            if h.country not in country_nodes:
                country_nodes[h.country] = g.add_node(
                    make_entity(
                        portfolio_id,
                        "Country",
                        h.country,
                        h.country,
                        timestamp=ts,
                        attributes={"country": h.country},
                    )
                )
            g.add_relationship(
                make_relationship(
                    portfolio_id,
                    company.id,
                    country_nodes[h.country].id,
                    "belongs_to",
                    label=f"{h.ticker} ∈ {h.country}",
                    weight=h.weight,
                    strength=0.7,
                )
            )

        if h.recommendation:
            dkey = f"{h.ticker}:{h.recommendation}"
            decision_nodes[dkey] = g.add_node(
                make_entity(
                    portfolio_id,
                    "Decision",
                    dkey,
                    f"{h.ticker} {h.recommendation}",
                    timestamp=ts,
                    confidence=max(0.5, min(0.99, (h.confidence or 70) / 100.0)),
                    attributes={
                        "ticker": h.ticker,
                        "recommendation": h.recommendation,
                        "confidence": h.confidence,
                        "decision_id": h.decision_id,
                    },
                )
            )
            g.add_relationship(
                make_relationship(
                    portfolio_id,
                    company.id,
                    decision_nodes[dkey].id,
                    "decides",
                    label=f"{h.ticker} → {h.recommendation}",
                    strength=0.9,
                    weight=h.weight,
                )
            )

    # Correlation edges (inferred)
    corr_edges = compute_correlations(holds)
    for edge in corr_edges:
        a = company_nodes.get(edge.ticker_a)
        b = company_nodes.get(edge.ticker_b)
        if not a or not b:
            continue
        corr_node = make_entity(
            portfolio_id,
            "Correlation",
            f"{edge.ticker_a}:{edge.ticker_b}",
            f"ρ {edge.ticker_a}/{edge.ticker_b}={edge.score:.2f}",
            timestamp=ts,
            confidence=0.65,
            attributes=edge.to_dict(),
        )
        g.add_node(corr_node)
        g.add_relationship(
            make_relationship(
                portfolio_id,
                a.id,
                corr_node.id,
                "correlates_with",
                label=f"{edge.ticker_a} correlates",
                strength=edge.score,
                inferred=True,
                attributes=edge.to_dict(),
            )
        )
        g.add_relationship(
            make_relationship(
                portfolio_id,
                corr_node.id,
                b.id,
                "correlates_with",
                label=f"with {edge.ticker_b}",
                strength=edge.score,
                inferred=True,
                attributes=edge.to_dict(),
            )
        )

    allocations = build_allocations(holds)
    exposures = compute_exposures(holds)
    risks = concentration_risks(holds, exposures)
    for risk in risks:
        rn = make_entity(
            portfolio_id,
            "Risk",
            risk.kind + ":" + risk.label,
            risk.label,
            timestamp=ts,
            attributes=risk.to_dict(),
        )
        g.add_node(rn)
        g.add_relationship(
            make_relationship(
                portfolio_id,
                portfolio_node.id,
                rn.id,
                "concentrates" if "concentration" in risk.kind else "pressures",
                label=risk.label,
                strength=min(1.0, float(risk.score)),
                inferred=True,
            )
        )

    decisions = tuple(
        DecisionSummary(
            ticker=h.ticker,
            recommendation=h.recommendation,
            confidence=h.confidence,
            decision_id=h.decision_id,
        )
        for h in holds
        if h.recommendation
    )

    ip = InstitutionalPortfolio(
        portfolio_id=portfolio_id,
        name=name,
        holdings=holds,
        allocations=allocations,
        exposures=exposures,
        risks=risks,
        decisions=decisions,
        cash_weight=float(cash_weight),
        base_currency=base_currency,
        graph_id=gid,
        version=PKG_VERSION,
        as_of=ts,
    )
    g.institutional_portfolio = ip
    g.meta = {
        "concentration": compute_concentration(holds),
        "average_correlation": average_correlation(corr_edges),
        "sector_exposures": [e.to_dict() for e in exposures_by_dimension(exposures, "sector")],
        "recommendation_mix": [
            e.to_dict() for e in exposures_by_dimension(exposures, "recommendation")
        ],
        "correlation_count": len(corr_edges),
        "company_graph_ids": {
            h.ticker: h.company_graph_id for h in holds if h.company_graph_id
        },
    }
    return g
