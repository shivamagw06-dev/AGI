"""Historical valuation bands (10Y PE/PB/EV-EBITDA) + current percentile."""

from __future__ import annotations

from typing import Any

from valuation_intelligence.schema import HistoricalBand


_VENDOR_METRICS = {"pe", "pb", "ev_ebitda", "ev_sales", "ptbv", "p_assets"}


def _percentile_rank(series: list[float], current: float) -> float | None:
    if not series:
        return None
    below = sum(1 for v in series if v <= current)
    return round(100.0 * below / len(series), 1)


def band_from_series(series: list[float], current: float | None, *, window: str = "10Y", source: str = "computed") -> HistoricalBand | None:
    clean = [float(v) for v in series if isinstance(v, (int, float)) and v > 0]
    if len(clean) < 3:
        return None
    clean_sorted = sorted(clean)
    n = len(clean_sorted)
    median = clean_sorted[n // 2] if n % 2 == 1 else (clean_sorted[n // 2 - 1] + clean_sorted[n // 2]) / 2.0
    cur = float(current) if isinstance(current, (int, float)) else None
    return HistoricalBand(
        window=window,
        median=round(median, 2),
        high=round(max(clean_sorted), 2),
        low=round(min(clean_sorted), 2),
        current=cur,
        percentile=_percentile_rank(clean_sorted, cur) if cur is not None else None,
        observations=n,
        source=source,
    )


def _pe_from_historical_depth(symbol: str) -> list[float]:
    try:
        from knowledge_factory.historical_depth.producers.derived import produce_derived

        derived = produce_derived(symbol)
        pe = ((derived.get("metrics") or {}).get("PE") or {}).get("points") or {}
        if isinstance(pe, dict):
            return [float(v) for v in pe.values() if isinstance(v, (int, float)) and v > 0]
    except Exception:
        return []
    return []


def _from_sector_ratio_warehouse(symbol: str, metric: str) -> list[float]:
    """Read the versioned CapIQ workbook baseline persisted in the warehouse."""
    key = (symbol or "").upper().replace(".NS", "").replace(".BO", "")
    if not key or metric not in _VENDOR_METRICS:
        return []
    try:
        from institutional_warehouse import store

        rows = store.all_rows("sector_ratio_history", entity=key, limit=5000)
    except Exception:
        return []
    points: list[tuple[int, float]] = []
    for row in rows:
        if str(row.get("metric") or "").lower() != metric:
            continue
        if str(row.get("median_eligibility") or "").upper() != "ELIGIBLE":
            continue
        try:
            year = int(str(row.get("fiscal_year") or "").upper().replace("FY", ""))
            value = float(row.get("value"))
        except (TypeError, ValueError):
            continue
        if value > 0:
            points.append((year, value))
    # One value per year. A later source version wins without blending vintages.
    by_year = {year: value for year, value in sorted(points)}
    return [by_year[year] for year in sorted(by_year)]


def historical_windows_from_series(
    series: list[float], current: float | None, *, source: str
) -> dict[str, HistoricalBand]:
    """Build auditable 3Y/5Y/10Y distributions from annual observations."""
    out: dict[str, HistoricalBand] = {}
    for years, label in ((3, "3Y"), (5, "5Y"), (10, "10Y")):
        sample = list(series[-years:])
        band = band_from_series(sample, current, window=label, source=source)
        if band is not None:
            out[label.lower()] = band
    return out


def historical_windows_for_symbol(
    symbol: str,
    *,
    current: dict[str, float | None],
) -> dict[str, dict[str, HistoricalBand]]:
    """Return workbook-backed windows for every comparable valuation metric."""
    out: dict[str, dict[str, HistoricalBand]] = {}
    for metric, current_value in current.items():
        series = _from_sector_ratio_warehouse(symbol, metric)
        windows = historical_windows_from_series(
            series, current_value, source="capital_iq_sector_ratio_workbook"
        )
        if windows:
            out[metric] = windows
    return out


def _pb_ev_from_historical_depth(symbol: str) -> tuple[list[float], list[float]]:
    pb_out: list[float] = []
    ev_out: list[float] = []
    try:
        from knowledge_factory.historical_depth.producers.derived import produce_derived

        derived = produce_derived(symbol)
        metrics = derived.get("metrics") or {}
        for key, bucket in (("PB", pb_out), ("EV_EBITDA", ev_out), ("EV/EBITDA", ev_out)):
            pts = (metrics.get(key) or {}).get("points") or {}
            if isinstance(pts, dict):
                for v in pts.values():
                    if isinstance(v, (int, float)) and v > 0:
                        bucket.append(float(v))
    except Exception:
        return [], []
    return pb_out, ev_out


def _pe_from_yahoo_annual(symbol: str, annual_eps: list[tuple[str, float]]) -> list[float]:
    """Approximate FY PE = year-end close / FY EPS using Yahoo monthly chart."""
    if not annual_eps:
        return []
    try:
        import json
        import urllib.request

        try:
            from app.market_data.providers.yahoo_symbols import to_yahoo_symbol

            sym = to_yahoo_symbol(symbol)
        except Exception:
            sym = f"{symbol.upper()}.NS"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1mo&range=10y"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AGIB-Valuation/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return []
        ts = result[0].get("timestamp") or []
        closes = ((result[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or []
        if not ts or not closes:
            return []
        # Map year → last available close in that calendar year
        by_year: dict[int, float] = {}
        for t, c in zip(ts, closes):
            if c is None:
                continue
            from datetime import datetime, timezone

            yr = datetime.fromtimestamp(int(t), tz=timezone.utc).year
            by_year[yr] = float(c)
        out: list[float] = []
        for period_end, eps in annual_eps:
            if eps in (None, 0):
                continue
            try:
                year = int(str(period_end)[:4])
            except (TypeError, ValueError):
                continue
            # Prefer year of period_end, else prior year close
            px = by_year.get(year) or by_year.get(year - 1)
            if px and eps > 0:
                out.append(round(px / eps, 4))
        return out
    except Exception:
        return []


def historical_bands_for_symbol(
    symbol: str,
    *,
    current_pe: float | None,
    current_pb: float | None,
    current_ev_ebitda: float | None,
    annual_eps: list[tuple[str, float]] | None = None,
    injected_series: dict[str, list[float]] | None = None,
) -> dict[str, HistoricalBand]:
    bands: dict[str, HistoricalBand] = {}
    key = (symbol or "").upper().replace(".NS", "").replace(".BO", "")

    if isinstance(injected_series, dict):
        for metric, series in injected_series.items():
            cur = {"pe": current_pe, "pb": current_pb, "ev_ebitda": current_ev_ebitda}.get(metric)
            band = band_from_series(list(series or []), cur, source="injected")
            if band is not None:
                bands[metric] = band
        if bands:
            return bands

    pe_series = _from_sector_ratio_warehouse(key, "pe")
    source = "capital_iq_sector_ratio_workbook"
    if len(pe_series) < 3:
        pe_series = _pe_from_historical_depth(key)
        source = "historical_depth"
    if len(pe_series) < 3:
        yahoo_pe = _pe_from_yahoo_annual(key, annual_eps or [])
        if len(yahoo_pe) >= 3:
            pe_series = yahoo_pe
            source = "yahoo_chart|earnings_eps"
    pe_band = band_from_series(pe_series, current_pe, source=source)
    if pe_band is not None:
        bands["pe"] = pe_band

    pb_series = _from_sector_ratio_warehouse(key, "pb")
    ev_series = _from_sector_ratio_warehouse(key, "ev_ebitda")
    pb_source = "capital_iq_sector_ratio_workbook"
    ev_source = "capital_iq_sector_ratio_workbook"
    depth_pb, depth_ev = _pb_ev_from_historical_depth(key)
    if len(pb_series) < 3:
        pb_series, pb_source = depth_pb, "historical_depth"
    if len(ev_series) < 3:
        ev_series, ev_source = depth_ev, "historical_depth"
    pb_band = band_from_series(pb_series, current_pb, source=pb_source)
    ev_band = band_from_series(ev_series, current_ev_ebitda, source=ev_source)
    if pb_band is not None:
        bands["pb"] = pb_band
    if ev_band is not None:
        bands["ev_ebitda"] = ev_band

    return bands
