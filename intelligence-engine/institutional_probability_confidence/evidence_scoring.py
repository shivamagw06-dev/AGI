"""Evidence scoring — deterministic inputs for probability and confidence."""

from __future__ import annotations

from typing import Any


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def score_evidence_quality(scenario_report: dict[str, Any]) -> dict[str, Any]:
    """Score evidence quality 0-100 from scenario report structure."""
    scenarios = scenario_report.get("scenarios") or []
    total_ev = 0
    with_ev = 0
    for s in scenarios:
        ev = s.get("supporting_evidence") or []
        total_ev += len(ev)
        if ev:
            with_ev += 1
    coverage = (with_ev / max(1, len(scenarios))) * 100.0
    density = _clamp(total_ev * 8.0)  # ~4 evidence × 3 scenarios → high
    contradictions = len(scenario_report.get("contradictions") or [])
    contra_penalty = min(25.0, contradictions * 4.0)
    score = _clamp(0.55 * coverage + 0.45 * density - contra_penalty)
    level = "High" if score >= 80 else "Medium" if score >= 55 else "Low"
    return {
        "score_pct": int(round(score)),
        "level": level,
        "evidence_items": total_ev,
        "scenarios_with_evidence": with_ev,
        "contradictions": contradictions,
    }


def score_historical_coverage(scenario_report: dict[str, Any], bundle_tip: dict[str, Any] | None = None) -> int:
    tip = bundle_tip or scenario_report.get("forecast_bundle_tip") or {}
    completeness = ((scenario_report.get("completeness") or {}).get("bundle") or {})
    score = float(completeness.get("score") or 0) * 100.0
    if tip.get("analogue_count"):
        score = max(score, 70.0)
    hist_cov = completeness.get("historical_coverage") or completeness.get("overall")
    if hist_cov == "Complete":
        score = max(score, 90.0)
    elif hist_cov == "Partial":
        score = max(score, 70.0)
    # Analogue presence boosts coverage signal
    ana = 0
    for s in scenario_report.get("scenarios") or []:
        ana += len(s.get("historical_analogues") or [])
    if ana >= 3:
        score = max(score, 85.0)
    return int(round(_clamp(score if score else 60.0)))


def score_analogue_strength(scenario_report: dict[str, Any]) -> tuple[int, int]:
    scores: list[float] = []
    count = 0
    for s in scenario_report.get("scenarios") or []:
        for a in s.get("historical_analogues") or []:
            count += 1
            if a.get("similarity_score") is not None:
                scores.append(float(a["similarity_score"]))
    if not count:
        return 40, 0
    avg = sum(scores) / len(scores) if scores else 65.0
    return int(round(_clamp(avg))), count


def score_freshness(scenario_report: dict[str, Any]) -> int:
    fresh = scenario_report.get("freshness") or {}
    if fresh.get("hip_enriched"):
        return 98
    if fresh.get("monitoring") == "current":
        return 92
    if fresh.get("catalog") == "institutional_seed":
        return 88
    return 75


def score_research_quality(scenario_report: dict[str, Any]) -> int:
    # Research tips live on bundle; scenario report may only have thesis
    if scenario_report.get("investment_thesis"):
        return 90
    return 70


def extract_missing_evidence(scenario_report: dict[str, Any]) -> list[str]:
    missing = list(((scenario_report.get("completeness") or {}).get("missing_evidence")) or [])
    # Institutional gaps commonly relevant to forecast quality
    defaults = []
    if "pattern_intelligence" in missing:
        defaults.append("Pattern & Cycle Intelligence")
    # Always surface forward-looking monitoring gaps as confidence reducers (not blockers)
    monitoring = scenario_report.get("monitoring_events") or []
    statuses = {m.get("status") for m in monitoring}
    if "Scheduled" in statuses or not monitoring:
        defaults.append("Updated Management Guidance")
        defaults.append("Next Earnings Call")
    # Dedup
    out: list[str] = []
    for m in missing + defaults:
        label = str(m).replace("_", " ").title() if "_" in str(m) else str(m)
        if label not in out:
            out.append(label)
    return out


def contradiction_level(n: int) -> str:
    if n >= 4:
        return "High"
    if n >= 2:
        return "Moderate"
    return "Low"


def missing_level(n: int) -> str:
    if n >= 4:
        return "High"
    if n >= 2:
        return "Moderate"
    return "Low"


def soft_triggers_from_report(scenario_report: dict[str, Any]) -> list[dict[str, Any]]:
    """CTI soft tip — derive watching triggers from monitoring + catalysts when CTI absent."""
    triggers = []
    for m in scenario_report.get("monitoring_events") or []:
        triggers.append(
            {
                "trigger": m.get("event"),
                "status": m.get("status") or "Watching",
                "importance": m.get("importance"),
                "source": "monitoring",
            }
        )
    for s in scenario_report.get("scenarios") or []:
        for c in (s.get("catalysts") or [])[:2]:
            triggers.append(
                {
                    "trigger": c.get("catalyst"),
                    "status": "Watching",
                    "polarity": c.get("polarity"),
                    "scenario": s.get("type"),
                    "source": "catalyst",
                }
            )
    # Dedup
    seen: set[str] = set()
    out = []
    for t in triggers:
        key = str(t.get("trigger"))
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out[:12]
