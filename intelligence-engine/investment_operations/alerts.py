"""P5.8 Alert Centre — explainable institutional alerts from compiled intelligence."""

from __future__ import annotations

from typing import Any

from investment_operations.util import as_float, now_iso


def build_alert_centre(
    company_packs: list[dict[str, Any]],
    *,
    monitoring: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    alerts: list[dict[str, Any]] = []

    for p in company_packs:
        if not p.get("ok"):
            continue
        oie = p.get("opportunity") or {}
        kd = {}
        if isinstance(oie.get("opportunity"), dict):
            kd = oie["opportunity"].get("knowledge_delta") or {}
        if not kd:
            kd = p.get("memory_delta") or {}
        ticker = p.get("display") or p.get("entity")
        score = as_float(oie.get("score"))

        if kd.get("status") and kd.get("status") != "UNCHANGED":
            alerts.append(
                _alert(
                    "knowledge_delta",
                    ticker,
                    p.get("entity"),
                    what=f"Knowledge Delta {kd.get('status')}",
                    why="Compiled CompanyMemory changed — research context may need refresh",
                    evidence={"summary": kd.get("summary"), "n_field_changes": kd.get("n_field_changes")},
                    severity="High" if (as_float(kd.get("n_field_changes")) or 0) >= 3 else "Medium",
                )
            )

        if score is not None and score >= 80:
            alerts.append(
                _alert(
                    "opportunity_score_change",
                    ticker,
                    p.get("entity"),
                    what=f"Opportunity Score {score}",
                    why="Score entered Critical research-attention band",
                    evidence={"score": score, "priority": oie.get("research_priority"), "why_now": oie.get("why_now")},
                    severity="High",
                )
            )

        for b in oie.get("blockers") or []:
            if b.get("severity") == "High":
                alerts.append(
                    _alert(
                        "contradiction",
                        ticker,
                        p.get("entity"),
                        what=b.get("title") or "High blocker",
                        why="High-severity research blocker reduces conviction quality",
                        evidence={"detail": b.get("detail"), "code": b.get("code")},
                        severity="High",
                    )
                )

        for c in oie.get("catalysts") or []:
            if c.get("importance") == "High":
                alerts.append(
                    _alert(
                        "catalyst",
                        ticker,
                        p.get("entity"),
                        what=c.get("name") or "Catalyst",
                        why="High-importance catalyst increases near-term research relevance",
                        evidence=c.get("evidence") or {"window": c.get("expected_window")},
                        severity="Medium",
                    )
                )

        if (p.get("hypotheses") or {}).get("_ok") and (p.get("hypotheses") or {}).get("enabled"):
            # Soft presence — not a strength change unless pack provides status
            pass

        if (p.get("scenarios") or {}).get("_ok"):
            alerts.append(
                _alert(
                    "scenario",
                    ticker,
                    p.get("entity"),
                    what="Scenario intelligence available",
                    why="Bull/base/bear context can be refreshed in workspace",
                    evidence={"source": "institutional_scenario_intelligence"},
                    severity="Low",
                )
            )

        if (p.get("causal") or {}).get("_ok"):
            alerts.append(
                _alert(
                    "macro_propagation",
                    ticker,
                    p.get("entity"),
                    what="Causal graph soft-pack available",
                    why="Macro/sector propagation context present for second-order review",
                    evidence={"source": "causal_graph"},
                    severity="Low",
                )
            )

    for a in (monitoring or {}).get("meaningful_alerts") or []:
        alerts.append(
            _alert(
                "monitoring",
                a.get("ticker"),
                a.get("entity"),
                what=f"Monitor: {a.get('signal')}",
                why=a.get("why_it_matters") or "Monitoring condition triggered",
                evidence=a.get("evidence") or {},
                severity="Medium",
            )
        )

    for r in (portfolio or {}).get("research_required") or []:
        alerts.append(
            _alert(
                "portfolio_exposure",
                r.get("holding"),
                None,
                what="Portfolio holding requires research",
                why=r.get("reason") or "Holding flagged by portfolio operations",
                evidence={"urgency": r.get("urgency")},
                severity=r.get("urgency") if r.get("urgency") in {"Critical", "High", "Medium", "Low"} else "Medium",
            )
        )

    sev = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    # Deduplicate
    seen = set()
    uniq = []
    for a in alerts:
        key = (a.get("type"), a.get("ticker"), a.get("what_changed"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    uniq.sort(key=lambda a: (sev.get(a.get("severity") or "", 9), a.get("ticker") or "", a.get("type") or ""))

    return {
        "as_of": now_iso(),
        "n": len(uniq),
        "alerts": uniq,
        "by_type": _group(uniq),
    }


def _alert(
    typ: str,
    ticker: str | None,
    entity: str | None,
    *,
    what: str,
    why: str,
    evidence: dict[str, Any],
    severity: str,
) -> dict[str, Any]:
    return {
        "type": typ,
        "ticker": ticker,
        "entity": entity,
        "severity": severity,
        "what_changed": what,
        "why_it_matters": why,
        "supporting_evidence": evidence,
        "issues_recommendations": False,
    }


def _group(alerts: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for a in alerts:
        k = a.get("type") or "other"
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))
