"""Independent opportunity dimensions — deterministic, evidence-backed."""

from __future__ import annotations

from typing import Any

from opportunity_intelligence.util import as_float, deep_get, dim_result


def _ev(path: str, value: Any, note: str) -> dict[str, Any]:
    return {"path": path, "value": value, "note": note}


def score_valuation(memory: dict[str, Any]) -> dict[str, Any]:
    vh = memory.get("valuation_history") or {}
    current = vh.get("current") or {}
    bands = (vh.get("historical_bands") or {}).get("pe") or {}
    rel = ((vh.get("relative") or {}).get("pe") or {})
    stance = str(vh.get("stance") or "").lower()

    score = 50.0
    signals: list[str] = []
    evidence: list[dict[str, Any]] = []
    available = bool(vh.get("available") or current or bands or rel)

    pct = as_float(bands.get("percentile"))
    if pct is not None:
        # Low historical percentile → valuation opportunity
        contrib = clamp_map(100.0 - pct, 0, 100, 20, 90)
        score = 0.55 * score + 0.45 * contrib
        signals.append(f"PE historical percentile {pct:.0f}")
        evidence.append(_ev("valuation_history.historical_bands.pe.percentile", pct, "historical_discount_signal"))

    premium = as_float(rel.get("premium_pct"))
    if premium is not None:
        if premium < -10:
            score += 18
            signals.append(f"Peer discount {premium:.1f}%")
        elif premium < 0:
            score += 10
            signals.append(f"Mild peer discount {premium:.1f}%")
        elif premium > 25:
            score -= 18
            signals.append(f"Rich peer premium {premium:.1f}%")
        elif premium > 10:
            score -= 10
            signals.append(f"Peer premium {premium:.1f}%")
        evidence.append(_ev("valuation_history.relative.pe.premium_pct", premium, "peer_relative"))

    if "discount" in stance:
        score += 8
        signals.append("Stance: discount")
    elif "premium" in stance:
        score -= 6
        signals.append("Stance: premium")

    pe = as_float(current.get("pe"))
    if pe is not None:
        evidence.append(_ev("valuation_history.current.pe", pe, "current_multiple"))

    coverage = 100.0 if (pct is not None or premium is not None) else (40.0 if available else 0.0)
    return dim_result(score=score, signals=signals, evidence=evidence, available=available, coverage=coverage)


