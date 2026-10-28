"""P5.1 Institutional Morning Office — orchestrated analyst briefing."""

from __future__ import annotations

from typing import Any

from investment_operations.util import as_float, now_iso, priority_rank, soft_call, today


def build_morning_office(
    company_packs: list[dict[str, Any]],
    *,
    holdings: list[str] | None = None,
) -> dict[str, Any]:
    rows = [_thin(p) for p in company_packs if p.get("ok")]
    holdings_set = {h.upper() for h in (holdings or [])}

    top_opps = sorted(
        rows,
        key=lambda r: (-(as_float(r.get("opportunity_score")) or 0), priority_rank(r.get("research_priority")), r.get("entity") or ""),
    )

    overnight = []
    for r in rows:
        if r.get("delta_status") and r.get("delta_status") != "UNCHANGED":
            overnight.append(
                {
                    "ticker": r.get("display"),
                    "entity": r.get("entity"),
                    "delta_status": r.get("delta_status"),
                    "summary": r.get("delta_summary"),
                    "n_field_changes": r.get("delta_changes"),
                }
            )
    overnight.sort(key=lambda x: (-(as_float(x.get("n_field_changes")) or 0), x.get("entity") or ""))

    portfolio_alerts = [
        r
        for r in top_opps
        if (r.get("display") in holdings_set or r.get("entity") in holdings_set)
        and (
            priority_rank(r.get("research_priority")) <= 1
            or (r.get("blocker_n") or 0) >= 2
            or (r.get("delta_status") not in {None, "UNCHANGED"})
        )
    ]

    catalysts = []
    for r in rows:
        for c in r.get("catalysts") or []:
            catalysts.append(
                {
                    "ticker": r.get("display"),
                    "entity": r.get("entity"),
                    **c,
                }
            )
    imp = {"High": 0, "Medium": 1, "Low": 2}
    catalysts.sort(key=lambda c: (imp.get(c.get("importance") or "", 9), c.get("ticker") or "", c.get("name") or ""))

    contradictions = []
    for p in company_packs:
        contra = p.get("contradictions") or {}
        if contra.get("_ok") is False:
            continue
        # Soft signals from contradiction pack or high blockers + optimistic corp
        blockers = (p.get("opportunity") or {}).get("blockers") or []
        high_b = [b for b in blockers if b.get("severity") == "High"]
        if high_b and ((p.get("opportunity") or {}).get("score") or 0) >= 55:
            contradictions.append(
                {
                    "ticker": p.get("display") or p.get("entity"),
                    "severity": "Medium",
                    "title": "Opportunity strength coexists with high blockers",
                    "blockers": [b.get("title") for b in high_b[:3]],
                    "evidence": "opportunity_intelligence.blockers",
                }
            )
        if contra.get("enabled") or contra.get("contradictions") or contra.get("steps"):
            contradictions.append(
                {
                    "ticker": p.get("display") or p.get("entity"),
                    "severity": "Low",
                    "title": "Contradiction reasoning soft-pack available",
                    "evidence": "contradiction_reasoning",
                }
            )

    analyst_priorities = [
        {
            "ticker": r.get("display"),
            "entity": r.get("entity"),
            "priority": r.get("research_priority"),
            "score": r.get("opportunity_score"),
            "why_now": r.get("why_now"),
            "reason": _attention_reason(r),
        }
        for r in top_opps
        if priority_rank(r.get("research_priority")) <= 2
    ][:15]

    # Soft market / macro overlays (never hard-fail)
    market = soft_call("investment_office", _soft_market_summary)
    macro = soft_call("investment_kg_macro", _soft_macro)
    themes = _theme_changes(company_packs)
    sectors = _sector_rotation(rows)

    return {
        "as_of": now_iso(),
        "session_date": today(),
        "greeting": f"Good Morning — Institutional Morning Office ({today()})",
        "market_summary": {
            "covered_companies": len(rows),
            "universe_ok": len(rows),
            "desk": market if market.get("_ok") else {"status": "soft_unavailable"},
            "note": "Compiled from existing intelligence engines — no new reasoning.",
        },
        "overnight_changes": overnight,
        "top_opportunities": [
            {
                "ticker": r.get("display"),
                "entity": r.get("entity"),
                "score": r.get("opportunity_score"),
                "research_priority": r.get("research_priority"),
                "why_now": r.get("why_now"),
            }
            for r in top_opps[:10]
        ],
        "new_contradictions": contradictions[:10],
        "portfolio_alerts": [
            {
                "ticker": r.get("display"),
                "priority": r.get("research_priority"),
                "score": r.get("opportunity_score"),
                "why": _attention_reason(r),
            }
            for r in portfolio_alerts[:10]
        ],
        "macro_updates": macro if macro.get("_ok") else {"chains": [], "status": "soft_unavailable"},
        "theme_changes": themes,
        "sector_rotation": sectors,
        "catalysts": catalysts[:20],
        "analyst_priorities": analyst_priorities,
        "companies_requiring_attention": analyst_priorities[:10],
    }


