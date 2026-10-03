"""PUB-01 source retrieval — soft-read immutable institutional objects. Compose only."""

from __future__ import annotations

from typing import Any

from institutional_publishing.models import EvidenceRef, SourceObjectRef


def _ref(object_type: str, object_id: str, label: str = "", provider: str = "") -> SourceObjectRef:
    return SourceObjectRef(
        object_type=object_type,
        object_id=object_id or object_type.lower(),
        label=label or object_type,
        provider=provider,
    )


def collect_sources(
    required: tuple[str, ...],
    *,
    ticker: str = "",
    portfolio_id: str = "agi-core-equity",
    policy: str = "family_office",
) -> tuple[list[SourceObjectRef], list[EvidenceRef], dict[str, Any]]:
    """Retrieve source payloads without interpreting or inventing recommendations."""
    refs: list[SourceObjectRef] = []
    evidence: list[EvidenceRef] = []
    payloads: dict[str, Any] = {}
    t = str(ticker or "").upper().strip()
    pid = str(portfolio_id or "agi-core-equity")

    for object_type in required:
        ot = str(object_type)
        if ot == "CompanyDecision":
            payload = _soft_company_decision(t or "AXISBANK")
            oid = str(payload.get("decision_id") or t or "company-decision")
            refs.append(_ref(ot, oid, f"Company decision {t}", "institutional_decision"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=f"ev-{oid}",
                    label=f"CompanyDecision:{oid}",
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("recommendation") or payload.get("note") or "referential"),
                )
            )
        elif ot == "PortfolioRisk":
            payload = _soft_portfolio_risk(pid)
            oid = str(payload.get("risk_id") or f"risk-{pid}")
            refs.append(_ref(ot, oid, "Portfolio risk", "institutional_portfolio_risk"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=f"ev-{oid}",
                    label=f"PortfolioRisk:{oid}",
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("overall_risk") or "risk object"),
                )
            )
        elif ot == "PolicyAssessment":
            payload = _soft_policy(pid, policy)
            oid = str(payload.get("policy_id") or f"policy-{pid}")
            refs.append(_ref(ot, oid, "Policy assessment", "institutional_policy"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=f"ev-{oid}",
                    label=f"PolicyAssessment:{oid}",
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("overall_status") or "policy object"),
                )
            )
        elif ot == "PortfolioDecision":
            payload = _soft_portfolio_decision(pid, policy)
            oid = str(payload.get("decision_id") or f"pd-{pid}")
            refs.append(_ref(ot, oid, "Portfolio decision", "institutional_portfolio_decision"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=f"ev-{oid}",
                    label=f"PortfolioDecision:{oid}",
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("recommendation") or "portfolio decision object"),
                )
            )
        elif ot == "CommitteeResolution":
            payload = _soft_committee(pid, policy)
            oid = str(payload.get("resolution_id") or f"cr-{pid}")
            refs.append(_ref(ot, oid, "Committee resolution", "institutional_committee"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=f"ev-{oid}",
                    label=f"CommitteeResolution:{oid}",
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("status") or payload.get("outcome") or "committee object"),
                )
            )
        elif ot == "Observation":
            payload = _soft_observation(t, pid)
            oid = str(payload.get("observation_id") or f"obs-{t or pid}")
            refs.append(_ref(ot, oid, "Observation", "institutional_observation"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=f"ev-{oid}",
                    label=f"Observation:{oid}",
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("title") or payload.get("summary") or "observation"),
                )
            )
        elif ot == "Evidence":
            payload = _soft_evidence(t)
            oid = str(payload.get("evidence_id") or f"evidence-{t or 'desk'}")
            refs.append(_ref(ot, oid, "Evidence pack", "evidence"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=oid,
                    label=str(payload.get("title") or "Evidence"),
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("snippet") or ""),
                )
            )
        elif ot == "Macro":
            payload = _soft_macro()
            oid = str(payload.get("macro_id") or "macro-desk")
            refs.append(_ref(ot, oid, "Macro context", "macro"))
            payloads[ot] = payload
            evidence.append(
                EvidenceRef(
                    evidence_id=f"ev-{oid}",
                    label=f"Macro:{oid}",
                    object_ref=f"{ot}:{oid}",
                    snippet=str(payload.get("summary") or "macro context"),
                )
            )
        elif ot == "Relationship":
            payload = _soft_relationships(t)
            oid = str(payload.get("relationship_pack_id") or f"rel-{t}")
            refs.append(_ref(ot, oid, "Cross-company relationships", "institutional_cross_company"))
            payloads[ot] = payload
        else:
            refs.append(_ref(ot, f"soft-{ot.lower()}", ot, "soft"))
            payloads[ot] = {"available": False, "object_type": ot}

    return refs, evidence, payloads


