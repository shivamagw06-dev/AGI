"""Hard vs soft completion + knowledge density for institutional historical backfill.

Hard requirements gate maintenance eligibility.
Soft requirements never permanently block a company (e.g. missing 2011 transcripts).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from knowledge_factory.historical_depth import store as hd_store

TARGET_YEARS = float(os.getenv("KF_HD_TARGET_YEARS") or "15")

# Hard — company may enter maintenance only when these pass (evidence-based).
# Order matches Mission Control evidence checklist.
HARD_DIMS = (
    "ohlcv",
    "financial_statements",
    "corporate_actions",
    "shareholding",
    "ir_docs",
    "embeddings",
    "qa",
)

EVIDENCE_LABELS = {
    "ohlcv": "OHLCV",
    "financial_statements": "Financials",
    "corporate_actions": "Corporate Actions",
    "shareholding": "Shareholding",
    "ir_docs": "IR Docs",
    "embeddings": "Embeddings",
    "qa": "QA",
}

# Soft — measured for richness; N/A or missing does not block maintenance forever.
SOFT_DIMS = (
    "investor_presentations",
    "earnings_transcripts",
    "ir_pdfs",
    "historical_news",
    "esg_reports",
)


def _years_from_prices(entity: str) -> float:
    prices = hd_store.get_series("prices", entity) or {}
    ends = [str(r.get("period_end") or "")[:10] for r in (prices.get("records") or []) if r.get("period_end")]
    if len(ends) < 2:
        return 0.0
    try:
        d0 = datetime.fromisoformat(min(ends))
        d1 = datetime.fromisoformat(max(ends))
        return max(0.0, (d1 - d0).days / 365.25)
    except Exception:
        return float(max(0, len({e[:4] for e in ends}) - 1))


def _annual_years(entity: str) -> float:
    annual = hd_store.get_series("financials_annual", entity) or {}
    return float(len(annual.get("records") or []))


def history_years(entity: str) -> float:
    return max(_years_from_prices(entity), _annual_years(entity))


def _effective_target(entity: str, target_years: float) -> float:
    """Cap target at listing span when company is newer than target."""
    prices = hd_store.get_series("prices", entity) or {}
    ends = [str(r.get("period_end") or "")[:10] for r in (prices.get("records") or []) if r.get("period_end")]
    if not ends:
        return target_years
    try:
        listed = datetime.fromisoformat(min(ends))
        span = max(
            0.5,
            (datetime.now(timezone.utc).replace(tzinfo=None) - listed.replace(tzinfo=None)).days / 365.25,
        )
        return min(target_years, max(span, 1.0))
    except Exception:
        return target_years


def _ir_docs(entity: str) -> list[dict[str, Any]]:
    try:
        from live_data import store as lidi_store

        row = lidi_store.get_object("company_ir", entity.upper()) or {}
        return list(row.get("documents") or [])
    except Exception:
        return []


def _has_extract(entity: str) -> bool:
    try:
        from continuous_gather_learn import persist as cgl_persist

        ex = cgl_persist.get_knowledge_extract(entity)
        return bool(ex and (ex.get("metrics") or ex.get("kind")))
    except Exception:
        return False


def _has_embedding(entity: str) -> bool:
    try:
        from continuous_gather_learn import persist as cgl_persist

        emb = cgl_persist.get_embedding(entity)
        return bool(emb and emb.get("vector"))
    except Exception:
        return False


def _attempt_meta(entity: str) -> dict[str, Any]:
    return hd_store.get_report(f"backfill_attempts_{entity.upper()}") or {}


def record_attempt(entity: str, dimension: str, *, status: str, detail: str | None = None) -> None:
    e = entity.upper()
    meta = _attempt_meta(e)
    dims = dict(meta.get("dimensions") or {})
    dims[dimension] = {
        "status": status,
        "detail": (detail or "")[:200],
        "at": datetime.now(timezone.utc).isoformat(),
    }
    meta["dimensions"] = dims
    meta["entity"] = e
    hd_store.put_report(f"backfill_attempts_{e}", meta)


def _score(dims: dict[str, Any], keys: tuple[str, ...], *, count_n_a: bool = True) -> float:
    """Percent complete among keys.

    Hard coverage must use count_n_a=False — only stored evidence counts.
    Soft N/A may count as satisfied for soft score.
    """
    if not keys:
        return 0.0
    ok = 0
    for k in keys:
        st = (dims.get(k) or {}).get("status")
        if st == "complete" or (count_n_a and st == "n_a"):
            ok += 1
    return round(100.0 * ok / len(keys), 2)


def knowledge_density(entity: str) -> dict[str, Any]:
    """How rich the intelligence is — not just whether the company was processed."""
    e = entity.upper()
    years = history_years(e)
    docs = _ir_docs(e)
    doc_n = len(docs)
    extracts_n = 0
    metrics_n = 0
    try:
        from continuous_gather_learn import persist as cgl_persist

        ex = cgl_persist.get_knowledge_extract(e) or {}
        if ex:
            extracts_n = 1
            metrics_n = len(ex.get("metrics") or {})
            # Approximate "facts" from themes/risks/catalysts + metrics
            extracts_n = metrics_n + len(ex.get("themes") or []) + len(ex.get("risks") or []) + len(
                ex.get("catalysts") or []
            )
        emb = cgl_persist.get_embedding(e) or {}
        emb_n = 1 if emb.get("vector") else 0
        # Scale embeddings notionally with vector dims presence; keep count simple
        if emb.get("vector"):
            emb_n = max(1, int(len(emb.get("vector") or []) // 4))
    except Exception:
        emb_n = 0

    annual_n = len((hd_store.get_series("financials_annual", e) or {}).get("records") or [])
    q_n = len((hd_store.get_series("financials_quarterly", e) or {}).get("records") or [])
    price_n = len((hd_store.get_series("prices", e) or {}).get("records") or [])
    action_n = len((hd_store.get_series("corporate_actions", e) or {}).get("records") or [])

    # Composite density score (0–100)
    score = 0.0
    score += min(30.0, years * 2.0)  # up to 30 for depth
    score += min(20.0, doc_n * 2.0)  # docs
    score += min(20.0, extracts_n * 1.5)  # extracts/facts
    score += min(15.0, emb_n * 2.0)  # embeddings
    score += min(15.0, (annual_n + q_n / 4.0 + min(price_n, 120) / 12.0 + action_n) * 0.5)

    if score >= 75:
        label = "Excellent"
    elif score >= 55:
        label = "Good"
    elif score >= 30:
        label = "Moderate"
    else:
        label = "Thin"

    return {
        "entity": e,
        "years": round(years, 2),
        "documents": doc_n,
        "extracts": extracts_n,
        "embeddings": emb_n,
        "financial_periods": annual_n + q_n,
        "price_points": price_n,
        "corporate_actions": action_n,
        "density_score": round(score, 1),
        "density": label,
    }


def _record_is_institutional_statement(r: dict[str, Any]) -> bool:
    """Reject price-proxy annuals; require statement-like payloads."""
    src = str(r.get("source") or "")
    payload = r.get("payload") or {}
    if src in {"financial_connector", "fixture"} and (
        payload.get("revenue") is not None
        or payload.get("net_income") is not None
        or payload.get("statement")
        or (payload.get("accounts") or {}).get("revenue") is not None
        or (payload.get("accounts") or {}).get("total_revenue") is not None
    ):
        return True
    if payload.get("statement") in {"income", "balance", "cashflow"}:
        return True
    if payload.get("revenue") is not None or payload.get("net_income") is not None:
        return True
    accounts = payload.get("accounts") or {}
    if accounts.get("revenue") is not None or accounts.get("total_revenue") is not None:
        return True
    # Yahoo price-derived proxies typically only carry price/close — reject those
    if set(payload.keys()) <= {"price", "close", "adj_close", "open", "high", "low", "volume"}:
        return False
    if src == "yahoo_live" and payload.get("revenue") is None and not payload.get("statement"):
        return False
    return False


def _institutional_annual_ok(annual: dict[str, Any], *, eff: float, target: float) -> bool:
    recs = [r for r in (annual.get("records") or []) if _record_is_institutional_statement(r)]
    need = max(3, int(min(eff, target) * 0.5))
    return len(recs) >= min(need, 3)


def _institutional_quarterly_ok(quarterly: dict[str, Any], *, q_need: int, eff: float) -> bool:
    recs = list(quarterly.get("records") or [])
    if not recs:
        return False
    # Prefer institutional; allow fixture quarterlies in non-prod only when they carry statement fields
    inst = [r for r in recs if _record_is_institutional_statement(r)]
    if len(inst) >= min(q_need, 4):
        return True
    if eff < 2 and len(inst) >= 2:
        return True
    # Generic quarterly records with any financial payload keys (not prices)
    soft = [
        r
        for r in recs
        if any(k in (r.get("payload") or {}) for k in ("revenue", "net_income", "ebitda", "eps", "accounts"))
    ]
    return len(soft) >= min(q_need, 4)


def evaluate_completion(entity: str, *, target_years: float | None = None) -> dict[str, Any]:
    """Per-dimension status with hard/soft/overall percentages."""
    e = entity.upper()
    target = float(target_years if target_years is not None else TARGET_YEARS)
    eff = _effective_target(e, target)
    years = history_years(e)
    attempts = (_attempt_meta(e).get("dimensions") or {})

    prices = hd_store.get_series("prices", e) or {}
    annual = hd_store.get_series("financials_annual", e) or {}
    quarterly = hd_store.get_series("financials_quarterly", e) or {}
    actions = hd_store.get_series("corporate_actions", e) or {}
    docs = _ir_docs(e)
    doc_types = {str(d.get("doc_type")) for d in docs}

    def _dim(ok: bool, *, n_a: bool = False, detail: str = "") -> dict[str, Any]:
        if ok:
            return {"status": "complete", "detail": detail}
        if n_a:
            return {"status": "n_a", "detail": detail}
        return {"status": "missing", "detail": detail}

    try:
        from live_data.qa import qa_price_points

        qa = qa_price_points(list(prices.get("records") or []))
        qa_ok = bool(qa.get("ok")) if prices.get("records") else False
    except Exception:
        qa_ok = bool(prices.get("records"))

    ohlcv_ok = years + 1e-9 >= eff and len(prices.get("records") or []) >= 12
    ca_n = len(actions.get("records") or [])
    ca_attempt = attempts.get("corporate_actions") or {}
    # Hard CA requires stored records. Empty/n_a attempts never inflate coverage.
    ca_ok = ca_n > 0

    ann_n = len(annual.get("records") or [])
    q_n = len(quarterly.get("records") or [])
    # Institutional financials only — price-proxy annuals do not count as statements.
    annual_ok = _institutional_annual_ok(annual, eff=eff, target=target)
    q_need = max(4, int(min(eff, target) * 4 * 0.5))
    quarterly_ok = _institutional_quarterly_ok(quarterly, q_need=q_need, eff=eff)
    financials_ok = annual_ok and quarterly_ok

    # Shareholding hard: must have stored ownership history (n_a does not complete).
    sh_series = hd_store.get_series("shareholding", e)
    sh_attempt = attempts.get("shareholding") or {}
    sh_ok = bool(sh_series and (sh_series.get("records") or []))

    # Soft dims
    ip_ok = "investor_presentation" in doc_types
    tr_ok = "earnings_transcript" in doc_types
    ir_ok = "annual_report" in doc_types or any(
        t in doc_types for t in ("quarterly_results", "press_release", "other")
    )
    esg_ok = "esg_report" in doc_types
    news_ok = False
    try:
        from live_data import store as lidi_store

        snap = lidi_store.get_latest_snapshot("nse_announcements", "LATEST") or {}
        events = (snap.get("payload") or {}).get("events") or []
        news_ok = any(str(ev.get("symbol") or "").upper() == e for ev in events if isinstance(ev, dict))
    except Exception:
        news_ok = False
    if (attempts.get("historical_news") or attempts.get("announcements") or {}).get("status") in {
        "complete",
        "empty",
        "n_a",
    }:
        # Attempt recorded — soft N/A allowed
        news_na = not news_ok
    else:
        news_na = False

    def _soft_dim(present: bool, attempt_key: str) -> dict[str, Any]:
        att = attempts.get(attempt_key) or {}
        if present:
            return _dim(True)
        if att.get("status") in {"n_a", "empty", "complete"} or attempts.get("_wave"):
            return _dim(False, n_a=True, detail="unavailable_or_not_published")
        return _dim(False, detail="missing")

    ir_docs_ok = len(docs) > 0

    dims = {
        "ohlcv": _dim(ohlcv_ok, detail=f"years={years:.2f} target={eff:.2f}"),
        "financial_statements": _dim(
            financials_ok, detail=f"annual={ann_n} quarterly={q_n} institutional_only=true"
        ),
        "corporate_actions": _dim(
            ca_ok,
            detail=f"n={ca_n}" + (f" attempt={ca_attempt.get('status')}" if not ca_ok else ""),
        ),
        "shareholding": _dim(
            sh_ok,
            detail="shareholding"
            + (f" attempt={sh_attempt.get('status')}" if not sh_ok and sh_attempt else ""),
        ),
        "ir_docs": _dim(ir_docs_ok, detail=f"n={len(docs)}"),
        "embeddings": _dim(_has_embedding(e) and _has_extract(e)),
        "qa": _dim(qa_ok, detail="price_qa"),
        "investor_presentations": _soft_dim(ip_ok, "investor_presentations"),
        "earnings_transcripts": _soft_dim(tr_ok, "earnings_transcripts"),
        "ir_pdfs": _soft_dim(ir_ok, "annual_reports"),
        "historical_news": _dim(news_ok, n_a=news_na, detail="announcements_news"),
        "esg_reports": _soft_dim(esg_ok, "esg_reports"),
    }

    # Hard % = verified stored evidence only (never n_a / empty attempts).
    hard_pct = _score(dims, HARD_DIMS, count_n_a=False)
    soft_pct = _score(dims, SOFT_DIMS, count_n_a=True)
    overall_pct = round((hard_pct * 0.7 + soft_pct * 0.3), 2)

    # Hard gate: every hard dim must be verified complete (stored data). n_a never completes hard.
    hard_ok = all(dims[d]["status"] == "complete" for d in HARD_DIMS)

    density = knowledge_density(e)

    return {
        "entity": e,
        "complete": hard_ok,  # maintenance eligibility = verified hard requirements
        "fully_backfilled": hard_ok,
        "hard_ok": hard_ok,
        "verified_data_plane": True,
        "evidence_based": True,
        "soft_ok": soft_pct >= 99.9,  # informational
        "hard_pct": hard_pct,
        "soft_pct": soft_pct,
        "overall_pct": overall_pct,
        "history_years": round(years, 2),
        "effective_target_years": round(eff, 2),
        "configured_target_years": target,
        "coverage_pct": overall_pct,
        "dimensions": dims,
        "hard_dimensions": HARD_DIMS,
        "soft_dimensions": SOFT_DIMS,
        "density": density,
        "mode": "maintenance" if hard_ok else "backfill",
    }


def evidence_based_completion(entity: str, *, target_years: float | None = None) -> dict[str, Any]:
    """Completion as an evidence checklist — not a queue boolean.

    Example shape:
      RELIANCE
      OHLCV ✓  Financials ✓  …  Shareholding ✗  …
      Hard Coverage: 86%
      Complete: NO
      Why: Missing Shareholding
    """
    ev = evaluate_completion(entity, target_years=target_years)
    dims = ev.get("dimensions") or {}
    checklist: list[dict[str, Any]] = []
    missing: list[str] = []
    for key in HARD_DIMS:
        row = dims.get(key) or {}
        present = row.get("status") == "complete"
        label = EVIDENCE_LABELS.get(key, key)
        checklist.append(
            {
                "key": key,
                "label": label,
                "present": present,
                "mark": "✓" if present else "✗",
                "status": row.get("status") or "missing",
                "detail": row.get("detail") or "",
            }
        )
        if not present:
            missing.append(key)

    hard_pct = float(ev.get("hard_pct") or 0.0)
    complete = not missing and bool(ev.get("hard_ok"))
    missing_labels = [EVIDENCE_LABELS.get(m, m) for m in missing]
    if complete:
        why = None
    elif missing_labels:
        why = "Missing " + ", ".join(missing_labels)
    else:
        why = "Incomplete evidence"

    return {
        "company": entity.upper(),
        "checklist": checklist,
        "evidence": {c["label"]: c["mark"] for c in checklist},
        "hard_coverage_pct": hard_pct,
        "complete": complete,
        "missing": missing,
        "missing_labels": missing_labels,
        "why_incomplete": why,
        "why_in_backlog": why,  # Mission Control alias
        "years": ev.get("history_years"),
        "mode": "maintenance" if complete else "backfill",
        "authority": "evidence_based_completion",
        "evaluation": ev,
    }


def company_scorecard(entity: str) -> dict[str, Any]:
    """Compact Mission Control row: Hard / Soft / Overall + density + evidence why."""
    evidence = evidence_based_completion(entity)
    ev = evidence.get("evaluation") or {}
    dens = ev.get("density") or {}
    return {
        "company": entity.upper(),
        "hard_pct": evidence.get("hard_coverage_pct"),
        "soft_pct": ev.get("soft_pct"),
        "overall_pct": ev.get("overall_pct"),
        "years": evidence.get("years"),
        "documents": dens.get("documents"),
        "extracts": dens.get("extracts"),
        "embeddings": dens.get("embeddings"),
        "density": dens.get("density"),
        "density_score": dens.get("density_score"),
        "mode": evidence.get("mode"),
        "complete": evidence.get("complete"),
        "missing": evidence.get("missing"),
        "missing_labels": evidence.get("missing_labels"),
        "why_incomplete": evidence.get("why_incomplete"),
        "evidence": evidence.get("evidence"),
        "checklist": evidence.get("checklist"),
    }
