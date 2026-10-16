"""Trigger objects — deterministic conditions that would change the institutional view."""

from __future__ import annotations

import hashlib
from typing import Any

from catalyst_trigger_intelligence.catalysts import company_catalysts
from catalyst_trigger_intelligence.schema import CTI_VERSION, TRIGGER_STATES
from catalyst_trigger_intelligence.store import get_store
from catalyst_trigger_intelligence import traces


def _trigger_id(entity: str, catalyst_id: str, condition: str) -> str:
    raw = f"{entity}|{catalyst_id}|{condition}".encode("utf-8")
    return f"TR-{hashlib.sha1(raw).hexdigest()[:10].upper()}"


def _current_scenario_from_fie(ticker: str) -> str:
    try:
        from forecast_intelligence.production import scenarios

        pack = scenarios(ticker)
        probs = (pack.get("probabilities") or {}).get("distribution") or {}
        if not probs:
            return "base"
        return max(probs.items(), key=lambda kv: float(kv[1] or 0))[0]
    except Exception:
        return "base"


def catalyst_to_trigger(catalyst: dict[str, Any], *, entity: str, current_scenario: str) -> dict[str, Any]:
    """Every catalyst produces a deterministic trigger object where appropriate."""
    cid = str(catalyst.get("id") or "catalyst")
    condition = str(catalyst.get("condition") or "")
    tid = _trigger_id(entity, cid, condition)
    impact = catalyst.get("impact") or "neutral"
    affected = "bull" if "bull" in impact else (
        "bear" if "bear" in impact else ("base" if "base" in impact else current_scenario)
    )
    return {
        "trigger_id": tid,
        "entity": entity.upper(),
        "entity_name": catalyst.get("entity_name") or entity.upper(),
        "catalyst_id": cid,
        "event": catalyst.get("event") or catalyst.get("label"),
        "condition": condition,
        "current_status": "inactive",
        "state": "Scheduled",
        "allowed_states": list(TRIGGER_STATES),
        "expected_date": catalyst.get("expected_date") or catalyst.get("horizon") or "calendar-dependent",
        "probability": float(catalyst.get("probability") or catalyst.get("confidence") or 0.5),
        "importance": catalyst.get("priority") or "Medium",
        "priority": catalyst.get("priority") or "Medium",
        "affected_scenario": affected,
        "impact": impact,
        "impact_label": catalyst.get("impact_label"),
        "monitoring_source": catalyst.get("monitoring_source") or "knowledge_base",
        "evidence": list(catalyst.get("evidence") or []),
        "confidence": float(catalyst.get("confidence") or catalyst.get("probability") or 0.5),
        "category": catalyst.get("category") or "company",
        "current_institutional_view": current_scenario,
        "institutional_rule": f"We are {current_scenario.replace('_', ' ').title()} Case unless: {condition}",
        "auto_rewrites_thesis": False,
        "cti_version": CTI_VERSION,
        "history": [{"from": None, "to": "Scheduled", "note": "generated"}],
    }


def build_company_triggers(ticker: str, *, persist: bool = True) -> dict[str, Any]:
    span = traces.begin("trigger_monitoring", meta={"ticker": ticker})
    t = (ticker or "").upper()
    current = _current_scenario_from_fie(t)
    cat_pack = company_catalysts(t, current_scenario=current)
    triggers: list[dict[str, Any]] = []
    store = get_store()

    for c in cat_pack.get("company") or []:
        tr = catalyst_to_trigger(c, entity=t, current_scenario=current)
        tr["state"] = "Watching"  # active institutional watch once generated
        tr["history"] = [
            {"from": None, "to": "Scheduled", "note": "generated"},
            {"from": "Scheduled", "to": "Watching", "note": "monitoring_office_watch"},
        ]
        if persist:
            store.upsert(tr)
        triggers.append(tr)

    # Sector / macro linked triggers also watched for the name
    for c in (cat_pack.get("sector_catalysts") or [])[:4]:
        tr = catalyst_to_trigger(c, entity=t, current_scenario=current)
        tr["state"] = "Watching"
        tr["scope"] = "sector"
        if persist:
            store.upsert(tr)
        triggers.append(tr)

    for c in (cat_pack.get("macro_catalysts") or [])[:4]:
        tr = catalyst_to_trigger(c, entity=t, current_scenario=current)
        tr["state"] = "Watching"
        tr["scope"] = "macro"
        if persist:
            store.upsert(tr)
        triggers.append(tr)

    # Merge FIE measurable scenario triggers as Watching conditions
    try:
        from forecast_intelligence.production import scenarios

        fie = scenarios(t)
        matrix = fie.get("trigger_matrix") or {}
        for scenario, items in matrix.items():
            for item in items or []:
                condition = f"{item.get('metric')} {item.get('condition')}"
                synthetic = {
                    "id": f"fie_{scenario}_{item.get('metric')}",
                    "label": condition,
                    "event": f"{scenario} path trigger",
                    "condition": condition,
                    "impact": f"strengthens_{scenario}" if scenario in {"bull", "bear", "base"} else "neutral",
                    "impact_label": f"Supports {scenario} scenario path",
                    "priority": "High" if scenario in {"bull", "bear"} else "Medium",
                    "probability": 0.55,
                    "monitoring_source": "forecast_intelligence.triggers",
                    "category": "company",
                    "entity_name": cat_pack.get("name"),
                    "evidence": [{"kind": "fie_trigger", "observable": item.get("observable", True)}],
                    "confidence": 0.7 if item.get("observable") else 0.4,
                }
                tr = catalyst_to_trigger(synthetic, entity=t, current_scenario=current)
                tr["state"] = "Watching"
                tr["affected_scenario"] = scenario
                tr["scope"] = "fie_scenario_trigger"
                if persist:
                    store.upsert(tr)
                triggers.append(tr)
    except Exception:
        pass

    by_state: dict[str, int] = {}
    for tr in triggers:
        by_state[tr["state"]] = by_state.get(tr["state"], 0) + 1

    out = {
        "ticker": t,
        "current_scenario": current,
        "triggers": triggers,
        "count": len(triggers),
        "by_state": by_state,
        "by_priority": _count_priority(triggers),
        "institutional_rule": "We are Base Case unless X happens.",
        "auto_rewrites_thesis": False,
        "cti_version": CTI_VERSION,
    }
    traces.end(span, output={"count": out["count"], "watching": by_state.get("Watching", 0)})
    return out


def _count_priority(triggers: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in triggers:
        p = str(t.get("priority") or "Medium")
        out[p] = out.get(p, 0) + 1
    return out
