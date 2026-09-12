"""UAG-01 response builder — assemble structured answers from retrieved objects."""

from __future__ import annotations

from typing import Any

from institutional_orchestrator.evidence_assembler import assemble_evidence, lineage_for_response
from institutional_orchestrator.models import (
    ExecutionStep,
    InstitutionalQuery,
    InstitutionalResponse,
)


def _value(value: Any, *, decimals: int = 2) -> str:
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "not reported"


def _money(value: Any, row: dict[str, Any]) -> str:
    """Use Indian units only for warehouse rows with verified normalisation."""
    meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
    method = str(meta.get("unit_method") or "").lower()
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "not reported"
    is_capiq = str(row.get("statement_version") or "").startswith("capiq_workbook_")
    if is_capiq or method in {"declared", "source_default", "assumed_canonical"} or "normal" in method:
        # Warehouse canonical currency is INR million; 10 million INR = 1 crore.
        return f"₹{amount / 10:,.1f} crore"
    return f"{amount:,.2f} (source units)"


def _year_number(value: Any) -> int | None:
    import re

    found = re.search(r"(\d{2,4})", str(value or ""))
    if not found:
        return None
    year = int(found.group(1))
    return year + 2000 if year < 100 else year


def _ten_year_summary(company: dict[str, Any]) -> str | None:
    """Render a factual decade trend from the canonical annual series."""
    history = [
        row for row in (company.get("annual_history") or [])
        if row.get("pat") is not None and _year_number(row.get("fiscal_year")) is not None
    ]
    if len(history) < 2:
        return None
    start, end = history[0], history[-1]
    start_year, end_year = _year_number(start.get("fiscal_year")), _year_number(end.get("fiscal_year"))
    try:
        start_pat, end_pat = float(start["pat"]), float(end["pat"])
        years = (end_year or 0) - (start_year or 0)
        cagr = ((end_pat / start_pat) ** (1 / years) - 1) * 100 if years > 0 and start_pat > 0 and end_pat > 0 else None
    except (TypeError, ValueError, ZeroDivisionError):
        cagr = None
    cagr_text = f"; PAT CAGR {cagr:.1f}%" if cagr is not None else ""
    balance = []
    if end.get("equity") is not None:
        balance.append(f"equity {_money(end.get('equity'), end)}")
    if end.get("assets") is not None:
        balance.append(f"assets {_money(end.get('assets'), end)}")
    try:
        if float(end.get("debt")) >= 0 and float(end.get("equity")) > 0:
            balance.append(f"debt/equity {float(end['debt']) / float(end['equity']):.2f}x")
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    balance_text = "; ".join(balance) if balance else "reported balance-sheet fields unavailable"
    ratio_text = _historical_ratio_context(company)
    summary = (
        f"{company.get('symbol')}: annual PAT {_money(start_pat, start)} in {start.get('fiscal_year')} → "
        f"{_money(end_pat, end)} in {end.get('fiscal_year')}{cagr_text}. "
        f"Balance-sheet snapshot ({end.get('fiscal_year')}): {balance_text}."
    )
    return f"{summary} {ratio_text}".strip()


def _historical_ratio_context(company: dict[str, Any]) -> str:
    """Summarise CapIQ ratio history without turning it into a recommendation."""
    rows = [row for row in (company.get("ratio_history") or []) if row.get("value") is not None]
    if not rows:
        return ""
    by_metric: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_metric.setdefault(str(row.get("metric") or "").lower(), []).append(row)
    snippets: list[str] = []
    for metric, label, percent in (
        ("roe", "ROE", True), ("roa", "ROA", True),
        ("debt_equity", "debt/equity", False), ("net_debt_ebitda", "net debt/EBITDA", False),
        ("pb", "P/BV", False), ("ev_ebitda", "EV/EBITDA", False),
    ):
        series = sorted(by_metric.get(metric) or [], key=lambda row: str(row.get("fiscal_year") or ""))
        if len(series) < 2:
            continue
        start, end = series[0], series[-1]
        try:
            a, b = float(start["value"]), float(end["value"])
        except (TypeError, ValueError):
            continue
        fmt = (lambda value: f"{value:.1%}") if percent else (lambda value: f"{value:.2f}x")
        snippets.append(f"{label} {fmt(a)} ({start.get('fiscal_year')}) → {fmt(b)} ({end.get('fiscal_year')})")
    if not snippets:
        return ""
    return "CapIQ historical ratio context: " + "; ".join(snippets[:4]) + "."


