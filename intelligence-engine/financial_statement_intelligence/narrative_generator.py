"""Analyst Narrative Generator — Module 12.

Turns computed deltas + rule-library findings into professional,
evidence-grounded prose:

    "Revenue increased 18%, driven primarily by ... Gross margins
    expanded 220 basis points ... allowing EBITDA to outpace revenue
    growth."

Every clause in the output traces to a specific computed number or a
finding from ``rule_library`` — nothing is invented. When a detail (like
a named driver: pricing vs volume) isn't available from the input data,
the narrative states the direction and magnitude only, rather than
fabricating a cause.
"""

from __future__ import annotations

from typing import Any, Optional

from financial_statement_intelligence.deltas import compute_deltas
from financial_statement_intelligence.rule_library import Finding, evaluate_rules
from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod


def _bps(delta: Optional[float]) -> Optional[float]:
    return round(delta * 10000, 0) if delta is not None else None


def _find(findings: list[Finding], *rule_id_prefixes: str) -> Optional[Finding]:
    for f in findings:
        if any(f.rule_id.startswith(p) for p in rule_id_prefixes):
            return f
    return None


def _revenue_sentence(prior: StatementPeriod, current: StatementPeriod, drivers: Optional[dict]) -> tuple[str, list[str]]:
    from financial_statement_intelligence.deltas import compute_deltas as _cd

    d = _cd(prior, current)
    rev_pct = d.pct("revenue")
    if rev_pct is None:
        return "Revenue for the period is not comparable to the prior period.", []
    direction = "increased" if rev_pct >= 0 else "declined"
    sentence = f"Revenue {direction} {abs(rev_pct) * 100:.1f}%"
    evidence = [f"revenue: {prior.revenue:,.0f} → {current.revenue:,.0f}"]
    if drivers and (drivers.get("volume_growth") is not None or drivers.get("pricing_growth") is not None):
        parts = []
        if drivers.get("pricing_growth") is not None:
            parts.append(f"higher realisation ({drivers['pricing_growth'] * 100:+.1f}%)")
        if drivers.get("volume_growth") is not None:
            parts.append(f"volume growth ({drivers['volume_growth'] * 100:+.1f}%)")
        sentence += f", driven primarily by {' and '.join(parts)}"
        evidence.append("driver breakdown supplied by caller")
    sentence += "."
    return sentence, evidence


_MARGIN_LEADIN_STRIP = (
    "implies gross margin expansion — ",
    "implies gross margin compression — ",
)


def _margin_sentence(findings: list[Finding], prior: StatementPeriod, current: StatementPeriod) -> tuple[str, list[str]]:
    d = compute_deltas(prior, current)
    gm = d.get("ratio_gross_margin")
    if gm is None or gm.abs_change is None:
        return "", []
    bps = _bps(gm.abs_change)
    direction = "expanded" if bps >= 0 else "contracted"
    sentence = f"Gross margins {direction} {abs(bps):.0f} basis points"
    evidence = [f"gross margin: {gm.prior * 100:.1f}% → {gm.current * 100:.1f}%"]
    gp_finding = _find(findings, "gross_profit_vs_cogs", "revenue_vs_gross_profit")
    if gp_finding:
        # Reuse the rule's own grounded explanation as the driver clause, never inventing a new one.
        clause = gp_finding.explanation.split("—", 1)[-1].strip().rstrip(".")
        for lead_in in _MARGIN_LEADIN_STRIP:
            if clause.startswith(lead_in):
                clause = clause[len(lead_in):]
                break
        sentence += f" — {clause}"
        evidence.append(gp_finding.explanation)
    sentence += "."
    return sentence, evidence


def _profitability_sentence(findings: list[Finding]) -> tuple[str, list[str]]:
    leverage_finding = _find(findings, "revenue_vs_ebitda", "gross_profit_vs_opex", "opex_vs_revenue")
    if not leverage_finding:
        return "", []
    clause = leverage_finding.explanation
    return clause, [clause]


def _cash_flow_sentence(findings: list[Finding], prior: StatementPeriod, current: StatementPeriod) -> tuple[str, list[str]]:
    pat_ocf = _find(findings, "pat_vs_operating_cf")
    if pat_ocf:
        return pat_ocf.explanation, [pat_ocf.explanation]
    fcf = current.free_cash_flow
    if fcf < 0:
        sentence = f"Free Cash Flow was negative at {fcf:,.0f} for the period."
        return sentence, [sentence]
    return "", []


def _leverage_sentence(findings: list[Finding]) -> tuple[str, list[str]]:
    lev = _find(findings, "debt_vs_ebitda", "cash_vs_total_debt", "interest_vs_ebit")
    if not lev:
        return "", []
    return lev.explanation, [lev.explanation]


