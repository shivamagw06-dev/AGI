"""Per-test evaluators for Committee Certification IC-10 v2.0."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from committee_certification_v2.schema import (
    BOILERPLATE_PHRASES,
    EVIDENCE_DIMENSIONS,
    EXPECTED_GATE_THRESHOLDS,
    FORBIDDEN_REC_TOKENS,
    SECTOR_VOCAB,
)


def _blob(*parts: Any) -> str:
    chunks: list[str] = []
    for p in parts:
        if p is None:
            continue
        if isinstance(p, str):
            chunks.append(p)
        else:
            try:
                chunks.append(json.dumps(p, default=str))
            except Exception:
                chunks.append(str(p))
    return " ".join(chunks).lower()


def _has_buy_sell(text: str) -> bool:
    low = text.lower()
    # word-boundary-ish checks
    for tok in FORBIDDEN_REC_TOKENS:
        if re.search(rf"\b{re.escape(tok)}\b", low):
            return True
    return False


def evidence_completeness(row: dict[str, Any]) -> dict[str, Any]:
    market = row.get("market") or {}
    earn = row.get("earnings") or {}
    own = row.get("ownership") or {}
    val = row.get("valuation") or {}
    cid = row.get("cid") or {}
    hist = val.get("historical") or {}
    peers = (val.get("peer_universe") or {}) if isinstance(val.get("peer_universe"), dict) else {}
    if not peers:
        peers = ((val.get("valuation") or {}).get("peers") or {}) if isinstance(val.get("valuation"), dict) else {}

    flags = {
        "live_market_context": bool(market.get("ok") or market.get("ltp") is not None),
        "financial_statements": bool(earn.get("ok") and float(earn.get("coverage_pct") or 0) >= 50),
        "ownership": bool(own.get("ok") and (own.get("promoter") is not None or own.get("fii") is not None)),
        "valuation": bool(val.get("ok") and (val.get("current") or {}).get("pe") is not None or (val.get("current") or {}).get("pb") is not None),
        "peer_universe": bool(peers.get("resolved") or peers.get("primary_peers") or peers.get("universe")),
        "historical_valuation": bool(hist.get("pe") or (isinstance(hist, dict) and any(isinstance(v, dict) and v.get("median") for v in hist.values()))),
        "ttm": bool(earn.get("ttm_available") or (isinstance(earn.get("ttm"), dict) and earn.get("ttm").get("available"))),
        "cid_attached": bool(
            (cid.get("valuation") or {}).get("pe") is not None
            or (cid.get("ownership") or {}).get("promoter") is not None
            or (cid.get("financial_statements") or cid.get("financials"))
        ),
    }
    # Fix valuation flag precedence
    cur = val.get("current") or {}
    flags["valuation"] = bool(val.get("ok") and (cur.get("pe") is not None or cur.get("pb") is not None or cur.get("ev_ebitda") is not None))

    hit = sum(1 for d in EVIDENCE_DIMENSIONS if flags.get(d))
    pct = round(100.0 * hit / max(1, len(EVIDENCE_DIMENSIONS)), 1)
    return {
        "test": "evidence_completeness",
        "pass": pct >= 95.0,
        "score_pct": pct,
        "hits": hit,
        "n": len(EVIDENCE_DIMENSIONS),
        "flags": flags,
    }


def financial_intelligence(row: dict[str, Any]) -> dict[str, Any]:
    earn = row.get("earnings") or {}
    ca = row.get("company_analysis") or {}
    fin = ca.get("financial_intelligence") or {}
    cov = float(earn.get("coverage_pct") or fin.get("coverage_pct") or 0)
    checks = {
        "income": bool(earn.get("income_available") or ((earn.get("latest_quarter") or {}).get("income_statement"))),
        "balance_sheet": bool(earn.get("balance_sheet_available") or ((earn.get("latest_annual") or {}).get("balance_sheet"))),
        "cash_flow": bool(earn.get("cash_flow_available") or ((earn.get("latest_annual") or {}).get("cash_flow"))),
        "ttm": bool(earn.get("ttm_available")),
        "growth": bool(((earn.get("metrics") or {}).get("yoy_growth") or {})),
        "margins": bool(
            ((earn.get("metrics") or {}).get("latest_quarter") or {}).get("ebitda_margin_pct") is not None
            or ((earn.get("metrics") or {}).get("latest_annual") or {}).get("pat_margin_pct") is not None
            or (row.get("valuation") or {}).get("quality")
        ),
        "returns": bool(
            ((earn.get("metrics") or {}).get("latest_annual") or {}).get("roe_pct") is not None
            or ((row.get("valuation") or {}).get("quality") or {}).get("roe") is not None
        ),
        "cash_conversion": bool(earn.get("cash_flow_available")),
    }
    hit = sum(1 for v in checks.values() if v)
    structural = round(100.0 * hit / max(1, len(checks)), 1)
    score = round(0.6 * min(100.0, cov) + 0.4 * structural, 1)
    return {
        "test": "financial_intelligence",
        "pass": score >= 90.0,
        "score_pct": score,
        "coverage_pct": cov,
        "checks": checks,
    }


def ownership_intelligence(row: dict[str, Any]) -> dict[str, Any]:
    own = row.get("ownership") or {}
    fields = {
        "promoter": own.get("promoter"),
        "fii": own.get("fii"),
        "dii": own.get("dii"),
        "mutual_funds": own.get("mutual_funds"),
        "insurance": own.get("insurance"),
        "pledge": own.get("promoter_pledge_pct") if own.get("promoter_pledge_pct") is not None else own.get("promoter_pledge"),
        "qoq": bool(own.get("qoq") or own.get("quarter_history")),
    }
    present = {k: v is not None and v is not False for k, v in fields.items()}
    # pledge may legitimately be 0 / False
    if own.get("ok") and "pledge" in fields:
        present["pledge"] = True  # field resolved (including explicit false/0)
    hit = sum(1 for v in present.values() if v)
    score = round(100.0 * hit / max(1, len(present)), 1) if own.get("ok") else 0.0
    missing_where_nse = (not own.get("ok")) or (own.get("promoter") is None and own.get("fii") is None)
    return {
        "test": "ownership_intelligence",
        "pass": own.get("ok") is True and not missing_where_nse and score >= 70.0,
        "score_pct": score,
        "fields": {k: fields[k] for k in fields},
        "present": present,
        "ownership_missing": missing_where_nse,
    }


def valuation_intelligence(row: dict[str, Any]) -> dict[str, Any]:
    val = row.get("valuation") or {}
    cur = val.get("current") or {}
    rel = val.get("relative") or {}
    hist = val.get("historical") or {}
    peers = val.get("peer_universe") or {}
    narrative = val.get("observations") or (val.get("narrative") or {}).get("observations") or []
    checks = {
        "peers": bool(peers.get("resolved") or peers.get("primary_peers")),
        "pe": cur.get("pe") is not None,
        "pb": cur.get("pb") is not None,
        "ev_ebitda": cur.get("ev_ebitda") is not None,
        "relative_pe": isinstance(rel.get("pe"), dict) and rel["pe"].get("peer_median") is not None,
        "historical": bool(hist.get("pe")),
        "premium_reason": bool((isinstance(rel.get("pe"), dict) and rel["pe"].get("reasons")) or narrative),
        "peg_or_growth": cur.get("peg") is not None or bool((val.get("growth") or {}).get("eps_cagr_3y")),
        "no_placeholder": "placeholder" not in _blob(cur, rel) and cur.get("pe") != 18.0,
    }
    hit = sum(1 for v in checks.values() if v)
    score = round(100.0 * hit / max(1, len(checks)), 1) if val.get("ok") else max(0.0, 20.0 * hit / max(1, len(checks)))
    return {
        "test": "valuation_intelligence",
        "pass": val.get("ok") is True and checks["peers"] and checks["no_placeholder"] and score >= 70.0,
        "score_pct": score,
        "checks": checks,
        "stance": val.get("stance"),
        "primary_peers": peers.get("primary_peers") or [],
    }


def sector_differentiation(row: dict[str, Any]) -> dict[str, Any]:
    sector = row.get("sector_key") or "unknown"
    vocab = SECTOR_VOCAB.get(sector, ())
    ca = row.get("company_analysis") or {}
    sector_block = ca.get("sector_intelligence") or {}
    text = _blob(
        sector_block.get("reasoning"),
        sector_block.get("priority_metrics"),
        ca.get("investment_thesis"),
        ca.get("executive_summary"),
        (row.get("valuation") or {}).get("observations"),
        (row.get("ownership") or {}).get("intelligence"),
        ((row.get("earnings") or {}).get("intelligence") or {}).get("observations"),
        row.get("sector_key"),
        ((row.get("valuation") or {}).get("peer_universe") or {}).get("industry"),
        ((row.get("valuation") or {}).get("peer_universe") or {}).get("sub_industry"),
    )
    # Also credit peer living-pack metrics for banks (CASA/NIM series)
    try:
        from peer_intelligence.peer_database.store import find_pack_for_ticker

        pack = find_pack_for_ticker(row.get("resolve") or "")
        if pack:
            text += " " + _blob([s.get("metric") for s in (pack.get("series") or [])])
            text += " " + _blob(pack.get("sector"), pack.get("notes"))
    except Exception:
        pass

    hits = [term for term in vocab if term in text]
    # Sector-specific reasoning (not generic fallback) boosts score
    reasoning = sector_block.get("reasoning") or []
    specific = False
    if isinstance(reasoning, list) and reasoning:
        joined = " ".join(str(x) for x in reasoning).lower()
        specific = "prioritise sector kpis from sif" not in joined and len(joined) > 40
    elif sector in SECTOR_VOCAB and hits:
        specific = True

    if not vocab:
        score = 40.0
    else:
        base = 100.0 * len(hits) / max(1, min(6, len(vocab)))
        score = min(100.0, base + (15.0 if specific else 0.0))
        # Cap when only industry label matches
        if len(hits) == 0 and not specific:
            score = 25.0 if (row.get("valuation") or {}).get("peer_universe", {}).get("industry") else 10.0
        elif len(hits) == 0 and specific:
            score = 55.0
    score = round(min(100.0, score), 1)
    return {
        "test": "sector_differentiation",
        "pass": score >= 50.0 and (bool(hits) or specific),
        "score_pct": score,
        "sector_key": sector,
        "vocab_hits": hits[:12],
        "specific_reasoning": specific,
    }


def decision_quality(row: dict[str, Any]) -> dict[str, Any]:
    de = row.get("decision") or {}
    ca = row.get("company_analysis") or {}
    gate = de.get("readiness_gate") or de.get("gate") or (ca.get("recommendation_readiness") or {})
    text = _blob(
        de.get("summary"),
        de.get("answer"),
        de.get("answer_enrichment"),
        ca.get("investment_thesis"),
        ca.get("bull_case"),
        ca.get("bear_case"),
        ca.get("risks"),
        ca.get("catalysts"),
        gate,
    )
    checks = {
        "buy_today_addressed": any(k in text for k in ("buy", "recommend", "conviction", "gate", "deferred", "watchlist", "eligible", "withheld")),
        "thesis": bool(ca.get("investment_thesis") or de.get("investment_thesis") or "thesis" in text),
        "risks": bool(ca.get("risks") or "risk" in text),
        "catalysts": bool(ca.get("catalysts") or "catalyst" in text),
        "gate_explained": bool(gate) or "gate" in text or "readiness" in text,
        "missing_evidence": "missing" in text or bool((gate or {}).get("missing") or (gate or {}).get("gaps")),
        "change_drivers": any(k in text for k in ("would change", "improve", "evidence", "coverage", "fresh")),
        "internally_consistent": not (
            (gate or {}).get("band") == "deferred" and "high conviction" in text and "not" not in text
        ),
    }
    hit = sum(1 for v in checks.values() if v)
    score = round(100.0 * hit / max(1, len(checks)), 1)
    return {
        "test": "decision_quality",
        "pass": score >= 70.0,
        "score_pct": score,
        "checks": checks,
        "gate_band": (gate or {}).get("band") or (gate or {}).get("gate"),
    }


def governance_integrity(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Suite-level: frozen locks + no BUY/SELL from evidence engines + gate thresholds."""
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    try:
        from phase2_investment_intelligence.schema import FROZEN_BASELINE_LOCKS

        checks["constitution_frozen"] = FROZEN_BASELINE_LOCKS.get("constitution") == "frozen"
        checks["governance_spec_frozen"] = FROZEN_BASELINE_LOCKS.get("governance_spec") == "frozen"
        checks["decision_engine_frozen"] = FROZEN_BASELINE_LOCKS.get("decision_engine_contracts") == "frozen"
        checks["gate_methodology_frozen"] = FROZEN_BASELINE_LOCKS.get("institutional_gate") == "frozen"
        details["frozen_locks"] = dict(FROZEN_BASELINE_LOCKS)
    except Exception as exc:  # noqa: BLE001
        checks["constitution_frozen"] = False
        details["freeze_error"] = str(exc)[:120]

    try:
        from decision_engine import readiness_gate as rg

        checks["gate_high_threshold"] = float(rg.HIGH_CONVICTION_COVERAGE) == EXPECTED_GATE_THRESHOLDS["high_conviction_coverage_pct"]
        checks["gate_moderate_threshold"] = float(rg.MODERATE_CONVICTION_COVERAGE) == EXPECTED_GATE_THRESHOLDS["moderate_conviction_coverage_pct"]
        checks["gate_watchlist_threshold"] = float(rg.WATCHLIST_COVERAGE) == EXPECTED_GATE_THRESHOLDS["watchlist_coverage_pct"]
        checks["gate_evidence_floor"] = float(rg.HIGH_CONVICTION_EVIDENCE_FLOOR) == EXPECTED_GATE_THRESHOLDS["high_conviction_evidence_floor_pct"]
        details["gate_thresholds"] = {
            "high": rg.HIGH_CONVICTION_COVERAGE,
            "moderate": rg.MODERATE_CONVICTION_COVERAGE,
            "watchlist": rg.WATCHLIST_COVERAGE,
            "evidence_floor": rg.HIGH_CONVICTION_EVIDENCE_FLOOR,
        }
    except Exception as exc:  # noqa: BLE001
        checks["gate_high_threshold"] = False
        details["gate_error"] = str(exc)[:120]

    # Evidence engines must not emit recommendations
    rec_violations = []
    for row in rows or []:
        for eng in ("ownership", "earnings", "valuation", "market"):
            pack = row.get(eng) or {}
            text = _blob(
                pack.get("observations"),
                (pack.get("intelligence") or {}).get("observations"),
                pack.get("narrative"),
                pack.get("stance"),
            )
            # Allow decision-layer text elsewhere; only flag evidence packs
            if eng in {"ownership", "earnings", "valuation"} and _has_buy_sell(text):
                # stance like "premium versus peers" is fine; "buy" token is not
                if re.search(r"\b(buy|sell|accumulate|reduce|overweight|underweight)\b", text):
                    rec_violations.append(f"{row.get('display')}:{eng}")
        if (row.get("valuation") or {}).get("issues_recommendations") is True:
            rec_violations.append(f"{row.get('display')}:valuation_flag")
        if (row.get("valuation") or {}).get("modifies_decision_engine") is True:
            rec_violations.append(f"{row.get('display')}:modifies_de")

    checks["no_evidence_engine_buy_sell"] = len(rec_violations) == 0
    details["rec_violations"] = rec_violations[:20]

    hit = sum(1 for v in checks.values() if v)
    score = round(100.0 * hit / max(1, len(checks)), 1)
    return {
        "test": "governance_integrity",
        "pass": score >= 100.0,
        "score_pct": score,
        "checks": checks,
        "details": details,
    }


