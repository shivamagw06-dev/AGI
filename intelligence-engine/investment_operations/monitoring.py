"""P5.4 Monitoring Office — continuous monitored entities from compiled intelligence."""

from __future__ import annotations

from typing import Any

from investment_operations.util import as_float, now_iso


def build_monitoring_office(company_packs: list[dict[str, Any]]) -> dict[str, Any]:
    monitored = []
    alerts = []
    for p in company_packs:
        if not p.get("ok"):
            continue
        oie = p.get("opportunity") or {}
        mem = p.get("memory") or {}
        kd = {}
        if isinstance(oie.get("opportunity"), dict):
            kd = oie["opportunity"].get("knowledge_delta") or {}
        if not kd:
            kd = p.get("memory_delta") or {}

        watches = [
            {"signal": "knowledge_delta", "condition": "status != UNCHANGED", "active": bool(kd.get("status") and kd.get("status") != "UNCHANGED")},
            {
                "signal": "opportunity_score",
                "condition": "score >= 80",
                "active": (as_float(oie.get("score")) or 0) >= 80,
                "value": oie.get("score"),
            },
            {
                "signal": "opportunity_score",
                "condition": "score < 35",
                "active": (as_float(oie.get("score")) or 50) < 35,
                "value": oie.get("score"),
            },
            {
                "signal": "ownership_or_governance",
                "condition": "high severity blocker",
                "active": any(b.get("severity") == "High" for b in (oie.get("blockers") or [])),
            },
            {
                "signal": "catalyst",
                "condition": "high importance catalyst present",
                "active": any(c.get("importance") == "High" for c in (oie.get("catalysts") or [])),
            },
        ]
        meaningful = [w for w in watches if w.get("active")]
        row = {
            "company": p.get("display") or p.get("entity"),
            "entity": p.get("entity"),
            "memory_version": mem.get("memory_version") or (oie.get("freshness") or {}).get("memory_version"),
            "opportunity_score": oie.get("score"),
            "research_priority": oie.get("research_priority"),
            "delta_status": kd.get("status"),
            "watches": watches,
            "active_alerts_n": len(meaningful),
        }
        monitored.append(row)
        for w in meaningful:
            alerts.append(
                {
                    "ticker": row["company"],
                    "entity": row["entity"],
                    "signal": w.get("signal"),
                    "condition": w.get("condition"),
                    "value": w.get("value"),
                    "why_it_matters": _why(w, oie, kd),
                    "evidence": {
                        "opportunity_score": oie.get("score"),
                        "delta_summary": kd.get("summary"),
                        "blockers": [b.get("title") for b in (oie.get("blockers") or [])[:3]],
                    },
                }
            )

    monitored.sort(key=lambda r: (-(r.get("active_alerts_n") or 0), r.get("entity") or ""))
    alerts.sort(key=lambda a: (a.get("entity") or "", a.get("signal") or ""))
    return {
        "as_of": now_iso(),
        "monitored_companies": len(monitored),
        "entities": monitored,
        "meaningful_alerts": alerts,
        "policy": "alert_only_on_meaningful_compiled_changes",
    }


def _why(watch: dict[str, Any], oie: dict[str, Any], kd: dict[str, Any]) -> str:
    sig = watch.get("signal")
    if sig == "knowledge_delta":
        return f"Compiled memory changed: {kd.get('summary') or kd.get('status')}"
    if sig == "opportunity_score":
        return f"Opportunity score {oie.get('score')} crossed monitoring threshold ({watch.get('condition')})"
    if sig == "ownership_or_governance":
        return "High-severity research blocker active — governance/quality concern warrants review"
    if sig == "catalyst":
        return "High-importance catalyst elevates near-term research relevance"
    return "Meaningful monitoring condition triggered"