def _comparison_answer(payloads: dict[str, Any], *, question: str = "") -> str | None:
    comparison = ((payloads.get("ComparisonEvidence") or {}).get("payload") or {})
    if not comparison.get("available"):
        return None
    lines: list[str] = []
    q = (question or comparison.get("question") or "").lower()
    wants_decade = any(term in q for term in ("10-year", "10 year", "decade", "long-term", "long term"))
    for company in (comparison.get("companies") or [])[:5]:
        symbol = company.get("symbol") or "Company"
        quarter = company.get("quarter") or {}
        annual = company.get("annual") or {}
        valuation = company.get("valuation") or {}
        period = quarter.get("fiscal_period") or annual.get("fiscal_year") or "latest available period"
        pat = quarter.get("pat") if quarter.get("pat") is not None else annual.get("pat")
        eps = quarter.get("eps") if quarter.get("eps") is not None else annual.get("eps")
        pe = valuation.get("pe") or valuation.get("pe_ratio")
        pb = valuation.get("pb") or valuation.get("pb_ratio")
        trend = company.get("earnings_trend") or {}
        yoy = trend.get("value")
        if yoy is None:
            yoy_text = "; PAT YoY unavailable on a like-for-like reported quarter"
        elif trend.get("basis") == "same_provider_unclassified":
            yoy_text = (
                f"; PAT YoY {float(yoy):+.1f}% vs {trend.get('prior_period')} "
                f"(same-provider {trend.get('source')} series; statement scope is unclassified and "
                "separate from the consolidated headline)"
            )
        else:
            yoy_text = f"; PAT YoY {float(yoy):+.1f}% vs {trend.get('prior_period')}"
        sources = ", ".join(company.get("sources") or []) or "institutional warehouse"
        as_of = company.get("as_of") or "not supplied"
        if wants_decade:
            decade = _ten_year_summary(company)
            if decade:
                lines.append(f"{decade} Source: {sources}; as of {as_of}.")
                continue
        lines.append(
            f"{symbol} ({period}): reported PAT {_money(pat, quarter if quarter.get('pat') is not None else annual)}; EPS {_value(eps)}; "
            f"P/E {_value(pe)}; P/B {_value(pb)}{yoy_text}. Source: {sources}; as of {as_of}."
        )
    return "Verified comparison — " + " ".join(lines) + " This is factual research, not an investment recommendation."


def _why_from_objects(payloads: dict[str, Any], intent: str) -> tuple[str, ...]:
    why: list[str] = []

    committee = ((payloads.get("CommitteeResolution") or {}).get("payload") or {}).get("resolution") or {}
    if committee:
        why.append(f"Committee status: {committee.get('status')} — {committee.get('outcome')}")
        for v in (committee.get("votes") or [])[:3]:
            why.append(f"{v.get('desk')} voted {v.get('vote')}: {v.get('rationale')}")

    decision = ((payloads.get("PortfolioDecision") or {}).get("payload") or {}).get("decision") or {}
    if decision:
        why.append(
            f"Portfolio decision: {decision.get('recommendation')} "
            f"(rule: {decision.get('rule_path') or '—'})"
        )
        for a in (decision.get("allocation_actions") or [])[:4]:
            why.append(
                f"Allocation: {a.get('ticker')} "
                f"{float(a.get('from_weight') or 0):.0%} → {float(a.get('to_weight') or 0):.0%}"
            )

    policy = ((payloads.get("PolicyAssessment") or {}).get("payload") or {}).get("assessment") or {}
    if policy:
        why.append(f"Policy status: {policy.get('overall_status')} (score {policy.get('compliance_score')})")
        for v in (policy.get("violations") or [])[:3]:
            why.append(f"Violation: {v.get('name')} — {v.get('required_action')}")

    risk = ((payloads.get("PortfolioRisk") or {}).get("payload") or {}).get("risk") or {}
    if risk:
        conc = risk.get("concentration") or {}
        why.append(
            f"Portfolio risk {risk.get('overall_risk')}: "
            f"concentration {conc.get('level')} HHI={conc.get('hhi')}"
        )

    cd = (payloads.get("CompanyDecision") or {}).get("payload") or {}
    if cd:
        rec = cd.get("recommendation") or (cd.get("decision") or {}).get("recommendation")
        if rec:
            why.append(f"Company decision reference: {cd.get('ticker') or ''} {rec}".strip())
        elif cd.get("note"):
            why.append(str(cd.get("note")))

    if not why:
        why.append(f"Consulted registered objects for intent '{intent}' — see evidence lineage")
    return tuple(why)


