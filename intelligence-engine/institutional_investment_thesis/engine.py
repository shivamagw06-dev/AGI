"""Deterministic Investment Thesis construction from frozen judgment packs.

Produces a living thesis object — not a chat answer, not a BUY/SELL decision.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from institutional_investment_thesis import store as thesis_store
from institutional_investment_thesis.schema import (
    DEFAULT_HOLDING_PERIOD,
    FORBIDDEN_DECISIONS,
    FREEZE_LOCKS,
    ITE_VERSION,
    LIFECYCLE_STATES,
    OWNER,
    TEN_QUESTIONS,
    THESIS_SCHEMA_VERSION,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip())


def _company_from_inputs(
    *,
    question: str,
    company: str | None,
    ticker: str | None,
    evidence_graph: dict[str, Any] | None,
) -> tuple[str, str | None]:
    if company:
        return _norm(company), (ticker.upper() if ticker else None)
    if ticker:
        return ticker.upper(), ticker.upper()
    eg = evidence_graph or {}
    entities = eg.get("entities") or []
    if isinstance(entities, list) and entities:
        e0 = entities[0]
        if isinstance(e0, dict):
            name = e0.get("name") or e0.get("entity_id") or e0.get("ticker")
            tick = e0.get("ticker") or e0.get("entity_id")
            if name:
                return _norm(name), (str(tick).upper() if tick else None)
        elif isinstance(e0, str) and e0:
            return e0.upper(), e0.upper()
    # Lightweight lexical fallback for well-known names in the question
    q = question.lower()
    for name, tick in (
        ("infosys", "INFY"),
        ("tcs", "TCS"),
        ("reliance", "RELIANCE"),
        ("hdfc bank", "HDFCBANK"),
        ("ltimindtree", "LTIM"),
        ("wipro", "WIPRO"),
    ):
        if name in q:
            return name.title() if name != "tcs" else "TCS", tick
    return "Unspecified Company", None


def _case_summary(case: dict[str, Any] | None) -> dict[str, Any] | None:
    if not case:
        return None
    return {
        "case_name": case.get("case_name"),
        "case_type": case.get("case_type"),
        "hypothesis": case.get("hypothesis"),
        "hypothesis_id": case.get("hypothesis_id"),
        "probability_pct": case.get("probability_pct"),
        "confidence": case.get("confidence"),
        "supporting_evidence": list(case.get("supporting_evidence") or [])[:8],
        "contradictory_evidence": list(case.get("contradictory_evidence") or [])[:8],
        "underlying_assumptions": list(case.get("underlying_assumptions") or [])[:6],
        "key_catalysts": list(case.get("key_catalysts") or [])[:6],
        "key_risks": list(case.get("key_risks") or [])[:6],
        "invalidation_conditions": list(case.get("invalidation_conditions") or [])[:6],
        "missing_evidence": list(case.get("missing_evidence") or [])[:6],
    }


def _investment_view(icr: dict[str, Any], ihe: dict[str, Any], company: str) -> str:
    report = icr.get("report") or {}
    preferred = icr.get("preferred_case") or report.get("preferred_case")
    cases = icr.get("cases") or {}
    case = cases.get(preferred) if preferred else None
    if case and case.get("hypothesis"):
        return _norm(f"{company}: {case.get('hypothesis')}")
    preferred_h = None
    for h in ihe.get("evaluated_hypotheses") or []:
        if isinstance(h, dict) and (h.get("preferred") or h.get("status") == "Preferred"):
            preferred_h = h
            break
    if preferred_h and preferred_h.get("hypothesis"):
        return _norm(f"{company}: {preferred_h.get('hypothesis')}")
    if report.get("outcome") == "insufficient_evidence":
        return f"{company}: Insufficient evidence for an investment view — thesis held as Watch."
    return f"{company}: Institutional view pending richer evidence; maintained as Watch."


def _why_now(icc: dict[str, Any], icr: dict[str, Any], iew: dict[str, Any]) -> str:
    conf = (icc.get("report") or {}).get("overall_confidence")
    n_elig = iew.get("n_eligible")
    n_cases = icr.get("n_cases")
    parts = []
    if n_elig:
        parts.append(f"{n_elig} weighted evidence items available")
    if n_cases:
        parts.append(f"committee constructed {n_cases} evidence-backed case(s)")
    if conf is not None:
        parts.append(f"institutional confidence {conf}/100")
    if not parts:
        return "Judgment stack evaluated; timing driven by current evidence balance."
    return "Why now: " + "; ".join(parts) + "."


def _market_missing(icr: dict[str, Any], ihe: dict[str, Any]) -> str:
    missing = list((icr.get("report") or {}).get("missing_evidence") or [])
    if not missing:
        for h in ihe.get("evaluated_hypotheses") or []:
            if isinstance(h, dict):
                missing.extend(h.get("missing_evidence") or [])
    items = []
    for m in missing[:5]:
        items.append(str(m.get("item") if isinstance(m, dict) else m))
    if not items:
        return "No critical missing-evidence items flagged by the committee."
    return "Market / evidence gaps: " + "; ".join(items) + "."


def _collect_field(cases: dict[str, Any], key: str) -> list[Any]:
    out: list[Any] = []
    seen = set()
    for role in ("bull", "base", "bear"):
        c = cases.get(role)
        if not c:
            continue
        for item in c.get(key) or []:
            s = _norm(item if not isinstance(item, dict) else item.get("item") or item)
            if not s or s.lower() in seen:
                continue
            seen.add(s.lower())
            out.append(item if isinstance(item, (dict, str)) else s)
    return out[:12]


def _supporting_evidence(iew: dict[str, Any], cases: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    for e in (iew.get("top_weighted") or iew.get("ordered_evidence") or [])[:8]:
        if isinstance(e, dict):
            out.append(
                {
                    "evidence_id": e.get("evidence_id"),
                    "weight_score": e.get("weight_score"),
                    "role": "supporting",
                }
            )
    for item in _collect_field(cases, "supporting_evidence"):
        if item not in out:
            out.append(item)
    return out[:16]


def _counter_evidence(iew: dict[str, Any], cases: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    for c in (iew.get("conflicts") or [])[:6]:
        if isinstance(c, dict):
            out.append({**c, "role": "conflict"})
    for item in _collect_field(cases, "contradictory_evidence"):
        out.append(item)
    return out[:16]


def _monitoring_checklist(
    catalysts: list[Any],
    missing: list[Any],
    invalidation: list[Any],
) -> list[str]:
    items: list[str] = []
    for c in catalysts[:6]:
        items.append(f"Monitor catalyst: {_norm(c)}")
    for m in missing[:6]:
        label = m.get("item") if isinstance(m, dict) else m
        items.append(f"Await evidence: {_norm(label)}")
    for inv in invalidation[:4]:
        items.append(f"Watch invalidation: {_norm(inv)}")
    # Earnings / guidance defaults for institutional cadence
    blob = " ".join(items).lower()
    if "earnings" not in blob:
        items.append("Await next earnings release before formal review")
    if "guidance" not in blob:
        items.append("Track management guidance updates")
    # Dedup
    seen = set()
    out = []
    for i in items:
        k = i.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(i)
    return out[:14]


def _bump_version(prev: dict[str, Any] | None) -> str:
    if not prev:
        return "1.0"
    ver = str(prev.get("version") or "1.0")
    try:
        major, minor = ver.split(".", 1)
        return f"{int(major)}.{int(minor) + 1}"
    except Exception:
        return "1.1"


def _lifecycle_for(prev: dict[str, Any] | None, *, create: bool) -> str:
    if create or not prev:
        return "Active"
    prev_life = str(prev.get("lifecycle") or "Active")
    if prev_life in {"Closed", "Archived"}:
        return prev_life
    if prev_life == "Active":
        return "Updated"
    if prev_life in {"Monitoring", "Needs Review", "Under Review", "Draft", "Updated"}:
        return "Updated"
    return "Active" if prev_life in LIFECYCLE_STATES else "Active"


def construct_thesis(
    *,
    question: str,
    company: str | None = None,
    ticker: str | None = None,
    evidence_weighting: dict[str, Any] | None = None,
    hypothesis_generation: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    evidence_graph: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
    force_new_version: bool = False,
) -> dict[str, Any]:
    """Build (and optionally persist) an Investment Thesis from frozen judgment packs."""
    iew = evidence_weighting or {}
    ihg = hypothesis_generation or {}
    ihe = hypothesis_evaluation or {}
    icr = committee_reasoning or {}
    icc = confidence_calibration or {}
    im = institutional_memory or {}
    eg = evidence_graph or {}
    fs = framework_selection or {}

    company_name, tick = _company_from_inputs(
        question=question, company=company, ticker=ticker, evidence_graph=eg
    )
    thesis_id = thesis_store.make_thesis_id(company_name, tick, question)
    prev = thesis_store.get(thesis_id)
    is_update = bool(prev) or force_new_version
    version = _bump_version(prev) if is_update else "1.0"
    lifecycle = _lifecycle_for(prev, create=not is_update)

    cases = icr.get("cases") or {}
    bull = _case_summary(cases.get("bull"))
    base = _case_summary(cases.get("base"))
    bear = _case_summary(cases.get("bear"))

    catalysts = _collect_field(cases, "key_catalysts")
    risks = _collect_field(cases, "key_risks")
    invalidation = _collect_field(cases, "invalidation_conditions")
    missing = list((icr.get("report") or {}).get("missing_evidence") or [])
    monitoring = _monitoring_checklist(catalysts, missing, invalidation)

    icc_report = icc.get("report") or {}
    confidence = icc_report.get("overall_confidence")
    if confidence is None:
        confidence = icc.get("overall_confidence")
    confidence_reason = icc_report.get("confidence_reason") or icc.get("confidence_reason")

    decision_status = "Watch"
    # Never emit buy/sell from ITE (Decision Engine is Sprint 5.2)
    if decision_status in FORBIDDEN_DECISIONS:
        decision_status = "Watch"

    ten = {
        "investment_view": _investment_view(icr, ihe, company_name),
        "why_now": _why_now(icc, icr, iew),
        "what_market_missing": _market_missing(icr, ihe),
        "bull_case": bull,
        "base_case": base,
        "bear_case": bear,
        "catalysts": catalysts,
        "risks": risks,
        "invalidation": invalidation,
        "monitoring_checklist": monitoring,
    }

    thesis = {
        "thesis_id": thesis_id,
        "company": company_name,
        "ticker": tick,
        "status": "ACTIVE" if lifecycle in {"Active", "Updated", "Monitoring"} else lifecycle.upper().replace(" ", "_"),
        "lifecycle": lifecycle,
        "decision_status": decision_status,
        "position_size": None,  # IDE / Portfolio later
        "investment_view": ten["investment_view"],
        "why_now": ten["why_now"],
        "what_market_missing": ten["what_market_missing"],
        "bull_case": bull,
        "base_case": base,
        "bear_case": bear,
        "supporting_evidence": _supporting_evidence(iew, cases),
        "counter_evidence": _counter_evidence(iew, cases),
        "catalysts": catalysts,
        "risks": risks,
        "invalidation": invalidation,
        "invalidation_conditions": invalidation,
        "monitoring_checklist": monitoring,
        "expected_holding_period": DEFAULT_HOLDING_PERIOD,
        "confidence": confidence,
        "confidence_level": icc_report.get("confidence_level") or icc.get("confidence_level"),
        "confidence_reason": confidence_reason,
        "confidence_change": 0.0 if not prev else None,
        "probability_distribution": icr.get("probability_distribution")
        or (icr.get("report") or {}).get("probability_distribution"),
        "preferred_case": icr.get("preferred_case"),
        "ten_questions": [
            {"id": k, "question": q, "answered": ten.get(k) is not None and ten.get(k) != []}
            for k, q in TEN_QUESTIONS
        ],
        "owner": OWNER,
        "version": version,
        "schema_version": THESIS_SCHEMA_VERSION,
        "ite_version": ITE_VERSION,
        "provenance": {
            "iew_version": iew.get("iew_version"),
            "ihg_version": ihg.get("ihg_version"),
            "ihe_version": ihe.get("ihe_version"),
            "icr_version": icr.get("icr_version"),
            "icc_version": icc.get("icc_version"),
            "committee_version": icr.get("committee_version"),
            "confidence_version": icc.get("confidence_version"),
            "framework_ids": list(fs.get("framework_ids") or []),
            "have_we_seen_this_before": im.get("have_we_seen_this_before"),
        },
        "citations": list((icr.get("report") or {}).get("citations") or [])[:20],
        "question": question,
        "as_of": as_of,
        "last_updated": _utc_now(),
        "created_at": (prev or {}).get("created_at") or _utc_now(),
        "buy_sell": None,
        "decision_engine": False,
        "analysis_only": True,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "judgment_stack_modified": False,
        "freeze_locks": dict(FREEZE_LOCKS),
        "metadata": dict(metadata or {}),
    }

    pack = {
        "ite_version": ITE_VERSION,
        "schema_version": THESIS_SCHEMA_VERSION,
        "thesis": thesis,
        "thesis_id": thesis_id,
        "persisted": False,
        "guides_thesis": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "judgment_changed": False,
        "buy_sell_emitted": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
    }

    if persist:
        saved = thesis_store.upsert(thesis, is_update=is_update)
        pack["thesis"] = saved
        pack["persisted"] = True
        pack["confidence_change"] = saved.get("confidence_change")

    return pack
