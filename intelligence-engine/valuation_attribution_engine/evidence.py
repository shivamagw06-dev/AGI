"""Evidence gathering for VARIE — warehouse / UVE / HVIE / MI only.

Never invents causes. Marks each factor as observed, derived, or inferred.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import unquote

ENGINE_CODE = "valuation_attribution_engine"
VERSION = "1.0.0"
MATERIAL_PCT = 0.5


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def num(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        out = float(value)
        return None if out != out else out
    except (TypeError, ValueError):
        return None


def pct_change(before: Any, after: Any) -> Optional[float]:
    start, end = num(before), num(after)
    if start is None or end is None or start == 0:
        return None
    return round(100.0 * (end - start) / abs(start), 2)


def factor(
    *,
    key: str,
    label: str,
    direction: str,
    statement: str,
    evidence_kind: str,
    strength: float,
    current: Any = None,
    previous: Any = None,
    change_pct: Any = None,
    source: str,
    contribution_pct: Optional[float] = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "direction": direction,  # supporting_premium | supporting_discount | neutral | mixed
        "statement": statement,
        "evidence_kind": evidence_kind,  # observed | derived | inferred
        "strength": round(float(strength), 3),
        "current": current,
        "previous": previous,
        "change_pct": change_pct,
        "contribution_pct": contribution_pct,
        "source": source,
    }


def load_universe_row(symbol: str, *, universe_limit: int = 5000) -> Optional[dict[str, Any]]:
    from market_intelligence_engine import universe

    uni = universe.load_universe(limit=universe_limit)
    ticker = str(symbol or "").strip().upper()
    for row in uni.get("rows") or []:
        if str(row.get("symbol") or "").upper() == ticker:
            return {**row, "_universe_meta": {
                "valuation_date": uni.get("valuation_date"),
                "previous_date": uni.get("previous_date"),
            }}
    return None


def load_warehouse_company(symbol: str) -> dict[str, Any]:
    try:
        from institutional_warehouse.production import read_company

        return read_company(symbol)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def load_hvie(symbol: str, *, metric: str = "pe", window: str = "10y") -> dict[str, Any]:
    try:
        from historical_valuation_intelligence.production import company as hvie_company

        return hvie_company(symbol, metric=metric, window=window)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def load_hvie_history(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    try:
        from historical_valuation_intelligence.production import history as hvie_history

        pack = hvie_history(symbol, metric=metric, window=window, limit=4000)
        # Normalize to a flat points list for callers.
        series = (pack.get("series") or {}).get(metric) or pack.get(metric) or {}
        points = series.get("points") if isinstance(series, dict) else None
        if points is None:
            points = pack.get("points") or []
        return {**pack, "points": points or [], "metric": metric}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200], "points": []}


def load_hvie_rerating(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    try:
        from historical_valuation_intelligence.production import rerating as hvie_rerating

        return hvie_rerating(symbol, metric=metric, window=window)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def load_flows() -> dict[str, Any]:
    try:
        from market_intelligence_engine import flows

        return flows.institutional_flows()
    except Exception:
        return {"ok": False, "available": False}


def annual_pair(wh: dict[str, Any]) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    """Latest and prior annual financial rows when available via company_view sheets."""
    try:
        from institutional_warehouse import store

        sym = wh.get("symbol")
        if not sym:
            return wh.get("latest_annual"), None
        rows = store.all_rows("financials_annual", entity=str(sym).upper(), limit=80)
        from institutional_warehouse.financials import canonical_statement_series
        rows = canonical_statement_series(rows, period_key="fiscal_year", annual=True)
        if not rows:
            return wh.get("latest_annual"), None
        latest = rows[-1]
        prior = rows[-2] if len(rows) >= 2 else None
        return latest, prior
    except Exception:
        return wh.get("latest_annual"), None


def ownership_pair(wh: dict[str, Any]) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    try:
        from institutional_warehouse import store

        sym = wh.get("symbol")
        if not sym:
            return wh.get("ownership"), None
        rows = store.all_rows("ownership", entity=str(sym).upper(), limit=8)
        rows = sorted(rows, key=lambda r: str(r.get("as_of") or r.get("date") or ""), reverse=True)
        if not rows:
            return wh.get("ownership"), None
        return rows[0], (rows[1] if len(rows) >= 2 else None)
    except Exception:
        return wh.get("ownership"), None


def research_timeline_rows(symbol: str, *, limit: int = 40) -> list[dict[str, Any]]:
    try:
        from institutional_warehouse import store

        rows = store.all_rows("research_timeline", entity=str(symbol).upper(), limit=limit)
        return sorted(rows, key=lambda r: str(r.get("date") or ""), reverse=True)
    except Exception:
        return []


def sector_members(sector: str, *, universe_limit: int = 5000) -> dict[str, Any]:
    from market_intelligence_engine import aggregation, universe

    name = unquote(str(sector or "")).strip()
    uni = universe.load_universe(limit=universe_limit)
    members = [r for r in (uni.get("rows") or []) if str(r.get("sector") or "") == name]
    if not members:
        members = [
            r for r in (uni.get("rows") or [])
            if str(r.get("sector") or "").lower() == name.lower()
        ]
    table = aggregation.sector_table(uni)
    valuation = next(
        (s for s in table if str(s.get("sector") or "").lower() == (members[0].get("sector") if members else name).lower()),
        {},
    )
    return {
        "ok": True,
        "sector": (members[0].get("sector") if members else name),
        "members": members,
        "valuation": valuation,
        "as_of": uni.get("valuation_date"),
        "universe": uni,
    }


def industry_members(industry: str, *, universe_limit: int = 5000) -> dict[str, Any]:
    from market_intelligence_engine import universe

    name = unquote(str(industry or "")).strip()
    uni = universe.load_universe(limit=universe_limit)
    members = [r for r in (uni.get("rows") or []) if str(r.get("industry") or "") == name]
    if not members:
        members = [
            r for r in (uni.get("rows") or [])
            if str(r.get("industry") or "").lower() == name.lower()
        ]
    return {
        "ok": bool(members),
        "industry": (members[0].get("industry") if members else name),
        "sector": members[0].get("sector") if members else None,
        "members": members,
        "as_of": uni.get("valuation_date"),
        "universe": uni,
        "error": None if members else "industry_not_found",
    }


def decompose_premium(premium_pct: Optional[float], factors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scale relative evidence strengths to the observed premium/discount.

    Derived only — not a causal identity. Residual absorbs remainder.
    """
    if premium_pct is None:
        return []
    signed = float(premium_pct)
    supporting = [
        f for f in factors
        if f.get("direction") == ("supporting_premium" if signed >= 0 else "supporting_discount")
        and (f.get("strength") or 0) > 0
    ]
    if not supporting:
        return [{
            "key": "residual",
            "label": "Residual / unexplained",
            "contribution_pct": round(signed, 1),
            "evidence_kind": "derived",
            "statement": "Primary driver cannot be determined from available data.",
            "source": ENGINE_CODE,
        }]
    total_strength = sum(float(f.get("strength") or 0) for f in supporting) or 1.0
    allocated = 0.0
    out = []
    for f in sorted(supporting, key=lambda x: -float(x.get("strength") or 0)):
        share = abs(signed) * float(f.get("strength") or 0) / total_strength
        # Keep residual for last bucket
        contrib = round(share if signed >= 0 else -share, 1)
        allocated += contrib
        row = {**f, "contribution_pct": contrib}
        out.append(row)
    residual = round(signed - allocated, 1)
    if abs(residual) >= 0.1:
        out.append({
            "key": "residual",
            "label": "Residual",
            "contribution_pct": residual,
            "evidence_kind": "derived",
            "statement": "Unallocated portion after ranking observed factors by relative evidence strength.",
            "source": ENGINE_CODE,
        })
    return out