def narrative_quality(row: dict[str, Any]) -> dict[str, Any]:
    ca = row.get("company_analysis") or {}
    val = row.get("valuation") or {}
    de = row.get("decision") or {}
    text = _blob(
        ca.get("executive_summary"),
        ca.get("investment_thesis"),
        ca.get("bull_case"),
        ca.get("bear_case"),
        val.get("observations"),
        (val.get("narrative") or {}).get("summary"),
        de.get("summary"),
    )
    checks = {
        "why_company": bool(ca.get("investment_thesis") or ca.get("business_overview") or len(text) > 80),
        "why_now_or_not": any(k in text for k in ("now", "timing", "catalyst", "deferred", "watchlist", "gate", "fresh", "near-term", "cycle")),
        "relative_to_whom": bool((val.get("peer_universe") or {}).get("primary_peers")) or "peer" in text,
        "evidence_backed": "evidence" in text or bool(val.get("ok") and ca.get("financial_intelligence")),
        "not_boilerplate": not any(p in text for p in BOILERPLATE_PHRASES),
    }
    hit = sum(1 for v in checks.values() if v)
    score = round(100.0 * hit / max(1, len(checks)), 1)
    return {
        "test": "narrative_quality",
        "pass": score >= 60.0 and checks["not_boilerplate"],
        "score_pct": score,
        "checks": checks,
    }