def score_financial(memory: dict[str, Any], delta: dict[str, Any] | None = None) -> dict[str, Any]:
    fh = memory.get("financial_history") or {}
    rev = fh.get("revenue") or {}
    pat = fh.get("pat") or {}
    ebitda = fh.get("ebitda") or {}
    ret = fh.get("returns") or {}
    cf = fh.get("cash_flow") or {}

    score = 45.0
    signals: list[str] = []
    evidence: list[dict[str, Any]] = []
    available = bool(fh.get("available"))

    yoy = as_float(rev.get("yoy"))
    if yoy is not None:
        if yoy >= 15:
            score += 16
            signals.append(f"Revenue YoY {yoy:.1f}% (strong)")
        elif yoy >= 8:
            score += 10
            signals.append(f"Revenue YoY {yoy:.1f}%")
        elif yoy < 0:
            score -= 14
            signals.append(f"Revenue YoY {yoy:.1f}% (contraction)")
        else:
            score += 4
            signals.append(f"Revenue YoY {yoy:.1f}%")
        evidence.append(_ev("financial_history.revenue.yoy", yoy, "revenue_momentum"))

    cagr = as_float(rev.get("cagr_5y") or rev.get("cagr_3y"))
    if cagr is not None and cagr >= 12:
        score += 8
        signals.append(f"Revenue CAGR {cagr:.1f}%")
        evidence.append(_ev("financial_history.revenue.cagr", cagr, "growth_depth"))

    pat_yoy = as_float(pat.get("yoy"))
    if pat_yoy is not None:
        if pat_yoy >= 15:
            score += 12
            signals.append(f"PAT YoY {pat_yoy:.1f}%")
        elif pat_yoy < 0:
            score -= 12
            signals.append(f"PAT YoY {pat_yoy:.1f}%")
        evidence.append(_ev("financial_history.pat.yoy", pat_yoy, "earnings_momentum"))

    margin = as_float(ebitda.get("margin"))
    trend = str(ebitda.get("trend") or "").lower()
    if "improv" in trend or "expand" in trend:
        score += 8
        signals.append("EBITDA margin improving")
    elif "deterior" in trend or "compress" in trend:
        score -= 10
        signals.append("EBITDA margin deteriorating")
    if margin is not None:
        evidence.append(_ev("financial_history.ebitda.margin", margin, "margin_level"))

    roe = as_float(ret.get("roe"))
    if roe is not None:
        if roe >= 18:
            score += 8
            signals.append(f"ROE {roe:.1f}%")
        elif roe < 8:
            score -= 6
            signals.append(f"ROE {roe:.1f}% (weak)")
        evidence.append(_ev("financial_history.returns.roe", roe, "returns"))

    ocf_q = as_float(cf.get("quality_ocf_to_pat"))
    if ocf_q is not None:
        if ocf_q >= 0.9:
            score += 6
            signals.append("Strong cash-flow quality")
        elif ocf_q < 0.5:
            score -= 8
            signals.append("Weak cash-flow quality")
        evidence.append(_ev("financial_history.cash_flow.quality_ocf_to_pat", ocf_q, "cash_quality"))

    # Positive knowledge delta on financial section boosts
    if isinstance(delta, dict):
        fin = (delta.get("sections") or {}).get("financial") or {}
        if fin.get("changed") and (delta.get("status") or "") != "UNCHANGED":
            score += 4
            signals.append("Financial Knowledge Delta updated")

    coverage = 100.0 if available and (yoy is not None or cagr is not None) else (30.0 if available else 0.0)
    return dim_result(score=score, signals=signals, evidence=evidence, available=available, coverage=coverage)


def score_ownership(memory: dict[str, Any]) -> dict[str, Any]:
    oh = memory.get("ownership_history") or {}
    latest = oh.get("latest") or {}
    trends = oh.get("trends") or {}

    score = 48.0
    signals: list[str] = []
    evidence: list[dict[str, Any]] = []
    available = bool(oh.get("available") or latest)

    for key, label, up_w, down_w in (
        ("fii", "FII", 14, 10),
        ("dii", "DII", 8, 6),
        ("mutual_funds", "Mutual Funds", 8, 6),
        ("promoter", "Promoter", 10, 12),
    ):
        direction = str(((trends.get(key) or {}).get("direction") or "")).lower()
        val = as_float(latest.get(key))
        if direction == "rising":
            score += up_w
            signals.append(f"{label} accumulating")
        elif direction == "falling":
            score -= down_w
            signals.append(f"{label} reducing")
        if val is not None:
            evidence.append(_ev(f"ownership_history.latest.{key}", val, f"{key}_level"))
            if direction:
                evidence.append(
                    _ev(f"ownership_history.trends.{key}.direction", direction, f"{key}_momentum")
                )

    pledge = as_float(latest.get("pledge") or latest.get("promoter_pledge_pct"))
    if pledge is not None:
        if pledge <= 1:
            score += 4
            signals.append("Pledge negligible")
        elif pledge >= 20:
            score -= 16
            signals.append(f"Elevated pledge {pledge:.1f}%")
        evidence.append(_ev("ownership_history.latest.pledge", pledge, "governance_pledge"))

    coverage = 100.0 if trends else (40.0 if available else 0.0)
    return dim_result(score=score, signals=signals, evidence=evidence, available=available, coverage=coverage)