def generate_long_form_note(series: FinancialSeries) -> dict[str, Any]:
    """A ~500-word, section-structured analyst note pulling together every
    Phase 2 engine — ratios, red flags, earnings quality, cash conversion,
    leverage, capital efficiency — each sentence grounded in a computed
    number. This is the Section F "produce a 500-word analyst note" answer.
    """
    from financial_statement_intelligence.earnings_quality import assess_earnings_quality
    from financial_statement_intelligence.health_score import score_financial_health
    from financial_statement_intelligence.ratio_engine import compute_ratios
    from financial_statement_intelligence.red_flag_detector import detect_red_flags
    from financial_statement_intelligence.statement_intelligence import overall_direction

    latest = series.latest()
    if latest is None:
        return {"available": False, "reason": "No periods in series."}

    direction = overall_direction(series)
    ratios = compute_ratios(series)
    eq = assess_earnings_quality(series)
    flags = detect_red_flags(series)
    health = score_financial_health(series)
    core_narrative = generate_narrative(series)

    sections: list[str] = []
    sections.append(
        f"EXECUTIVE SUMMARY. {series.company}'s latest period ({latest.label}) shows an overall "
        f"{direction['verdict']} trend (net score {direction['net_score']}), based on "
        f"{direction['latest_period_positive_findings']} favourable and {direction['latest_period_concern_findings']} "
        f"concerning findings from the period's Income Statement, Balance Sheet, and Cash Flow Statement. "
        f"{core_narrative.get('narrative', '')}"
    )
    sections.append(
        f"RATIOS. Gross Margin stands at {ratios.get('gross_margin')}, EBITDA Margin at "
        f"{ratios.get('ebitda_margin')}, and Net Margin at {ratios.get('net_margin')}. Liquidity is "
        f"reflected in a Current Ratio of {ratios.get('current_ratio')} and a Quick Ratio of "
        f"{ratios.get('quick_ratio')}. Returns stand at ROE {ratios.get('roe')}, ROCE {ratios.get('roce')}, "
        f"and ROIC {ratios.get('roic')}."
    )
    sections.append(
        f"CASH CONVERSION. {eq.get('label', 'Not assessed')} (score {eq.get('score', 'n/a')}/10). "
        + " ".join(s["explanation"] for s in (eq.get("signals") or [])[:2])
    )
    sections.append(
        f"LEVERAGE. Debt/Equity is {ratios.get('debt_to_equity')} and Net Debt/EBITDA is "
        f"{ratios.get('net_debt_to_ebitda')}, with Interest Coverage of {ratios.get('interest_coverage')}x. "
        f"{'Leverage is elevated and warrants monitoring.' if (ratios.get('net_debt_to_ebitda') or 0) > 3 else 'Leverage sits within a conventional range for a non-financial business.'}"
    )
    sections.append(
        f"CAPITAL EFFICIENCY. ROIC of {ratios.get('roic')} against a Return on Capital Employed of "
        f"{ratios.get('roce')} indicates "
        + ("capital is being deployed above a typical cost-of-capital hurdle." if (ratios.get('roic') or 0) > 0.10
           else "capital efficiency below a typical cost-of-capital hurdle, warranting scrutiny of recent capex/investment decisions.")
    )
    sections.append(
        f"RED FLAGS. {flags['total_flags']} flag(s) detected ({flags['high_severity_count']} high severity, "
        f"{flags['medium_severity_count']} medium severity). "
        + (("Most notably: " + flags["flags"][0]["evidence"]) if flags["flags"] else "No material red flags were detected in this period.")
    )
    sections.append(
        f"CONCLUSION. Overall Financial Strength scores {health.get('overall_financial_strength')}/100. "
        f"{series.company} presents a {direction['verdict']} financial profile this period; "
        f"{'continued monitoring of the flagged items above is warranted before drawing further conclusions.' if flags['total_flags'] > 0 else 'no immediate red flags temper the picture described above.'}"
    )

    note = " ".join(sections)
    word_count = len(note.split())
    return {
        "available": True,
        "company": series.company,
        "period": latest.label,
        "note": note,
        "word_count": word_count,
        "sections": ["EXECUTIVE SUMMARY", "RATIOS", "CASH CONVERSION", "LEVERAGE", "CAPITAL EFFICIENCY", "RED FLAGS", "CONCLUSION"],
        "grounded_in": {
            "overall_direction": direction, "ratios": ratios, "earnings_quality": eq,
            "red_flags": flags, "health_score": health,
        },
    }


def generate_narrative(
    series: FinancialSeries, *, drivers: Optional[dict[str, float]] = None
) -> dict[str, Any]:
    """Module 12: analyst-quality narrative for the latest period, fully
    evidence-grounded. ``drivers`` optionally supplies pricing/volume
    breakdown when the caller has it — the narrative never fabricates one."""
    prior, current = series.pair(lag=1)
    if prior is None or current is None:
        return {"available": False, "reason": "Need at least two periods for a narrative."}

    deltas = compute_deltas(prior, current)
    findings = evaluate_rules(deltas)

    sentences: list[str] = []
    evidence: list[str] = []

    for sentence, ev in (
        _revenue_sentence(prior, current, drivers),
        _margin_sentence(findings, prior, current),
        _profitability_sentence(findings),
        _cash_flow_sentence(findings, prior, current),
        _leverage_sentence(findings),
    ):
        if sentence:
            sentences.append(sentence)
            evidence.extend(ev)

    narrative = " ".join(sentences) if sentences else (
        f"{series.company}'s {current.label} results show no material period-over-period change "
        f"in the metrics tracked."
    )
    return {
        "available": True,
        "company": series.company,
        "period": current.label,
        "narrative": narrative,
        "sentence_count": len(sentences),
        "evidence": evidence,
        "underlying_findings": [f.rule_id for f in findings],
    }
