"""Institutional Readiness Gate — diagnostic, freshness-aware.

Separates:
  • Company quality (franchise strength)
  • Investment / market opportunity
  • Institutional readiness (coverage completeness)
  • Analytical confidence (reliability of *available* evidence)
  • Recommendation readiness (how close to a cleared gate)

Never conflate thin research packs with a weak business.
Stale required evidence automatically reduces recommendation readiness.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# Coverage / recommendation-readiness bands
HIGH_CONVICTION_COVERAGE = 95.0
MODERATE_CONVICTION_COVERAGE = 80.0
WATCHLIST_COVERAGE = 60.0
HIGH_CONVICTION_EVIDENCE_FLOOR = 80.0

# Constitution: freshness thresholds (days)
FRESHNESS_THRESHOLDS_DAYS = {
    "financials": 120,  # audited / quarterly statements
    "ownership": 120,  # statutory shareholding window ~ quarter
    "valuation": 1,  # multiples / live valuation inputs
    "price": 1,  # live price
    "filings": 14,  # material filings should be ingested promptly
    "news": 7,
    "technicals": 1,
    "research": 180,
    "macro": 30,
}

GATE_VERSION = "readiness-gate-v1.1.0"


def _pct(*vals: Any, default: float = 0.0) -> float:
    for v in vals:
        if v is None:
            continue
        try:
            n = float(v)
        except (TypeError, ValueError):
            continue
        if n <= 1.5:
            n *= 100.0
        return max(0.0, min(100.0, n))
    return float(default)


def _has_records(series: Any) -> bool:
    if not isinstance(series, dict):
        return False
    return bool(series.get("records") or series.get("items") or series.get("documents"))


def _parse_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s[:32])
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        try:
            dt = datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None


def _age_days(ts: Any, *, now: datetime | None = None) -> float | None:
    dt = _parse_ts(ts)
    if not dt:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def _layer_status_score(layers: dict[str, Any], key: str) -> tuple[float, str]:
    row = layers.get(key) or {}
    st = str(row.get("status") or "incomplete")
    sc = row.get("score")
    if st == "complete" and sc is not None:
        return 100.0, "available"
    if st == "partial":
        return 65.0, "partial"
    if sc is not None:
        return 45.0, "thin"
    return 15.0, "missing"


def _latest_from(*candidates: Any) -> str | None:
    best: datetime | None = None
    best_s: str | None = None
    for c in candidates:
        if isinstance(c, list):
            for item in c[:20]:
                if isinstance(item, dict):
                    for k in ("as_of", "period_end", "updated_at", "generated_at", "available_from", "date"):
                        dt = _parse_ts(item.get(k))
                        if dt and (best is None or dt > best):
                            best, best_s = dt, str(item.get(k))[:32]
                else:
                    dt = _parse_ts(item)
                    if dt and (best is None or dt > best):
                        best, best_s = dt, str(item)[:32]
        elif isinstance(c, dict):
            for k in ("as_of", "period_end", "updated_at", "generated_at", "available_from", "latest_period", "date"):
                dt = _parse_ts(c.get(k))
                if dt and (best is None or dt > best):
                    best, best_s = dt, str(c.get(k))[:32]
            recs = c.get("records") or c.get("items") or c.get("documents")
            if isinstance(recs, list) and recs:
                nested = _latest_from(recs)
                dt = _parse_ts(nested)
                if dt and (best is None or dt > best):
                    best, best_s = dt, nested
        else:
            dt = _parse_ts(c)
            if dt and (best is None or dt > best):
                best, best_s = dt, str(c)[:32]
    return best_s


def compute_coverage_board(
    *,
    layers: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    evidence_completion: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    irp: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Per-domain coverage % used by the readiness gate."""
    layers = layers if isinstance(layers, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cid = cid if isinstance(cid, dict) else {}
    leo = live_evidence if isinstance(live_evidence, dict) else {}
    ecp = evidence_completion if isinstance(evidence_completion, dict) else {}
    ve = valuation_pack if isinstance(valuation_pack, dict) else {}
    irp = irp if isinstance(irp, dict) else {}
    readiness = ca.get("recommendation_readiness") or {}
    r_scores = readiness.get("scores") or {}
    fin = ca.get("financial_intelligence") or {}
    val = ca.get("valuation_intelligence") or {}
    panel = ecp.get("quality_panel") or {}

    financials = _pct(fin.get("coverage_pct"), r_scores.get("financial_intelligence"), default=0)
    if financials < 20 and (fin.get("narrative") or fin.get("enabled")):
        financials = max(financials, 40.0)

    ownership = 0.0
    sh = cid.get("shareholding") or cid.get("ownership") or ca.get("shareholding") or ca.get("ownership")
    if _has_records(sh) or (isinstance(sh, dict) and (sh.get("promoter") is not None or sh.get("fii") is not None)):
        ownership = 90.0
    elif isinstance(sh, dict) and sh:
        ownership = 55.0
    elif r_scores.get("evidence_confidence"):
        ownership = min(50.0, _pct(r_scores.get("evidence_confidence"), default=0) * 0.5)

    valuation = _pct(val.get("coverage_pct"), r_scores.get("valuation"), default=0)
    if valuation < 20 and (val.get("current_pe") is not None or ve.get("latest_valuation") or val.get("narrative")):
        valuation = max(valuation, 55.0 if val.get("current_pe") is not None else 40.0)
    peer_ok = bool(val.get("peer_pe") or val.get("peer_comparison") or (ca.get("identity") or {}).get("peers"))
    if not peer_ok and valuation > 0:
        valuation = min(valuation, 70.0)

    macro_s, _ = _layer_status_score(layers, "macro")
    industry_s, _ = _layer_status_score(layers, "industry")
    macro = round(0.5 * macro_s + 0.5 * industry_s, 1)
    if r_scores.get("sector_intelligence"):
        macro = max(macro, _pct(r_scores.get("sector_intelligence")))

    tech_s, tech_state = _layer_status_score(layers, "technical")
    technicals = 20.0 if tech_state == "missing" else tech_s

    news = 30.0
    filings = 30.0
    research = _pct(r_scores.get("research"), default=40)
    objs = leo.get("evidence_objects") or leo.get("objects") or []
    if objs:
        kinds = {str((o or {}).get("kind") or (o or {}).get("type") or "").lower() for o in objs if isinstance(o, dict)}
        if any("news" in k or "announcement" in k for k in kinds):
            news = 85.0
        if any("filing" in k or "annual" in k or "quarter" in k or "result" in k for k in kinds):
            filings = 90.0
        research = max(research, 70.0)
    if cid.get("evidence_timeline") or cid.get("research") or cid.get("filings"):
        filings = max(filings, 75.0)
        research = max(research, 70.0)
    if irp.get("evidence") or irp.get("ranked_evidence") or irp.get("institutional_briefing"):
        research = max(research, 85.0)
        news = max(news, 55.0)
    if panel.get("coverage_pct") is not None:
        research = max(research, min(95.0, _pct(panel.get("coverage_pct"))))

    board = {
        "financials": round(financials, 1),
        "ownership": round(ownership, 1),
        "valuation": round(valuation, 1),
        "macro": round(macro, 1),
        "technicals": round(technicals, 1),
        "news": round(news, 1),
        "filings": round(filings, 1),
        "research": round(research, 1),
    }
    overall = round(sum(board.values()) / max(1, len(board)), 1)
    return {"dimensions": board, "overall_coverage_pct": overall}


def compute_freshness_penalties(
    *,
    company_analysis: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply constitution freshness rules; stale required evidence reduces readiness."""
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cid = cid if isinstance(cid, dict) else {}
    leo = live_evidence if isinstance(live_evidence, dict) else {}
    ve = valuation_pack if isinstance(valuation_pack, dict) else {}
    now = now or datetime.now(timezone.utc)

    fin = ca.get("financial_intelligence") or {}
    val = ca.get("valuation_intelligence") or {}
    sh = cid.get("shareholding") or cid.get("ownership") or ca.get("shareholding") or ca.get("ownership") or {}
    filings = cid.get("filings") or cid.get("evidence_timeline") or leo.get("evidence_objects") or []
    price_ts = (
        (leo.get("market") or {}).get("as_of")
        or (leo.get("quote") or {}).get("as_of")
        or val.get("price_as_of")
        or ve.get("as_of")
    )

    stamps = {
        "financials": _latest_from(fin, fin.get("latest_period"), fin.get("as_of"), fin.get("updated_at")),
        "ownership": _latest_from(sh, sh.get("as_of") if isinstance(sh, dict) else None, sh.get("period") if isinstance(sh, dict) else None),
        "valuation": _latest_from(val, ve, val.get("as_of"), ve.get("as_of") if isinstance(ve, dict) else None),
        "price": _latest_from(price_ts),
        "filings": _latest_from(filings, leo.get("generated_at")),
        "news": _latest_from(leo.get("news"), leo.get("generated_at")),
        "technicals": _latest_from(price_ts, leo.get("generated_at")),
        "research": _latest_from(cid.get("research"), cid.get("updated_at"), ca.get("generated_at")),
        "macro": _latest_from(ca.get("macro"), leo.get("macro")),
    }

    stale: list[dict[str, Any]] = []
    penalties: dict[str, float] = {}
    for key, threshold in FRESHNESS_THRESHOLDS_DAYS.items():
        age = _age_days(stamps.get(key), now=now)
        present = stamps.get(key) is not None
        # Missing live price is a freshness constitution breach when valuation path is open
        if key == "price" and not present:
            stale.append(
                {
                    "dimension": "price",
                    "label": "Live price",
                    "status": "missing",
                    "threshold_days": threshold,
                    "latest_available": None,
                    "age_days": None,
                    "required": "Current trading-day price / quote",
                    "expected_impact": "High",
                    "penalty_pct": 12.0,
                }
            )
            penalties["price"] = 12.0
            continue
        if not present:
            continue
        if age is not None and age > threshold:
            impact = "High" if key in {"financials", "ownership", "valuation", "price", "filings"} else "Medium"
            pen = 15.0 if impact == "High" else 8.0
            stale.append(
                {
                    "dimension": key,
                    "label": key.replace("_", " ").title(),
                    "status": "stale",
                    "threshold_days": threshold,
                    "latest_available": stamps.get(key),
                    "age_days": round(age, 1),
                    "required": f"Refresh within {threshold}-day freshness window",
                    "expected_impact": impact,
                    "penalty_pct": pen,
                }
            )
            penalties[key] = pen

    # Material filing detected but not ingested
    material_gap = False
    if leo.get("material_filing_detected") and not (_has_records({"records": filings}) or filings):
        material_gap = True
        stale.append(
            {
                "dimension": "filings",
                "label": "Material filing",
                "status": "not_ingested",
                "threshold_days": FRESHNESS_THRESHOLDS_DAYS["filings"],
                "latest_available": None,
                "age_days": None,
                "required": "Ingest detected material exchange filing",
                "expected_impact": "High",
                "penalty_pct": 18.0,
            }
        )
        penalties["material_filing"] = 18.0

    total_penalty = min(45.0, sum(penalties.values()))
    return {
        "stale_items": stale,
        "penalties": penalties,
        "total_penalty_pct": round(total_penalty, 1),
        "stamps": stamps,
        "material_filing_not_ingested": material_gap,
        "thresholds_days": dict(FRESHNESS_THRESHOLDS_DAYS),
        "constitution_rule": (
            "If any required evidence exceeds its freshness threshold, "
            "automatically reduce Recommendation Readiness; below threshold → INCONCLUSIVE."
        ),
    }


def build_diagnostic_cards(
    *,
    board: dict[str, Any],
    layers: dict[str, Any],
    ca: dict[str, Any],
    cid: dict[str, Any],
    peer_ok: bool,
    freshness: dict[str, Any],
) -> list[dict[str, Any]]:
    """Actionable cards: status, required items, latest available, expected impact."""
    dims = board.get("dimensions") or {}
    stamps = freshness.get("stamps") or {}
    stale_by = {s["dimension"]: s for s in freshness.get("stale_items") or []}
    cards: list[dict[str, Any]] = []

    def card(
        key: str,
        title: str,
        *,
        ok: bool,
        warn: bool = False,
        required: list[str],
        impact: str,
        latest: str | None = None,
        why_matters: str = "",
    ) -> None:
        stale = stale_by.get(key)
        if stale and ok:
            ok = False
            warn = True
        if ok:
            status, mark = "available", "✓"
        elif warn or (stale and stale.get("status") == "stale"):
            status, mark = ("outdated" if stale else "partial"), "⚠"
        else:
            status, mark = "missing", "❌"
        if stale and stale.get("status") == "not_ingested":
            status, mark = "not_ingested", "❌"
        latest_s = latest or stamps.get(key) or (stale or {}).get("latest_available")
        req = list(required)
        if stale and stale.get("required") and stale["required"] not in req:
            req.insert(0, str(stale["required"]))
        cards.append(
            {
                "key": key,
                "label": title,
                "present": ok,
                "warn": (not ok) and status in {"partial", "outdated"},
                "mark": mark,
                "status": status,
                "latest_available": latest_s,
                "age_days": (stale or {}).get("age_days"),
                "freshness_threshold_days": FRESHNESS_THRESHOLDS_DAYS.get(key),
                "required": req[:4],
                "expected_impact": impact,
                "why_it_matters": why_matters,
                "detail": (
                    f"Latest available: {latest_s}" if latest_s and not ok else (f"coverage {dims.get(key)}%" if key in dims else "")
                ),
            }
        )

    card(
        "business",
        "Business analysis",
        ok=float((layers.get("company_quality") or {}).get("score") or 0) > 0 or bool(ca.get("business_quality")),
        required=["Business quality pack with moat / model evidence"],
        impact="High",
        why_matters="Franchise quality is the foundation of any ownership case.",
    )
    card(
        "financials",
        "Financial statements",
        ok=float(dims.get("financials") or 0) >= 60,
        warn=float(dims.get("financials") or 0) >= 35,
        required=["Latest audited annual statements", "Most recent quarterly results"],
        impact="High",
        latest=stamps.get("financials"),
        why_matters="Without current statements, returns and leverage cannot be institutionally verified.",
    )
    card(
        "macro",
        "Macro analysis",
        ok=float(dims.get("macro") or 0) >= 55,
        warn=float(dims.get("macro") or 0) >= 35,
        required=["Current rate / credit / liquidity context for the sector"],
        impact="Medium",
        latest=stamps.get("macro"),
        why_matters="Macro transmission can re-rate even high-quality franchises.",
    )
    card(
        "valuation",
        "Peer valuation",
        ok=peer_ok and float(dims.get("valuation") or 0) >= 70,
        warn=float(dims.get("valuation") or 0) >= 40,
        required=["Peer multiple comparison", "Historical valuation percentile", "Current trading-day valuation inputs"],
        impact="High",
        latest=stamps.get("valuation"),
        why_matters="Incomplete peer valuation blocks margin-of-safety judgement.",
    )
    card(
        "ownership",
        "Shareholding",
        ok=float(dims.get("ownership") or 0) >= 80 and "ownership" not in stale_by,
        warn=float(dims.get("ownership") or 0) >= 40 or "ownership" in stale_by,
        required=["Latest statutory shareholding pattern", "Promoter / FII / DII breakdown", "Pledge status"],
        impact="High",
        latest=stamps.get("ownership"),
        why_matters="Ownership shifts and pledging are material institutional signals.",
    )
    card(
        "filings",
        "Earnings / filings",
        ok=float(dims.get("filings") or 0) >= 75 and "filings" not in stale_by,
        warn=float(dims.get("filings") or 0) >= 40,
        required=["Latest earnings release / exchange filing indexed", "Management commentary if published"],
        impact="High",
        latest=stamps.get("filings"),
        why_matters="Material filings must be ingested before conviction can rise.",
    )
    card(
        "technicals",
        "Technical model",
        ok=float(dims.get("technicals") or 0) >= 70,
        warn=float(dims.get("technicals") or 0) >= 40,
        required=["Current trend / range / participation snapshot"],
        impact="Medium",
        latest=stamps.get("technicals"),
        why_matters="Technicals inform timing — never override quality — but low confidence still caps readiness.",
    )
    card(
        "research",
        "Research corpus",
        ok=float(dims.get("research") or 0) >= 70,
        warn=float(dims.get("research") or 0) >= 45,
        required=["Indexed research / house notes for the issuer"],
        impact="Medium",
        latest=stamps.get("research"),
        why_matters="Research corpus supports contradiction checks and committee memory.",
    )
    return cards


def compute_analytical_confidence(
    *,
    layers: dict[str, Any],
    board: dict[str, Any],
    freshness: dict[str, Any],
    diagnostic_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reliability of *available* evidence — not completeness."""
    available = [c for c in diagnostic_cards if c.get("present")]
    dims = board.get("dimensions") or {}
    # Consistency proxy: variance of present layer scores that are complete/partial
    scores = []
    for key in ("company_quality", "financial_quality", "management", "valuation", "risk", "macro", "industry"):
        row = layers.get(key) or {}
        if row.get("status") in {"complete", "partial"} and row.get("score") is not None:
            scores.append(float(row["score"]))
    consistency = 70.0
    if len(scores) >= 2:
        mean = sum(scores) / len(scores)
        var = sum((s - mean) ** 2 for s in scores) / len(scores)
        # Lower variance → higher consistency
        consistency = max(40.0, min(95.0, 90.0 - (var**0.5) * 0.8))
    # Available pillar strength
    present_cov = [float(dims[c["key"]]) for c in available if c.get("key") in dims]
    strength = sum(present_cov) / len(present_cov) if present_cov else 35.0
    stale_high = sum(1 for s in freshness.get("stale_items") or [] if s.get("expected_impact") == "High")
    score = round(0.55 * consistency + 0.45 * strength - stale_high * 6.0, 1)
    score = max(0.0, min(100.0, score))

    if score >= 75 and stale_high == 0:
        label = "High"
        conditional = len(available) < 5 or float(board.get("overall_coverage_pct") or 0) < MODERATE_CONVICTION_COVERAGE
    elif score >= 55:
        label = "Moderate"
        conditional = True
    else:
        label = "Low"
        conditional = True

    if conditional and label == "High":
        display = "High (conditional)"
        explanation = (
            "The available evidence is internally consistent, but institutional coverage "
            "is insufficient for a recommendation."
        )
    elif label == "High":
        display = "High"
        explanation = "Available evidence is consistent and coverage supports institutional analysis."
    elif label == "Moderate":
        display = "Moderate"
        explanation = "Available evidence is usable, but gaps or mild inconsistency keep confidence conditional."
    else:
        display = "Low"
        explanation = "Available evidence is thin or conflicting; treat analytical conclusions as provisional."

    return {
        "score_pct": score,
        "label": label,
        "display": display,
        "conditional": conditional or label != "High",
        "explanation": explanation,
        "consistency_pct": round(consistency, 1),
        "available_pillar_strength_pct": round(strength, 1),
        "available_count": len(available),
    }


def compute_quality_opportunity(
    *,
    layers: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Company quality vs market opportunity — independent of readiness."""
    layers = layers if isinstance(layers, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    bq = ca.get("business_quality") or {}
    fin = ca.get("financial_intelligence") or {}

    cq = _pct((layers.get("company_quality") or {}).get("score"), bq.get("business_quality_score"), default=55)
    fq_layer = layers.get("financial_quality") or {}
    fq = _pct(fq_layer.get("company_quality_score"), fq_layer.get("score"), default=55)
    mgmt = _pct((layers.get("management") or {}).get("score"), default=55)
    company_quality = round((cq * 0.45 + fq * 0.35 + mgmt * 0.20) / 10.0, 1)

    val = _pct((layers.get("valuation") or {}).get("score"), default=55)
    exp = _pct((layers.get("market_expectations") or {}).get("score"), default=55)
    tech = _pct((layers.get("technical") or {}).get("score"), default=50)
    macro = _pct((layers.get("macro") or {}).get("score"), default=55)
    market_opportunity = round((val * 0.35 + exp * 0.25 + tech * 0.20 + macro * 0.20) / 10.0, 1)

    strengths: list[str] = []
    weaknesses: list[str] = []
    for x in (bq.get("strengths") or fin.get("what_improved") or [])[:4]:
        strengths.append(str(x).replace("_", " ").strip().capitalize())
    for x in (bq.get("weaknesses") or fin.get("what_deteriorated") or [])[:4]:
        weaknesses.append(str(x).replace("_", " ").strip().capitalize())
    model = str((ca.get("identity") or {}).get("business_model") or "").strip()
    if model and not strengths:
        strengths.append(model[:120])
    if cq >= 70 and "Franchise durability" not in strengths:
        strengths.append("Franchise quality signals constructive")
    if fq < 55:
        weaknesses.append("Financial trend evidence still soft")
    if not strengths:
        strengths.append("Identity and sector context available for analysis")
    if not weaknesses:
        weaknesses.append("Incomplete verified datasets limit precision")

    return {
        "company_quality_10": company_quality,
        "market_opportunity_10": market_opportunity,
        "company_quality_100": round(company_quality * 10, 1),
        "market_opportunity_100": round(market_opportunity * 10, 1),
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
    }


def evaluate_readiness_gate(
    *,
    layers: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    evidence_completion: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    irp: dict[str, Any] | None = None,
    external_gate_blocked: bool = False,
    name: str = "this company",
) -> dict[str, Any]:
    """Full Institutional Readiness Gate for Ask / Decision Engine."""
    layers = layers if isinstance(layers, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cid_d = cid if isinstance(cid, dict) else {}
    board = compute_coverage_board(
        layers=layers,
        company_analysis=ca,
        cid=cid_d,
        live_evidence=live_evidence,
        evidence_completion=evidence_completion,
        valuation_pack=valuation_pack,
        irp=irp,
    )
    dims = board["dimensions"]
    institutional_readiness = float(board["overall_coverage_pct"])
    qo = compute_quality_opportunity(layers=layers, company_analysis=ca)
    freshness = compute_freshness_penalties(
        company_analysis=ca,
        cid=cid_d,
        live_evidence=live_evidence,
        valuation_pack=valuation_pack,
    )

    peer_ok = bool(
        (ca.get("valuation_intelligence") or {}).get("peer_pe")
        or (ca.get("valuation_intelligence") or {}).get("peer_comparison")
        or (ca.get("identity") or {}).get("peers")
    )
    diagnostic_cards = build_diagnostic_cards(
        board=board,
        layers=layers,
        ca=ca,
        cid=cid_d,
        peer_ok=peer_ok,
        freshness=freshness,
    )
    # Backward-compatible checklist alias
    checklist = diagnostic_cards

    analytical = compute_analytical_confidence(
        layers=layers,
        board=board,
        freshness=freshness,
        diagnostic_cards=diagnostic_cards,
    )

    # Recommendation readiness = coverage minus freshness penalties (completeness + freshness)
    recommendation_readiness = round(
        max(0.0, institutional_readiness - float(freshness.get("total_penalty_pct") or 0)),
        1,
    )
    # Legacy alias used by earlier UI / summary fields
    evidence_confidence = recommendation_readiness

    missing = [c["label"] for c in diagnostic_cards if not c["present"]]
    warnings = [c["label"] for c in diagnostic_cards if c.get("warn")]
    reason_bullets = []
    for c in diagnostic_cards:
        if not c["present"]:
            bit = c["label"]
            if c.get("status") == "outdated" and c.get("latest_available"):
                bit += f" outdated (latest {c['latest_available']})"
            elif c.get("status") == "missing":
                bit += " missing"
            reason_bullets.append(bit)

    if recommendation_readiness >= HIGH_CONVICTION_COVERAGE and analytical["score_pct"] >= 70:
        band = "high_conviction_allowed"
        band_label = "High Conviction allowed"
        passed = True
    elif recommendation_readiness >= MODERATE_CONVICTION_COVERAGE:
        band = "moderate_conviction"
        band_label = "Moderate Conviction"
        passed = True
    elif recommendation_readiness >= WATCHLIST_COVERAGE:
        band = "watchlist"
        band_label = "Watchlist"
        passed = False
    else:
        band = "deferred"
        band_label = "Recommendation Deferred"
        passed = False

    if external_gate_blocked and band in {"high_conviction_allowed", "moderate_conviction"}:
        band = "watchlist" if recommendation_readiness >= WATCHLIST_COVERAGE else "deferred"
        band_label = "Watchlist" if band == "watchlist" else "Recommendation Deferred"
        passed = False
        if "External evidence gate blocked" not in missing:
            missing.append("External evidence gate blocked")

    # Never High Conviction when readiness < 80
    if recommendation_readiness < HIGH_CONVICTION_EVIDENCE_FLOOR and band == "high_conviction_allowed":
        band = "moderate_conviction"
        band_label = "Moderate Conviction"
        passed = True

    # Freshness constitution: any high-impact stale/missing required evidence below moderate → inconclusive
    high_stale = [s for s in freshness.get("stale_items") or [] if s.get("expected_impact") == "High"]
    if high_stale and recommendation_readiness < MODERATE_CONVICTION_COVERAGE:
        band = "deferred"
        band_label = "Recommendation Deferred"
        passed = False

    hard_fail = band == "deferred" or (
        external_gate_blocked and recommendation_readiness < MODERATE_CONVICTION_COVERAGE
    )
    investment_thesis_status = "INCONCLUSIVE" if hard_fail or band == "watchlist" else "FORMED"
    not_a_negative_view = investment_thesis_status == "INCONCLUSIVE"

    required_evidence = []
    for c in diagnostic_cards:
        if not c["present"]:
            req = "; ".join(c.get("required") or []) or c["label"]
            required_evidence.append(f"{c['label']}: {req}")

    status_mark = "FAILED" if hard_fail or band == "watchlist" else "PASSED"
    if band in {"watchlist", "deferred"}:
        reason_lead = (
            f"Institutional readiness is {institutional_readiness:.0f}% and recommendation readiness is "
            f"{recommendation_readiness:.0f}% — below the bar for a conviction call. "
            "This should not be interpreted as a negative view of the company."
        )
    else:
        reason_lead = (
            f"Recommendation readiness {recommendation_readiness:.0f}% supports institutional analysis. "
            f"Analytical confidence: {analytical['display']}."
        )

    decision_line = (
        "Institutional recommendation withheld."
        if investment_thesis_status == "INCONCLUSIVE"
        else "Institutional recommendation pathway open — conviction still follows the decision stack."
    )

    return {
        "programme": "AGIB_INSTITUTIONAL_READINESS_GATE",
        "version": GATE_VERSION,
        "passed": bool(passed) and not hard_fail,
        "status": status_mark,
        "status_mark": "❌ FAILED" if status_mark == "FAILED" else "✓ PASSED",
        "band": band,
        "band_label": band_label,
        "hard_fail": hard_fail,
        "gate_blocks_high_conviction": recommendation_readiness < HIGH_CONVICTION_EVIDENCE_FLOOR,
        # Primary diagnostic metrics
        "institutional_readiness_pct": institutional_readiness,
        "analytical_confidence": analytical,
        "analytical_confidence_display": analytical["display"],
        "analytical_confidence_explanation": analytical["explanation"],
        "recommendation_readiness_pct": recommendation_readiness,
        "decision_line": decision_line,
        # Legacy aliases (UI / older consumers)
        "overall_coverage_pct": institutional_readiness,
        "evidence_confidence_pct": recommendation_readiness,
        "required_confidence_pct": HIGH_CONVICTION_EVIDENCE_FLOOR,
        "coverage": dims,
        "checklist": checklist,
        "diagnostic_cards": diagnostic_cards,
        "available": [c["label"] for c in diagnostic_cards if c["present"]],
        "missing": missing,
        "warnings": warnings,
        "reason_bullets": reason_bullets[:8],
        "additional_evidence_required": required_evidence[:8],
        "freshness": freshness,
        "company_quality_10": qo["company_quality_10"],
        "market_opportunity_10": qo["market_opportunity_10"],
        "company_quality_100": qo["company_quality_100"],
        "market_opportunity_100": qo["market_opportunity_100"],
        "strengths": qo["strengths"],
        "weaknesses": qo["weaknesses"],
        "investment_thesis_status": investment_thesis_status,
        "not_a_negative_view": not_a_negative_view,
        "reason": reason_lead,
        "summary_for_user": {
            "title": "Institutional Gate Status",
            "status": status_mark,
            "reason": reason_lead,
            "reason_bullets": reason_bullets[:6],
            "checklist": checklist,
            "diagnostic_cards": diagnostic_cards,
            "institutional_readiness_pct": institutional_readiness,
            "analytical_confidence": analytical["display"],
            "analytical_confidence_explanation": analytical["explanation"],
            "recommendation_readiness_pct": recommendation_readiness,
            "evidence_confidence_pct": recommendation_readiness,  # alias
            "required_confidence_pct": HIGH_CONVICTION_EVIDENCE_FLOOR,
            "company_quality_10": qo["company_quality_10"],
            "market_opportunity_10": qo["market_opportunity_10"],
            "coverage": dims,
            "overall_coverage_pct": institutional_readiness,
            "investment_thesis": investment_thesis_status,
            "decision": decision_line,
            "note": (
                "Insufficient evidence must not be read as a negative company view."
                if not_a_negative_view
                else "Evidence supports analysis; conviction still follows the decision stack."
            ),
        },
        "thresholds": {
            "high_conviction_coverage_pct": HIGH_CONVICTION_COVERAGE,
            "moderate_conviction_coverage_pct": MODERATE_CONVICTION_COVERAGE,
            "watchlist_coverage_pct": WATCHLIST_COVERAGE,
            "high_conviction_evidence_floor_pct": HIGH_CONVICTION_EVIDENCE_FLOOR,
            "freshness_days": dict(FRESHNESS_THRESHOLDS_DAYS),
        },
        "company": name,
        "never_conflate_data_with_quality": True,
        "never_recommend_on_stale_data": True,
    }
