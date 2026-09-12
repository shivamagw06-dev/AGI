"""RIE research modules — evidence-backed, no recommendations."""

from __future__ import annotations

from typing import Any, Optional

from research_intelligence_engine.confidence import section_confidence
from research_intelligence_engine.evidence import growth_pct, metric, series_values
from research_intelligence_engine.models import FORBIDDEN_TOKENS


def _block(
    title: str,
    findings: list[str],
    *,
    observed: list[str],
    derived: list[str],
    inferred: list[str],
    evidence: list[dict[str, Any]],
    confidence: dict[str, Any],
    status: str = "ok",
) -> dict[str, Any]:
    text = " ".join(findings)
    lowered = text.lower()
    for tok in FORBIDDEN_TOKENS:
        if tok in lowered.split() or f" {tok} " in f" {lowered} ":
            return {
                "ok": False,
                "title": title,
                "status": "dqiv_reject",
                "error": f"forbidden_language:{tok}",
                "findings": [],
                "explainability": {"observed": observed, "derived": derived, "inferred": []},
                "evidence": evidence,
                "confidence": {"confidence": "Low", "score": 0.0, "missing": ["language_policy"]},
            }
    return {
        "ok": True,
        "title": title,
        "status": status,
        "findings": findings,
        "summary": " ".join(findings)[:1200],
        "explainability": {
            "observed": observed,
            "derived": derived,
            "inferred": inferred,
        },
        "evidence": evidence,
        "confidence": confidence,
    }


def executive(bundle: dict[str, Any]) -> dict[str, Any]:
    m = bundle.get("master") or {}
    uve = bundle.get("uve") or {}
    hvie = bundle.get("hvie") or {}
    vpae = bundle.get("vpae") or {}
    name = m.get("company_name") or bundle.get("symbol")
    sector = m.get("sector") or "unspecified sector"
    model = vpae.get("primary_model") or uve.get("primary_model") or "valuation model unavailable"
    pct = hvie.get("historical_percentile")
    regime = hvie.get("regime")
    inputs = bundle.get("inputs_present") or {}
    missing = [k for k, v in inputs.items() if not v]
    findings = [
        f"{name} operates in {sector}.",
        f"Primary valuation model: {model}.",
    ]
    if pct is not None:
        findings.append(f"Own-history valuation percentile is {pct} ({regime or 'regime n/a'}).")
    else:
        findings.append("Historical valuation percentile is unavailable pending HVIE coverage.")
    if missing:
        findings.append(f"Research focus: close gaps in {', '.join(missing[:5])}.")
    else:
        findings.append("Core warehouse and engine inputs are present for a full research dossier.")
    conf = section_confidence(
        required_hits=sum(1 for k in ("master", "uve", "hvie", "financials_annual") if inputs.get(k)),
        required_total=4,
        observations=len(bundle.get("annual") or []),
        missing=missing[:6],
    )
    return _block(
        "Executive Research Summary",
        findings,
        observed=[f"sector={sector}", f"primary_model={model}"],
        derived=[f"historical_percentile={pct}", f"regime={regime}"],
        inferred=["research_focus_from_missing_inputs"],
        evidence=[{"source": "warehouse.company_master"}, {"source": "uve/hvie/vpae"}],
        confidence=conf,
    )


def business(bundle: dict[str, Any]) -> dict[str, Any]:
    m = bundle.get("master") or {}
    docs = bundle.get("research_documents") or []
    latest_doc = docs[-1] if docs else {}
    annual = bundle.get("latest_annual") or {}
    rev = metric(annual, "revenue", "total_revenue", "sales")
    findings = [
        f"Business model context: {m.get('industry') or m.get('industry_dna') or 'industry unclassified'} within {m.get('sector') or 'n/a'}.",
    ]
    if latest_doc.get("summary"):
        findings.append(str(latest_doc.get("summary"))[:280])
    if latest_doc.get("strategy"):
        findings.append(f"Strategy themes: {str(latest_doc.get('strategy'))[:180]}.")
    if rev is not None:
        findings.append(f"Latest reported revenue level observed at {rev}.")
    if len(findings) < 2:
        findings.append("Business intelligence limited — research_intelligence documents thin for this symbol.")
    hits = sum([
        bool(m.get("sector")),
        bool(latest_doc),
        rev is not None,
    ])
    conf = section_confidence(required_hits=hits, required_total=3, observations=len(docs),
                              missing=[] if hits >= 2 else ["research_documents"])
    return _block(
        "Business Intelligence",
        findings,
        observed=[f"sector={m.get('sector')}", f"industry={m.get('industry')}"],
        derived=["document_themes"] if latest_doc else [],
        inferred=["operating_model_from_industry_label"] if m.get("industry_dna") else [],
        evidence=[{"source": "warehouse.company_master"}, {"source": "warehouse.research_intelligence"}],
        confidence=conf,
    )


