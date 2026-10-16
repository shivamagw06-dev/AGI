"""Soft system integration facade — inventory + optional catalog bootstrap."""

from __future__ import annotations

from typing import Any, Callable


PROGRAMMES: tuple[dict[str, Any], ...] = (
    {"phase": "10.1", "short": "CMKP", "module": "continuous_macro_knowledge", "role": "macro_knowledge"},
    {"phase": "10.5", "short": "MFI", "module": "macroeconomic_forecast_intelligence", "role": "macro_forecast"},
    {"phase": "11.1", "short": "CSKP", "module": "continuous_sector_knowledge", "role": "sector_knowledge"},
    {"phase": "11.5", "short": "SFI", "module": "sector_forecast_intelligence", "role": "sector_forecast"},
    {"phase": "12.1", "short": "CMKTP", "module": "continuous_market_knowledge", "role": "market_knowledge"},
    {"phase": "12.2", "short": "HMKIP", "module": "historical_market_intelligence", "role": "market_history"},
    {"phase": "12.3", "short": "MKRI", "module": "market_relationship_intelligence", "role": "market_relationships"},
    {"phase": "12.4", "short": "HMKAI", "module": "historical_market_analogue_intelligence", "role": "market_analogues"},
    {"phase": "12.5", "short": "MKFI", "module": "market_forecast_intelligence", "role": "market_forecast"},
    {
        "phase": "4.0",
        "short": "RIH",
        "module": "research_intelligence_hub",
        "role": "research_intelligence_hub",
        "primary_knowledge_object": True,
    },
    {
        "phase": "IIEX",
        "short": "IIEX",
        "module": "institutional_intelligence_examination",
        "role": "cio_investment_committee_assessment",
    },
)


def _soft_health(module: str) -> dict[str, Any] | None:
    try:
        mod = __import__(f"{module}.production", fromlist=["health"])
        fn: Callable[[], dict[str, Any]] | None = getattr(mod, "health", None)
        if callable(fn):
            return fn()
    except Exception:
        return None
    return None


def inventory() -> dict[str, Any]:
    rows = []
    online = 0
    for p in PROGRAMMES:
        h = _soft_health(p["module"])
        ok = bool(h and (h.get("status") == "ok" or h.get("ok") is True))
        if ok:
            online += 1
        rows.append(
            {
                **p,
                "online": ok,
                "version": (h or {}).get("version") or (h or {}).get("mkfi_version") or (h or {}).get("ieg_version"),
                "ask_triggers_collection": (h or {}).get("ask_triggers_collection"),
            }
        )
    return {
        "n": len(rows),
        "online": online,
        "programmes": rows,
        "research_centric": True,
        "primary_knowledge_object": "ResearchObject",
        "providers_queried": [],
        "fabricated": False,
    }


def bootstrap(*, publish_rih: bool = True, publish_mkfi: bool = False) -> dict[str, Any]:
    """Ops-only soft bootstrap of catalog hubs / forecasts. Never Ask."""
    out: dict[str, Any] = {"ok": True, "actions": [], "providers_queried": [], "ask_triggered": False}
    if publish_rih:
        try:
            from research_intelligence_hub.production import run as rih_run

            summary = rih_run()
            out["actions"].append({"programme": "RIH", "result": summary})
        except Exception as exc:
            out["actions"].append({"programme": "RIH", "error": str(exc)})
            out["ok"] = False
    if publish_mkfi:
        try:
            from market_forecast_intelligence.production import run as mkfi_run

            summary = mkfi_run(markets=["India"], horizons=["6 Months"])
            out["actions"].append({"programme": "MKFI", "result": summary})
        except Exception as exc:
            out["actions"].append({"programme": "MKFI", "error": str(exc)})
            out["ok"] = False
    return out


def health() -> dict[str, Any]:
    inv = inventory()
    return {
        "status": "ok" if inv["online"] >= 1 else "degraded",
        "programme": "System Integration",
        "programme_short": "SYSINT",
        "research_centric": True,
        "primary_knowledge_object": "ResearchObject",
        "inventory": inv,
        "ask_triggers_collection": False,
        "providers_queried_always": [],
        "apis": {
            "rih": "/v1/research/hub",
            "mkfi": "/v1/market/forecast",
            "sfi": "/v1/sector/forecast",
            "mfi": "/v1/macro/forecast",
            "iiex": "/v1/iiex/dashboard",
            "mission_control": "/v1/mission-control/dashboard",
        },
    }
