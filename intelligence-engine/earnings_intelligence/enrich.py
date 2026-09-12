"""Merge Financial Statements Pack into CID for company_analysis / readiness consumption."""

from __future__ import annotations

from typing import Any


def _period_row(stmt: dict[str, Any] | None, meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "period_end": meta.get("period_end"),
        "period_start": meta.get("period_start"),
        "label": meta.get("quarter_label") or meta.get("fiscal_year_label"),
        "filing_date": meta.get("filing_date"),
        "source": meta.get("source"),
        "xbrl_url": meta.get("xbrl_url"),
        "accounts": dict(stmt or {}),
        "coverage": 1.0 if stmt else 0.0,
    }


def merge_financials_into_dossier(dossier: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(dossier, dict) or not isinstance(pack, dict) or not pack.get("ok"):
        return dossier
    out = dict(dossier)

    fs = dict(out.get("financial_statements") or {})
    for key in ("income_statement", "balance_sheet", "cash_flow"):
        block = dict(fs.get(key) or {"annual": [], "quarterly": []})
        block.setdefault("annual", [])
        block.setdefault("quarterly", [])
        fs[key] = block

    # Quarterly income
    for row in pack.get("quarter_history") or []:
        if not row.get("income_statement"):
            continue
        fs["income_statement"]["quarterly"].append(_period_row(row.get("income_statement"), row))
        if row.get("segments"):
            fs.setdefault("segments", {}).setdefault("quarterly", []).append(
                {"period_end": row.get("period_end"), "segments": row.get("segments")}
            )
    # Annual statements
    for row in pack.get("annual_history") or []:
        meta = row
        if row.get("income_statement"):
            fs["income_statement"]["annual"].append(_period_row(row.get("income_statement"), meta))
        if row.get("balance_sheet"):
            fs["balance_sheet"]["annual"].append(_period_row(row.get("balance_sheet"), meta))
        if row.get("cash_flow"):
            fs["cash_flow"]["annual"].append(_period_row(row.get("cash_flow"), meta))

    # Cap lengths
    for stmt in ("income_statement", "balance_sheet", "cash_flow"):
        fs[stmt]["quarterly"] = (fs[stmt].get("quarterly") or [])[:40]
        fs[stmt]["annual"] = (fs[stmt].get("annual") or [])[:25]

    fs["versions"] = list(fs.get("versions") or [])
    fs["versions"].append(
        {
            "engine": pack.get("engine"),
            "version": pack.get("version"),
            "as_of": (pack.get("freshness") or {}).get("as_of"),
            "coverage_pct": pack.get("coverage_pct"),
            "source": pack.get("source"),
            "recorded_at": pack.get("generated_at"),
        }
    )
    fs["versions"] = fs["versions"][-40:]
    fs["ttm"] = pack.get("ttm")
    fs["summary"] = pack.get("cid_summary")
    out["financial_statements"] = fs

    # Metrics for company_analysis.normalise_financials
    lq = pack.get("latest_quarter") or {}
    la = pack.get("latest_annual") or {}
    lq_inc = lq.get("income_statement") or {}
    la_bal = la.get("balance_sheet") or {}
    la_cf = la.get("cash_flow") or {}
    metrics = dict(out.get("financial_metrics") or {})
    yoy = (pack.get("metrics") or {}).get("yoy_growth") or {}
    qoq = (pack.get("metrics") or {}).get("qoq_growth") or {}
    lq_m = (pack.get("metrics") or {}).get("latest_quarter") or {}
    la_m = (pack.get("metrics") or {}).get("latest_annual") or {}
    rev_growth = yoy.get("revenue_growth_pct")
    if rev_growth is None:
        rev_growth = qoq.get("revenue_growth_pct")
    pat_growth = yoy.get("pat_growth_pct")
    if pat_growth is None:
        pat_growth = qoq.get("pat_growth_pct")

    fills = {
        "revenue": lq_inc.get("revenue_from_operations"),
        "total_revenue": lq_inc.get("revenue_from_operations"),
        "ebitda": lq_inc.get("ebitda"),
        "ebit": lq_inc.get("ebit"),
        "net_income": lq_inc.get("pat_owners") or lq_inc.get("pat"),
        "eps": lq_inc.get("eps_basic"),
        "revenue_growth": rev_growth,
        "earnings_growth": pat_growth,
        "ebitda_margin": lq_m.get("ebitda_margin_pct"),
        "operating_margin": lq_m.get("ebit_margin_pct") or lq_m.get("ebitda_margin_pct"),
        "net_margin": lq_m.get("pat_margin_pct"),
        "npm": lq_m.get("pat_margin_pct"),
        "roe": la_m.get("roe_pct") or lq_m.get("roe_pct"),
        "roic": la_m.get("roce_pct"),
        "debt_to_equity": la_m.get("debt_to_equity"),
        "fcf": la_cf.get("free_cash_flow") or la_m.get("fcf"),
        "free_cash_flow": la_cf.get("free_cash_flow") or la_m.get("fcf"),
        "operating_cash_flow": la_cf.get("operating_cash_flow") or la_m.get("ocf"),
        "cash": la_bal.get("cash"),
        "total_debt": la_bal.get("total_debt"),
        "equity": la_bal.get("total_equity"),
        "cash_conversion": la_m.get("cash_conversion"),
        "leverage": la_m.get("debt_to_equity"),
    }
    for k, v in fills.items():
        if metrics.get(k) in (None, "", []) and v is not None:
            metrics[k] = v
    out["financial_metrics"] = metrics

    # Institutional financials block (wins over soft metrics in CA bridge)
    fin = dict(out.get("financials") or {})
    for k, v in fills.items():
        if v is not None:
            fin[k] = v
    fin["coverage_pct"] = pack.get("coverage_pct")
    fin["source"] = "earnings_intelligence"
    fin["latest_quarter"] = lq.get("quarter_label") or lq.get("period_end")
    fin["latest_annual"] = la.get("fiscal_year_label") or la.get("period_end")
    out["financials"] = fin
    out["financial_intelligence"] = {
        **fin,
        "enabled": True,
        "coverage_pct": pack.get("coverage_pct"),
        "narrative": (pack.get("intelligence") or {}).get("reasoning"),
        "observations": (pack.get("intelligence") or {}).get("observations") or [],
        "ttm": pack.get("ttm"),
        "metrics": pack.get("metrics"),
    }

    hist = dict(out.get("financial_history") or {})
    hist["counts"] = {
        "quarterly_indexed": pack.get("historical_quarters_indexed"),
        "annual_indexed": pack.get("historical_annuals_indexed"),
        "quarterly_parsed": pack.get("historical_quarters_parsed"),
        "annual_parsed": pack.get("historical_annuals_parsed"),
    }
    hist["coverage"] = pack.get("cid_summary")
    trends = {}
    if yoy.get("revenue_growth_pct") is not None:
        trends["revenue_growth"] = "up" if yoy["revenue_growth_pct"] > 0 else "down"
    if yoy.get("pat_growth_pct") is not None:
        trends["roe"] = "up" if yoy["pat_growth_pct"] > 0 else "down"
        trends["growth"] = trends["revenue_growth"] if "revenue_growth" in trends else ("up" if yoy["pat_growth_pct"] > 0 else "down")
    if lq_m.get("ebitda_margin_pct") is not None:
        trends["margins"] = "monitored"
    if la_m.get("fcf") is not None:
        trends["fcf"] = "up" if float(la_m["fcf"]) > 0 else "down"
        trends["cash_flow"] = trends["fcf"]
    hist["kpi_trends"] = trends
    out["financial_history"] = hist

    out["earnings_intelligence"] = {
        "enabled": True,
        "ok": True,
        "pack_summary": pack.get("cid_summary"),
        "intelligence": pack.get("intelligence"),
        "freshness": pack.get("freshness"),
        "lineage": pack.get("lineage"),
        "confidence": pack.get("confidence"),
        "score": pack.get("score"),
        "evidence": pack.get("evidence"),
    }

    timeline = list(out.get("evidence_timeline") or [])
    timeline.append(
        {
            "at": pack.get("generated_at"),
            "kind": "financial_statements",
            "evidence_type": "financial_statements",
            "source": "earnings_intelligence",
            "summary": (pack.get("intelligence") or {}).get("reasoning"),
            "as_of": (pack.get("freshness") or {}).get("as_of"),
        }
    )
    out["evidence_timeline"] = timeline[-200:]

    # Soft document breadcrumbs so coverage counts
    docs = dict(out.get("documents") or {})
    if pack.get("latest_quarter"):
        qr = list(docs.get("quarterly_results") or [])
        qr.append(
            {
                "title": f"NSE financial results {pack['latest_quarter'].get('quarter_label')}",
                "period_end": pack["latest_quarter"].get("period_end"),
                "source": pack["latest_quarter"].get("source"),
                "xbrl_url": pack["latest_quarter"].get("xbrl_url"),
            }
        )
        docs["quarterly_results"] = qr[-40:]
    if pack.get("latest_annual"):
        ar = list(docs.get("annual_reports") or [])
        ar.append(
            {
                "title": f"NSE annual financial results {pack['latest_annual'].get('fiscal_year_label')}",
                "period_end": pack["latest_annual"].get("period_end"),
                "source": pack["latest_annual"].get("source"),
                "xbrl_url": pack["latest_annual"].get("xbrl_url"),
            }
        )
        docs["annual_reports"] = ar[-25:]
    out["documents"] = docs
    return out
