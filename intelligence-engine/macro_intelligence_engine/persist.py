"""Persist MIE outputs to warehouse tabs (append-oriented)."""

from __future__ import annotations

from typing import Any

from macro_intelligence_engine.models import ENGINE_CODE


def persist_macro_pack(pack: dict[str, Any]) -> dict[str, Any]:
    written = {
        "macro_regimes": 0,
        "macro_history": 0,
        "macro_forecasts": 0,
        "macro_relationships": 0,
        "macro_alerts": 0,
        "macro_runtime": 0,
    }
    try:
        from institutional_warehouse import gateway
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}

    country = pack.get("country") or "India"
    as_of = (pack.get("generated_at") or "")[:10]
    quality = pack.get("macro_quality") or {}
    modules = pack.get("modules") or {}
    probs = pack.get("probabilities") or {}

    regime_val = pack.get("regime")
    if isinstance(regime_val, dict):
        regime_val = (
            regime_val.get("label")
            or regime_val.get("name")
            or regime_val.get("regime")
            or "Recovery"
        )
    cycle_val = pack.get("cycle")
    if not isinstance(cycle_val, str):
        cycle_val = str(cycle_val or "")

    regime_row = {
        "country": country,
        "as_of": as_of,
        "regime": str(regime_val or "")[:160],
        "cycle": str(cycle_val or "")[:160],
        "macro_confidence": quality.get("macro_confidence"),
        "score": quality.get("score"),
        "bull_pct": probs.get("bull"),
        "base_pct": probs.get("base"),
        "bear_pct": probs.get("bear"),
        "status": pack.get("status"),
        "dqiv": (pack.get("dqiv") or {}).get("status"),
        "executive_summary": (pack.get("executive_summary") or "")[:500],
        "version": pack.get("version"),
    }
    try:
        r = gateway.write(
            "macro_regimes",
            [regime_row],
            source=ENGINE_CODE,
            actor="mie",
            reason="mie_regime_snapshot",
        )
        written["macro_regimes"] = int(r.get("written") or 0)
    except Exception:
        pass

    history_row = {
        **regime_row,
        "event": "generated",
        "generated_at": pack.get("generated_at"),
    }
    try:
        r = gateway.write(
            "macro_history",
            [history_row],
            source=ENGINE_CODE,
            actor="mie",
            reason="mie_history_append",
        )
        written["macro_history"] = int(r.get("written") or 0)
    except Exception:
        pass

    forecast_mod = modules.get("forecast") or {}
    directions = forecast_mod.get("directions") or {}
    if directions:
        try:
            r = gateway.write(
                "macro_forecasts",
                [{
                    "country": country,
                    "as_of": as_of,
                    "horizon": "scenario",
                    "gdp_direction": directions.get("gdp"),
                    "inflation_direction": directions.get("inflation"),
                    "rates_direction": directions.get("rates"),
                    "liquidity_direction": directions.get("liquidity"),
                    "currency_direction": directions.get("currency"),
                    "commodity_direction": directions.get("commodities"),
                    "status": "generated",
                    "version": pack.get("version"),
                }],
                source=ENGINE_CODE,
                actor="mie",
                reason="mie_forecast_append",
            )
            written["macro_forecasts"] = int(r.get("written") or 0)
        except Exception:
            pass

    rel_mod = modules.get("relationships") or {}
    rel_rows = []
    for item in rel_mod.get("relationships") or []:
        rel_rows.append({
            "country": country,
            "as_of": as_of,
            "pair": item.get("pair"),
            "strength": item.get("strength"),
            "confidence": item.get("confidence"),
            "observation_count": item.get("observations"),
        })
    if rel_rows:
        try:
            r = gateway.write(
                "macro_relationships",
                rel_rows,
                source=ENGINE_CODE,
                actor="mie",
                reason="mie_relationships_append",
            )
            written["macro_relationships"] = int(r.get("written") or 0)
        except Exception:
            pass

    risk_mod = modules.get("risks") or {}
    alert_rows = []
    for risk in risk_mod.get("risks") or []:
        if risk.get("level") == "High":
            alert_rows.append({
                "country": country,
                "as_of": as_of,
                "alert": risk.get("risk"),
                "level": risk.get("level"),
                "status": "open",
            })
    if alert_rows:
        try:
            r = gateway.write(
                "macro_alerts",
                alert_rows,
                source=ENGINE_CODE,
                actor="mie",
                reason="mie_alerts_append",
            )
            written["macro_alerts"] = int(r.get("written") or 0)
        except Exception:
            pass

    try:
        r = gateway.write(
            "macro_runtime",
            [{
                "country": country,
                "queue_status": "COMPLETE" if pack.get("status") == "PASS" else "FAILED",
                "lifecycle": "READY",
                "macro_confidence": quality.get("macro_confidence"),
                "last_run_at": pack.get("generated_at"),
                "completed_at": pack.get("generated_at") if pack.get("status") == "PASS" else None,
                "updated_at": pack.get("generated_at"),
                "last_error": None if pack.get("ok") else str((pack.get("dqiv") or {}).get("errors") or "")[:280],
            }],
            source=ENGINE_CODE,
            actor="mie",
            reason="mie_runtime_upsert",
        )
        written["macro_runtime"] = int(r.get("written") or 0)
    except Exception:
        pass

    return {"ok": True, "written": written}
