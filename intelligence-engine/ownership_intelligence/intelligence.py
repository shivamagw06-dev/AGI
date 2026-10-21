"""Derived ownership intelligence — analytical facts only (no BUY/SELL)."""

from __future__ import annotations

from typing import Any

from ownership_intelligence.trends import rolling_trend


def _f(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _band(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 80:
        return "high"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "developing"
    return "low"


def derive_observations(
    current: dict[str, Any],
    *,
    qoq: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Return analytical ownership observations (no recommendations)."""
    obs: list[str] = []
    prom = _f(current.get("promoter"))
    fii = _f(current.get("fii"))
    dii = _f(current.get("dii"))
    mf = _f(current.get("mutual_funds"))
    ins = _f(current.get("insurance"))
    pub = _f(current.get("public"))
    pledge = _f(current.get("promoter_pledge_pct"))
    pledged = current.get("promoter_pledge")

    inst = None
    if fii is not None or dii is not None:
        inst = round((fii or 0.0) + (dii or 0.0), 4)

    if prom is not None and prom <= 5 and inst is not None and inst >= 50:
        obs.append("Institutionally owned")
    elif (
        prom is not None
        and 35.0 <= prom <= 65.0
        and inst is not None
        and inst >= 25.0
    ):
        # Balanced control + institutions (e.g. mid-promoter large-caps)
        obs.append("Mixed promoter + institutional ownership")
    elif prom is not None and prom >= 50:
        obs.append("Promoter controlled")

    if prom is not None and prom >= 70:
        obs.append("Highly concentrated ownership")
    elif prom is not None and prom <= 5 and pub is not None and pub >= 90:
        obs.append("Dispersed ownership")

    if inst is not None and inst >= 45:
        obs.append("High institutional participation")
    elif inst is not None and inst < 25:
        obs.append("Lower institutional participation")

    deltas = (qoq or {}).get("deltas_pp") or {}
    if _f(deltas.get("fii")) is not None:
        d = float(deltas["fii"])
        if d > 0.25:
            obs.append("FII accumulation")
        elif d < -0.25:
            obs.append("FII selling")
    if _f(deltas.get("mutual_funds")) is not None:
        d = float(deltas["mutual_funds"])
        if d > 0.25:
            obs.append("Mutual fund accumulation")
        elif d < -0.25:
            obs.append("Mutual fund reduction")
    if _f(deltas.get("insurance")) is not None and float(deltas["insurance"]) > 0.25:
        obs.append("Insurance accumulation")
    if _f(deltas.get("dii")) is not None:
        d = float(deltas["dii"])
        if d > 0.25:
            obs.append("Increasing institutional participation")
        elif d < -0.25:
            obs.append("Decreasing institutional participation")

    # Stability from rolling promoter/FII
    hist = history or []
    prom_t = rolling_trend(hist, "promoter")
    fii_t = rolling_trend(hist, "fii")
    if prom_t.get("direction") == "stable" and fii_t.get("direction") in {"stable", "insufficient_history"}:
        obs.append("Stable ownership")
    if prom is not None and prom >= 50:
        obs.append("Strong promoter alignment" if prom >= 65 else "Promoter alignment present")
        obs.append("Governance comfort")
    if pledged is True or (pledge is not None and pledge > 0):
        if pledge is not None and pledge >= 5:
            obs.append("Promoter pledge concern")
        else:
            obs.append("Promoter pledge present")
    elif pledged is False or pledge == 0.0:
        if prom is not None and prom > 0:
            obs.append("No promoter pledge reported")

    if prom is not None and prom >= 70:
        obs.append("Ownership concentration risk")

    # Dedupe preserve order
    seen: set[str] = set()
    uniq = []
    for o in obs:
        if o not in seen:
            seen.add(o)
            uniq.append(o)
    return uniq


def build_intelligence_layer(
    current: dict[str, Any],
    *,
    qoq: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    freshness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured ownership intelligence object for Decision Engine / CID."""
    observations = derive_observations(current, qoq=qoq, history=history)
    prom = _f(current.get("promoter"))
    fii = _f(current.get("fii"))
    dii = _f(current.get("dii"))
    mf = _f(current.get("mutual_funds"))
    ins = _f(current.get("insurance"))
    pledge = _f(current.get("promoter_pledge_pct"))
    inst = None
    if fii is not None or dii is not None:
        inst = round((fii or 0.0) + (dii or 0.0), 4)

    # Soft analytical scores (evidence quality / structure — not investment recommendation)
    present = sum(
        1
        for k in ("promoter", "public", "fii", "dii", "mutual_funds", "insurance")
        if _f(current.get(k)) is not None
    )
    coverage_score = round(100.0 * present / 6.0, 1)

    # Ownership quality: completeness + no pledge concern + institutional or clear control structure
    quality = coverage_score
    if "Promoter pledge concern" in observations:
        quality -= 15
    if "Stable ownership" in observations:
        quality += 5
    if "Institutionally owned" in observations or "Promoter controlled" in observations:
        quality += 5
    quality = max(0.0, min(100.0, quality))

    # Stability from trends
    hist = history or []
    prom_t = rolling_trend(hist, "promoter")
    fii_t = rolling_trend(hist, "fii")
    stability = 70.0
    if prom_t.get("direction") == "stable":
        stability += 10
    elif prom_t.get("direction") in {"increasing", "decreasing"}:
        stability -= 10
    if fii_t.get("direction") == "stable":
        stability += 5
    elif fii_t.get("direction") == "decreasing":
        stability -= 5
    stability = max(0.0, min(100.0, stability))

    institutional_participation = 0.0 if inst is None else max(0.0, min(100.0, inst * 1.1))
    if prom is not None and prom <= 5:
        promoter_alignment = 40.0  # professionally managed — alignment via institutions
    elif prom is None:
        promoter_alignment = 0.0
    else:
        promoter_alignment = max(0.0, min(100.0, prom))

    pledge_risk = 0.0
    if current.get("promoter_pledge") is True or (pledge or 0) > 0:
        pledge_risk = max(10.0, min(100.0, (pledge or 10.0) * 2.5))

    # Governance signals — analytical
    gov_signals = []
    if "No promoter pledge reported" in observations:
        gov_signals.append("no_promoter_pledge")
    if "Promoter pledge concern" in observations:
        gov_signals.append("elevated_pledge")
    if "Governance comfort" in observations:
        gov_signals.append("clear_control_structure")
    if "Institutionally owned" in observations:
        gov_signals.append("institutional_oversight")

    # Trend summary
    trend_label = "stable"
    if "FII accumulation" in observations or "Mutual fund accumulation" in observations:
        trend_label = "institutional_accumulation"
    elif "FII selling" in observations or "Decreasing institutional participation" in observations:
        trend_label = "institutional_reduction"
    elif "Increasing institutional participation" in observations:
        trend_label = "institutional_accumulation"

    stale = bool((freshness or {}).get("stale"))
    confidence = round(min(0.95, 0.35 + 0.1 * present + (0.1 if not stale else 0.0)), 3)

    reasoning_parts = [
        f"Promoter {prom:.2f}%" if prom is not None else "Promoter unavailable",
        f"FII {fii:.2f}%" if fii is not None else None,
        f"DII {dii:.2f}%" if dii is not None else None,
        f"MF {mf:.2f}%" if mf is not None else None,
        f"Insurance {ins:.2f}%" if ins is not None else None,
    ]
    reasoning = "; ".join(p for p in reasoning_parts if p)
    if observations:
        reasoning += ". Observations: " + "; ".join(observations[:6]) + "."

    return {
        "ownership_quality": round(quality, 1),
        "ownership_quality_band": _band(quality),
        "ownership_stability": round(stability, 1),
        "institutional_participation": round(institutional_participation, 1),
        "promoter_alignment": round(promoter_alignment, 1),
        "governance_signals": gov_signals,
        "pledge_risk": round(pledge_risk, 1),
        "ownership_trend": trend_label,
        "ownership_confidence": confidence,
        "observations": observations,
        "structure": {
            "promoter_pct": prom,
            "fii_pct": fii,
            "dii_pct": dii,
            "mutual_funds_pct": mf,
            "insurance_pct": ins,
            "institutional_pct": inst,
            "public_pct": _f(current.get("public")),
            "promoter_pledge": current.get("promoter_pledge"),
            "promoter_pledge_pct": pledge,
        },
        "trends": {
            "promoter": prom_t,
            "fii": fii_t,
            "dii": rolling_trend(hist, "dii"),
            "mutual_funds": rolling_trend(hist, "mutual_funds"),
            "insurance": rolling_trend(hist, "insurance"),
        },
        "reasoning": reasoning,
        "not_a_recommendation": True,
    }