def _soft_company_decision(ticker: str) -> dict[str, Any]:
    try:
        from institutional_decision.production import get_decision  # type: ignore

        out = get_decision(ticker)
        if isinstance(out, dict):
            d = out.get("decision") or out
            if isinstance(d, dict):
                return {**d, "ticker": ticker, "available": True}
    except Exception:
        pass
    return {
        "ticker": ticker,
        "decision_id": f"soft-cd-{ticker}",
        "recommendation": "",
        "note": "Company decision soft-unavailable; publication composes placeholder reference only",
        "available": False,
    }


def _soft_portfolio_risk(portfolio_id: str) -> dict[str, Any]:
    try:
        from institutional_portfolio_risk.production import evaluate_portfolio_risk

        r = evaluate_portfolio_risk({"portfolio_id": portfolio_id})
        if r.get("ok") and isinstance(r.get("risk"), dict):
            return {**r["risk"], "available": True}
    except Exception:
        pass
    return {
        "risk_id": f"soft-risk-{portfolio_id}",
        "portfolio_id": portfolio_id,
        "overall_risk": "",
        "available": False,
        "note": "Portfolio risk soft-unavailable",
    }


def _soft_policy(portfolio_id: str, policy: str) -> dict[str, Any]:
    try:
        from institutional_policy.production import check_policy

        p = check_policy({"portfolio_id": portfolio_id, "policy": policy})
        if p.get("ok") and isinstance(p.get("assessment"), dict):
            return {**p["assessment"], "available": True}
    except Exception:
        pass
    return {
        "policy_id": f"soft-policy-{portfolio_id}",
        "overall_status": "",
        "available": False,
        "note": "Policy soft-unavailable",
    }


def _soft_portfolio_decision(portfolio_id: str, policy: str) -> dict[str, Any]:
    try:
        from institutional_portfolio_decision.production import decide_portfolio

        d = decide_portfolio({"portfolio_id": portfolio_id, "policy": policy})
        if d.get("ok") and isinstance(d.get("decision"), dict):
            return {**d["decision"], "available": True}
    except Exception:
        pass
    return {
        "decision_id": f"soft-pd-{portfolio_id}",
        "recommendation": "",
        "available": False,
        "note": "Portfolio decision soft-unavailable",
    }


def _soft_committee(portfolio_id: str, policy: str) -> dict[str, Any]:
    try:
        from institutional_committee.production import review_committee

        c = review_committee({"portfolio_id": portfolio_id, "policy": policy})
        if c.get("ok") and isinstance(c.get("resolution"), dict):
            return {**c["resolution"], "available": True}
    except Exception:
        pass
    return {
        "resolution_id": f"soft-cr-{portfolio_id}",
        "status": "",
        "outcome": "",
        "available": False,
        "note": "Committee soft-unavailable",
    }


def _soft_observation(ticker: str, portfolio_id: str) -> dict[str, Any]:
    subject = ticker or portfolio_id
    return {
        "observation_id": f"obs-{subject.lower()}",
        "title": f"Desk observation — {subject}",
        "summary": "Composed from institutional observation slot; no new analysis by PUB-01",
        "severity": "info",
        "available": True,
        "system_generated_by_pub": False,
    }


def _soft_evidence(ticker: str) -> dict[str, Any]:
    return {
        "evidence_id": f"evidence-{ticker.lower() or 'desk'}",
        "title": f"Evidence pack — {ticker or 'desk'}",
        "snippet": "Referential evidence slot for publication composition",
        "available": True,
    }


def _soft_macro() -> dict[str, Any]:
    return {
        "macro_id": "macro-desk",
        "summary": "Macro context slot for briefs — sourced referentially, not forecast by PUB-01",
        "drivers": ["interest_rates", "fx", "gdp"],
        "available": True,
    }


def _soft_relationships(ticker: str) -> dict[str, Any]:
    if not ticker:
        return {"relationship_pack_id": "rel-none", "available": False}
    try:
        from institutional_cross_company.production import get_company_relationships

        out = get_company_relationships(ticker)
        return {
            "relationship_pack_id": f"rel-{ticker}",
            "competitors": out.get("competitors") or [],
            "macro_drivers": out.get("macro_drivers") or [],
            "available": bool(out.get("ok")),
            "owns_graph": False,
        }
    except Exception:
        return {"relationship_pack_id": f"rel-{ticker}", "available": False}