def score_corporate(memory: dict[str, Any]) -> dict[str, Any]:
    corp = memory.get("corporate_history") or {}
    events = (memory.get("event_timeline") or {}).get("events") or []
    obs = list(corp.get("observations") or [])
    strategy = corp.get("strategy_evolution") or {}

    score = 45.0
    signals: list[str] = []
    evidence: list[dict[str, Any]] = []
    available = bool(corp.get("available") or events or obs)

    positive_kw = (
        "capacity",
        "expansion",
        "buyback",
        "acquisition",
        "ai ",
        "artificial intelligence",
        "dividend",
        "new product",
        "international",
        "approval",
        "commission",
        "capex",
        "guidance rais",
    )
    negative_kw = ("litigation", "penalty", "fraud", "investigation", "downgrade", "guidance cut", "impairment")

    blob_parts = [str(o).lower() for o in obs]
    for row in (strategy.values() if isinstance(strategy, dict) else []):
        if isinstance(row, dict):
            blob_parts.extend(str(t).lower() for t in (row.get("strategy_themes") or []))
    for e in events[-20:]:
        blob_parts.append(str(e.get("title") or "").lower())
    blob = " | ".join(blob_parts)

    hits_pos = [k.strip() for k in positive_kw if k in blob]
    hits_neg = [k.strip() for k in negative_kw if k in blob]
    score += min(18, 4 * len(hits_pos))
    score -= min(18, 6 * len(hits_neg))
    for h in hits_pos[:6]:
        signals.append(f"Corporate momentum: {h}")
    for h in hits_neg[:4]:
        signals.append(f"Corporate concern: {h}")

    if events:
        evidence.append(
            _ev(
                "event_timeline.n",
                (memory.get("event_timeline") or {}).get("n"),
                "recent_corporate_events",
            )
        )
        for e in events[-4:]:
            evidence.append(
                {
                    "path": "event_timeline.events",
                    "value": e.get("title"),
                    "date": e.get("date"),
                    "note": "corporate_event",
                }
            )

    if obs:
        evidence.append(_ev("corporate_history.observations", obs[:3], "corporate_observations"))

    coverage = 80.0 if (obs or events) else (20.0 if available else 0.0)
    return dim_result(score=score, signals=signals, evidence=evidence, available=available, coverage=coverage)


def score_sector(memory: dict[str, Any], graph: dict[str, Any] | None = None) -> dict[str, Any]:
    sh = memory.get("sector_history") or {}
    score = 50.0
    signals: list[str] = []
    evidence: list[dict[str, Any]] = []
    available = bool(sh.get("sector_key") or (graph or {}).get("sector_key"))

    sector_key = sh.get("sector_key") or (graph or {}).get("sector_key")
    if sector_key:
        signals.append(f"Sector key: {sector_key}")
        evidence.append(_ev("sector_history.sector_key", sector_key, "sector_identity"))

    themes = list((graph or {}).get("themes") or [])
    if themes:
        score += min(12, 4 * len(themes))
        signals.append(f"Theme exposure: {', '.join(themes[:4])}")
        evidence.append(_ev("knowledge_graph.themes", themes, "theme_tailwind"))

    peers = list((graph or {}).get("peers") or [])
    if peers:
        signals.append(f"Peer set: {', '.join(peers[:4])}")
        evidence.append(_ev("knowledge_graph.peers", peers[:6], "competitive_set"))
        score += 4

    # Competitive position from memory if present
    comp = memory.get("competitive_position") or {}
    if isinstance(comp, dict) and comp:
        obs = comp.get("observations") or comp.get("summary")
        if obs:
            score += 4
            signals.append("Competitive position available in memory")
            evidence.append(_ev("competitive_position", obs if not isinstance(obs, list) else obs[:2], "positioning"))

    coverage = 70.0 if sector_key else (30.0 if available else 0.0)
    return dim_result(score=score, signals=signals, evidence=evidence, available=available, coverage=coverage)