def _direct_answer(question: str, intent: str, payloads: dict[str, Any], why: tuple[str, ...]) -> str:
    committee = ((payloads.get("CommitteeResolution") or {}).get("payload") or {}).get("resolution") or {}
    decision = ((payloads.get("PortfolioDecision") or {}).get("payload") or {}).get("decision") or {}
    policy = ((payloads.get("PolicyAssessment") or {}).get("payload") or {}).get("assessment") or {}
    risk = ((payloads.get("PortfolioRisk") or {}).get("payload") or {}).get("risk") or {}

    q = (question or "").lower()

    if intent == "Comparison":
        comparison = _comparison_answer(payloads, question=question)
        if comparison:
            return comparison
        return "Verified comparison data is unavailable for every requested company; no conclusion was inferred."

    if intent == "Committee" or committee:
        status = committee.get("status") or "Unavailable"
        outcome = committee.get("outcome") or ""
        rec = committee.get("decision_recommendation") or decision.get("recommendation") or ""
        return (
            f"The investment committee resolved '{status}'. {outcome} "
            f"Referenced portfolio recommendation: {rec or '—'}. "
            "UAG-01 does not invent a new investment recommendation."
        ).strip()

    if intent == "Policy" or ("policy" in q or "violation" in q):
        status = policy.get("overall_status") or "Unavailable"
        n = policy.get("violation_count") or len(policy.get("violations") or [])
        actions = policy.get("required_actions") or []
        action = actions[0] if actions else "No remediation required"
        return f"Policy status is {status} with {n} violation(s). Primary action: {action}."

    if intent == "Risk" or risk:
        return (
            f"Portfolio overall risk is {risk.get('overall_risk') or 'Unavailable'}. "
            f"Concentration: {(risk.get('concentration') or {}).get('level') or '—'}. "
            "Details are sourced from PRE-01; no new risk score was computed by Ask."
        )

    if intent == "Portfolio Analysis" or decision:
        return (
            f"Portfolio recommendation is '{decision.get('recommendation') or 'Unavailable'}' "
            f"with posture {decision.get('investment_posture') or '—'}. "
            "This reflects CIO-01; Universal Ask does not generate portfolio advice."
        )

    if intent == "Company Analysis":
        cd = (payloads.get("CompanyDecision") or {}).get("payload") or {}
        rec = cd.get("recommendation") or (cd.get("decision") or {}).get("recommendation")
        ticker = cd.get("ticker") or ""
        if rec:
            return (
                f"Company decision for {ticker}: {rec}. "
                "Retrieved from the company decision object — not generated by the orchestrator."
            )
        return (
            "Company analysis objects were consulted. "
            "No authoritative company recommendation was available to surface."
        )

    if why:
        return why[0]
    return f"Orchestrated answer for intent '{intent}'. See supporting evidence and lineage."


def _confidence(steps: tuple[ExecutionStep, ...], payloads: dict[str, Any]) -> int:
    if not steps:
        return 0
    ok = sum(1 for s in steps if s.status == "ok")
    base = int(round(100.0 * ok / len(steps)))
    # Bonus when authoritative stack present
    if "PortfolioDecision" in payloads and "PortfolioRisk" in payloads:
        base = min(100, base + 5)
    if "CommitteeResolution" in payloads:
        base = min(100, base + 5)
    return base


def build_response(
    query: InstitutionalQuery,
    *,
    steps: tuple[ExecutionStep, ...],
    payloads: dict[str, Any],
    generated_at: str = "",
) -> InstitutionalResponse:
    evidence = assemble_evidence(payloads)
    lineage = lineage_for_response(payloads)
    why = _why_from_objects(payloads, query.intent)
    answer = _direct_answer(query.question, query.intent, payloads, why)

    risk = ((payloads.get("PortfolioRisk") or {}).get("payload") or {}).get("risk") or {}
    related_risks = tuple(risk.get("warnings") or [])[:6]

    policy = ((payloads.get("PolicyAssessment") or {}).get("payload") or {}).get("assessment") or {}
    related_obs = tuple(policy.get("warnings") or [])[:4]

    committee = ((payloads.get("CommitteeResolution") or {}).get("payload") or {}).get("resolution") or {}
    committee_history = tuple(
        [f"{committee.get('status')}: {committee.get('outcome')}"]
        + list(committee.get("follow_up_items") or [])[:4]
    ) if committee else ()

    impacts: list[str] = []
    decision = ((payloads.get("PortfolioDecision") or {}).get("payload") or {}).get("decision") or {}
    for a in (decision.get("allocation_actions") or [])[:6]:
        impacts.append(
            f"{a.get('ticker')}: {float(a.get('from_weight') or 0):.0%} → "
            f"{float(a.get('to_weight') or 0):.0%}"
        )

    missing = tuple(s.object_type for s in steps if s.status in {"missing", "error"})
    warnings: list[str] = []
    if missing:
        warnings.append(f"Missing/failed objects: {', '.join(missing)}")
    warnings.append("UAG-01 orchestrates only — it does not generate investment recommendations")

    return InstitutionalResponse(
        query_id=query.query_id,
        question=query.question,
        intent=query.intent,
        direct_answer=answer,
        why=why,
        supporting_evidence=evidence,
        related_risks=related_risks,
        related_observations=related_obs,
        committee_history=committee_history,
        related_portfolio_impacts=tuple(impacts),
        confidence=_confidence(steps, payloads),
        evidence_lineage=lineage,
        objects_consulted=tuple(payloads.keys()),
        execution_plan=steps,
        missing_objects=missing,
        warnings=tuple(warnings),
        sections={
            "direct_answer": answer,
            "why": list(why),
            "evidence": [e.to_dict() for e in evidence],
            "lineage": list(lineage),
        },
        diagnostics=None,
        generated_at=generated_at,
        llm=False,
        generates_recommendations=False,
    )