def financial_quality(bundle: dict[str, Any]) -> dict[str, Any]:
    a = bundle.get("latest_annual") or {}
    p = bundle.get("prev_annual") or {}
    rev = metric(a, "revenue", "total_revenue", "sales")
    pat = metric(a, "pat", "net_income", "profit_after_tax")
    cfo = metric(a, "operating_cash_flow", "cfo", "cash_from_operations")
    equity = metric(a, "equity", "shareholders_equity", "book_equity")
    debt = metric(a, "total_debt", "debt", "borrowings")
    findings = []
    if rev is not None and pat is not None:
        findings.append(f"Latest revenue {rev}; PAT {pat}.")
    if cfo is not None and pat is not None and pat != 0:
        findings.append(f"Cash conversion (CFO/PAT) ≈ {round(cfo / pat, 2)}.")
    if equity is not None and debt is not None and equity != 0:
        findings.append(f"Debt/Equity ≈ {round(debt / equity, 2)}.")
    g = growth_pct(rev, metric(p, "revenue", "total_revenue", "sales"))
    if g is not None:
        findings.append(f"Revenue change vs prior year: {g}%.")
    if not findings:
        findings.append("Financial quality unavailable — annual statements missing.")
    hits = sum(x is not None for x in (rev, pat, cfo, equity))
    conf = section_confidence(
        required_hits=hits, required_total=4,
        observations=len(bundle.get("annual") or []),
        missing=[] if hits >= 2 else ["financials_annual"],
    )
    return _block(
        "Financial Quality",
        findings,
        observed=["warehouse.financials_annual"],
        derived=["cash_conversion", "debt_equity", "revenue_growth"],
        inferred=[],
        evidence=[{"source": "warehouse.financials_annual", "rows": len(bundle.get("annual") or [])}],
        confidence=conf,
    )


def growth(bundle: dict[str, Any]) -> dict[str, Any]:
    annual = bundle.get("annual") or []
    a, p = bundle.get("latest_annual") or {}, bundle.get("prev_annual") or {}
    pairs = [
        ("Revenue", "revenue", "total_revenue", "sales"),
        ("PAT", "pat", "net_income", "profit_after_tax"),
        ("EPS", "eps", "earnings_per_share"),
        ("Book value", "book_value", "bvps"),
        ("CFO", "operating_cash_flow", "cfo"),
    ]
    findings = []
    derived = []
    for label, *keys in pairs:
        g = growth_pct(metric(a, *keys), metric(p, *keys))
        if g is not None:
            findings.append(f"{label} growth: {g}%.")
            derived.append(f"{label.lower().replace(' ', '_')}_growth={g}")
    revs = series_values(annual, "revenue") or series_values(annual, "total_revenue")
    if len(revs) >= 3:
        ups = sum(1 for i in range(1, len(revs)) if revs[i] >= revs[i - 1])
        findings.append(f"Revenue direction consistency: {round(100.0 * ups / (len(revs) - 1), 1)}% of periods non-decreasing.")
    if not findings:
        findings.append("Growth analysis unavailable — insufficient multi-period statements.")
    conf = section_confidence(
        required_hits=min(3, len(findings)), required_total=3,
        observations=len(annual),
        missing=[] if annual else ["financials_annual"],
    )
    return _block(
        "Growth Intelligence",
        findings,
        observed=[f"annual_periods={len(annual)}"],
        derived=derived,
        inferred=["growth_stability_from_direction_consistency"] if len(revs) >= 3 else [],
        evidence=[{"source": "warehouse.financials_annual"}],
        confidence=conf,
    )


