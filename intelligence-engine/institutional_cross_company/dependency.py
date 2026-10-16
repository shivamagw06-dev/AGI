"""CCI-01 dependency maps — structural links used by propagation (not forecasts)."""

from __future__ import annotations

from typing import Any

from institutional_cross_company.schema import ECOSYSTEMS, MACRO_DRIVERS


def dependency_map(driver: str) -> dict[str, Any]:
    """
    Macro → Sector → Channel → Companies

    Dependency structure only — no prediction of returns or decisions.
    """
    d = str(driver or "").lower().strip().replace(" ", "_")
    aliases = {"rates": "interest_rates", "rbi": "interest_rates", "crude": "oil", "currency": "fx"}
    d = aliases.get(d, d)
    meta = MACRO_DRIVERS.get(d)
    if not meta:
        return {"driver": d, "ok": False, "steps": [], "companies": [], "predictive": False}

    companies: list[str] = []
    sectors = list(meta.get("affects_sectors") or ())
    clusters = set(meta.get("affects_clusters") or ())
    for eco in ECOSYSTEMS.values():
        if eco.get("cluster") in clusters or d in (eco.get("macro") or ()):
            companies.extend(str(m).upper() for m in (eco.get("members") or ()))

    steps = [
        meta.get("label") or d,
        " / ".join(sectors[:3]) or "Affected sectors",
        str(meta.get("channel") or "Transmission channel"),
        "Company exposures",
        "Portfolio holdings (if held)",
        "Risk / Policy / Committee (downstream consumers)",
    ]
    return {
        "driver": d,
        "ok": True,
        "steps": steps,
        "sectors": sectors,
        "clusters": list(clusters),
        "companies": sorted(set(companies)),
        "channel": meta.get("channel"),
        "predictive": False,
        "dependency_propagation_only": True,
    }
