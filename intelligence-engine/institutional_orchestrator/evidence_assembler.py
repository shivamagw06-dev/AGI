"""UAG-01 evidence assembler — lineage references from consulted objects."""

from __future__ import annotations

from typing import Any

from institutional_orchestrator.models import EvidenceRef
from institutional_orchestrator.schema import LINEAGE_CHAIN


def assemble_evidence(payloads: dict[str, Any]) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = []

    comparison = (payloads.get("ComparisonEvidence") or {}).get("payload") or {}
    if comparison.get("available"):
        for company in (comparison.get("companies") or [])[:5]:
            symbol = str(company.get("symbol") or "company")
            sources = ", ".join(company.get("sources") or []) or "warehouse"
            as_of = company.get("as_of") or "not supplied"
            refs.append(
                EvidenceRef(
                    object_type="ComparisonEvidence",
                    object_id=symbol,
                    label=f"Verified warehouse facts: {symbol}",
                    snippet=f"Source: {sources}; as of: {as_of}",
                    provider="institutional_warehouse",
                )
            )

    cd = payloads.get("CompanyDecision", {}).get("payload") or {}
    if cd:
        ticker = str(cd.get("ticker") or payloads.get("CompanyDecision", {}).get("ticker") or "")
        rec = cd.get("recommendation") or (cd.get("decision") or {}).get("recommendation")
        refs.append(
            EvidenceRef(
                object_type="CompanyDecision",
                object_id=str(cd.get("decision_id") or ticker or "company"),
                label=f"Company decision {ticker}".strip(),
                snippet=str(rec or cd.get("note") or "Company decision object consulted"),
                provider="institutional_decision",
            )
        )

    risk = (payloads.get("PortfolioRisk", {}) or {}).get("payload") or {}
    risk_obj = risk.get("risk") or risk
    if risk_obj and risk.get("ok", True):
        refs.append(
            EvidenceRef(
                object_type="PortfolioRisk",
                object_id=str(risk_obj.get("risk_id") or "risk"),
                label=f"Portfolio risk {risk_obj.get('overall_risk') or ''}".strip(),
                snippet=(
                    f"Concentration {(risk_obj.get('concentration') or {}).get('level')}; "
                    f"warnings={len(risk_obj.get('warnings') or [])}"
                ),
                provider="institutional_portfolio_risk",
            )
        )

    policy = (payloads.get("PolicyAssessment", {}) or {}).get("payload") or {}
    assessment = policy.get("assessment") or policy
    if assessment and policy.get("ok", True):
        refs.append(
            EvidenceRef(
                object_type="PolicyAssessment",
                object_id=str(assessment.get("policy_id") or "policy"),
                label=f"Policy {assessment.get('overall_status') or ''}".strip(),
                snippet=f"Violations={assessment.get('violation_count') or len(assessment.get('violations') or [])}",
                provider="institutional_policy",
            )
        )

    decision = (payloads.get("PortfolioDecision", {}) or {}).get("payload") or {}
    dobj = decision.get("decision") or decision
    if dobj and decision.get("ok", True):
        refs.append(
            EvidenceRef(
                object_type="PortfolioDecision",
                object_id=str(dobj.get("decision_id") or "cio"),
                label=f"Portfolio decision: {dobj.get('recommendation') or ''}".strip(),
                snippet=str(dobj.get("rule_path") or dobj.get("investment_posture") or ""),
                provider="institutional_portfolio_decision",
            )
        )

    committee = (payloads.get("CommitteeResolution", {}) or {}).get("payload") or {}
    res = committee.get("resolution") or committee
    if res and committee.get("ok", True):
        refs.append(
            EvidenceRef(
                object_type="CommitteeResolution",
                object_id=str(res.get("resolution_id") or "ice"),
                label=f"Committee: {res.get('status') or ''}".strip(),
                snippet=str(res.get("outcome") or ""),
                provider="institutional_committee",
            )
        )

    for key in ("Observation", "Forecast", "Research", "PortfolioGraph"):
        block = payloads.get(key) or {}
        if not block:
            continue
        payload = block.get("payload") or {}
        refs.append(
            EvidenceRef(
                object_type=key,
                object_id=str(payload.get("id") or key.lower()),
                label=key,
                snippet=str(payload.get("note") or payload.get("status") or "consulted"),
                provider=str(block.get("object_type") or key),
            )
        )

    return tuple(refs)


def lineage_for_response(payloads: dict[str, Any]) -> tuple[str, ...]:
    present = set(payloads.keys())
    chain = []
    mapping = {
        "Evidence": "Research",
        "Reason": "Research",
        "Company Decision": "CompanyDecision",
        "Portfolio Risk": "PortfolioRisk",
        "Policy Assessment": "PolicyAssessment",
        "Portfolio Decision": "PortfolioDecision",
        "Committee Resolution": "CommitteeResolution",
    }
    for label in LINEAGE_CHAIN:
        ot = mapping.get(label)
        if ot and ot in present:
            chain.append(label)
        elif label == "Evidence" and ("Research" in present or "Observation" in present or "ComparisonEvidence" in present):
            chain.append(label)
    # Always show full institutional chain labels that were consulted
    if not chain:
        return LINEAGE_CHAIN
    # Fill remaining known labels for transparency
    for label in LINEAGE_CHAIN:
        if label not in chain and mapping.get(label) in present:
            chain.append(label)
    return tuple(dict.fromkeys(chain)) or LINEAGE_CHAIN
