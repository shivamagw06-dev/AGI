"""Institutional Coverage Health production surface.

Splits platform coverage into five layers so data availability is never
confused with valuation applicability (VPAE).

Primary KPI:
  Valuation Coverage =
    companies with a valid primary valuation model + sufficient supporting data
    ÷ companies expected to have a valuation model

No vendor calls. No BUY/SELL language. No UI-side calculations required.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

ENGINE_CODE = "institutional_coverage_health"
VERSION = "1.0.0"

_CACHE: dict[str, Any] = {"payload": None, "at": 0.0, "limit": None}
_CACHE_TTL_SEC = 90.0

# Statuses that mean the instrument is out of valuation scope (exclude denom).
_EXCLUDE_FROM_EXPECTED = frozenset({"NOT_APPLICABLE"})

# Statuses that still represent a deliberate, applicable primary model.
_APPLICABLE_STATUSES = frozenset({
    "VALID",
    "BANKING_MODEL",
    "NBFC_MODEL",
    "INSURANCE_MODEL",
    "REIT",
    "INVIT",
    "ETF",
    "LOSS_MAKING",
    "EXTREME_VALUATION",
})

_METRIC_KEYS = (
    "pe",
    "pb",
    "roe",
    "roce",
    "ev_ebitda",
    "ev_sales",
    "dividend_yield",
    "ps",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100.0 * numerator / denominator, 1)


def _bar(pct: float) -> str:
    filled = max(0, min(10, int(round(pct / 10.0))))
    return ("█" * filled) + ("░" * (10 - filled))


def _layer(name: str, pct: float, *, covered: int = 0, universe: int = 0, detail: Optional[dict] = None) -> dict[str, Any]:
    return {
        "name": name,
        "pct": pct,
        "covered": covered,
        "universe": universe,
        "bar": _bar(pct),
        **({"detail": detail} if detail else {}),
    }


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "role": "institutional_coverage_health",
        "definition": (
            "Coverage = companies with a valid valuation methodology and "
            "sufficient supporting data ÷ companies expected to have a valuation model"
        ),
        "layers": [
            "universe",
            "data",
            "valuation",
            "metric",
            "intelligence",
        ],
        "primary_kpi": "valuation_coverage",
        "rule": "vpae_applicability_not_pe_presence",
        "reads": [
            "institutional_warehouse.company_master",
            "institutional_warehouse.valuation_ratios",
            "institutional_warehouse.financials_annual",
            "institutional_warehouse.ownership",
            "institutional_warehouse.daily_market_history",
            "institutional_warehouse.corporate_actions",
            "institutional_warehouse.hvie_company_state",
            "institutional_warehouse.research_intelligence",
            "valuation_policy.evaluate",
        ],
        "endpoints": [
            "/v1/valuation/coverage/health",
            "/v1/valuation/coverage/valuation",
            "/v1/valuation/coverage/metrics",
            "/v1/valuation/coverage/research",
            "/v1/valuation/coverage/residual",
            "/v1/valuation/coverage-health/health",
        ],
        "language": "analysis_only",
        "checked_at": _now(),
    }


def _entity_set(tab_id: str) -> set[str]:
    try:
        from institutional_warehouse import store

        return {str(s).strip().upper() for s in (store.entities(tab_id) or []) if s}
    except Exception:
        return set()


def _paged_rows(tab_id: str, *, max_rows: int = 100_000) -> list[dict[str, Any]]:
    """Read all effective rows for a tab.

    ``store.all_rows`` / ``store.fetch`` clamp to ``MAX_LIMIT`` (5000). Coverage
    health must page past that or residual gaps falsely treat bootstrapped
    companies as missing (first 5k valuation_ratios rows ≈ 295 symbols).
    """
    from institutional_warehouse import store

    page_size = 5000
    offset = 0
    out: list[dict[str, Any]] = []
    while offset < max_rows:
        try:
            page = store.fetch(tab_id, limit=page_size, offset=offset)
        except Exception:
            break
        rows = page.get("rows") or []
        if not rows:
            break
        out.extend(rows)
        total = int(page.get("total") or 0)
        offset += len(rows)
        if offset >= total or len(rows) < page_size:
            break
    return out


def _load_masters() -> list[dict[str, Any]]:
    rows = _paged_rows("company_master", max_rows=20_000)
    out = []
    for r in rows:
        sym = str(r.get("symbol") or "").strip().upper()
        if not sym:
            continue
        out.append(r)
    return out


def _provider_ratio_index() -> dict[str, dict[str, Any]]:
    """symbol → {source, ratios: {name: payload}} — paged, no N+1."""
    provider_by_symbol: dict[str, dict[str, Any]] = {}
    ratio_rows = _paged_rows("valuation_ratios", max_rows=100_000)
    ratio_rows = sorted(
        ratio_rows,
        key=lambda r: str(r.get("reported_date") or ""),
        reverse=True,
    )
    for rr in ratio_rows:
        sym = str(rr.get("symbol") or "").strip().upper()
        name = str(rr.get("ratio_name") or "").strip().lower()
        if not sym or not name:
            continue
        bucket = provider_by_symbol.setdefault(
            sym,
            {"source": rr.get("source") or rr.get("provider") or "upstox", "ratios": {}},
        )
        if name in bucket["ratios"]:
            continue
        val = rr.get("company_value")
        bucket["ratios"][name] = {
            "company_value": val,
            "sector_value": rr.get("sector_value"),
            "reported_date": rr.get("reported_date"),
            "dqiv_status": rr.get("dqiv_status"),
            "confidence": rr.get("confidence"),
        }
    return provider_by_symbol


def _annual_index() -> dict[str, dict[str, Any]]:
    """Latest annual facts per symbol for VPAE financial health."""
    by_sym: dict[str, dict[str, Any]] = {}
    rows = _paged_rows("financials_annual", max_rows=100_000)
    rows = sorted(rows, key=lambda r: str(r.get("fiscal_year") or ""), reverse=True)
    for r in rows:
        sym = str(r.get("symbol") or "").strip().upper()
        if not sym or sym in by_sym:
            continue
        by_sym[sym] = {
            "revenue": r.get("revenue"),
            "pat": r.get("pat"),
            "ebitda": r.get("ebitda"),
            "equity": r.get("equity") or r.get("shareholders_equity"),
            "book_value": r.get("book_value"),
            "cash": r.get("cash"),
            "free_cash_flow": r.get("free_cash_flow"),
            "debt": r.get("debt"),
            "shares": r.get("shares") or r.get("shares_outstanding"),
            "fiscal_year": r.get("fiscal_year"),
            "statement_type": r.get("statement_type"),
        }
    return by_sym


def _statement_field_sets(annual_by_sym: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    income: set[str] = set()
    balance: set[str] = set()
    cash_flow: set[str] = set()
    for sym, row in annual_by_sym.items():
        if row.get("revenue") is not None or row.get("pat") is not None:
            income.add(sym)
        if row.get("equity") is not None or row.get("book_value") is not None or row.get("debt") is not None:
            balance.add(sym)
        if row.get("free_cash_flow") is not None or row.get("cash") is not None:
            cash_flow.add(sym)
    return {"income": income, "balance": balance, "cash_flow": cash_flow}


def _price_set() -> set[str]:
    """Symbols with any daily market history (current price proxy)."""
    return _entity_set("daily_market_history")


def _has_isin(master: dict[str, Any]) -> bool:
    isin = str(master.get("isin") or "").strip().upper()
    return bool(isin) and isin not in {"NA", "N/A", "-", "NONE", "NULL"}


def _is_delisted(master: dict[str, Any]) -> bool:
    for key in ("listing_status", "status", "trading_status", "active"):
        raw = master.get(key)
        if raw is None:
            continue
        text = str(raw).strip().upper()
        if text in {"DELISTED", "INACTIVE", "SUSPENDED", "FALSE", "0", "N"}:
            return True
    return False


def valuation_covered(policy: dict[str, Any]) -> tuple[Optional[bool], str]:
    """Return (covered|None for excluded, reason_code).

    None → exclude from expected denominator (NOT_APPLICABLE).
    """
    if not policy.get("ok"):
        return False, "not_in_warehouse"
    status = str(policy.get("status") or "").upper()
    if status in _EXCLUDE_FROM_EXPECTED:
        return None, "not_applicable"
    primary_model = policy.get("primary_model")
    primary = policy.get("primary_metric")
    if not primary_model or not primary:
        return False, "no_primary_model"
    if status == "INSUFFICIENT_DATA":
        return False, "insufficient_data"
    if status not in _APPLICABLE_STATUSES:
        # Unknown status — require primary metric Applicable + non-NONE coverage.
        pass
    metrics = policy.get("metrics") or {}
    entry = metrics.get(primary) or {}
    if str(entry.get("status") or "").lower() == "unavailable":
        return False, "primary_unavailable"
    if str(policy.get("coverage") or "").upper() == "NONE":
        return False, "no_supporting_data"
    return True, "complete"


def _evaluate_universe(
    masters: list[dict[str, Any]],
    provider_by_symbol: dict[str, dict[str, Any]],
    annual_by_sym: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    from valuation_policy.engine import evaluate

    evaluated: list[dict[str, Any]] = []
    for master in masters:
        sym = str(master.get("symbol") or "").strip().upper()
        record = {
            "ok": True,
            "symbol": sym,
            "master": master,
            "latest_annual": annual_by_sym.get(sym) or {},
            "latest_price": {},
            "provider_ratios": provider_by_symbol.get(sym) or {},
            "coverage": {},
        }
        policy = evaluate(sym, record=record)
        covered, reason = valuation_covered(policy)
        company = policy.get("company") or {}
        evaluated.append(
            {
                "symbol": sym,
                "company": company.get("name") or master.get("company_name") or sym,
                "sector": company.get("sector") or master.get("sector"),
                "instrument_type": company.get("instrument_type"),
                "industry_dna": company.get("industry_dna"),
                "primary_model": policy.get("primary_model"),
                "primary_metric": policy.get("primary_metric"),
                "status": policy.get("status"),
                "confidence": policy.get("confidence"),
                "coverage_level": policy.get("coverage"),
                "dqiv": (policy.get("dqiv") or {}).get("status"),
                "valuation_covered": covered,
                "reason_code": reason,
                "unavailable_primary": [
                    {
                        "metric": m,
                        "reason": ((policy.get("metrics") or {}).get(m) or {}).get("reason"),
                    }
                    for m in (policy.get("unavailable_metrics") or [])
                    if m == policy.get("primary_metric")
                ],
                "has_isin": _has_isin(master),
                "delisted": _is_delisted(master),
                "provider_ratios": bool((provider_by_symbol.get(sym) or {}).get("ratios")),
            }
        )
    return evaluated


def _data_coverage(
    universe_syms: set[str],
    masters: list[dict[str, Any]],
    annual_by_sym: dict[str, dict[str, Any]],
    provider_by_symbol: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    n = len(universe_syms)
    fields = _statement_field_sets(annual_by_sym)
    profile = {str(m.get("symbol") or "").strip().upper() for m in masters if m.get("company_name")}
    ownership = _entity_set("ownership")
    prices = _price_set()
    actions = _entity_set("corporate_actions")
    ratios = set(provider_by_symbol.keys())

    layers = {
        "company_profile": _pct(len(profile & universe_syms), n),
        "income_statement": _pct(len(fields["income"] & universe_syms), n),
        "balance_sheet": _pct(len(fields["balance"] & universe_syms), n),
        "cash_flow": _pct(len(fields["cash_flow"] & universe_syms), n),
        "shareholding": _pct(len(ownership & universe_syms), n),
        "current_price": _pct(len(prices & universe_syms), n),
        "corporate_actions": _pct(len(actions & universe_syms), n),
        "key_ratios": _pct(len(ratios & universe_syms), n),
    }
    raw_pct = round(sum(layers.values()) / max(len(layers), 1), 1)
    return {
        "pct": raw_pct,
        "layers": layers,
        "counts": {
            "company_profile": len(profile & universe_syms),
            "income_statement": len(fields["income"] & universe_syms),
            "balance_sheet": len(fields["balance"] & universe_syms),
            "cash_flow": len(fields["cash_flow"] & universe_syms),
            "shareholding": len(ownership & universe_syms),
            "current_price": len(prices & universe_syms),
            "corporate_actions": len(actions & universe_syms),
            "key_ratios": len(ratios & universe_syms),
        },
        "universe": n,
    }


def _metric_coverage_block(
    universe_syms: set[str],
    provider_by_symbol: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    n = len(universe_syms)
    metrics: dict[str, dict[str, Any]] = {}
    for key in _METRIC_KEYS:
        hit = 0
        for sym in universe_syms:
            ratios = (provider_by_symbol.get(sym) or {}).get("ratios") or {}
            payload = ratios.get(key)
            if payload is None:
                continue
            val = payload.get("company_value") if isinstance(payload, dict) else payload
            if val is not None:
                hit += 1
        metrics[key] = {
            "pct": _pct(hit, n),
            "covered": hit,
            "universe": n,
            "label": {
                "pe": "PE",
                "pb": "PB",
                "roe": "ROE",
                "roce": "ROCE",
                "ev_ebitda": "EV/EBITDA",
                "ev_sales": "EV/Sales",
                "dividend_yield": "Dividend Yield",
                "ps": "P/S",
            }.get(key, key.upper()),
        }
    avg = round(sum(m["pct"] for m in metrics.values()) / max(len(metrics), 1), 1)
    return {"pct": avg, "metrics": metrics, "universe": n}


def _hvie_pipeline_snapshot(universe_syms: set[str]) -> dict[str, Any]:
    """Prefer persisted HVIE universe queue completion state when available."""
    try:
        from historical_valuation_intelligence.universe_programme import queue as univ_queue

        rows = univ_queue.all_queue_rows()
    except Exception:
        rows = []
    if not rows:
        return {}
    by_sym = {
        str(r.get("symbol") or "").strip().upper(): r
        for r in rows
        if r.get("symbol")
    }
    # Restrict to coverage universe when provided.
    scoped = [by_sym[s] for s in universe_syms if s in by_sym] if universe_syms else list(by_sym.values())
    if not scoped:
        scoped = list(by_sym.values())
    n = len(scoped) or 1
    complete = sum(1 for r in scoped if str(r.get("lifecycle") or "").upper() == "COMPLETE")
    percentiles = sum(1 for r in scoped if r.get("has_percentile") or r.get("last_percentile") is not None)
    bands = sum(1 for r in scoped if r.get("has_bands"))
    regimes = sum(1 for r in scoped if r.get("has_regime") or r.get("last_regime"))
    research = sum(1 for r in scoped if r.get("has_research"))
    eligible = sum(1 for r in scoped if r.get("eligible") is True)
    seeded = sum(1 for r in scoped if int(r.get("observations") or 0) > 0)
    statistics = sum(1 for r in scoped if r.get("has_statistics"))
    return {
        "source": "hvie_universe_queue",
        "universe": len(scoped),
        "eligible": eligible,
        "seeded_history": seeded,
        "statistics": statistics,
        "percentiles": percentiles,
        "bands": bands,
        "regimes": regimes,
        "research": research,
        "complete": complete,
        "historical_percentile_pct": _pct(percentiles, n),
        "historical_bands_pct": _pct(bands, n),
        "regime_pct": _pct(regimes, n),
        "complete_pct": _pct(complete, n),
    }


def _intelligence_coverage(universe_syms: set[str], evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(universe_syms)
    hvie_rows = []
    try:
        hvie_rows = _paged_rows("hvie_company_state", max_rows=20_000)
    except Exception:
        hvie_rows = []

    hvie_by_sym = {
        str(r.get("symbol") or "").strip().upper(): r
        for r in hvie_rows
        if r.get("symbol")
    }
    research = _entity_set("research_intelligence")
    timeline = _entity_set("research_timeline")

    percentile = 0
    bands = 0
    regime = 0
    for sym in universe_syms:
        st = hvie_by_sym.get(sym) or {}
        if not st.get("seeded"):
            continue
        if st.get("last_percentile") is not None:
            percentile += 1
        # Bands implied by seeded historical state with observations
        if int(st.get("observations") or 0) >= 12 or st.get("last_percentile") is not None:
            bands += 1
        if st.get("last_regime"):
            regime += 1

    # Prefer queue completion plane when the universe programme has classified names.
    pipe = _hvie_pipeline_snapshot(universe_syms)
    if pipe and int(pipe.get("universe") or 0) >= max(1, int(0.5 * n)):
        percentile = int(pipe.get("percentiles") or percentile)
        bands = int(pipe.get("bands") or bands)
        regime = int(pipe.get("regimes") or regime)

    varie = len((research | timeline) & universe_syms)
    research_summary = len(research & universe_syms)
    confidence = sum(
        1
        for row in evaluated
        if row.get("symbol") in universe_syms
        and str(row.get("confidence") or "").upper() in {"HIGH", "MEDIUM"}
    )

    layers = {
        "historical_percentile": _pct(percentile, n),
        "historical_bands": _pct(bands, n),
        "regime": _pct(regime, n),
        "varie": _pct(varie, n),
        "research_summary": _pct(research_summary, n),
        "confidence": _pct(confidence, n),
    }
    hist_pct = round(
        (layers["historical_percentile"] + layers["historical_bands"] + layers["regime"]) / 3.0,
        1,
    )
    research_intel_pct = round((layers["varie"] + layers["research_summary"]) / 2.0, 1)
    return {
        "pct": round(sum(layers.values()) / max(len(layers), 1), 1),
        "historical_intelligence_pct": hist_pct,
        "research_intelligence_pct": research_intel_pct,
        "layers": layers,
        "counts": {
            "historical_percentile": percentile,
            "historical_bands": bands,
            "regime": regime,
            "varie": varie,
            "research_summary": research_summary,
            "confidence": confidence,
        },
        "universe": n,
        "hvie_seeded": sum(1 for s in universe_syms if (hvie_by_sym.get(s) or {}).get("seeded")),
        "hvie_pipeline": pipe,
    }


def _dqiv_pct(expected: list[dict[str, Any]]) -> float:
    if not expected:
        return 0.0
    ok = 0
    for row in expected:
        dq = str(row.get("dqiv") or "").upper()
        if dq in {"FAIL", "REJECT", "ERROR"}:
            continue
        # PASS / WARN / missing DQIV with a covered valuation all count as usable
        if dq in {"PASS", "OK", "VALID", "HIGH", "CLEAN", "WARN", "WARNING"} or row.get("valuation_covered") is True:
            ok += 1
        elif not dq:
            ok += 1
    return _pct(ok, len(expected))


def _valuation_block(evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    expected = [r for r in evaluated if r.get("valuation_covered") is not None]
    covered_rows = [r for r in expected if r.get("valuation_covered") is True]
    missing = [r for r in expected if r.get("valuation_covered") is False]
    excluded = [r for r in evaluated if r.get("valuation_covered") is None]

    by_model: dict[str, int] = {}
    for r in covered_rows:
        model = str(r.get("primary_model") or "UNKNOWN")
        by_model[model] = by_model.get(model, 0) + 1

    by_reason: dict[str, int] = {}
    for r in missing:
        code = str(r.get("reason_code") or "unknown")
        by_reason[code] = by_reason.get(code, 0) + 1

    examples = [
        {
            "symbol": r["symbol"],
            "company": r.get("company"),
            "primary_model": r.get("primary_model"),
            "available": True,
            "status": r.get("status"),
        }
        for r in covered_rows[:8]
    ]

    return {
        "pct": _pct(len(covered_rows), len(expected)),
        "covered": len(covered_rows),
        "expected": len(expected),
        "excluded_not_applicable": len(excluded),
        "missing": len(missing),
        "by_primary_model": dict(sorted(by_model.items(), key=lambda kv: (-kv[1], kv[0]))),
        "missing_by_reason": dict(sorted(by_reason.items(), key=lambda kv: (-kv[1], kv[0]))),
        "examples": examples,
        "definition": (
            "Companies with a valid primary valuation model (VPAE) and sufficient "
            "supporting data, divided by companies expected to have a valuation model. "
            "NOT_APPLICABLE instruments are excluded from the denominator."
        ),
    }


def _research_block(
    universe_syms: set[str],
    evaluated: list[dict[str, Any]],
    annual_by_sym: dict[str, dict[str, Any]],
    provider_by_symbol: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    n = len(universe_syms)
    hvie = _entity_set("hvie_company_state")
    # Seeded subset
    seeded: set[str] = set()
    try:
        from institutional_warehouse import store

        for r in store.all_rows("hvie_company_state", limit=8000) or []:
            if r.get("seeded"):
                seeded.add(str(r.get("symbol") or "").strip().upper())
    except Exception:
        seeded = hvie

    by_sym = {r["symbol"]: r for r in evaluated}
    covered_val = {r["symbol"] for r in evaluated if r.get("valuation_covered") is True}
    needs_statements = []
    needs_history = []
    needs_ratios = []
    needs_review = []
    ready = []

    for sym in sorted(universe_syms):
        has_stmt = sym in annual_by_sym
        has_hist = sym in seeded
        has_ratios = bool((provider_by_symbol.get(sym) or {}).get("ratios"))
        has_val = sym in covered_val
        row = by_sym.get(sym)
        dq = str((row or {}).get("dqiv") or "").upper()

        if has_stmt and has_hist and has_ratios and has_val and dq not in {"FAIL", "REJECT", "ERROR"}:
            ready.append(sym)
        elif not has_stmt:
            needs_statements.append(sym)
        elif not has_hist:
            needs_history.append(sym)
        elif not has_ratios:
            needs_ratios.append(sym)
        else:
            needs_review.append(sym)

    return {
        "research_ready": len(ready),
        "pct": _pct(len(ready), n),
        "universe": n,
        "needs_statements": len(needs_statements),
        "needs_history": len(needs_history),
        "needs_ratios": len(needs_ratios),
        "needs_review": len(needs_review),
        "samples": {
            "needs_statements": needs_statements[:12],
            "needs_history": needs_history[:12],
            "needs_ratios": needs_ratios[:12],
            "needs_review": needs_review[:12],
        },
    }


def _residual_block(
    masters: list[dict[str, Any]],
    provider_by_symbol: dict[str, dict[str, Any]],
    evaluated: list[dict[str, Any]],
) -> dict[str, Any]:
    missing_isin = []
    no_fundamentals = []
    provider_failure = []
    delisted = []
    insufficient = []

    for master in masters:
        sym = str(master.get("symbol") or "").strip().upper()
        if _is_delisted(master):
            delisted.append(sym)
            continue
        if not _has_isin(master):
            missing_isin.append(sym)
            continue
        if not (provider_by_symbol.get(sym) or {}).get("ratios"):
            # Distinguish failure vs never attempted using evaluation reason when present
            row = next((r for r in evaluated if r["symbol"] == sym), None)
            if row and row.get("reason_code") == "insufficient_data":
                insufficient.append(sym)
            no_fundamentals.append(sym)

    # Provider failures approximated via DQIV FAIL on evaluated rows with ISIN
    for row in evaluated:
        if str(row.get("dqiv") or "").upper() in {"FAIL", "REJECT", "ERROR"} and row.get("has_isin"):
            provider_failure.append(row["symbol"])

    residual = sorted(set(missing_isin) | set(no_fundamentals) | set(provider_failure) | set(delisted))
    with_ratios = sum(
        1 for m in masters
        if (provider_by_symbol.get(str(m.get("symbol") or "").strip().upper()) or {}).get("ratios")
    )
    return {
        "residual_missing": len(residual),
        "missing_isin": len(missing_isin),
        "isin_available": max(0, len(masters) - len(missing_isin) - len(delisted)),
        "with_upstox_key_ratios": with_ratios,
        "no_upstox_fundamentals": len(no_fundamentals),
        "provider_failure": len(set(provider_failure)),
        "delisted": len(delisted),
        "insufficient_valuation_inputs": len(insufficient),
        "samples": {
            "missing_isin": missing_isin[:20],
            "no_upstox_fundamentals": no_fundamentals[:20],
            "provider_failure": sorted(set(provider_failure))[:20],
            "delisted": delisted[:20],
        },
        "note": (
            "Residual gaps are warehouse-derived from a full paged scan of "
            "valuation_ratios (not the 5k store.all_rows cap). Live bootstrap "
            "queue states (Pending / Retry / Failed / ETA) come from "
            "/api/market/upstox-bootstrap/status and may read 0 after Node redeploy."
        ),
    }


def coverage_health(*, limit: int = 6000, force: bool = False) -> dict[str, Any]:
    """Full five-layer coverage dashboard payload."""
    now_ts = time.time()
    if (
        not force
        and _CACHE["payload"] is not None
        and _CACHE.get("limit") == limit
        and (now_ts - float(_CACHE.get("at") or 0)) < _CACHE_TTL_SEC
    ):
        cached = dict(_CACHE["payload"])
        cached["cached"] = True
        return cached

    try:
        masters = _load_masters()
    except Exception as exc:
        return {
            "ok": False,
            "error": f"warehouse_unavailable:{exc}",
            "engine": ENGINE_CODE,
            "version": VERSION,
        }

    if limit and len(masters) > limit:
        masters = masters[:limit]

    universe_n = len(masters)
    universe_syms = {str(m.get("symbol") or "").strip().upper() for m in masters}

    provider_by_symbol = _provider_ratio_index()
    annual_by_sym = _annual_index()
    evaluated = _evaluate_universe(masters, provider_by_symbol, annual_by_sym)

    valuation = _valuation_block(evaluated)
    data = _data_coverage(universe_syms, masters, annual_by_sym, provider_by_symbol)
    metrics = _metric_coverage_block(universe_syms, provider_by_symbol)
    intelligence = _intelligence_coverage(universe_syms, evaluated)
    research = _research_block(universe_syms, evaluated, annual_by_sym, provider_by_symbol)
    residual = _residual_block(masters, provider_by_symbol, evaluated)

    expected = [r for r in evaluated if r.get("valuation_covered") is not None]
    dqiv_pct = _dqiv_pct(expected)

    tracked = universe_n  # MI / warehouse tracked = master count today
    universe_pct = _pct(tracked, universe_n) if universe_n else 0.0

    dashboard = [
        _layer("Universe", universe_pct, covered=tracked, universe=universe_n),
        _layer("Raw Data", data["pct"], covered=data["counts"]["key_ratios"], universe=universe_n),
        _layer(
            "Valuation",
            valuation["pct"],
            covered=valuation["covered"],
            universe=valuation["expected"],
        ),
        _layer(
            "Historical Intelligence",
            intelligence["historical_intelligence_pct"],
            covered=intelligence["counts"]["historical_percentile"],
            universe=universe_n,
        ),
        _layer(
            "Research Intelligence",
            intelligence["research_intelligence_pct"],
            covered=intelligence["counts"]["research_summary"],
            universe=universe_n,
        ),
        _layer("DQIV", dqiv_pct, covered=int(round(dqiv_pct * valuation["expected"] / 100.0)) if valuation["expected"] else 0, universe=valuation["expected"]),
    ]

    hvie_pipe = intelligence.get("hvie_pipeline") or {}
    hvie_pipeline_dashboard = None
    if hvie_pipe:
        hvie_pipeline_dashboard = [
            {"name": "Universe", "count": hvie_pipe.get("universe"), "pct": 100.0},
            {"name": "Eligible", "count": hvie_pipe.get("eligible")},
            {"name": "Seeded", "count": hvie_pipe.get("seeded_history")},
            {"name": "History Built", "count": hvie_pipe.get("seeded_history")},
            {"name": "Statistics", "count": hvie_pipe.get("statistics")},
            {"name": "Percentiles", "count": hvie_pipe.get("percentiles")},
            {"name": "Bands", "count": hvie_pipe.get("bands")},
            {"name": "Regimes", "count": hvie_pipe.get("regimes")},
            {"name": "Research Timeline", "count": hvie_pipe.get("research")},
            {"name": "Complete", "count": hvie_pipe.get("complete")},
        ]

    payload = {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "primary_kpi": "valuation_coverage",
        "definition": health()["definition"],
        "universe": {
            "companies": universe_n,
            "tracked": tracked,
            "pct": universe_pct,
        },
        "data_coverage": data,
        "valuation_coverage": valuation,
        "metric_coverage": metrics,
        "intelligence_coverage": intelligence,
        "hvie_pipeline": hvie_pipe,
        "hvie_pipeline_dashboard": hvie_pipeline_dashboard,
        "research_coverage": research,
        "residual_gap": residual,
        "dashboard": dashboard,
        "legacy_note": (
            "Do not use (PE OR Upstox ratios) / company_master as the primary KPI — "
            "it mixes data availability with valuation applicability."
        ),
        "vpae_integration": {
            "example": {
                "metric": "PE",
                "status": "Unavailable",
                "reason": "Negative earnings",
                "primary_model": "EV/Sales",
                "coverage": "Complete",
            },
            "rule": (
                "Unavailable applicable metrics are not counted as missing coverage "
                "when a valid primary model exists."
            ),
        },
        "language": "analysis_only",
        "checked_at": _now(),
        "cached": False,
    }
    _CACHE["payload"] = payload
    _CACHE["at"] = now_ts
    _CACHE["limit"] = limit
    return payload


def valuation_coverage(*, limit: int = 6000) -> dict[str, Any]:
    pack = coverage_health(limit=limit)
    if not pack.get("ok"):
        return pack
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "valuation_coverage": pack["valuation_coverage"],
        "universe": pack["universe"],
        "checked_at": pack["checked_at"],
    }


def metric_coverage(*, limit: int = 6000) -> dict[str, Any]:
    pack = coverage_health(limit=limit)
    if not pack.get("ok"):
        return pack
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "metric_coverage": pack["metric_coverage"],
        "universe": pack["universe"],
        "checked_at": pack["checked_at"],
    }


def research_coverage(*, limit: int = 6000) -> dict[str, Any]:
    pack = coverage_health(limit=limit)
    if not pack.get("ok"):
        return pack
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "research_coverage": pack["research_coverage"],
        "checked_at": pack["checked_at"],
    }


def bootstrap_residual(*, limit: int = 6000) -> dict[str, Any]:
    pack = coverage_health(limit=limit)
    if not pack.get("ok"):
        return pack
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "residual_gap": pack["residual_gap"],
        "universe": pack["universe"],
        "bootstrap_hint": {
            "status_api": "/api/market/upstox-bootstrap/status",
            "missing_isin_api": "/api/market/upstox-bootstrap/missing-isin",
            "failures_api": "/api/market/upstox-bootstrap/failures",
        },
        "checked_at": pack["checked_at"],
    }
