"""The valuation service every AGI product reads.

Consumers ask one question and get a whole answer — valuation, sector context,
coverage and provenance together — rather than stitching five calls and
re-deriving the same multiple three different ways. That stitching is what let
the terminal, Ask and the warehouse disagree in the first place.
"""

from __future__ import annotations

from statistics import median
from typing import Any, Optional

from valuation_engine import attribution, engine, graph

ENGINE_CODE = "unified_valuation_engine"
VERSION = "3.0"

#: Multiples a sector median is worth taking. Money amounts are not comparable
#: across companies of different size.
_COMPARABLE = ("pe", "pb", "ev_ebitda", "ev_sales", "ps", "dividend_yield", "roe", "roa", "roce")


def _policy_for(symbol: str, record: dict[str, Any]) -> dict[str, Any]:
    """Mandatory VPAE gate — every valuation response carries policy."""
    try:
        from valuation_policy import evaluate

        return evaluate(symbol, record=record) or {}
    except Exception:
        # Fall back to sector_lens baseline so a policy import failure never
        # blanks the terminal — but mark that the gate degraded.
        try:
            from valuation_terminal.sector_lens import lens_for

            master = record.get("master") or {}
            lens = lens_for(master.get("industry_dna") or master.get("industry"), master.get("sector")) or {}
            return {
                "ok": True,
                "degraded": True,
                "primary_metric": lens.get("primary_metric") or "pe",
                "primary_model": str(lens.get("primary_metric") or "pe").upper(),
                "supporting_metrics": list(lens.get("supporting_metrics") or []),
                "hidden_metrics": list(lens.get("suppressed_metrics") or []),
                "unavailable_metrics": [],
                "status": "UNDER_REVIEW",
                "reason": lens.get("rationale") or "Degraded to sector_lens baseline.",
                "confidence": "LOW",
                "coverage": "PARTIAL",
                "lens_baseline": lens,
            }
        except Exception:
            return {}


