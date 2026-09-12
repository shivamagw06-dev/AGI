"""Financial Analyst — Do the financial statements support the investment thesis?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion, ticker_of
from institutional_analysts.flags import is_iai_financial_enabled
from institutional_analysts.memory import get_previous_opinion


def _legacy_analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    cid = ctx.get("company_dossier") if isinstance(ctx.get("company_dossier"), dict) else {}
    dvc = ctx.get("data_validation") if isinstance(ctx.get("data_validation"), dict) else {}
    yfp = ctx.get("yahoo_enrichment") if isinstance(ctx.get("yahoo_enrichment"), dict) else {}
    fin = ca.get("financial_intelligence") if isinstance(ca.get("financial_intelligence"), dict) else {}
    hist = cid.get("financial_statements") if isinstance(cid.get("financial_statements"), dict) else {}
    name = company_name(ctx)

    def metric(*keys: str, default: str = "n/a") -> str:
        for src in (fin, hist, yfp, dvc):
            if not isinstance(src, dict):
                continue
            for k in keys:
                if src.get(k) not in (None, "", []):
                    return str(src.get(k))
            metrics = src.get("metrics") if isinstance(src.get("metrics"), dict) else {}
            for k in keys:
                if metrics.get(k) not in (None, "", []):
                    return str(metrics.get(k))
        return default

    quality = fin.get("financial_quality") or fin.get("quality") or "Mixed — track cash conversion and return on capital"
    trend = str(fin.get("trend") or fin.get("what_changed") or "")
    stance = "Bullish" if "improv" in trend.lower() or "strong" in str(quality).lower() else "Neutral"
    if "deterior" in trend.lower() or "weak" in str(quality).lower():
        stance = "Bearish"

    evidence = as_list(fin.get("evidence") or fin.get("what_deserves_monitoring") or dvc.get("checks"), limit=6)
    if not evidence:
        evidence = [f"Financial statement history for {name}", "Validated institutional financial metrics"]

    coverage = pick_confidence(fin.get("confidence"), dvc.get("confidence"), dvc.get("coverage_pct"), default=0.56)
    return structured_opinion(
        role="financial",
        summary=f"{name}: financial quality rests on earnings durability, cash conversion, and balance-sheet resilience.",
        strengths=as_list(
            [metric("roe", default=""), metric("cash_flow", "fcf", "operating_cash_flow", default=""), quality],
            limit=4,
        )
        or ["Earnings durability under review"],
        weaknesses=as_list(fin.get("what_deserves_monitoring") or ["Cash conversion confirmation", "Leverage path"], limit=4),
        evidence=evidence,
        unanswered_questions=[
            "Is incremental return on capital expanding or fading?",
            "How clean is cash conversion versus reported earnings?",
        ],
        sections={
            "revenue": metric("revenue", "sales", "total_revenue", default="See latest reported revenue trend"),
            "margins": metric("margins", "ebitda_margin", "operating_margin", default="Margin trajectory under review"),
            "ebitda": metric("ebitda"),
            "ebit": metric("ebit", "operating_profit"),
            "net_profit": metric("net_profit", "pat", "net_income"),
            "cash_flow": metric("cash_flow", "fcf", "operating_cash_flow", default="Cash conversion needs confirmation"),
            "roe": metric("roe"),
            "roic": metric("roic", "roce"),
            "debt": metric("debt", "net_debt", "leverage", default="Leverage within franchise norms if capital ratios hold"),
            "working_capital": metric("working_capital", "nwc"),
            "capital_allocation": fin.get("capital_allocation") or "Balance growth investment against returns to owners",
            "financial_quality": quality,
            "trend": trend or "Monitor sequential and year-on-year prints",
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(0.45 + 0.08 * min(len(evidence), 5), default=0.5),
            "knowledge": coverage,
            "freshness": pick_confidence(dvc.get("freshness"), default=0.55),
            "coverage": coverage,
        },
        ctx=ctx,
    )


def _metric_from(sources: list[dict[str, Any]], *keys: str, default: str = "") -> str:
    for src in sources:
        if not isinstance(src, dict):
            continue
        for k in keys:
            if src.get(k) not in (None, "", []):
                return str(src.get(k))
        metrics = src.get("metrics") if isinstance(src.get("metrics"), dict) else {}
        for k in keys:
            if metrics.get(k) not in (None, "", []):
                return str(metrics.get(k))
    return default


def _evidence_pack(ctx: dict[str, Any], name: str) -> dict[str, Any]:
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    cid = ctx.get("company_dossier") if isinstance(ctx.get("company_dossier"), dict) else {}
    dvc = ctx.get("data_validation") if isinstance(ctx.get("data_validation"), dict) else {}
    yfp = ctx.get("yahoo_enrichment") if isinstance(ctx.get("yahoo_enrichment"), dict) else {}
    sector = ctx.get("sector_intelligence") if isinstance(ctx.get("sector_intelligence"), dict) else {}
    fin = ca.get("financial_intelligence") if isinstance(ca.get("financial_intelligence"), dict) else {}
    hist = cid.get("financial_statements") if isinstance(cid.get("financial_statements"), dict) else {}
    sources = [fin, hist, yfp, dvc]

    refs = as_list(fin.get("evidence") or fin.get("what_deserves_monitoring") or dvc.get("checks"), limit=6)
    if not refs:
        refs = [f"Financial statement history for {name}", "Validated institutional financial metrics"]

    return {
        "company": name,
        "ticker": ticker_of(ctx),
        "revenue": _metric_from(sources, "revenue", "sales", "total_revenue"),
        "margins": _metric_from(sources, "margins", "ebitda_margin", "operating_margin"),
        "ebitda": _metric_from(sources, "ebitda"),
        "ebit": _metric_from(sources, "ebit", "operating_profit"),
        "net_profit": _metric_from(sources, "net_profit", "pat", "net_income"),
        "cash_flow": _metric_from(sources, "cash_flow", "fcf", "operating_cash_flow"),
        "roe": _metric_from(sources, "roe"),
        "roa": _metric_from(sources, "roa"),
        "roic": _metric_from(sources, "roic", "roce"),
        "debt": _metric_from(sources, "debt", "net_debt", "leverage"),
        "working_capital": _metric_from(sources, "working_capital", "nwc"),
        "interest_coverage": _metric_from(sources, "interest_coverage"),
        "capex": _metric_from(sources, "capex"),
        "capital_allocation": fin.get("capital_allocation")
        or "Balance growth investment against returns to owners",
        "financial_quality": fin.get("financial_quality") or fin.get("quality") or "",
        "quality": fin.get("quality") or "",
        "trend": str(fin.get("trend") or fin.get("what_changed") or ""),
        "narrative": str(fin.get("narrative") or ""),
        "monitors": as_list(fin.get("what_deserves_monitoring"), limit=6),
        "validation_checks": as_list(dvc.get("checks"), limit=8),
        "multi_year_history": as_list(hist.get("annual") or hist.get("history"), limit=6),
        "quarterly_history": as_list(hist.get("quarterly"), limit=4),
        "history_notes": as_list(fin.get("history_notes"), limit=4),
        "sector": sector,
        "indian_peers": as_list(sector.get("indian_peers") or sector.get("peers"), limit=4),
        "global_peers": as_list(sector.get("global_peers"), limit=4),
        "evidence_refs": [{"claim": r, "source_ref": "institutional research"} for r in refs],
    }


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    if not is_iai_financial_enabled():
        return _legacy_analyse(ctx)

    from institutional_analysts.financial.brain import think

    name = company_name(ctx)
    ca = ctx.get("company_analysis") if isinstance(ctx.get("company_analysis"), dict) else {}
    dvc = ctx.get("data_validation") if isinstance(ctx.get("data_validation"), dict) else {}
    fin = ca.get("financial_intelligence") if isinstance(ca.get("financial_intelligence"), dict) else {}
    evidence = _evidence_pack(ctx, name)

    coverage = pick_confidence(fin.get("confidence"), dvc.get("confidence"), dvc.get("coverage_pct"), default=0.56)
    conf = {
        "evidence": pick_confidence(0.45 + 0.08 * min(len(evidence.get("evidence_refs") or []), 5), default=0.5),
        "knowledge": coverage,
        "freshness": pick_confidence(dvc.get("freshness"), default=0.55),
        "coverage": coverage,
        "historical_coverage": coverage,
    }

    previous = get_previous_opinion(ticker_of(ctx), "financial")
    brain = think(
        company=name,
        evidence=evidence,
        previous=previous,
        confidence=conf,
        ticker=ticker_of(ctx),
    )
    conf_out = brain.get("confidence") if isinstance(brain.get("confidence"), dict) else conf

    summary = str(brain.get("summary") or brain.get("executive_opinion") or "")
    base = structured_opinion(
        role="financial",
        summary=summary,
        strengths=list(brain.get("strengths") or []),
        weaknesses=list(brain.get("weaknesses") or []),
        evidence=[
            (e.get("claim") if isinstance(e, dict) else str(e))
            for e in (evidence.get("evidence_refs") or [])
        ],
        unanswered_questions=list(brain.get("unanswered_questions") or brain.get("missing_evidence") or []),
        sections={
            "revenue": evidence.get("revenue") or "Revenue trajectory under review",
            "margins": evidence.get("margins") or "Margin trajectory under review",
            "ebitda": evidence.get("ebitda") or "n/a",
            "ebit": evidence.get("ebit") or "n/a",
            "net_profit": evidence.get("net_profit") or "n/a",
            "cash_flow": evidence.get("cash_flow") or "Cash conversion needs confirmation",
            "roe": evidence.get("roe") or "n/a",
            "roic": evidence.get("roic") or "n/a",
            "debt": evidence.get("debt") or "Leverage under review",
            "working_capital": evidence.get("working_capital") or "Working capital under review",
            "capital_allocation": evidence.get("capital_allocation"),
            "financial_quality": (brain.get("financial_quality") or {}).get("grade")
            or evidence.get("financial_quality"),
            "trend": (brain.get("historical_trend") or {}).get("overall") or evidence.get("trend"),
            "executive_opinion": brain.get("executive_opinion"),
            "iai_version": brain.get("iai_version"),
            "quality_status": (brain.get("quality_checks") or {}).get("status"),
            "archetype": ((brain.get("archetype") or {}).get("primary") or {}).get("name"),
            "trajectory": brain.get("trajectory"),
        },
        stance=str(brain.get("stance") or "Neutral"),
        confidence=conf_out,
        ctx=ctx,
    )

    structured = brain.get("structured_financial_opinion") or {}
    for key in (
        "executive_opinion",
        "financial_quality",
        "profitability",
        "growth_quality",
        "earnings_quality",
        "cash_flow",
        "balance_sheet",
        "capital_allocation",
        "financial_dna",
        "historical_trend",
        "benchmarking",
        "assumptions",
        "uncertainties",
        "missing_evidence",
        "quality_checks",
    ):
        if key in structured:
            base[key] = structured[key]
        elif brain.get(key) is not None:
            base[key] = brain.get(key)

    base["structured_financial_opinion"] = structured
    base["case_studies"] = brain.get("case_studies")
    base["archetype"] = brain.get("archetype")
    base["historical_outcomes"] = brain.get("historical_outcomes")
    base["lessons_learned"] = brain.get("lessons_learned")
    base["learning_chain"] = brain.get("learning_chain")
    base["reasoning"] = brain.get("reasoning")
    base["validation"] = brain.get("validation")
    base["analyst_memory"] = brain.get("memory")
    base["trajectory"] = brain.get("trajectory")
    base["primary_question_answer"] = brain.get("primary_question_answer")
    base["institutional_financial_opinion"] = brain.get("institutional_financial_opinion") or summary
    base["iai_version"] = brain.get("iai_version")
    base["iai_active"] = True
    base["iai_financial_v1"] = True
    base["ready_for_committee"] = brain.get("ready_for_committee")

    if isinstance(base.get("confidence"), dict):
        for k in ("accounting", "historical_coverage", "reasoning"):
            if k in conf_out:
                base["confidence"][k] = conf_out[k]

    if previous:
        notes = []
        wc = base.get("what_changed") if isinstance(base.get("what_changed"), dict) else {}
        notes.extend(list(wc.get("notes") or []))
        for note in brain.get("what_changed") or []:
            if note and note not in notes:
                notes.append(note)
        if wc:
            wc["notes"] = notes[:6]
            wc["trajectory"] = brain.get("trajectory")
            base["what_changed"] = wc
        elif notes:
            base["what_changed"] = {
                "previous_stance": previous.get("stance"),
                "current_stance": base.get("stance"),
                "changed": True,
                "notes": notes[:6],
                "trajectory": brain.get("trajectory"),
            }

    return base