def committee_verdict(per_company: dict[str, Any]) -> str:
    """Map company scores → Committee Ready / Watchlist / Deferred / Research Required."""
    e = float((per_company.get("evidence_completeness") or {}).get("score_pct") or 0)
    f = float((per_company.get("financial_intelligence") or {}).get("score_pct") or 0)
    o = float((per_company.get("ownership_intelligence") or {}).get("score_pct") or 0)
    v = float((per_company.get("valuation_intelligence") or {}).get("score_pct") or 0)
    s = float((per_company.get("sector_differentiation") or {}).get("score_pct") or 0)
    gaps = sum(
        1
        for block in (per_company.get("evidence_completeness") or {}).get("flags", {}).values()
        if not block
    )
    avg = (e + f + o + v) / 4.0
    if avg >= 90 and f >= 90 and o >= 70 and v >= 70 and gaps <= 1:
        if s >= 50:
            return "Committee Ready"
        return "Watchlist"
    if avg >= 75 and gaps <= 2:
        return "Watchlist"
    if avg >= 55:
        return "Deferred"
    return "Research Required"


def fingerprint_row(row: dict[str, Any]) -> str:
    """Stable fingerprint for robustness (ignore latency/timestamps)."""
    slim = {
        "display": row.get("display"),
        "pe": ((row.get("valuation") or {}).get("current") or {}).get("pe"),
        "pb": ((row.get("valuation") or {}).get("current") or {}).get("pb"),
        "peer_med": ((((row.get("valuation") or {}).get("valuation") or {}).get("peers") or {}).get("median_pe")),
        "promoter": (row.get("ownership") or {}).get("promoter"),
        "fii": (row.get("ownership") or {}).get("fii"),
        "fin_cov": (row.get("earnings") or {}).get("coverage_pct"),
        "stance": (row.get("valuation") or {}).get("stance"),
        "gate": ((row.get("decision") or {}).get("readiness_gate") or {}).get("band"),
    }
    raw = json.dumps(slim, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