def _sector_lens(industry_dna: Optional[str], sector: Optional[str],
                 policy: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Lens payload for consumers — VPAE-enriched when policy is present."""
    if policy and policy.get("ok"):
        baseline = policy.get("lens_baseline") or {}
        return {
            "industry_dna": (policy.get("company") or {}).get("industry_dna") or industry_dna,
            "primary_sector": (policy.get("company") or {}).get("sector") or sector,
            "primary_metric": policy.get("primary_metric") or baseline.get("primary_metric") or "pe",
            "primary_metric_label": policy.get("primary_model") or baseline.get("primary_metric_label"),
            "supporting_metrics": list(policy.get("supporting_metrics") or []),
            "suppressed_metrics": list(policy.get("hidden_metrics") or []),
            "visible_metrics": [
                policy.get("primary_metric"),
                *[m for m in (policy.get("supporting_metrics") or []) if m != policy.get("primary_metric")],
            ],
            "rationale": policy.get("reason") or baseline.get("rationale"),
            "status": policy.get("status"),
            "confidence": policy.get("confidence"),
            "policy_engine": policy.get("engine"),
        }
    try:
        from valuation_terminal.sector_lens import lens_for

        return lens_for(industry_dna, sector) or {}
    except Exception:
        return {}


def _visible(metric: str, industry_dna: Optional[str],
             policy: Optional[dict[str, Any]] = None) -> bool:
    """Whether a metric means anything for this business.

    A bank has no conventional enterprise value, so EV/EBITDA is hidden rather
    than shown as a number nobody should read. VPAE is the authority when present.
    """
    if policy and policy.get("ok"):
        try:
            from valuation_policy import is_meaningful

            return bool(is_meaningful(metric, policy))
        except Exception:
            pass
    try:
        from valuation_terminal.sector_lens import is_meaningful as lens_meaningful

        return bool(lens_meaningful(metric, industry_dna))
    except Exception:
        return True


def _percentile(value: Optional[float], series: list[float]) -> Optional[float]:
    if value is None or len(series) < 5:
        return None
    below = sum(1 for item in series if item <= value)
    return round(100.0 * below / len(series), 1)


def get_company_valuation(symbol: str, *, record: Optional[dict[str, Any]] = None,
                          peers: Optional[list[dict[str, Any]]] = None,
                          history: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    """One company's valuation with the context needed to read it."""
    ticker = str(symbol or "").strip().upper()
    if record is None:
        from institutional_warehouse.production import read_company

        record = read_company(ticker)
    if not record or not record.get("ok", True):
        return {"ok": False, "symbol": ticker, "error": "not_in_warehouse",
                "engine": ENGINE_CODE, "version": VERSION}

    master = record.get("master") or {}
    industry_dna = master.get("industry_dna") or master.get("industry")
    sector = master.get("sector")

    # Attach latest Upstox ratios when the caller did not already supply them.
    if not record.get("provider_ratios"):
        try:
            from valuation_ratios.ingest import latest_provider_ratios

            record = {**record, "provider_ratios": latest_provider_ratios(ticker)}
        except Exception:
            pass

    # Policy first — UVE computes numbers; VPAE decides what may be shown.
    policy = _policy_for(ticker, record)
    if policy.get("ok") and (policy.get("company") or {}).get("industry_dna"):
        industry_dna = policy["company"]["industry_dna"]

    values = engine.compute(record)
    lens = _sector_lens(industry_dna, sector, policy)
    provider = (record.get("provider_ratios") or {}).get("ratios") or {}

    metrics: dict[str, Any] = {}
    for name, value in values.items():
        payload = value.to_dict()
        payload["meaningful"] = _visible(name, industry_dna, policy)
        policy_metric = (policy.get("metrics") or {}).get(name) if policy else None
        if policy_metric:
            payload["applicability"] = {
                "status": policy_metric.get("status"),
                "reason": policy_metric.get("reason"),
                "confidence": policy_metric.get("confidence"),
                "model": policy_metric.get("model"),
            }
        if name in provider and isinstance(provider.get(name), dict):
            payload["provider"] = {
                "source": "upstox",
                "sector_value": provider[name].get("sector_value"),
                "reported_date": provider[name].get("reported_date"),
                "dqiv_status": provider[name].get("dqiv_status"),
                "confidence": provider[name].get("confidence"),
            }
        metrics[name] = payload

    # Sector and historical context, once the company's own multiples exist.
    # Prefer Upstox sector_value over peer-sample medians when available.
    peer_rows = peers or []
    history_rows = history or []
    context: dict[str, Any] = {}
    for name in _COMPARABLE:
        own = values.get(name)
        own_value = own.value if own else None
        peer_series = [v for v in (_as_number(p.get(name)) for p in peer_rows) if v is not None]
        past_series = [v for v in (_as_number(h.get(name)) for h in history_rows) if v is not None]
        provider_sector = None
        if isinstance(provider.get(name), dict):
            provider_sector = _as_number(provider[name].get("sector_value"))
        sector_median = provider_sector if provider_sector is not None else (
            round(median(peer_series), 4) if peer_series else None
        )
        context[name] = {
            "sector_median": sector_median,
            "sector_source": "upstox" if provider_sector is not None else ("peers" if peer_series else None),
            "peer_count": len(peer_series),
            "premium_pct": (round(100.0 * (own_value - sector_median) / sector_median, 2)
                            if own_value is not None and sector_median else None),
            "historical_median": round(median(past_series), 4) if past_series else None,
            "historical_percentile": _percentile(own_value, past_series),
            "observations": len(past_series),
        }

    return {
        "ok": True,
        "symbol": ticker,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "company": {
            "name": master.get("company_name"),
            "sector": sector,
            "industry": industry_dna,
            "instrument_type": (policy.get("company") or {}).get("instrument_type"),
        },
        "metrics": metrics,
        "context": context,
        "lens": lens,
        "policy": {
            "ok": bool(policy.get("ok")),
            "primary_model": policy.get("primary_model"),
            "primary_metric": policy.get("primary_metric"),
            "supporting_models": policy.get("supporting_models") or [],
            "supporting_metrics": policy.get("supporting_metrics") or [],
            "hidden_models": policy.get("hidden_models") or [],
            "hidden_metrics": policy.get("hidden_metrics") or [],
            "unavailable_models": policy.get("unavailable_models") or [],
            "unavailable_metrics": policy.get("unavailable_metrics") or [],
            "status": policy.get("status"),
            "reason": policy.get("reason"),
            "reason_codes": policy.get("reason_codes") or [],
            "confidence": policy.get("confidence"),
            "coverage": policy.get("coverage"),
            "metrics": policy.get("metrics") or {},
            "dqiv": policy.get("dqiv"),
            "engine": policy.get("engine"),
            "version": policy.get("version"),
            "provenance": policy.get("provenance"),
        } if policy else None,
        "coverage": _coverage(values, industry_dna, policy),
        "provenance": _provenance(record, values),
    }


def _as_number(value: Any) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _coverage(
    values: dict[str, engine.Value],
    industry_dna: Optional[str],
    policy: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """What could be computed, counted only over metrics that apply here."""
    applicable = [name for name in graph.METRICS
                  if name not in ("sector_premium", "historical_percentile", "relative_score")
                  and _visible(name, industry_dna, policy)]
    available = [name for name in applicable
                 if values.get(name) and values[name].available]
    unavailable = {
        name: values[name].note or f"needs {', '.join(values[name].missing)}"
        for name in applicable
        if values.get(name) and not values[name].available
    }
    out = {
        "applicable": len(applicable),
        "available": len(available),
        "pct": round(100.0 * len(available) / len(applicable), 1) if applicable else 0.0,
        "unavailable": unavailable,
    }
    if policy and policy.get("coverage_detail"):
        out["policy"] = policy["coverage_detail"]
    return out


def _provenance(record: dict[str, Any], values: dict[str, engine.Value]) -> dict[str, Any]:
    """Where the numbers came from, read from row metadata rather than assumed.

    Nothing here names a vendor: a row states its own source, so the display
    stays correct when a new provider starts writing.
    """
    def block(key: str) -> dict[str, Any]:
        row = record.get(key) or {}
        meta = row.get("_meta") if isinstance(row.get("_meta"), dict) else {}
        return {
            "source": row.get("source") or meta.get("source"),
            "updated_at": meta.get("updated_at") or row.get("last_updated"),
            "version": meta.get("version"),
            "reported_unit": meta.get("reported_unit"),
            "confidence": meta.get("confidence"),
        }

    sources = sorted({s for value in values.values() for s in value.sources})
    provider = record.get("provider_ratios") or {}
    return {
        "price": block("latest_price"),
        "financials": block("latest_annual"),
        "consensus": block("consensus"),
        "provider_ratios": {
            "source": provider.get("source") or ("upstox" if provider.get("ratios") else None),
            "as_of": provider.get("as_of"),
            "ratios": list((provider.get("ratios") or {}).keys()),
        },
        "freshness": {},
        "sources": sources,
        "formula": ENGINE_CODE,
        "formula_version": VERSION,
    }


def get_sector_valuation(sector: str, *, companies: list[dict[str, Any]]) -> dict[str, Any]:
    """Sector medians and distribution from already-computed company valuations."""
    name = str(sector or "").strip()
    rows = [c for c in companies if str((c.get("company") or {}).get("sector") or "") == name]
    out: dict[str, Any] = {}
    for metric in _COMPARABLE:
        series = [v for v in (
            _as_number(((c.get("metrics") or {}).get(metric) or {}).get("value")) for c in rows
        ) if v is not None]
        if not series:
            continue
        ordered = sorted(series)
        out[metric] = {
            "median": round(median(ordered), 4),
            "low": ordered[0],
            "high": ordered[-1],
            "companies": len(ordered),
        }
    return {
        "ok": True,
        "sector": name,
        "companies": len(rows),
        "metrics": out,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def explain_valuation_change(symbol: str, before: dict[str, Any],
                             after: dict[str, Any]) -> dict[str, Any]:
    """Why this company's multiples moved between two observations."""
    return {"ok": True, "symbol": str(symbol or "").upper(),
            **attribution.change_log(before, after)}


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "metrics": list(graph.METRICS),
        "computation_order": graph.topological(),
        "reads": "institutional_warehouse",
    }