def profitability(bundle: dict[str, Any]) -> dict[str, Any]:
    a = bundle.get("latest_annual") or {}
    ratio = bundle.get("latest_ratio") or {}
    fields = [
        ("ROE", metric(ratio, "roe") or metric(a, "roe")),
        ("ROCE", metric(ratio, "roce") or metric(a, "roce")),
        ("ROA", metric(ratio, "roa") or metric(a, "roa")),
        ("Operating margin", metric(ratio, "operating_margin", "opm") or metric(a, "operating_margin")),
        ("Net margin", metric(ratio, "net_margin", "npm") or metric(a, "net_margin")),
    ]
    findings = []
    for label, val in fields:
        if val is not None:
            findings.append(f"{label}: {val}.")
    p = bundle.get("prev_annual") or {}
    roe_now = metric(ratio, "roe") or metric(a, "roe")
    roe_prev = metric(p, "roe")
    if roe_now is not None and roe_prev is not None:
        direction = "improving" if roe_now > roe_prev else ("deteriorating" if roe_now < roe_prev else "stable")
        findings.append(f"ROE is {direction} versus the prior period ({roe_prev} → {roe_now}).")
    if not findings:
        findings.append("Profitability metrics unavailable.")
    hits = sum(1 for _, v in fields if v is not None)
    conf = section_confidence(required_hits=hits, required_total=5, observations=len(bundle.get("annual") or []))
    return _block(
        "Profitability Intelligence",
        findings,
        observed=["valuation_ratios", "financials_annual"],
        derived=["roe_direction"],
        inferred=[],
        evidence=[{"source": "warehouse.valuation_ratios"}, {"source": "warehouse.financials_annual"}],
        confidence=conf,
    )


