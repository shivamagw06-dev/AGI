"""Warehouse-backed market universe — one row per company with latest valuation."""

from __future__ import annotations

from typing import Any, Optional

from valuation_terminal.sector_lens import lens_for, is_meaningful

_SANE = {
    "pe": (2.0, 250.0),
    "pb": (0.05, 60.0),
    "ev_ebitda": (1.0, 100.0),
    "roe": (-80.0, 120.0),
    "dividend_yield": (0.0, 20.0),
}


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        out = float(value)
        return None if out != out else out
    except (TypeError, ValueError):
        return None


def _sane(field: str, value: Any) -> Optional[float]:
    n = _num(value)
    if n is None:
        return None
    low, high = _SANE.get(field, (float("-inf"), float("inf")))
    return n if low <= n <= high else None


def load_universe(*, limit: int = 5000) -> dict[str, Any]:
    """Latest valuation snapshot joined to company_master and consensus."""
    from institutional_warehouse import db, store

    masters = store.all_rows("company_master", limit=limit)
    if not masters:
        return {"ok": False, "error": "no_companies", "rows": []}

    # Latest valuation date in warehouse.
    table = db.physical_table("historical_valuation")
    latest = db.query(f'SELECT MAX("date") AS d FROM {table}')
    val_date = (latest[0].get("d") if latest else None) or None
    valuations: dict[str, dict[str, Any]] = {}
    if val_date:
        for row in store.fetch("historical_valuation", filters={"date": val_date}, limit=limit)["rows"]:
            sym = str(row.get("symbol") or "").upper()
            if sym:
                valuations[sym] = row

    # Previous day for change detection.
    prev_date = None
    prev_vals: dict[str, dict[str, Any]] = {}
    if val_date:
        prior = db.query(
            f'SELECT MAX("date") AS d FROM {table} WHERE "date" < ?',
            (val_date,),
        )
        prev_date = prior[0].get("d") if prior else None
        if prev_date:
            for row in store.fetch("historical_valuation", filters={"date": prev_date}, limit=limit)["rows"]:
                sym = str(row.get("symbol") or "").upper()
                if sym:
                    prev_vals[sym] = row

    consensus_map: dict[str, dict[str, Any]] = {}
    for row in store.all_rows("consensus", limit=limit * 2):
        sym = str(row.get("symbol") or "").upper()
        if not sym:
            continue
        existing = consensus_map.get(sym)
        if not existing or str(row.get("consensus_date") or "") > str(existing.get("consensus_date") or ""):
            consensus_map[sym] = row

    # Latest Upstox valuation_ratios for the full universe (not a truncated page).
    provider_map: dict[str, dict[str, dict[str, Any]]] = {}
    try:
        from valuation_ratios.ingest import PROVIDER_OWNED, latest_ratio_map

        for sym, pack in latest_ratio_map().items():
            inner: dict[str, dict[str, Any]] = {}
            for name in PROVIDER_OWNED:
                if pack.get(name) is None:
                    continue
                inner[name] = {
                    "company_value": pack[name],
                    "sector_value": pack.get(f"{name}_sector"),
                    "reported_date": pack.get("as_of"),
                }
            if inner:
                provider_map[sym] = inner
    except Exception:
        provider_map = {}

    rows: list[dict[str, Any]] = []
    for master in masters:
        sym = str(master.get("symbol") or "").upper()
        if not sym:
            continue
        val = valuations.get(sym) or {}
        prev = prev_vals.get(sym) or {}
        consensus = consensus_map.get(sym) or {}
        provider = provider_map.get(sym) or {}
        industry_dna = master.get("industry_dna") or master.get("industry")
        # VPAE gate — instrument / loss-making / DNA before any sector aggregate.
        try:
            from valuation_policy import evaluate as vpae_evaluate

            policy = vpae_evaluate(
                sym,
                record={
                    "ok": True,
                    "symbol": sym,
                    "master": master,
                    "provider_ratios": {"ratios": provider},
                    "latest_annual": {},
                    "latest_price": {},
                },
            )
        except Exception:
            policy = {}
        valuation_covered = None
        policy_status = None
        primary_model = None
        policy_coverage = None
        if policy.get("ok"):
            industry_dna = (policy.get("company") or {}).get("industry_dna") or industry_dna
            lens = {
                "primary_metric": policy.get("primary_metric"),
                "primary_metric_label": policy.get("primary_model"),
                "supporting_metrics": policy.get("supporting_metrics") or [],
                "suppressed_metrics": policy.get("hidden_metrics") or [],
                "rationale": policy.get("reason"),
                "status": policy.get("status"),
                "confidence": policy.get("confidence"),
            }
            policy_status = str(policy.get("status") or "").upper() or None
            primary_model = policy.get("primary_model")
            policy_coverage = policy.get("coverage")
            # VPAE applicability — primary KPI for institutional coverage.
            if policy_status == "NOT_APPLICABLE":
                valuation_covered = None
            elif policy_status == "INSUFFICIENT_DATA" or policy_coverage == "NONE":
                valuation_covered = False
            elif primary_model and policy.get("primary_metric"):
                primary_entry = (policy.get("metrics") or {}).get(policy.get("primary_metric")) or {}
                valuation_covered = str(primary_entry.get("status") or "").lower() != "unavailable"
            else:
                valuation_covered = False
        else:
            lens = lens_for(industry_dna, master.get("sector")) or {}
            valuation_covered = False
        primary = lens.get("primary_metric") or "pe"

        # Prefer Upstox provider ratios over sparse computed warehouse multiples.
        def _provider_or_val(metric: str) -> Optional[float]:
            block = provider.get(metric) or {}
            return _sane(metric, block.get("company_value")) if block else _sane(metric, val.get(metric))

        pe = _provider_or_val("pe")
        pb = _provider_or_val("pb")
        ev = _provider_or_val("ev_ebitda")
        roe = _provider_or_val("roe")
        roa = _num((provider.get("roa") or {}).get("company_value"))
        roce = _num((provider.get("roce") or {}).get("company_value"))
        # Sector benchmarks are Upstox-owned only — never fall back to warehouse
        # sector_median (that often equals the peer median and falsely looks like
        # an Upstox sector print with 0% premium).
        sector_pe = _num((provider.get("pe") or {}).get("sector_value"))
        sector_pb = _num((provider.get("pb") or {}).get("sector_value"))
        sector_ev = _num((provider.get("ev_ebitda") or {}).get("sector_value"))
        sector_roe = _num((provider.get("roe") or {}).get("sector_value"))
        has_provider = bool(provider)

        source = "upstox" if has_provider else (val.get("source") or "warehouse.historical_valuation")
        row = {
            "symbol": sym,
            "company_name": master.get("company_name") or sym,
            "instrument_key": master.get("instrument_key"),
            "isin": master.get("isin"),
            "sector": master.get("sector"),
            "industry": master.get("industry"),
            "industry_dna": industry_dna,
            "primary_metric": primary,
            "cmp": _num(val.get("cmp")),
            "market_cap": _num(val.get("market_cap")),
            "pe": pe,
            "pb": pb,
            "ev_ebitda": ev,
            "roe": roe,
            "roa": roa,
            "roce": roce,
            "dividend_yield": _sane("dividend_yield", val.get("dividend_yield")),
            "percentile": _num(val.get("percentile")),
            "sector_median_pe": sector_pe,
            "sector_median_pb": sector_pb,
            "sector_median_ev_ebitda": sector_ev,
            "sector_median_roe": sector_roe,
            "industry_median_pe": _num(val.get("industry_median")),
            "relative_score": _num(val.get("relative_valuation_score")),
            "prev_pe": _sane("pe", prev.get("pe")),
            "prev_pb": _sane("pb", prev.get("pb")),
            "pe_change_pct": _pct_change(prev.get("pe"), pe),
            "pb_change_pct": _pct_change(prev.get("pb"), pb),
            "consensus_target": _num(consensus.get("target_price")),
            "consensus_upside": _pct_change(val.get("cmp"), consensus.get("target_price")),
            "analyst_count": _num(consensus.get("analyst_count") or consensus.get("buy")),
            "valuation_date": val_date or (next(iter(provider.values()), {}) or {}).get("reported_date"),
            "source": source,
            "provider_coverage": len(provider) if has_provider else 0,
            "has_upstox_sector_benchmark": any(
                v is not None for v in (sector_pe, sector_pb, sector_ev, sector_roe)
            ),
            "primary_model": primary_model or lens.get("primary_metric_label"),
            "policy_status": policy_status or lens.get("status"),
            "policy_coverage": policy_coverage,
            "policy_confidence": lens.get("confidence"),
            "valuation_covered": valuation_covered,
        }
        primary_val = row.get(primary)
        if primary_val is None or not is_meaningful(primary, industry_dna):
            primary_val = pe if pe is not None else pb
        row["primary_value"] = primary_val
        # Premium vs Upstox sector benchmark for the primary metric.
        sector_bench = {
            "pe": sector_pe, "pb": sector_pb, "ev_ebitda": sector_ev, "roe": sector_roe,
        }.get(primary)
        if primary_val is not None and sector_bench:
            row["sector_premium_pct"] = round(100.0 * (primary_val - sector_bench) / sector_bench, 2)
        else:
            row["sector_premium_pct"] = None
        rows.append(row)

    return {
        "ok": True,
        "valuation_date": val_date,
        "previous_date": prev_date,
        "count": len(rows),
        "rows": rows,
    }


# Cap extreme % changes from tiny denominators / sign flips (matches rotation).
_PCT_CHANGE_CAP = 150.0


def _pct_change(before: Any, after: Any) -> Optional[float]:
    try:
        start, end = float(before), float(after)
    except (TypeError, ValueError):
        return None
    if start == 0:
        return None
    # Require a meaningful prior multiple so 0.0002 → 30 does not explode.
    if abs(start) < 0.5:
        return None
    raw = 100.0 * (end - start) / abs(start)
    capped = max(-_PCT_CHANGE_CAP, min(_PCT_CHANGE_CAP, raw))
    return round(capped, 2)