def daily_attribution(row: dict[str, Any], wh: dict[str, Any]) -> dict[str, Any]:
    """Attribute short-horizon multiple move via UVE attribution graph."""
    from valuation_engine.attribution import MATERIAL_PCT as UVE_MATERIAL, explain_change

    pe = num(row.get("pe"))
    prev_pe = num(row.get("prev_pe"))
    cmp_now = num(row.get("cmp"))
    annual = wh.get("latest_annual") or {}
    eps = num(annual.get("eps") or annual.get("diluted_eps") or annual.get("basic_eps"))
    # Without prior CMP/EPS, fall back to PE-only observation.
    before = {"pe": prev_pe, "cmp": None, "eps": eps}
    after = {"pe": pe, "cmp": cmp_now, "eps": eps}
    # Prefer HVIE daily_change when available later; this is universe observation.
    if pe is None or prev_pe is None:
        return {
            "ok": True,
            "material": False,
            "note": "Insufficient prior PE observation for daily attribution.",
            "material_pct": UVE_MATERIAL,
        }
    change = pct_change(prev_pe, pe)
    entry = explain_change("pe", before, after)
    material = change is not None and abs(change) >= UVE_MATERIAL
    reason = entry.get("summary")
    if entry.get("uncomparable") and not entry.get("drivers"):
        # Price/EPS inputs unavailable — state PE observation only.
        if material:
            reason = (
                f"PE moved {change:+.1f}% vs prior observation "
                f"({prev_pe} → {pe}). Price/EPS inputs were not both available "
                f"to isolate the arithmetic driver."
            )
        else:
            reason = f"PE effectively unchanged vs prior observation (below {UVE_MATERIAL}% materiality)."
    return {
        "ok": True,
        "material": material,
        "yesterday": prev_pe,
        "today": pe,
        "change_pct": change,
        "uve": entry,
        "reason": reason,
        "material_pct": UVE_MATERIAL,
        "as_of": (row.get("_universe_meta") or {}).get("valuation_date"),
        "previous_date": (row.get("_universe_meta") or {}).get("previous_date"),
        "source": "valuation_engine.attribution + market_intelligence_engine.universe",
    }


def confidence_score(factors: list[dict[str, Any]], *, hvie_ok: bool, coverage: int) -> int:
    score = 45
    observed = sum(1 for f in factors if f.get("evidence_kind") == "observed")
    score += min(35, observed * 8)
    if hvie_ok:
        score += 10
    if coverage:
        score += 8
    if not factors:
        score = min(score, 40)
    return min(96, score)