def _thin(p: dict[str, Any]) -> dict[str, Any]:
    oie = p.get("opportunity") or {}
    opp = oie.get("opportunity") if isinstance(oie.get("opportunity"), dict) else {}
    delta = p.get("memory_delta") or opp.get("knowledge_delta") or oie.get("opportunity", {}).get("knowledge_delta")
    if not isinstance(delta, dict):
        delta = (oie.get("freshness") and {}) or {}
    # Prefer structured knowledge_delta on opportunity pack
    kd = None
    if isinstance(oie.get("opportunity"), dict):
        kd = oie["opportunity"].get("knowledge_delta")
    if not isinstance(kd, dict):
        kd = p.get("memory_delta") if isinstance(p.get("memory_delta"), dict) else {}
    return {
        "entity": p.get("entity"),
        "display": p.get("display") or oie.get("display") or p.get("entity"),
        "opportunity_score": oie.get("score") if oie.get("score") is not None else opp.get("score"),
        "research_priority": oie.get("research_priority") or opp.get("research_priority"),
        "why_now": oie.get("why_now") or opp.get("why_now"),
        "catalysts": oie.get("catalysts") or opp.get("catalysts") or [],
        "blocker_n": len(oie.get("blockers") or opp.get("blockers") or []),
        "delta_status": kd.get("status"),
        "delta_summary": kd.get("summary"),
        "delta_changes": kd.get("n_field_changes"),
        "sector_key": ((p.get("memory") or {}).get("sector_history") or {}).get("sector_key")
        or ((p.get("knowledge_graph") or {}).get("sector_key")),
        "themes": (p.get("knowledge_graph") or {}).get("themes") or [],
    }


def _attention_reason(r: dict[str, Any]) -> str:
    bits = []
    if r.get("research_priority") in {"Critical", "High"}:
        bits.append(f"Research priority {r.get('research_priority')}")
    if r.get("delta_status") and r.get("delta_status") != "UNCHANGED":
        bits.append(f"Knowledge Delta {r.get('delta_status')}")
    if (r.get("blocker_n") or 0) >= 2:
        bits.append(f"{r.get('blocker_n')} blockers")
    if r.get("why_now"):
        bits.append(str(r["why_now"])[:140])
    return "; ".join(bits) if bits else "Scheduled coverage review"


def _soft_market_summary() -> dict[str, Any]:
    # Prefer cached desk — never block Morning Office on full aggregate rebuild
    try:
        from investment_office.production import cached_desk

        desk = cached_desk()
        if isinstance(desk, dict) and desk.get("enabled"):
            return {
                "enabled": True,
                "from_cache": True,
                "attention_count": len(desk.get("companies_requiring_attention") or []),
                "queue_count": len(desk.get("todays_research_queue") or []),
                "regime": ((desk.get("morning_executive_brief") or {}).get("market_regime")),
            }
    except Exception:
        pass
    try:
        from investment_office.production import health

        h = health()
        return {"enabled": h.get("enabled"), "status": h.get("status"), "from_cache": False}
    except Exception as exc:  # noqa: BLE001
        return {"enabled": False, "error": str(exc)[:120]}


def _soft_macro() -> dict[str, Any]:
    from investment_knowledge_graph.production import macro

    return macro(None)


def _theme_changes(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, list[str]] = {}
    for p in packs:
        for th in (p.get("knowledge_graph") or {}).get("themes") or []:
            counts.setdefault(th, []).append(p.get("display") or p.get("entity"))
    out = [{"theme": k, "members": sorted(v), "n": len(v)} for k, v in counts.items()]
    out.sort(key=lambda x: (-x["n"], x["theme"]))
    return out


def _sector_rotation(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by: dict[str, list[float]] = {}
    for r in rows:
        sk = r.get("sector_key") or "unknown"
        sc = as_float(r.get("opportunity_score"))
        if sc is not None:
            by.setdefault(sk, []).append(sc)
    out = [
        {
            "sector_key": k,
            "n": len(v),
            "avg_opportunity_score": round(sum(v) / len(v), 1),
            "max_opportunity_score": round(max(v), 1),
        }
        for k, v in by.items()
    ]
    out.sort(key=lambda x: (-x["avg_opportunity_score"], x["sector_key"]))
    return out
