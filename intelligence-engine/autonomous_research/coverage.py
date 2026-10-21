"""P6.3 Coverage Manager — institutional research coverage freshness."""

from __future__ import annotations

from typing import Any

from autonomous_research.util import as_float, delta_of, oie_of, today


def build_coverage(
    company_packs: list[dict[str, Any]],
    *,
    drafts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    draft_by = {(d.get("entity") or d.get("company") or "").upper(): d for d in (drafts or [])}
    stale = []
    missing = []
    upcoming = []
    covered = []

    for p in company_packs:
        entity = p.get("entity")
        display = p.get("display") or entity
        oie = oie_of(p)
        mem = p.get("memory") or {}
        kd = delta_of(p)
        has_draft = bool(draft_by.get((entity or "").upper()) or draft_by.get((display or "").upper()))
        mem_ver = mem.get("memory_version") or (oie.get("freshness") or {}).get("memory_version")
        score = as_float(oie.get("score"))

        row = {
            "company": display,
            "entity": entity,
            "ok": bool(p.get("ok")),
            "memory_version": mem_ver,
            "opportunity_score": score,
            "research_priority": oie.get("research_priority"),
            "has_research_draft": has_draft,
            "delta_status": kd.get("status"),
        }
        if p.get("ok"):
            covered.append(row)
        else:
            missing.append({**row, "reason": "compiled_intelligence_unavailable"})
            continue

        # Stale heuristics: no memory version, or material delta without draft, or monitor-only with no draft
        if mem_ver is None:
            stale.append({**row, "reason": "missing_memory_version"})
        elif kd.get("status") and kd.get("status") != "UNCHANGED" and not has_draft:
            stale.append({**row, "reason": "delta_without_research_draft"})
        elif oie.get("research_priority") in {"Critical", "High"} and not has_draft:
            upcoming.append({**row, "reason": "high_priority_needs_update"})

        if any(c.get("importance") == "High" for c in (oie.get("catalysts") or [])):
            upcoming.append({**row, "reason": "high_importance_catalyst"})

    return {
        "session_date": today(),
        "coverage": {
            "total_companies": len(company_packs),
            "covered_ok": len(covered),
            "stale_reports": stale,
            "missing_coverage": missing,
            "upcoming_updates": _dedupe(upcoming),
            "draft_n": len(drafts or []),
        },
        "rows": covered,
    }


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for r in rows:
        key = (r.get("entity"), r.get("reason"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    out.sort(key=lambda r: (r.get("entity") or "", r.get("reason") or ""))
    return out
