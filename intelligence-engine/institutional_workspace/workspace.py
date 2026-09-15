"""RW-01 workspace assembly — company / portfolio / committee contexts."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Optional

from institutional_workspace.diagnostics import build_diagnostics
from institutional_workspace.evidence_browser import browse_evidence
from institutional_workspace.linked_objects import build_linked_objects
from institutional_workspace.models import InstitutionalWorkspace
from institutional_workspace.navigation import ask_deep_link, navigation_items
from institutional_workspace import notes as notes_mod
from institutional_workspace.schema import (
    COMPANY_SECTIONS,
    NAVIGATION,
    PORTFOLIO_SECTIONS,
    WORKSPACE_ENGINE_VERSION,
)
from institutional_workspace.timeline import build_timeline

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _wid(context: str, subject: str) -> str:
    raw = f"{context}|{subject}|{WORKSPACE_ENGINE_VERSION}"
    return f"rw-{context}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _soft_company_decision(ticker: str) -> dict[str, Any]:
    try:
        from institutional_decision.production import get_decision  # type: ignore

        out = get_decision(ticker)
        if isinstance(out, dict):
            return out.get("decision") or out
    except Exception:
        pass
    return {
        "ticker": ticker,
        "recommendation": "",
        "decision_id": f"soft-{ticker}",
        "note": "Company decision soft-unavailable",
        "available": False,
    }


def _soft_portfolio_stack(portfolio_id: str) -> dict[str, Any]:
    out: dict[str, Any] = {"risk": None, "policy": None, "decision": None, "committee": None}
    try:
        from institutional_portfolio_risk.production import evaluate_portfolio_risk

        r = evaluate_portfolio_risk({"portfolio_id": portfolio_id})
        if r.get("ok"):
            out["risk"] = r.get("risk")
    except Exception:
        pass
    try:
        from institutional_policy.production import check_policy

        p = check_policy({"portfolio_id": portfolio_id, "policy": "family_office"})
        if p.get("ok"):
            out["policy"] = p.get("assessment")
    except Exception:
        pass
    try:
        from institutional_portfolio_decision.production import decide_portfolio

        d = decide_portfolio({"portfolio_id": portfolio_id, "policy": "family_office"})
        if d.get("ok"):
            out["decision"] = d.get("decision")
    except Exception:
        pass
    try:
        from institutional_committee.production import review_committee

        c = review_committee({"portfolio_id": portfolio_id, "policy": "family_office"})
        if c.get("ok"):
            out["committee"] = c.get("resolution")
    except Exception:
        pass
    return out


def assemble_company_workspace(ticker: str, *, focus: str = "overview") -> InstitutionalWorkspace:
    t = str(ticker or "").upper().strip() or "AXISBANK"
    decision = _soft_company_decision(t)
    # Soft pull portfolio stack for linkage when company appears in AGI core book
    stack = _soft_portfolio_stack("agi-core-equity")
    evidence = browse_evidence(
        ticker=t,
        linked_decision_id=str(decision.get("decision_id") or ""),
        linked_risk_id=str((stack.get("risk") or {}).get("risk_id") or ""),
    )
    timeline = build_timeline(
        context="company",
        subject_id=t,
        company_decision=decision,
        portfolio_risk=stack.get("risk"),
        policy=stack.get("policy"),
        portfolio_decision=stack.get("decision"),
        committee=stack.get("committee"),
        evidence=[e.to_dict() for e in evidence[:3]],
    )
    linked = build_linked_objects(
        ticker=t,
        portfolio_id="agi-core-equity",
        company_decision=decision,
        portfolio_risk=stack.get("risk"),
        policy=stack.get("policy"),
        portfolio_decision=stack.get("decision"),
        committee=stack.get("committee"),
    )
    context_key = f"company:{t}"
    note_rows = notes_mod.seed_demo_notes(context_key, ticker=t)

    sections = {k: {"status": "available" if k != focus else "active"} for k in COMPANY_SECTIONS}
    sections["overview"] = {
        "title": t,
        "headline": f"Living research workspace for {t}",
        "recommendation": decision.get("recommendation") or "—",
        "story": (
            f"Complete investment story for {t}: decisions, evidence, forecasts, "
            "portfolio exposure, policy, and committee outcomes — linked, not a static report."
        ),
    }
    sections["decision_history"] = {"latest": decision}
    sections["risk"] = {"portfolio_risk": stack.get("risk")}
    sections["forecast"] = {"status": "soft"}
    sections["observations"] = {"status": "soft"}
    sections["evidence"] = {"count": len(evidence)}
    sections["timeline"] = {"count": len(timeline)}
    sections["research_notes"] = {"count": len(note_rows)}

    missing = []
    if not decision.get("recommendation"):
        missing.append("CompanyDecision.recommendation")
    if not stack.get("risk"):
        missing.append("PortfolioRisk")

    ws = InstitutionalWorkspace(
        workspace_id=_wid("company", t),
        context="company",
        active_object=focus or "overview",
        title=f"{t} Research Workspace",
        timeline=timeline,
        linked_objects=linked,
        sections=sections,
        evidence=evidence,
        notes=note_rows,
        navigation=navigation_items(context="company", ticker=t),
        ask_deep_link=ask_deep_link(ticker=t, question=f"Why did the recommendation change for {t}?"),
        diagnostics=None,
        generated_at=now_iso(),
        ticker=t,
        portfolio_id="",
    )
    return replace(ws, diagnostics=build_diagnostics(ws, missing_links=missing))


def assemble_portfolio_workspace(
    portfolio_id: str = "agi-core-equity",
    *,
    focus: str = "overview",
) -> InstitutionalWorkspace:
    pid = str(portfolio_id or "agi-core-equity").strip()
    if pid in {"default", "DEFAULT"}:
        pid = "agi-core-equity"
    stack = _soft_portfolio_stack(pid)
    evidence = browse_evidence(
        portfolio_id=pid,
        linked_decision_id=str((stack.get("decision") or {}).get("decision_id") or ""),
        linked_risk_id=str((stack.get("risk") or {}).get("risk_id") or ""),
    )
    timeline = build_timeline(
        context="portfolio",
        subject_id=pid,
        portfolio_risk=stack.get("risk"),
        policy=stack.get("policy"),
        portfolio_decision=stack.get("decision"),
        committee=stack.get("committee"),
        evidence=[e.to_dict() for e in evidence[:2]],
    )
    linked = build_linked_objects(
        portfolio_id=pid,
        portfolio_risk=stack.get("risk"),
        policy=stack.get("policy"),
        portfolio_decision=stack.get("decision"),
        committee=stack.get("committee"),
    )
    context_key = f"portfolio:{pid}"
    note_rows = notes_mod.seed_demo_notes(context_key, portfolio_id=pid)

    sections = {k: {"status": "available"} for k in PORTFOLIO_SECTIONS}
    sections["overview"] = {
        "portfolio_id": pid,
        "headline": "Portfolio research workspace",
        "overall_risk": (stack.get("risk") or {}).get("overall_risk"),
        "policy_status": (stack.get("policy") or {}).get("overall_status"),
        "recommendation": (stack.get("decision") or {}).get("recommendation"),
        "committee_status": (stack.get("committee") or {}).get("status"),
    }
    sections["risk"] = stack.get("risk") or {}
    sections["policy"] = stack.get("policy") or {}
    sections["decision"] = stack.get("decision") or {}
    sections["committee"] = stack.get("committee") or {}
    sections["holdings"] = {"source": "PKG-01"}
    sections["scenario_analysis"] = {"status": "future"}

    missing = [k for k, v in (("PortfolioRisk", stack.get("risk")), ("PolicyAssessment", stack.get("policy")), ("PortfolioDecision", stack.get("decision")), ("CommitteeResolution", stack.get("committee"))) if not v]

    ws = InstitutionalWorkspace(
        workspace_id=_wid("portfolio", pid),
        context="portfolio",
        active_object=focus or "overview",
        title=f"{pid} Portfolio Workspace",
        timeline=timeline,
        linked_objects=linked,
        sections=sections,
        evidence=evidence,
        notes=note_rows,
        navigation=navigation_items(context="portfolio", portfolio_id=pid),
        ask_deep_link=ask_deep_link(
            portfolio_id=pid,
            question="Which holdings should I reduce?",
        ),
        diagnostics=None,
        generated_at=now_iso(),
        ticker="",
        portfolio_id=pid,
    )
    return replace(ws, diagnostics=build_diagnostics(ws, missing_links=missing))


def assemble_committee_workspace() -> InstitutionalWorkspace:
    stack = _soft_portfolio_stack("agi-core-equity")
    committee = stack.get("committee") or {}
    linked = build_linked_objects(
        portfolio_id="agi-core-equity",
        portfolio_risk=stack.get("risk"),
        policy=stack.get("policy"),
        portfolio_decision=stack.get("decision"),
        committee=committee,
    )
    timeline = build_timeline(
        context="committee",
        subject_id="agi-investment-committee",
        portfolio_risk=stack.get("risk"),
        policy=stack.get("policy"),
        portfolio_decision=stack.get("decision"),
        committee=committee,
    )
    evidence = browse_evidence(portfolio_id="agi-core-equity")
    ws = InstitutionalWorkspace(
        workspace_id=_wid("committee", "agi"),
        context="committee",
        active_object="committee",
        title="Investment Committee Workspace",
        timeline=timeline,
        linked_objects=linked,
        sections={
            "overview": {
                "status": committee.get("status"),
                "outcome": committee.get("outcome"),
                "recommendation": committee.get("decision_recommendation"),
            }
        },
        evidence=evidence,
        notes=notes_mod.seed_demo_notes("committee:agi", portfolio_id="agi-core-equity"),
        navigation=NAVIGATION,
        ask_deep_link=ask_deep_link(question="Why was this deferred?"),
        diagnostics=None,
        generated_at=now_iso(),
        portfolio_id="agi-core-equity",
    )
    return replace(ws, diagnostics=build_diagnostics(ws))
