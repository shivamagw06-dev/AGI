"""Cross-sectional screening over the versioned sector-ratio warehouse.

The workbook is annual historical evidence, not a live quote source.  Results
therefore carry the latest fiscal as-of date and remain research screens rather
than recommendations.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Any, Iterable

from valuation_intelligence.conditioning import percentile_rank, premium_discount, quality_matrix


METRIC_ALIASES = {
    "p/e": "pe", "pe": "pe", "p/b": "pb", "p/bv": "pb", "pb": "pb",
    "p/tbv": "ptbv", "ptbv": "ptbv", "ev/ebitda": "ev_ebitda",
    "ev_ebitda": "ev_ebitda", "ev/sales": "ev_sales", "ev_sales": "ev_sales",
    "fcf yield": "fcf_yield", "fcf_yield": "fcf_yield",
}
COMPARABLE_MULTIPLES = {"pe", "pb", "ptbv", "p_assets", "ev_ebitda", "ev_sales"}
QUALITY_METRICS = {"roe", "ebitda_margin", "fcf_yield", "net_debt_ebitda", "debt_equity"}
SECTOR_ALIASES = {
    "bank": "Banks", "banks": "Banks", "nbfc": "NBFC_Finance", "nbfcs": "NBFC_Finance",
    "insurance": "Insurance", "it": "IT", "technology": "IT", "oil and gas": "Oil_Gas",
    "oil & gas": "Oil_Gas", "power": "Power", "telecom": "Telecom",
}
BROAD_SECTORS = {
    "Financials", "Information Technology", "Health Care", "Consumer Staples",
    "Consumer Discretionary", "Industrials", "Materials", "Communication Services",
    "Energy", "Utilities", "Real Estate",
}


def _year(value: Any) -> int | None:
    try:
        return int(str(value or "").upper().replace("FY", ""))
    except (TypeError, ValueError):
        return None


def _number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and abs(out) != float("inf") else None


def _median(values: Iterable[float | None]) -> float | None:
    clean = [float(value) for value in values if isinstance(value, (int, float))]
    return round(float(statistics.median(clean)), 4) if clean else None


def build_screen(
    rows: list[dict[str, Any]], *, metric: str, sector: str | None = None,
    window_years: int = 10, limit: int = 25, sort: str = "cheapest",
    max_historical_percentile: int | None = None, min_discount_pct: int | None = None,
    min_roe: int | None = None, min_ebitda_margin: int | None = None,
) -> dict[str, Any]:
    """Build a deterministic screen from already-governed warehouse rows."""
    canonical = METRIC_ALIASES.get(str(metric or "").strip().lower(), str(metric or "").strip().lower())
    window_years = max(3, min(int(window_years or 10), 10))
    limit = max(1, min(int(limit or 25), 100))
    sector_key = str(sector or "").strip().lower()
    grouped: dict[str, dict[str, list[tuple[int, float, dict[str, Any]]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if sector_key and sector_key not in {
            str(row.get("source_sector") or "").lower(), str(row.get("sector") or "").lower()
        }:
            continue
        symbol = str(row.get("symbol") or "").strip().upper()
        row_metric = str(row.get("metric") or "").strip().lower()
        year, value = _year(row.get("fiscal_year")), _number(row.get("value"))
        if not symbol or year is None or value is None:
            continue
        if row_metric in COMPARABLE_MULTIPLES and (
            value <= 0 or str(row.get("median_eligibility") or "ELIGIBLE").upper() != "ELIGIBLE"
        ):
            continue
        grouped[symbol][row_metric].append((year, value, row))

    candidates: list[dict[str, Any]] = []
    for symbol, metrics in grouped.items():
        observations = sorted(metrics.get(canonical) or [], key=lambda item: item[0])
        if len(observations) < 3:
            continue
        latest_year, current, latest_row = observations[-1]
        history = [value for year, value, _row in observations if year <= latest_year][-window_years:]
        historical_median = _median(history)
        historical_percentile = percentile_rank(current, history)
        latest_quality: dict[str, float] = {}
        for quality_metric in QUALITY_METRICS:
            quality_rows = sorted(metrics.get(quality_metric) or [], key=lambda item: item[0])
            eligible = [item for item in quality_rows if item[0] <= latest_year]
            if eligible:
                latest_quality[quality_metric] = eligible[-1][1]
        candidates.append({
            "symbol": symbol,
            "company_name": latest_row.get("company_name"),
            "sector": latest_row.get("sector"), "source_sector": latest_row.get("source_sector"),
            "metric": canonical, "value": round(current, 4), "fiscal_year": f"FY{latest_year}",
            "as_of": latest_row.get("as_of"), "historical_window": f"{window_years}Y",
            "historical_median": historical_median,
            "historical_percentile": historical_percentile,
            "premium_discount_vs_history_pct": premium_discount(current, historical_median),
            "observations": len(history), "quality": latest_quality,
            "source_version": latest_row.get("source_version"),
        })

    sector_median = _median(row["value"] for row in candidates)
    peer_roe = _median(row["quality"].get("roe") for row in candidates)
    peer_margin = _median(row["quality"].get("ebitda_margin") for row in candidates)
    peer_leverage = _median(
        row["quality"].get("net_debt_ebitda", row["quality"].get("debt_equity")) for row in candidates
    )
    peer_values = [row["value"] for row in candidates]
    output: list[dict[str, Any]] = []
    for row in candidates:
        quality = row["quality"]
        peer_premium = premium_discount(row["value"], sector_median)
        row["peer_median"] = sector_median
        row["peer_percentile"] = percentile_rank(row["value"], peer_values)
        row["premium_discount_vs_peers_pct"] = peer_premium
        row["valuation_conditioning"] = quality_matrix(
            historical_percentile=row["historical_percentile"], peer_premium_pct=peer_premium,
            roe=quality.get("roe"), peer_roe=peer_roe,
            eps_cagr=None, peer_eps_cagr=None,
            leverage=quality.get("net_debt_ebitda", quality.get("debt_equity")), peer_leverage=peer_leverage,
        )
        if max_historical_percentile is not None and (row["historical_percentile"] is None or row["historical_percentile"] > max_historical_percentile):
            continue
        history_discount = row.get("premium_discount_vs_history_pct")
        if min_discount_pct is not None and (history_discount is None or history_discount > -abs(min_discount_pct)):
            continue
        if min_roe is not None and quality.get("roe", float("-inf")) < min_roe:
            continue
        if min_ebitda_margin is not None and quality.get("ebitda_margin", float("-inf")) < min_ebitda_margin:
            continue
        output.append(row)

    sort_key = {
        "cheapest": lambda row: row["value"],
        "largest_discount": lambda row: row.get("premium_discount_vs_history_pct") if row.get("premium_discount_vs_history_pct") is not None else float("inf"),
        "most_expensive": lambda row: -row["value"],
        "highest_roe": lambda row: -row["quality"].get("roe", float("-inf")),
    }.get(sort, lambda row: row["value"])
    output.sort(key=sort_key)
    as_of_dates = sorted({str(row.get("as_of")) for row in output if row.get("as_of")})
    return {
        "ok": bool(output), "status": "SUPPORTED" if output else "DATA_REQUIRED",
        "metric": canonical, "sector_filter": sector or None, "sort": sort,
        "latest_fiscal_as_of": as_of_dates[-1] if as_of_dates else None,
        "data_freshness": "ANNUAL_HISTORICAL_SNAPSHOT_NOT_LIVE",
        "universe_companies": len(candidates), "matched_companies": len(output),
        "rows": output[:limit],
        "allowed_use": "research_screening_only",
        "warning": "Ranking uses annual Capital IQ workbook observations. Confirm current market multiples and primary evidence before any investment decision.",
    }


def screen_relative_valuation(
    *, metric: str, sector: str | None = None, window_years: int = 10,
    limit: int = 25, sort: str = "cheapest", max_historical_percentile: int | None = None,
    min_discount_pct: int | None = None, min_roe: int | None = None,
    min_ebitda_margin: int | None = None,
) -> dict[str, Any]:
    """Load relevant warehouse rows and execute the governed screen."""
    from institutional_warehouse import store

    canonical = METRIC_ALIASES.get(str(metric or "").strip().lower(), str(metric or "").strip().lower())
    source_sector = SECTOR_ALIASES.get(str(sector or "").strip().lower(), sector)
    sector_filter = (
        {"sector": source_sector} if source_sector in BROAD_SECTORS
        else {"source_sector": source_sector} if source_sector else {}
    )
    metrics = {canonical, *QUALITY_METRICS}
    rows: list[dict[str, Any]] = []
    for row_metric in metrics:
        payload = store.fetch(
            "sector_ratio_history", filters={"metric": row_metric, **sector_filter},
            limit=5000, include_overrides=True,
        )
        rows.extend(payload.get("rows") or [])
    return build_screen(
        rows, metric=canonical, sector=source_sector, window_years=window_years, limit=limit, sort=sort,
        max_historical_percentile=max_historical_percentile, min_discount_pct=min_discount_pct,
        min_roe=min_roe, min_ebitda_margin=min_ebitda_margin,
    )