def capital_allocation(bundle: dict[str, Any]) -> dict[str, Any]:
    actions = bundle.get("corporate_actions") or []
    a = bundle.get("latest_annual") or {}
    kinds: dict[str, int] = {}
    for row in actions:
        k = str(row.get("action_type") or row.get("event") or "other").lower()
        kinds[k] = kinds.get(k, 0) + 1
    findings = []
    if kinds:
        top = ", ".join(f"{k}×{v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:6])
        findings.append(f"Corporate action mix observed: {top}.")
    div = metric(a, "dividend", "dividends", "dividend_paid")
    capex = metric(a, "capex", "capital_expenditure")
    if div is not None:
        findings.append(f"Dividend cash recorded: {div}.")
    if capex is not None:
        findings.append(f"Capex recorded: {capex}.")
    if not findings:
        findings.append("Capital allocation evidence thin — limited corporate actions / statement fields.")
    conf = section_confidence(
        required_hits=min(3, len(findings)), required_total=3,
        observations=len(actions),
        missing=[] if actions or div is not None else ["corporate_actions"],
    )
    return _block(
        "Capital Allocation Intelligence",
        findings,
        observed=[f"corporate_actions={len(actions)}"],
        derived=["action_mix"],
        inferred=[],
        evidence=[{"source": "warehouse.corporate_actions"}, {"source": "warehouse.financials_annual"}],
        confidence=conf,
    )


def valuation(bundle: dict[str, Any]) -> dict[str, Any]:
    uve, hvie, varie, vpae = bundle.get("uve") or {}, bundle.get("hvie") or {}, bundle.get("varie") or {}, bundle.get("vpae") or {}
    findings = []
    model = vpae.get("primary_model") or uve.get("primary_model")
    if model:
        findings.append(f"Applicable model: {model}.")
    pct = hvie.get("historical_percentile")
    regime = hvie.get("regime")
    if pct is not None:
        findings.append(f"Historical position: percentile {pct}, regime {regime or 'n/a'}.")
    prem = (varie.get("attribution") or {}).get("premium_pct") if isinstance(varie.get("attribution"), dict) else varie.get("premium_pct")
    if prem is None:
        prem = (varie.get("summary") or {}).get("premium_pct") if isinstance(varie.get("summary"), dict) else None
    if prem is not None:
        findings.append(f"Premium/discount signal from VARIE: {prem}%.")
    drivers = varie.get("drivers") or (varie.get("attribution") or {}).get("drivers")
    if isinstance(drivers, list) and drivers:
        findings.append(f"Attribution drivers: {', '.join(str(d)[:40] for d in drivers[:4])}.")
    if not findings:
        findings.append("Valuation intelligence incomplete — UVE/HVIE/VARIE packs unavailable.")
    hits = sum([bool(model), pct is not None, bool(varie.get("ok")), bool(uve)])
    conf = section_confidence(required_hits=hits, required_total=4, observations=len(bundle.get("historical_valuation") or []))
    return _block(
        "Valuation Intelligence",
        findings,
        observed=["uve", "hvie", "varie", "vpae"],
        derived=["premium_drivers", "historical_percentile"],
        inferred=[],
        evidence=[
            {"source": "unified_valuation_engine"},
            {"source": "historical_valuation_intelligence"},
            {"source": "valuation_attribution_engine"},
            {"source": "valuation_policy"},
        ],
        confidence=conf,
    )


def ownership(bundle: dict[str, Any]) -> dict[str, Any]:
    own = bundle.get("latest_ownership") or {}
    series = bundle.get("ownership") or {}
    intel = bundle.get("ownership_intel") or {}
    fields = [
        ("Promoter", own.get("promoter_pct") or own.get("promoter")),
        ("FII", own.get("fii_pct") or own.get("fii")),
        ("DII", own.get("dii_pct") or own.get("dii")),
        ("Mutual funds", own.get("mutual_fund_pct") or own.get("mutual_funds")),
        ("Public/Retail", own.get("public_pct") or own.get("retail_pct") or own.get("public")),
    ]
    findings = [f"{label}: {val}." for label, val in fields if val is not None]
    if len(bundle.get("ownership") or []) >= 2:
        findings.append(f"Ownership history depth: {len(bundle.get('ownership') or [])} snapshots.")
    if intel.get("ok") and intel.get("summary"):
        findings.append(str(intel.get("summary"))[:220])
    if not findings:
        findings.append("Ownership intelligence unavailable — ownership table empty for symbol.")
    conf = section_confidence(
        required_hits=min(4, len(findings)), required_total=4,
        observations=len(bundle.get("ownership") or []),
        missing=[] if own else ["ownership"],
    )
    return _block(
        "Ownership Intelligence",
        findings,
        observed=["warehouse.ownership"],
        derived=["ownership_trend_depth"],
        inferred=[],
        evidence=[{"source": "warehouse.ownership"}, {"source": "ownership_intelligence"}],
        confidence=conf,
    )


def risk(bundle: dict[str, Any]) -> dict[str, Any]:
    a = bundle.get("latest_annual") or {}
    hvie = bundle.get("hvie") or {}
    findings = []
    risks = []
    debt = metric(a, "total_debt", "debt")
    equity = metric(a, "equity", "shareholders_equity")
    if debt is not None and equity is not None and equity > 0 and debt / equity > 1.5:
        risks.append(("Financial Risk", f"Debt/Equity {round(debt/equity, 2)} exceeds 1.5."))
    pct = hvie.get("historical_percentile")
    if pct is not None and pct >= 80:
        risks.append(("Valuation Risk", f"Own-history percentile {pct} is in the expensive band."))
    if not (bundle.get("inputs_present") or {}).get("financials_annual"):
        risks.append(("Execution Risk", "Statement coverage missing — financial monitoring incomplete."))
    if not (bundle.get("inputs_present") or {}).get("ownership"):
        risks.append(("Liquidity Risk", "Ownership series missing — institutional flow monitoring limited."))
    docs = bundle.get("research_documents") or []
    if docs and docs[-1].get("risks"):
        risks.append(("Business Risk", str(docs[-1].get("risks"))[:180]))
    if not risks:
        findings.append("No evidence-backed elevated risks identified from available warehouse inputs.")
    else:
        for label, text in risks:
            findings.append(f"{label}: {text}")
    conf = section_confidence(required_hits=1 if findings else 0, required_total=1,
                              observations=len(bundle.get("annual") or []) + len(bundle.get("historical_valuation") or []))
    return _block(
        "Risk Intelligence",
        findings,
        observed=["financials", "hvie", "research_documents"],
        derived=["debt_equity_flag", "valuation_regime_flag"],
        inferred=[],
        evidence=[{"source": "warehouse"}, {"source": "hvie"}],
        confidence=conf,
    )


def catalysts(bundle: dict[str, Any]) -> dict[str, Any]:
    timeline = bundle.get("research_timeline") or []
    actions = bundle.get("corporate_actions") or []
    hvie = bundle.get("hvie") or {}
    findings = []
    if timeline:
        recent = timeline[-5:]
        findings.append(
            "Recent research timeline: "
            + "; ".join(f"{r.get('date')}:{r.get('event')}" for r in recent if r.get("event"))
        )
    if actions:
        findings.append(f"Corporate actions on record: {len(actions)} (latest {actions[-1].get('date')}).")
    if hvie.get("regime"):
        findings.append(f"Current valuation regime: {hvie.get('regime')}.")
    if not findings:
        findings.append("No dated catalysts observed in research_timeline / corporate_actions.")
    conf = section_confidence(
        required_hits=min(3, len(findings)), required_total=3,
        observations=len(timeline) + len(actions),
    )
    return _block(
        "Catalyst Intelligence",
        findings,
        observed=["research_timeline", "corporate_actions", "hvie.regime"],
        derived=[],
        inferred=[],
        evidence=[{"source": "warehouse.research_timeline"}, {"source": "warehouse.corporate_actions"}],
        confidence=conf,
    )


def monitoring(bundle: dict[str, Any]) -> dict[str, Any]:
    watches = [
        "Watch Revenue",
        "Watch Margins",
        "Watch ROE",
        "Watch Debt",
        "Watch Cash Flow",
        "Watch Valuation",
        "Watch Institutional Ownership",
    ]
    inputs = bundle.get("inputs_present") or {}
    findings = []
    for w in watches:
        findings.append(w)
    missing = [k for k, v in inputs.items() if not v]
    if missing:
        findings.append(f"Priority gaps: {', '.join(missing[:5])}.")
    conf = section_confidence(required_hits=len(watches), required_total=len(watches), observations=1)
    return _block(
        "Monitoring Intelligence",
        findings,
        observed=["checklist_template"],
        derived=["priority_gaps_from_inputs"],
        inferred=[],
        evidence=[{"source": "rie.monitoring"}],
        confidence=conf,
    )


def timeline(bundle: dict[str, Any]) -> dict[str, Any]:
    events = []
    for r in bundle.get("research_timeline") or []:
        events.append({
            "date": r.get("date"),
            "event": r.get("event"),
            "source": "research_timeline",
            "detail": r.get("results") or r.get("guidance") or r.get("management"),
        })
    for r in bundle.get("corporate_actions") or []:
        events.append({
            "date": r.get("date"),
            "event": r.get("action_type") or r.get("event") or "corporate_action",
            "source": "corporate_actions",
            "detail": r.get("description") or r.get("notes"),
        })
    events.sort(key=lambda e: str(e.get("date") or ""))
    findings = [
        f"{e.get('date')}: {e.get('event')} ({e.get('source')})"
        for e in events[-20:]
    ] or ["Research timeline empty for this symbol."]
    conf = section_confidence(
        required_hits=1 if events else 0, required_total=1,
        observations=len(events),
        missing=[] if events else ["research_timeline", "corporate_actions"],
    )
    block = _block(
        "Research Timeline",
        findings,
        observed=[f"events={len(events)}"],
        derived=["chronological_merge"],
        inferred=[],
        evidence=[{"source": "warehouse.research_timeline"}, {"source": "warehouse.corporate_actions"}],
        confidence=conf,
    )
    block["events"] = events[-100:]
    return block


SECTION_BUILDERS = {
    "executive": executive,
    "business": business,
    "financial_quality": financial_quality,
    "growth": growth,
    "profitability": profitability,
    "capital_allocation": capital_allocation,
    "valuation": valuation,
    "ownership": ownership,
    "risk": risk,
    "catalysts": catalysts,
    "monitoring": monitoring,
    "timeline": timeline,
}
