"""API-facing Valuation Policy & Applicability Engine surface."""

from __future__ import annotations

from typing import Any, Optional

from valuation_policy.engine import applicable_metrics, evaluate, is_meaningful
from valuation_policy.models import ENGINE_CODE, VERSION


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "role": "mandatory_valuation_policy_layer",
        "gates": ["unified_valuation_engine", "valuation_terminal", "market_intelligence", "ask_agi"],
        "extends": "valuation_terminal.sector_lens",
        "endpoints": [
            "/v1/valuation/applicability/{symbol}",
            "/v1/valuation/model/{symbol}",
            "/v1/valuation/explanation/{symbol}",
            "/v1/valuation/coverage/{symbol}",
            "/v1/valuation/status/{symbol}",
            "/v1/valuation/universe",
            "/v1/valuation-policy/health",
        ],
    }


def applicability(symbol: str, *, record: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return evaluate(symbol, record=record)


def model(symbol: str, *, record: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    policy = evaluate(symbol, record=record)
    if not policy.get("ok"):
        return policy
    return {
        "ok": True,
        "symbol": policy["symbol"],
        "engine": ENGINE_CODE,
        "version": VERSION,
        "primary_model": policy["primary_model"],
        "primary_metric": policy["primary_metric"],
        "supporting_models": policy["supporting_models"],
        "hidden_models": policy["hidden_models"],
        "unavailable_models": policy["unavailable_models"],
        "status": policy["status"],
        "confidence": policy["confidence"],
        "company": policy.get("company"),
    }


def explanation(symbol: str, *, record: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    policy = evaluate(symbol, record=record)
    if not policy.get("ok"):
        return policy
    hidden = []
    for metric in policy.get("hidden_metrics") or []:
        entry = (policy.get("metrics") or {}).get(metric) or {}
        hidden.append(
            {
                "model": entry.get("model") or metric.upper(),
                "metric": metric,
                "status": "Hidden",
                "reason": entry.get("reason"),
                "confidence": entry.get("confidence"),
                "source": entry.get("source"),
            }
        )
    unavailable = []
    for metric in policy.get("unavailable_metrics") or []:
        entry = (policy.get("metrics") or {}).get(metric) or {}
        unavailable.append(
            {
                "model": entry.get("model") or metric.upper(),
                "metric": metric,
                "status": "Unavailable",
                "reason": entry.get("reason"),
                "confidence": entry.get("confidence"),
                "source": entry.get("source"),
            }
        )
    return {
        "ok": True,
        "symbol": policy["symbol"],
        "engine": ENGINE_CODE,
        "version": VERSION,
        "primary_model": policy["primary_model"],
        "why": policy["reason"],
        "status": policy["status"],
        "confidence": policy["confidence"],
        "reason_codes": policy.get("reason_codes") or [],
        "supporting_models": policy["supporting_models"],
        "hidden": hidden,
        "unavailable": unavailable,
        "ask_summary": _ask_summary(policy),
        "provenance": policy.get("provenance"),
    }


def coverage(symbol: str, *, record: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    policy = evaluate(symbol, record=record)
    if not policy.get("ok"):
        return policy
    detail = policy.get("coverage_detail") or {}
    return {
        "ok": True,
        "symbol": policy["symbol"],
        "engine": ENGINE_CODE,
        "version": VERSION,
        "coverage": policy.get("coverage"),
        "financial_coverage": detail.get("financial_coverage"),
        "statement_coverage": detail.get("statement_coverage"),
        "historical_coverage": detail.get("historical_coverage"),
        "market_coverage": detail.get("market_coverage"),
        "missing_fields": detail.get("missing_fields") or [],
        "confidence": policy.get("confidence"),
        "status": policy.get("status"),
        "applicable_metrics": applicable_metrics(policy),
    }


def status(symbol: str, *, record: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    policy = evaluate(symbol, record=record)
    if not policy.get("ok"):
        return policy
    return {
        "ok": True,
        "symbol": policy["symbol"],
        "engine": ENGINE_CODE,
        "version": VERSION,
        "status": policy["status"],
        "primary_model": policy["primary_model"],
        "confidence": policy["confidence"],
        "coverage": policy["coverage"],
        "reason": policy["reason"],
        "dqiv": policy.get("dqiv"),
        "instrument_type": (policy.get("company") or {}).get("instrument_type"),
        "industry_dna": (policy.get("company") or {}).get("industry_dna"),
    }


def _ask_summary(policy: dict[str, Any]) -> str:
    name = (policy.get("company") or {}).get("name") or policy.get("symbol")
    lines = [
        f"Primary Valuation Model: {policy.get('primary_model')}",
        f"Reason: {policy.get('reason')}",
    ]
    supporting = policy.get("supporting_models") or []
    if supporting:
        lines.append("Supporting Metrics: " + ", ".join(supporting))
    hidden = policy.get("hidden_models") or []
    if hidden:
        lines.append("Hidden Metrics: " + ", ".join(hidden))
    lines.append(f"Status: {policy.get('status')}")
    lines.append(f"Confidence: {policy.get('confidence')}")
    lines.insert(0, f"{name}")
    return "\n".join(lines)


def universe(
    *,
    sector: Optional[str] = None,
    instrument_type: Optional[str] = None,
    primary_model: Optional[str] = None,
    status_filter: Optional[str] = None,
    confidence: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    """Admin listing — evaluates policy for a page of company_master rows."""
    try:
        from institutional_warehouse import store
    except Exception as exc:
        return {"ok": False, "error": f"warehouse_unavailable:{exc}", "rows": []}

    rows_raw = store.all_rows("company_master", limit=6000) or []
    # Normalize
    masters = []
    for r in rows_raw:
        sym = str(r.get("symbol") or "").strip().upper()
        if not sym:
            continue
        masters.append(r)

    # Cheap pre-filter on master fields before full evaluate.
    if sector:
        sec = sector.strip().lower()
        masters = [r for r in masters if str(r.get("sector") or "").strip().lower() == sec]

    # Optional provider-ratio index (symbol → payload) — one pass, no N+1.
    # valuation_ratios is long-form: one row per (symbol, ratio_name).
    provider_by_symbol: dict[str, dict[str, Any]] = {}
    try:
        ratio_rows = store.all_rows("valuation_ratios", limit=20000) or []
        # Newest first so first sighting of a ratio wins.
        ratio_rows = sorted(
            ratio_rows,
            key=lambda r: str(r.get("reported_date") or ""),
            reverse=True,
        )
        for rr in ratio_rows:
            sym = str(rr.get("symbol") or "").strip().upper()
            name = str(rr.get("ratio_name") or "").strip().lower()
            if not sym or name not in {"pe", "pb", "roa", "roe", "roce", "ev_ebitda"}:
                continue
            bucket = provider_by_symbol.setdefault(
                sym, {"source": rr.get("source") or rr.get("provider") or "upstox", "ratios": {}}
            )
            if name in bucket["ratios"]:
                continue
            bucket["ratios"][name] = {
                "company_value": rr.get("company_value"),
                "sector_value": rr.get("sector_value"),
                "reported_date": rr.get("reported_date"),
                "dqiv_status": rr.get("dqiv_status"),
                "confidence": rr.get("confidence"),
            }
    except Exception:
        provider_by_symbol = {}

    evaluated: list[dict[str, Any]] = []
    # Evaluate a working window larger than page so post-filters still fill.
    scan_cap = min(len(masters), max((limit + offset) * 5, limit + 200))
    for r in masters[:scan_cap]:
        sym = str(r.get("symbol") or "").strip().upper()
        record = {
            "ok": True,
            "symbol": sym,
            "master": r,
            "latest_annual": {},
            "latest_price": {},
            "provider_ratios": provider_by_symbol.get(sym) or {},
            "coverage": {},
        }
        policy = evaluate(sym, record=record)
        if not policy.get("ok"):
            continue
        company = policy.get("company") or {}
        if instrument_type and str(company.get("instrument_type") or "").upper() != instrument_type.upper():
            continue
        if primary_model and str(policy.get("primary_model") or "").upper() != primary_model.upper():
            continue
        if status_filter and str(policy.get("status") or "").upper() != status_filter.upper():
            continue
        if confidence and str(policy.get("confidence") or "").upper() != confidence.upper():
            continue
        evaluated.append(
            {
                "symbol": policy["symbol"],
                "company": company.get("name"),
                "sector": company.get("sector"),
                "industry_dna": company.get("industry_dna"),
                "instrument_type": company.get("instrument_type"),
                "primary_model": policy.get("primary_model"),
                "supporting_models": policy.get("supporting_models"),
                "hidden_models": policy.get("hidden_models"),
                "status": policy.get("status"),
                "confidence": policy.get("confidence"),
                "reason": policy.get("reason"),
                "coverage": policy.get("coverage"),
                "dqiv": (policy.get("dqiv") or {}).get("status"),
                "dqiv_warnings": (policy.get("dqiv") or {}).get("warnings") or [],
                "provenance": policy.get("provenance"),
            }
        )

    page = evaluated[offset : offset + limit]
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "total_scanned": scan_cap,
        "total_matched": len(evaluated),
        "offset": offset,
        "limit": limit,
        "rows": page,
        "filters": {
            "sector": sector,
            "instrument_type": instrument_type,
            "primary_model": primary_model,
            "status": status_filter,
            "confidence": confidence,
        },
    }


# Re-export helpers used by UVE gating.
__all__ = [
    "health",
    "applicability",
    "model",
    "explanation",
    "coverage",
    "status",
    "universe",
    "evaluate",
    "is_meaningful",
    "applicable_metrics",
]