def score_macro(
    memory: dict[str, Any],
    graph: dict[str, Any] | None = None,
    scenarios: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = 50.0
    signals: list[str] = []
    evidence: list[dict[str, Any]] = []

    edges = list((graph or {}).get("edges") or [])
    exposures = [e for e in edges if e.get("rel") in {"EXPOSED_TO", "AFFECTED_BY", "USES"}]
    available = bool(exposures or scenarios)

    for e in exposures[:8]:
        tgt = e.get("target")
        signals.append(f"Graph exposure: {e.get('rel')} → {tgt}")
        evidence.append({"path": "knowledge_graph.edges", "value": e, "note": "macro_or_factor_link"})

    # Soft scenario tilt
    if isinstance(scenarios, dict):
        text = str(scenarios)[:800].lower()
        if "bull" in text and "bear" in text:
            score += 4
            signals.append("Scenario intelligence available (bull/base/bear)")
            evidence.append({"path": "institutional_scenario_intelligence", "value": True, "note": "scenario_pack"})
        if "headwind" in text or "risk" in text:
            score -= 4

    sector_key = (memory.get("sector_history") or {}).get("sector_key") or (graph or {}).get("sector_key")
    # Light sector-macro priors (deterministic heuristics, not live macro pulls)
    priors = {
        "banks": ("Rate-sensitive sector — NIM/deposit franchise central", 2),
        "it_services": ("USD / global IT demand exposure", 2),
        "auto": ("Commodity cost & demand cycle exposure", 0),
        "cement": ("Infra / housing cycle exposure", 2),
        "power": ("Regulated returns / capex cycle", 1),
        "pharma": ("USD export & regulatory cycle", 1),
    }
    if sector_key in priors:
        note, bump = priors[sector_key]
        score += bump
        signals.append(note)
        evidence.append(_ev("sector_macro_prior", sector_key, note))

    coverage = 60.0 if exposures or scenarios else (25.0 if sector_key else 0.0)
    return dim_result(score=score, signals=signals, evidence=evidence, available=available or bool(sector_key), coverage=coverage)


def score_technical(memory: dict[str, Any]) -> dict[str, Any]:
    """Supporting evidence only — never dominates Opportunity Score."""
    pi = memory.get("price_intelligence") or {}
    score = 50.0
    signals: list[str] = []
    evidence: list[dict[str, Any]] = []
    available = bool(pi.get("available") or pi.get("latest_price") is not None)

    r1 = as_float(pi.get("return_1y_pct"))
    r5 = as_float(pi.get("return_5y_pct"))
    dd = as_float(deep_get(pi, "drawdown.max_drawdown_pct"))

    if r1 is not None:
        if r1 > 20:
            score += 10
            signals.append(f"1Y relative strength {r1:.1f}%")
        elif r1 < -20:
            score -= 8
            signals.append(f"1Y weakness {r1:.1f}%")
        evidence.append(_ev("price_intelligence.return_1y_pct", r1, "trend_context"))
    if r5 is not None and r5 > 50:
        score += 6
        signals.append(f"5Y trend {r5:.1f}%")
        evidence.append(_ev("price_intelligence.return_5y_pct", r5, "long_trend"))
    if dd is not None and dd <= -40:
        score -= 6
        signals.append(f"Deep drawdown context {dd:.1f}%")
        evidence.append(_ev("price_intelligence.drawdown.max_drawdown_pct", dd, "risk_context"))

    coverage = 70.0 if available else 0.0
    return dim_result(score=score, signals=signals, evidence=evidence, available=available, coverage=coverage)


def clamp_map(x: float, in_lo: float, in_hi: float, out_lo: float, out_hi: float) -> float:
    if in_hi == in_lo:
        return out_lo
    t = (float(x) - in_lo) / (in_hi - in_lo)
    t = max(0.0, min(1.0, t))
    return out_lo + t * (out_hi - out_lo)


def extract_hypotheses(hyp_pack: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    supporting: list[str] = []
    contradicting: list[str] = []
    if not isinstance(hyp_pack, dict):
        return supporting, contradicting
    rows = (
        hyp_pack.get("hypotheses")
        or hyp_pack.get("items")
        or hyp_pack.get("active")
        or []
    )
    if isinstance(rows, dict):
        rows = list(rows.values())
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        text = str(row.get("statement") or row.get("hypothesis") or row.get("title") or "")[:160]
        status = str(row.get("status") or row.get("stance") or row.get("direction") or "").lower()
        conf = as_float(row.get("confidence"))
        label = text or status
        if not label:
            continue
        if any(k in status for k in ("strength", "support", "confirm", "rising", "bull")):
            supporting.append(label)
        elif any(k in status for k in ("weak", "contradict", "reject", "falsif", "bear")):
            contradicting.append(label)
        elif conf is not None and conf >= 0.7:
            supporting.append(label)
        elif conf is not None and conf <= 0.35:
            contradicting.append(label)
    return supporting[:8], contradicting[:8]
