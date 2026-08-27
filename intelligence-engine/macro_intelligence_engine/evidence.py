"""Load macro evidence from warehouse + CMKP/HMIP/MRI/HMAI/MFI. Never call vendors."""

from __future__ import annotations

from typing import Any, Optional

from macro_intelligence_engine.indicators import SERIES_CATALOGUE as CATALOGUE
from macro_intelligence_engine.models import DEFAULT_COUNTRY


def _safe(fn) -> Optional[dict[str, Any]]:
    try:
        out = fn()
        return out if isinstance(out, dict) else {"value": out}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _rows(tab: str, *, limit: int = 200, filters: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    try:
        from institutional_warehouse import store

        page = store.fetch(tab, limit=limit, filters=filters or {})
        return list(page.get("rows") or [])
    except Exception:
        try:
            from institutional_warehouse import store

            return list(store.all_rows(tab, limit=limit) or [])
        except Exception:
            return []


def _extract_snapshot(india: dict[str, Any], global_macro: dict[str, Any], latest_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Normalize heterogeneous upstream payloads into a series snapshot."""
    snap: dict[str, Any] = {}

    for row in latest_rows:
        key = str(row.get("series_id") or row.get("indicator") or row.get("name") or "").strip().lower()
        if not key:
            continue
        # normalize spaces
        key = key.replace(" ", "_").replace("-", "_")
        snap[key] = {
            "value": row.get("value") or row.get("latest"),
            "as_of": row.get("as_of") or row.get("date"),
            "direction": row.get("direction") or row.get("trend"),
            "unit": row.get("unit"),
            "source": row.get("source") or "warehouse.macro_latest",
        }

    def _ingest_list(payload: dict[str, Any], source: str) -> None:
        if not payload or payload.get("ok") is False:
            return
        candidates: list[Any] = []
        for key in ("indicators", "series", "rows", "releases", "items", "latest"):
            val = payload.get(key)
            if isinstance(val, list):
                candidates.extend(val)
        # some dashboards nest under countries
        for nest_key in ("india", "global", "data"):
            nested = payload.get(nest_key)
            if isinstance(nested, dict):
                for key in ("indicators", "series", "rows"):
                    val = nested.get(key)
                    if isinstance(val, list):
                        candidates.extend(val)
            elif isinstance(nested, list):
                candidates.extend(nested)

        for item in candidates:
            if not isinstance(item, dict):
                continue
            name = str(
                item.get("indicator")
                or item.get("series_id")
                or item.get("name")
                or item.get("metric")
                or ""
            ).strip().lower().replace(" ", "_").replace("-", "_")
            if not name:
                continue
            # Map common labels onto catalogue keys
            aliases = {
                "gdp": "gdp_growth",
                "gdp_yoy": "gdp_growth",
                "repo": "repo_rate",
                "rbi_repo_rate": "repo_rate",
                "federal_funds_rate": "fed_funds",
                "us_cpi": "cpi",
                "india_cpi": "cpi",
                "consumer_price_index": "cpi",
                "wholesale_price_index": "wpi",
                "industrial_production": "iip",
                "forex_reserves": "fx_reserves",
                "usd_inr": "usdinr",
                "india_10_year": "india_10y",
                "us_10_year": "us_10y",
                "crude_oil": "brent",
                "brent_crude": "brent",
            }
            key = aliases.get(name, name)
            if key not in snap:
                snap[key] = {
                    "value": item.get("value") or item.get("latest") or item.get("level"),
                    "as_of": item.get("as_of") or item.get("date") or item.get("period"),
                    "direction": item.get("direction") or item.get("trend") or item.get("change_direction"),
                    "unit": item.get("unit"),
                    "source": source,
                }

    _ingest_list(india or {}, "cmkp.india")
    _ingest_list(global_macro or {}, "cmkp.global")

    # Seed directional defaults for catalogue keys still missing so explainability works
    # without inventing numeric values — only direction/status placeholders.
    for key, meta in CATALOGUE.items():
        if key not in snap:
            snap[key] = {
                "value": None,
                "as_of": None,
                "direction": None,
                "unit": meta.get("unit"),
                "source": "catalogue_placeholder",
                "status": "waiting_series",
            }
    return snap


def load_bundle(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    """Gather MIE inputs. Soft-fails per engine. Never invents values."""
    ctry = (country or DEFAULT_COUNTRY).strip() or DEFAULT_COUNTRY

    cmkp_dash = _safe(lambda: __import__("continuous_macro_knowledge.production", fromlist=["dashboard"]).dashboard())
    cmkp_india = _safe(lambda: __import__("continuous_macro_knowledge.production", fromlist=["india"]).india())
    cmkp_global = _safe(
        lambda: __import__("continuous_macro_knowledge.production", fromlist=["global_macro"]).global_macro()
    )
    hmip = _safe(
        lambda: __import__("historical_macro_intelligence.production", fromlist=["dashboard"]).dashboard()
    )
    hmai_regime = _safe(
        lambda: __import__(
            "historical_macro_analogue_intelligence.production", fromlist=["current_regime"]
        ).current_regime(country=ctry)
    )
    mfi_forecast = _safe(
        lambda: __import__(
            "macroeconomic_forecast_intelligence.production", fromlist=["forecast"]
        ).forecast(country=ctry)
    )
    mfi_scenarios = _safe(
        lambda: __import__(
            "macroeconomic_forecast_intelligence.production", fromlist=["scenarios"]
        ).scenarios(country=ctry)
    )
    mri = _safe(
        lambda: __import__(
            "macroeconomic_relationship_intelligence.production", fromlist=["dashboard"]
        ).dashboard()
    )

    latest_rows = _rows("macro_latest", limit=500)
    series_rows = _rows("macro_series", limit=500)
    events = _rows("macro_events", limit=100)
    regimes = _rows("macro_regimes", limit=50)
    history = _rows("macro_history", limit=100)
    alerts = _rows("macro_alerts", limit=50)
    calendar = _rows("macro_calendar", limit=50)
    rel_rows = _rows("macro_relationships", limit=200)

    snapshot = _extract_snapshot(cmkp_india or {}, cmkp_global or {}, latest_rows)

    inputs_present = {
        "cmkp": bool(cmkp_dash and cmkp_dash.get("ok") is not False),
        "hmip": bool(hmip and hmip.get("ok") is not False),
        "hmai_regime": bool(hmai_regime and hmai_regime.get("ok") is not False and not hmai_regime.get("error")),
        "mfi_forecast": bool(mfi_forecast and mfi_forecast.get("ok") is not False and not mfi_forecast.get("error")),
        "mfi_scenarios": bool(mfi_scenarios and mfi_scenarios.get("ok") is not False and not mfi_scenarios.get("error")),
        "mri": bool(mri and mri.get("ok") is not False and not mri.get("error")),
        "macro_latest": bool(latest_rows),
        "macro_series": bool(series_rows),
        "macro_events": bool(events),
        "macro_relationships": bool(rel_rows),
    }

    observed_count = sum(
        1 for k, v in snapshot.items()
        if isinstance(v, dict) and v.get("value") is not None and v.get("status") != "waiting_series"
    )

    return {
        "country": ctry,
        "snapshot": snapshot,
        "cmkp": {"dashboard": cmkp_dash, "india": cmkp_india, "global": cmkp_global},
        "hmip": hmip,
        "hmai_regime": hmai_regime,
        "mfi_forecast": mfi_forecast,
        "mfi_scenarios": mfi_scenarios,
        "mri": mri,
        "warehouse": {
            "macro_latest": latest_rows,
            "macro_series": series_rows,
            "macro_events": events,
            "macro_regimes": regimes,
            "macro_history": history,
            "macro_alerts": alerts,
            "macro_calendar": calendar,
            "macro_relationships": rel_rows,
        },
        "inputs_present": inputs_present,
        "observed_series_count": observed_count,
        "catalogue_size": len(CATALOGUE),
    }


def load_company_context(symbol: str) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    master: dict[str, Any] = {}
    try:
        from institutional_warehouse import store

        page = store.fetch("company_master", filters={"symbol": ticker}, limit=1)
        rows = page.get("rows") or []
        master = rows[0] if rows else {}
    except Exception:
        master = {}
    return {
        "symbol": ticker,
        "company_name": master.get("company_name") or master.get("name"),
        "sector": master.get("sector"),
        "industry": master.get("industry"),
        "master": master,
    }

