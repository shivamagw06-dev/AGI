"""P5.2 Research Operations Queue — deterministic analyst work queue."""

from __future__ import annotations

from typing import Any

from investment_operations.util import as_float, priority_rank, today


def build_research_queue(
    company_packs: list[dict[str, Any]],
    *,
    holdings: list[str] | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    holdings_set = {h.upper() for h in (holdings or [])}
    tasks = []
    for p in company_packs:
        if not p.get("ok"):
            continue
        oie = p.get("opportunity") or {}
        score = as_float(oie.get("score")) or 0.0
        priority = oie.get("research_priority") or "Monitor"
        kd = {}
        if isinstance(oie.get("opportunity"), dict):
            kd = oie["opportunity"].get("knowledge_delta") or {}
        if not kd:
            kd = p.get("memory_delta") or {}
        delta_n = as_float(kd.get("n_field_changes")) or 0.0
        catalysts = oie.get("catalysts") or []
        high_cat = sum(1 for c in catalysts if c.get("importance") == "High")
        blockers = oie.get("blockers") or []
        high_block = sum(1 for b in blockers if b.get("severity") == "High")
        in_port = (p.get("display") or "").upper() in holdings_set or (p.get("entity") or "") in holdings_set

        # Composite urgency score (transparent, deterministic)
        urgency = (
            score * 0.45
            + (4 - min(priority_rank(priority), 4)) * 12
            + min(20.0, delta_n * 3)
            + high_cat * 8
            + high_block * 5
            + (10 if in_port else 0)
        )
        freshness = ((oie.get("freshness") or {}).get("memory_compiled_at")) or (
            (p.get("memory") or {}).get("compiled_at")
        )
        reason_bits = []
        if priority in {"Critical", "High"}:
            reason_bits.append(f"Opportunity priority {priority}")
        if kd.get("status") and kd.get("status") != "UNCHANGED":
            reason_bits.append(f"Delta {kd.get('status')} ({int(delta_n)} fields)")
        if high_cat:
            reason_bits.append(f"{high_cat} high catalysts")
        if in_port:
            reason_bits.append("Portfolio holding")
        if oie.get("why_now"):
            reason_bits.append(str(oie["why_now"])[:120])

        deadline = "same_day" if urgency >= 70 or priority == "Critical" else (
            "this_week" if urgency >= 50 or priority == "High" else "monitor"
        )
        tasks.append(
            {
                "research_task": {
                    "company": p.get("display") or p.get("entity"),
                    "entity": p.get("entity"),
                    "priority": priority,
                    "reason": "; ".join(reason_bits) or "Coverage maintenance",
                    "deadline": deadline,
                    "supporting_evidence": {
                        "opportunity_score": score,
                        "knowledge_delta": {
                            "status": kd.get("status"),
                            "n_field_changes": kd.get("n_field_changes"),
                            "summary": kd.get("summary"),
                        },
                        "catalysts": [
                            {"name": c.get("name"), "importance": c.get("importance")}
                            for c in catalysts[:4]
                        ],
                        "blockers": [
                            {"title": b.get("title"), "severity": b.get("severity")}
                            for b in blockers[:4]
                        ],
                        "portfolio_relevant": in_port,
                        "memory_freshness": freshness,
                    },
                },
                "urgency_score": round(urgency, 1),
            }
        )

    tasks.sort(
        key=lambda t: (
            -t["urgency_score"],
            priority_rank(t["research_task"].get("priority")),
            t["research_task"].get("entity") or "",
        )
    )
    trimmed = tasks[: max(1, min(int(limit), 100))]
    return {
        "session_date": today(),
        "n": len(trimmed),
        "universe_n": len(company_packs),
        "tasks": [t["research_task"] for t in trimmed],
        "urgency": [{"company": t["research_task"]["company"], "urgency_score": t["urgency_score"]} for t in trimmed],
    }
