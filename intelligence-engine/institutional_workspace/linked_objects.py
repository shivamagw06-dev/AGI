"""RW-01 linked objects — clickable lineage navigation."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from institutional_workspace.models import LinkedObject


def _href(object_type: str, object_id: str, *, ticker: str = "", portfolio_id: str = "") -> str:
    if object_type == "CompanyDecision" and ticker:
        return f"/agi/companies/{quote(ticker)}?tab=decision"
    if object_type == "PortfolioRisk" and portfolio_id:
        return f"/agi/portfolio?focus=risk&portfolio={quote(portfolio_id)}"
    if object_type == "PolicyAssessment" and portfolio_id:
        return f"/agi/portfolio?focus=policy&portfolio={quote(portfolio_id)}"
    if object_type == "PortfolioDecision" and portfolio_id:
        return f"/agi/portfolio?focus=decision&portfolio={quote(portfolio_id)}"
    if object_type == "CommitteeResolution":
        return "/agi/committee"
    if object_type == "Evidence" and ticker:
        return f"/agi/companies/{quote(ticker)}?tab=evidence_references"
    if object_type == "Forecast" and ticker:
        return f"/agi/companies/{quote(ticker)}?tab=forecast"
    if object_type == "Observation" and ticker:
        return f"/agi/companies/{quote(ticker)}?tab=overview"
    if object_type == "KnowledgeGraph" and ticker:
        return f"/agi/companies/{quote(ticker)}?tab=knowledge_graph"
    if object_type == "ResearchNote":
        return f"/agi/research?note={quote(object_id)}"
    if ticker:
        return f"/agi/companies/{quote(ticker)}"
    if portfolio_id:
        return f"/agi/portfolio?portfolio={quote(portfolio_id)}"
    return f"/agi/research?object={quote(object_id)}"


def build_linked_objects(
    *,
    ticker: str = "",
    portfolio_id: str = "",
    company_decision: dict[str, Any] | None = None,
    portfolio_risk: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    portfolio_decision: dict[str, Any] | None = None,
    committee: dict[str, Any] | None = None,
) -> tuple[LinkedObject, ...]:
    links: list[LinkedObject] = []

    def add(object_type: str, object_id: str, label: str, relation: str, summary: str = "") -> None:
        if not object_id and not label:
            return
        links.append(
            LinkedObject(
                object_type=object_type,
                object_id=object_id or object_type.lower(),
                label=label,
                href=_href(object_type, object_id or object_type, ticker=ticker, portfolio_id=portfolio_id),
                relation=relation,
                summary=summary,
            )
        )

    if company_decision:
        add(
            "CompanyDecision",
            str(company_decision.get("decision_id") or ticker),
            f"Company decision {company_decision.get('recommendation') or ''}".strip(),
            "decision",
            str(company_decision.get("note") or ""),
        )
    if portfolio_risk:
        add(
            "PortfolioRisk",
            str(portfolio_risk.get("risk_id") or ""),
            f"Portfolio risk {portfolio_risk.get('overall_risk') or ''}".strip(),
            "risk",
        )
    if policy:
        add(
            "PolicyAssessment",
            str(policy.get("policy_id") or ""),
            f"Policy {policy.get('overall_status') or ''}".strip(),
            "policy",
        )
    if portfolio_decision:
        add(
            "PortfolioDecision",
            str(portfolio_decision.get("decision_id") or ""),
            f"Portfolio decision {portfolio_decision.get('recommendation') or ''}".strip(),
            "decision",
            str(portfolio_decision.get("rule_path") or ""),
        )
    if committee:
        add(
            "CommitteeResolution",
            str(committee.get("resolution_id") or ""),
            f"Committee {committee.get('status') or ''}".strip(),
            "committee",
            str(committee.get("outcome") or ""),
        )

    if ticker:
        add("Evidence", f"evidence-{ticker}", "Evidence browser", "evidence")
        add("Forecast", f"forecast-{ticker}", "Forecast", "forecast")
        add("KnowledgeGraph", f"kg-{ticker}", "Knowledge graph", "graph")
        add("Observation", f"obs-{ticker}", "Observations", "observation")

    # Lineage order hint as relations chain
    order = [
        "Evidence",
        "CompanyDecision",
        "PortfolioRisk",
        "PolicyAssessment",
        "PortfolioDecision",
        "CommitteeResolution",
    ]
    links.sort(key=lambda o: order.index(o.object_type) if o.object_type in order else 99)
    return tuple(links)
