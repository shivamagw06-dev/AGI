"""P6.6 Evidence Monitor — meaningful compiled changes → research tasks."""

from __future__ import annotations

from typing import Any

from autonomous_research.util import as_float, delta_of, now_iso, oie_of


def build_evidence_monitor(company_packs: list[dict[str, Any]]) -> dict[str, Any]:
    events = []
    for p in company_packs:
        if not p.get("ok"):
            continue
        oie = oie_of(p)
        kd = delta_of(p)
        mem = p.get("memory") or {}
        ticker = p.get("display") or p.get("entity")

        if kd.get("status") and kd.get("status") != "UNCHANGED":
            events.append(
                _ev(
                    ticker,
                    p.get("entity"),
                    "knowledge_delta",
                    f"Memory delta {kd.get('status')}",
                    meaningful=True,
                    evidence={"summary": kd.get("summary"), "n_field_changes": kd.get("n_field_changes")},
                )
            )

        oh = mem.get("ownership_history") or {}
        for key in ("fii", "promoter", "dii"):
            direction = ((oh.get("trends") or {}).get(key) or {}).get("direction")
            if direction in {"rising", "falling"}:
                events.append(
                    _ev(
                        ticker,
                        p.get("entity"),
                        "ownership_change",
                        f"{key.upper()} {direction}",
                        meaningful=True,
                        evidence={"path": f"ownership_history.trends.{key}", "direction": direction},
                    )
                )

        for c in oie.get("catalysts") or []:
            if c.get("importance") == "High":
                events.append(
                    _ev(
                        ticker,
                        p.get("entity"),
                        "corporate_or_event",
                        c.get("name") or "Catalyst",
                        meaningful=True,
                        evidence=c.get("evidence") or {"importance": c.get("importance")},
                    )
                )

        for b in oie.get("blockers") or []:
            if b.get("severity") == "High":
                events.append(
                    _ev(
                        ticker,
                        p.get("entity"),
                        "risk_flag",
                        b.get("title") or "Blocker",
                        meaningful=True,
                        evidence={"detail": b.get("detail"), "code": b.get("code")},
                    )
                )

        score = as_float(oie.get("score"))
        if score is not None and (score >= 80 or score < 35):
            events.append(
                _ev(
                    ticker,
                    p.get("entity"),
                    "opportunity_extremum",
                    f"Opportunity score {score}",
                    meaningful=True,
                    evidence={"score": score, "priority": oie.get("research_priority")},
                )
            )

    # Only meaningful → research tasks
    tasks = [
        {
            "company": e["ticker"],
            "entity": e["entity"],
            "trigger": e["category"],
            "what_changed": e["what_changed"],
            "evidence": e["evidence"],
        }
        for e in events
        if e.get("meaningful")
    ]
    tasks.sort(key=lambda t: (t.get("entity") or "", t.get("trigger") or ""))
    return {
        "as_of": now_iso(),
        "events_n": len(events),
        "meaningful_n": len(tasks),
        "events": events,
        "research_tasks": tasks,
        "policy": "only_meaningful_compiled_changes_become_tasks",
    }


def _ev(
    ticker: str,
    entity: str | None,
    category: str,
    what: str,
    *,
    meaningful: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "entity": entity,
        "category": category,
        "what_changed": what,
        "meaningful": meaningful,
        "evidence": evidence,
    }
