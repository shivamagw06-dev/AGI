"""Score and narrate the 13-layer investment decision hierarchy.

Soft-wire only — consumes canonical AGI packages. Never skips a layer.
Never emits framework codes or provider names.
"""

from __future__ import annotations

from typing import Any

from decision_engine.schema import LAYER_ORDER, LAYER_QUESTIONS, LAYER_WEIGHTS


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(n)))


def _pct(v: Any, default: float | None = None) -> float | None:
    if v is None:
        return default
    try:
        n = float(v)
    except (TypeError, ValueError):
        return default
    if n <= 1.5:
        n *= 100.0
    return _clamp(n)


def _txt(v: Any, limit: int = 320) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return s[:limit]


def _grade(score: float | None) -> str:
    if score is None:
        return "Developing"
    s = float(score)
    if s >= 90:
        return "A+"
    if s >= 85:
        return "A"
    if s >= 80:
        return "A-"
    if s >= 75:
        return "B+"
    if s >= 70:
        return "B"
    if s >= 60:
        return "C+"
    if s >= 50:
        return "C"
    return "D"


_LAYER_TITLES = {
    "macro": "Macro",
    "industry": "Industry",
    "company_quality": "Company Quality",
    "financial_quality": "Financial Quality",
    "management": "Management",
    "valuation": "Valuation",
    "market_expectations": "Market Expectations",
    "technical": "Technical & Flow",
    "risk": "Risk",
    "catalysts": "Catalysts",
    "probability": "Probability",
    "expected_return": "Expected Return",
    "decision": "Investment Decision",
}


def _layer(
    key: str,
    *,
    score: float | None,
    status: str,
    reasoning: str,
    evidence: list[str] | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": key,
        "title": _LAYER_TITLES.get(key, key.replace("_", " ").title()),
        "question": LAYER_QUESTIONS.get(key, ""),
        "weight": LAYER_WEIGHTS.get(key),
        "score": None if score is None else round(_clamp(score), 1),
        "grade": _grade(score) if score is not None else None,
        "status": status,  # complete | partial | incomplete
        "reasoning": reasoning,
        "evidence": [e for e in (evidence or []) if e][:6],
        "why_it_matters": LAYER_QUESTIONS.get(key, ""),
    }
    if extras:
        out.update(extras)
    return out


def _name(ca: dict, cid: dict, ticker: str | None) -> str:
    identity = ca.get("identity") or cid.get("identity") or {}
    return identity.get("company_name") or ticker or cid.get("ticker") or "the company"


def score_macro(
    *,
    ca: dict,
    mee: dict,
    aws_macro: dict | None,
    briefing: dict,
) -> dict[str, Any]:
    evidence: list[str] = []
    score = 55.0
    status = "incomplete"
    bits: list[str] = []

    regime = None
    if isinstance(aws_macro, dict):
        regime = (
            ((aws_macro.get("e01") or aws_macro.get("market_regime") or {}) if isinstance(aws_macro.get("e01") or aws_macro.get("market_regime"), dict) else {})
        )
        label = None
        if isinstance(aws_macro.get("market_regime"), dict):
            label = aws_macro["market_regime"].get("label") or aws_macro["market_regime"].get("regime")
        elif isinstance(aws_macro.get("e01"), dict):
            label = aws_macro["e01"].get("label") or aws_macro["e01"].get("regime")
        if label:
            regime = str(label)
            evidence.append(f"Market regime context: {regime}.")
            status = "partial"
            low = regime.lower()
            if any(x in low for x in ("bull", "expand", "risk-on", "supportive")):
                score = 78
            elif any(x in low for x in ("bear", "stress", "risk-off", "tight")):
                score = 42
            else:
                score = 58

    macro_drivers = list(briefing.get("macro_drivers") or [])
    if isinstance(ca.get("macro_context"), dict):
        macro_drivers.extend(list((ca.get("macro_context") or {}).get("drivers") or [])[:4])
    for d in macro_drivers[:6]:
        t = _txt(d, 140)
        if t:
            evidence.append(t)
            status = "partial" if status == "incomplete" else status
            score = min(85, score + 3)

    # MEE events as macro freshness
    events = (mee or {}).get("events") or (mee or {}).get("recent_events") or []
    if events:
        status = "complete" if status != "incomplete" else "partial"
        score = min(88, score + 4)
        evidence.append("Recent market-event context is available to frame the ownership environment.")

    name_hint = "Macro"
    if status == "incomplete":
        bits.append(
            f"{name_hint} conditions should still be assessed before ownership — rates, liquidity, growth and risk appetite "
            "decide whether equities in this style are ownable even when the company itself looks attractive."
        )
        score = 52
    else:
        bits.append(
            f"Macro score reflects whether the current policy, growth and risk-appetite backdrop supports owning this equity. "
            f"Current read is {_grade(score)}-grade for ownership timing — not a company quality judgement."
        )
    if evidence:
        bits.append(" ".join(evidence[:3]))
    bits.append("Macro matters because even excellent businesses can re-rate lower in hostile rate or liquidity regimes.")
    return _layer("macro", score=score, status=status, reasoning=" ".join(bits), evidence=evidence)


def score_industry(*, ca: dict, sif: dict, briefing: dict) -> dict[str, Any]:
    evidence: list[str] = []
    sector = ca.get("sector_intelligence") or sif or {}
    score = _pct(sector.get("coverage_pct"), 55) or 55
    status = "partial" if sector else "incomplete"
    narrative = _txt(sector.get("narrative") or sector.get("reasoning") or briefing.get("sector_drivers"), 280)
    if narrative:
        evidence.append(narrative)
        status = "complete" if score >= 50 else "partial"
        score = max(score, 62)
    for d in (briefing.get("sector_drivers") or [])[:3]:
        t = _txt(d, 120)
        if t:
            evidence.append(t)
    identity = ca.get("identity") or {}
    industry = identity.get("industry") or identity.get("sector") or sif.get("sector_name") or "the industry"
    if status == "incomplete":
        reasoning = (
            f"Industry structure for {industry} still needs fuller operating evidence, but the investment committee "
            "must still ask whether demand, competition and regulation are improving or deteriorating before sizing a position."
        )
        score = 54
    else:
        reasoning = (
            f"Industry score for {industry} asks whether the competitive field is becoming more or less attractive. "
            f"Current industry quality read: {_grade(score)}. Industry matters because company excellence cannot "
            "fully offset a structurally impaired sector."
        )
    return _layer("industry", score=score, status=status, reasoning=reasoning, evidence=evidence)


def score_company_quality(*, ca: dict, cid: dict, ticker: str | None) -> dict[str, Any]:
    bq = ca.get("business_quality") or {}
    score = _pct(bq.get("business_quality_score"), None)
    status = "complete" if score is not None else "incomplete"
    if score is None:
        score = 58
        status = "partial" if (ca.get("identity") or {}).get("business_model") else "incomplete"
    name = _name(ca, cid, ticker)
    model = _txt((ca.get("identity") or {}).get("business_model"), 200)
    evidence = []
    if model:
        evidence.append(model)
    if bq.get("grade"):
        evidence.append(f"Business quality grade {bq.get('grade')}.")
    strengths = [str(x).replace("_", " ").strip().capitalize() for x in (bq.get("strengths") or [])[:5]]
    weaknesses = [str(x).replace("_", " ").strip().capitalize() for x in (bq.get("weaknesses") or [])[:5]]
    if model and not strengths:
        strengths.append(model[:140])
    if not weaknesses and status != "complete":
        weaknesses.append("Business-quality evidence still forming")
    reasoning = (
        f"Company quality asks whether {name} is a high-quality franchise — business model, moat, pricing power and "
        f"operating leverage. Current business quality score: {round(score)}/100 ({_grade(score)}). "
        "Quality matters because valuation and leverage only work when excess returns can persist."
    )
    if strengths:
        reasoning += " Strengths: " + "; ".join(strengths[:3]) + "."
    if weaknesses:
        reasoning += " Watch items: " + "; ".join(weaknesses[:3]) + "."
    return _layer(
        "company_quality",
        score=score,
        status=status if score is not None else "incomplete",
        reasoning=reasoning,
        evidence=evidence,
        extras={
            "grade": _grade(score),
            "strengths": strengths[:5],
            "weaknesses": weaknesses[:5],
            "company_quality_score": round(float(score), 1),
        },
    )


def score_financial(*, ca: dict) -> dict[str, Any]:
    """Company financial quality is separate from evidence/data completeness.

    Never blend coverage into the company-quality score — thin packs must not
    look like weak businesses.
    """
    fin = ca.get("financial_intelligence") or {}
    cov = _pct(fin.get("coverage_pct"), None)
    company_score = 55.0
    status = "incomplete"
    evidence: list[str] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    if fin.get("narrative"):
        evidence.append(_txt(fin.get("narrative"), 220) or "")
        status = "partial"
        company_score = 62
    improved = [str(x).replace("_", " ") for x in (fin.get("what_improved") or [])[:4]]
    deteriorated = [str(x).replace("_", " ") for x in (fin.get("what_deteriorated") or [])[:4]]
    if improved:
        company_score += 8 * min(3, len(improved))
        evidence.extend([f"Improving: {x}." for x in improved])
        strengths.extend([x.capitalize() for x in improved])
        status = "complete" if cov and cov >= 40 else "partial"
    if deteriorated:
        company_score -= 7 * min(3, len(deteriorated))
        evidence.extend([f"Softening: {x}." for x in deteriorated])
        weaknesses.extend([x.capitalize() for x in deteriorated])
    company_score = _clamp(company_score)
    evidence_quality = _clamp(cov if cov is not None else (35.0 if status != "incomplete" else 20.0))
    if status == "incomplete":
        reasoning = (
            f"Financial company quality is provisional ({round(company_score)}/100) because statement history is thin. "
            f"Evidence quality is {round(evidence_quality)}/100 — incomplete data lowers confidence, not an automatic "
            "judgement that the franchise is weak."
        )
        # Keep company score neutral-provisional; do not crush it with coverage
        company_score = 58.0 if fin.get("enabled") else 52.0
    else:
        reasoning = (
            f"Financial company quality {round(company_score)}/100 asks whether growth, margins, returns and cash "
            f"conversion are strengthening. Evidence quality {round(evidence_quality)}/100 is reported separately — "
            "thin coverage must not be read as a weak business."
        )
    if not strengths and status != "incomplete":
        strengths.append("Financial narrative available for trend reading")
    if evidence_quality < 60:
        weaknesses.append("Latest statement reconciliation incomplete")
    return _layer(
        "financial_quality",
        score=company_score,
        status=status,
        reasoning=reasoning,
        evidence=[e for e in evidence if e],
        extras={
            "company_quality_score": round(company_score, 1),
            "evidence_quality_score": round(evidence_quality, 1),
            "coverage_pct": round(evidence_quality, 1),
            "strengths": strengths[:5],
            "weaknesses": weaknesses[:5],
            "never_conflate_data_with_quality": True,
        },
    )


def score_management(*, ca: dict, iie: dict) -> dict[str, Any]:
    bq = ca.get("business_quality") or {}
    dims = bq.get("dimensions") or bq.get("scores") or {}
    mgmt = _pct(dims.get("management_quality") or dims.get("management"), None)
    iie_mgmt = ((iie or {}).get("management_quality") or {}) if isinstance(iie, dict) else {}
    if mgmt is None and isinstance(iie_mgmt, dict):
        mgmt = _pct(iie_mgmt.get("score"), None)
    status = "complete" if mgmt is not None else "incomplete"
    score = mgmt if mgmt is not None else 55.0
    evidence = []
    if ca.get("financial_intelligence", {}).get("capital_allocation"):
        evidence.append(f"Capital allocation signal: {ca['financial_intelligence']['capital_allocation']}.")
        status = "partial" if status == "incomplete" else status
        score = max(score, 58)
    reasoning = (
        f"Management score {round(score)}/100 asks whether capital allocation, execution and governance are likely "
        "to create shareholder wealth. Management matters because quality businesses are destroyed by poor capital decisions."
    )
    if status == "incomplete":
        reasoning += " Direct management scoring evidence remains limited — treat this layer as provisional."
    return _layer("management", score=score, status=status, reasoning=reasoning, evidence=evidence)


def score_valuation(*, ca: dict, ve: dict) -> dict[str, Any]:
    val = ca.get("valuation_intelligence") or {}
    score = 55.0
    status = "incomplete"
    evidence: list[str] = []
    if val.get("narrative"):
        evidence.append(_txt(val["narrative"], 220) or "")
        status = "partial"
        score = 58
    if val.get("current_pe") is not None:
        evidence.append(f"Current P/E about {val.get('current_pe')}.")
        status = "partial"
    prem = val.get("premium_discount_vs_history_pct")
    if prem is not None:
        try:
            p = float(prem)
            # Higher score when cheaper vs history (discount)
            score = _clamp(70 - p * 0.8)
            status = "complete"
            evidence.append(f"Versus history: {p:+.0f}%.")
        except (TypeError, ValueError):
            pass
    mos = None
    if isinstance(ve, dict):
        latest = ve.get("latest_valuation") or ve.get("valuation") or ve
        if isinstance(latest, dict):
            mos = latest.get("margin_of_safety") or latest.get("mos")
            if mos is not None:
                try:
                    m = float(mos)
                    if abs(m) <= 1.5:
                        m *= 100
                    score = _clamp(0.5 * score + 0.5 * (55 + m * 0.5))
                    status = "complete"
                    evidence.append(f"Margin of safety context: {m:.0f}%.")
                except (TypeError, ValueError):
                    pass
    if status == "incomplete":
        reasoning = (
            "Valuation coverage is incomplete, so the committee reframes the question: not merely 'is it cheap', "
            "but 'is it attractive relative to quality and growth once fuller multiples history arrives'. "
            "Incomplete valuation lowers conviction, not the need for the layer."
        )
        score = 50
    else:
        reasoning = (
            f"Valuation score {round(score)}/100 asks whether price is attractive relative to quality and growth — "
            "not whether the multiple looks low in isolation. Paying up for quality can still be correct; "
            "cheapness without quality is often a value trap."
        )
    return _layer("valuation", score=score, status=status, reasoning=reasoning, evidence=[e for e in evidence if e])


def score_expectations(*, ca: dict, val_layer_score: float) -> dict[str, Any]:
    val = ca.get("valuation_intelligence") or {}
    evidence = []
    status = "incomplete"
    score = 55.0
    if val.get("forward_pe") is not None and val.get("current_pe") is not None:
        try:
            fwd = float(val["forward_pe"])
            cur = float(val["current_pe"])
            if fwd < cur:
                score = 68
                evidence.append("Forward multiple below trailing suggests earnings growth is partly priced as relief.")
            else:
                score = 48
                evidence.append("Forward multiple at or above trailing suggests demanding growth is already priced.")
            status = "partial"
        except (TypeError, ValueError):
            pass
    prem = val.get("premium_discount_vs_history_pct")
    if prem is not None:
        try:
            p = float(prem)
            # High premium = expectations already rich = lower expectation score (less room)
            score = _clamp(65 - max(0, p) * 0.6 + min(0, p) * -0.2)
            status = "complete"
            evidence.append("Historical premium/discount frames how much optimism is embedded.")
        except (TypeError, ValueError):
            pass
    if status == "incomplete":
        score = _clamp(val_layer_score * 0.9)
        reasoning = (
            "Market-expectations evidence is limited. The committee still asks what is already priced — "
            "because even good results can disappoint if the bar is too high."
        )
        status = "partial"
    else:
        reasoning = (
            f"Expectation score {round(score)}/100 asks what the market already assumes. "
            "High embedded optimism reduces upside asymmetry even for strong franchises."
        )
    return _layer("market_expectations", score=score, status=status, reasoning=reasoning, evidence=evidence)


def score_technical(*, market: dict) -> dict[str, Any]:
    market = market if isinstance(market, dict) else {}
    snap = market.get("snapshot") or {}
    pos = snap.get("range_position_0_1")
    momentum = market.get("momentum")
    evidence = []
    status = "incomplete"
    score = 55.0
    if isinstance(pos, (int, float)):
        score = _clamp(35 + float(pos) * 50)
        status = "complete"
        evidence.append(f"52-week range position roughly {float(pos)*100:.0f}th percentile.")
    if momentum:
        evidence.append(f"Momentum context: {momentum}.")
        status = "complete" if status != "incomplete" else "partial"
        if str(momentum).lower() in {"positive", "constructive"}:
            score = max(score, 72)
        elif str(momentum).lower() in {"soft", "negative"}:
            score = min(score, 45)
    if status == "incomplete":
        reasoning = (
            "Technical and flow evidence is incomplete. The layer still matters for entry timing and liquidity, "
            "but it never overrides business quality or valuation."
        )
        score = 50
    else:
        reasoning = (
            f"Technical score {round(score)}/100 reflects trend, range position and participation. "
            "Flow analysis informs timing — it does not certify business quality."
        )
    return _layer("technical", score=score, status=status, reasoning=reasoning, evidence=evidence)


def score_risk(*, ca: dict, briefing: dict, iie: dict) -> dict[str, Any]:
    risks = list(ca.get("risks") or briefing.get("risks") or [])
    if isinstance(iie, dict):
        risks.extend(list((iie.get("risks") or []))[:4])
    risks = [str(r) for r in risks if r][:8]
    # Lower risk → higher score
    n = len(risks)
    if n == 0:
        score = 60.0
        status = "incomplete"
        reasoning = (
            "Formal risk inventory is still forming. The committee assumes competitive, execution and valuation risks "
            "remain live until disproved — incomplete risk lists raise caution rather than comfort."
        )
    else:
        score = _clamp(88 - n * 6)
        status = "complete"
        reasoning = (
            f"Risk score {round(score)}/100 (higher is safer) reflects identified business, financial and path-dependency risks. "
            "Risk analysis matters because expected return is meaningless without the left tail."
        )
    return _layer("risk", score=score, status=status, reasoning=reasoning, evidence=risks[:5], extras={"risk_items": risks})


def build_catalysts(*, ca: dict, briefing: dict, iie: dict) -> dict[str, Any]:
    pos = list(ca.get("catalysts") or briefing.get("catalysts") or [])
    if isinstance(iie, dict):
        pos.extend(list(iie.get("catalysts") or [])[:4])
    pos = [str(x) for x in pos if x][:8]
    neg = list(ca.get("risks") or [])[:4]
    if not pos:
        pos = ["Next earnings and management commentary", "Further enrichment of operating evidence"]
    reasoning = (
        "Catalysts answer why the stock should move. Near-term prints, policy and competitive events reshape "
        "the probability distribution — they are not substitutes for business quality."
    )
    return _layer(
        "catalysts",
        score=None,
        status="complete" if pos else "partial",
        reasoning=reasoning,
        evidence=pos,
        extras={
            "positive": pos,
            "negative": [str(x) for x in neg if x][:6],
            "horizon": {
                "near_term": pos[:2],
                "medium_term": pos[2:4] or pos[:1],
                "long_term": pos[4:6] or ["Structural demand and competitive position"],
            },
        },
    )


def build_probability(*, ca: dict, iie: dict, overall: float) -> dict[str, Any]:
    scenarios = {}
    if isinstance(iie, dict):
        scenarios = iie.get("scenarios") or iie.get("probability_scenarios") or {}
    bull_p = _pct((scenarios.get("bull") or {}).get("probability"), 25) if isinstance(scenarios.get("bull"), dict) else 25
    base_p = _pct((scenarios.get("base") or {}).get("probability"), 50) if isinstance(scenarios.get("base"), dict) else 50
    bear_p = _pct((scenarios.get("bear") or {}).get("probability"), 25) if isinstance(scenarios.get("bear"), dict) else 25
    # Normalise
    total = (bull_p or 0) + (base_p or 0) + (bear_p or 0) or 100
    bull_p, base_p, bear_p = [round(100 * (x or 0) / total, 1) for x in (bull_p, base_p, bear_p)]

    # Return bands scale with overall quality
    bull_ret = round(12 + (overall - 50) * 0.35, 1)
    base_ret = round(4 + (overall - 50) * 0.22, 1)
    bear_ret = round(-8 - max(0, 70 - overall) * 0.15, 1)
    bull_case = [str(x) for x in (ca.get("bull_case") or [])[:3]]
    bear_case = [str(x) for x in (ca.get("bear_case") or [])[:3]]
    reasoning = (
        "The probability engine replaces single-point price targets with a distribution. "
        f"Bull {bull_p}% / Base {base_p}% / Bear {bear_p}% keeps the committee honest about asymmetry."
    )
    return _layer(
        "probability",
        score=None,
        status="complete",
        reasoning=reasoning,
        evidence=[],
        extras={
            "bull": {"probability": bull_p, "expected_return_pct": bull_ret, "narrative": bull_case},
            "base": {"probability": base_p, "expected_return_pct": base_ret, "narrative": []},
            "bear": {"probability": bear_p, "expected_return_pct": bear_ret, "narrative": bear_case},
        },
    )


def build_expected_return(*, probability: dict, overall: float, risk_score: float) -> dict[str, Any]:
    bull = (probability.get("bull") or {})
    base = (probability.get("base") or {})
    bear = (probability.get("bear") or {})
    pw = (
        (bull.get("probability", 25) / 100) * bull.get("expected_return_pct", 0)
        + (base.get("probability", 50) / 100) * base.get("expected_return_pct", 0)
        + (bear.get("probability", 25) / 100) * bear.get("expected_return_pct", 0)
    )
    upside = bull.get("expected_return_pct", 0)
    downside = abs(bear.get("expected_return_pct", 0))
    rr = round(upside / downside, 2) if downside else None
    reasoning = (
        f"Probability-weighted expected return is about {pw:.1f}% over a 12-month institutional horizon. "
        "Expected return must compensate for identified risks — edge without payoff asymmetry is not investable."
    )
    return _layer(
        "expected_return",
        score=None,
        status="complete",
        reasoning=reasoning,
        evidence=[],
        extras={
            "upside_pct": upside,
            "downside_pct": -abs(bear.get("expected_return_pct", 0)),
            "probability_weighted_return_pct": round(pw, 1),
            "risk_reward": rr,
            "expected_cagr_proxy_pct": round(pw, 1),
            "margin_of_safety_proxy": round((risk_score - 50) * 0.2 + (overall - 50) * 0.15, 1),
        },
    )


def build_decision(
    *,
    overall: float,
    layers: dict[str, dict],
    expected_return: dict,
    gate_blocked: bool,
    name: str,
    readiness_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    grade = _grade(overall)
    gate = readiness_gate if isinstance(readiness_gate, dict) else {}
    evidence_conf = float(gate.get("evidence_confidence_pct") or 0)
    band = str(gate.get("band") or "")
    hard_fail = bool(gate.get("hard_fail")) or band == "deferred"
    soft_watch = band == "watchlist"
    quality_blocked = hard_fail or soft_watch or gate_blocked

    suitable = []
    unsuitable = []
    if overall >= 75 and not quality_blocked and evidence_conf >= 80:
        suitable = ["Long Term", "Core Portfolio", "SIP"]
        unsuitable = ["Short-Term Trading", "High-Leverage Positions"]
        stance = "Constructive accumulation case"
    elif overall >= 60 and not hard_fail:
        suitable = ["Long Term", "Watchlist / staged entry"]
        unsuitable = ["High-Leverage Positions"]
        stance = "Selective / wait for better entry or evidence"
    else:
        suitable = ["Watchlist"]
        unsuitable = ["Core Portfolio", "High-Leverage Positions", "Short-Term Trading"]
        stance = "Inconclusive — evidence bar not met (not a negative company view)"

    if quality_blocked:
        missing = gate.get("additional_evidence_required") or gate.get("missing") or []
        miss_txt = "; ".join(str(m) for m in missing[:4]) if missing else "validated coverage incomplete"
        conclusion = (
            f"Investment thesis for {name}: INCONCLUSIVE. "
            f"Current evidence is insufficient for an institutional-level recommendation "
            f"(evidence confidence {evidence_conf:.0f}% vs required {gate.get('required_confidence_pct', 80)}%). "
            f"This should not be interpreted as a negative view of the company. "
            f"Additional evidence required: {miss_txt}. "
            f"Layered decision score {round(overall)}/100 (grade {grade}) remains analytical context — not a trade ticket."
        )
        action = "Recommendation deferred — evidence insufficient"
        investment_thesis_status = "INCONCLUSIVE"
    else:
        er = (expected_return.get("probability_weighted_return_pct") or 0)
        if overall >= 80 and er >= 12 and evidence_conf >= 80:
            action = "Constructive — suitable for long-term accumulation"
        elif overall >= 65 and er >= 6:
            action = "Selective — staged entry / hold bias"
        elif overall < 55 or er < 0:
            action = "Avoid / wait — payoff does not compensate for risk"
        else:
            action = "Watch — require better valuation or evidence"
        conclusion = (
            f"Institutional investment conclusion for {name}: overall score {round(overall)}/100 (grade {grade}). "
            f"{action}. Evidence confidence {evidence_conf:.0f}%. "
            "This is an investment-committee style conclusion — not a brokerage order ticket."
        )
        investment_thesis_status = "FORMED"

    reasoning = conclusion + " " + stance + "."
    # Confidence reported to users = evidence confidence when gated; else blended
    confidence_pct = (
        evidence_conf
        if quality_blocked and evidence_conf
        else round(_clamp(55 + (overall - 50) * 0.7), 1)
    )
    return _layer(
        "decision",
        score=overall,
        status="complete",
        reasoning=reasoning,
        evidence=list(gate.get("available") or [])[:6],
        extras={
            "overall_score": round(overall, 1),
            "investment_grade": grade,
            "action": action,
            "investment_thesis_status": investment_thesis_status,
            "not_a_negative_view": investment_thesis_status == "INCONCLUSIVE",
            "suitable_for": suitable,
            "unsuitable_for": unsuitable,
            "layer_scores": {
                k: layers[k].get("score")
                for k in LAYER_WEIGHTS
                if k in layers and layers[k].get("score") is not None
            },
            "company_quality_10": gate.get("company_quality_10"),
            "market_opportunity_10": gate.get("market_opportunity_10"),
            "evidence_confidence_pct": evidence_conf or None,
            "confidence_pct": confidence_pct,
            "expected_return_12m_pct": expected_return.get("probability_weighted_return_pct"),
            "bull_case_pct": (layers.get("probability") or {}).get("bull", {}).get("expected_return_pct"),
            "base_case_pct": (layers.get("probability") or {}).get("base", {}).get("expected_return_pct"),
            "bear_case_pct": (layers.get("probability") or {}).get("bear", {}).get("expected_return_pct"),
            "probability_weighted_return_pct": expected_return.get("probability_weighted_return_pct"),
            "risk_reward": expected_return.get("risk_reward"),
            "gate_blocked": quality_blocked,
            "readiness_band": band or None,
            "pre_questions": [
                "Is this an excellent business?",
                "Is management trustworthy and capable?",
                "Are the financials strengthening or weakening?",
                "Is valuation attractive relative to quality and growth?",
                "What is the market already expecting?",
                "What events could materially change the case?",
                "What is the probability distribution of outcomes?",
                "Does expected return compensate for identified risks?",
            ],
        },
    )


def assemble_layers(
    *,
    query: str = "",
    ticker: str | None = None,
    cid: dict | None = None,
    company_analysis: dict | None = None,
    sector_intelligence: dict | None = None,
    live_evidence: dict | None = None,
    evidence_completion: dict | None = None,
    valuation_pack: dict | None = None,
    market_events: dict | None = None,
    investment_intelligence: dict | None = None,
    institutional_briefing: dict | None = None,
    intelligence_construction: dict | None = None,
    aws_macro: dict | None = None,
    irp: dict | None = None,
    gate_blocked: bool = False,
) -> dict[str, Any]:
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cid = cid if isinstance(cid, dict) else {}
    sif = sector_intelligence if isinstance(sector_intelligence, dict) else {}
    briefing = institutional_briefing if isinstance(institutional_briefing, dict) else {}
    iie = investment_intelligence if isinstance(investment_intelligence, dict) else {}
    ve = valuation_pack if isinstance(valuation_pack, dict) else {}
    mee = market_events if isinstance(market_events, dict) else {}
    ic = intelligence_construction if isinstance(intelligence_construction, dict) else {}
    market = (ic.get("answer_enrichment") or {}).get("market_intelligence") or (
        (ic.get("sections") or {}).get("market_performance") or {}
    )
    name = _name(ca, cid, ticker)

    layers: dict[str, dict[str, Any]] = {}
    layers["macro"] = score_macro(ca=ca, mee=mee, aws_macro=aws_macro, briefing=briefing)
    layers["industry"] = score_industry(ca=ca, sif=sif, briefing=briefing)
    layers["company_quality"] = score_company_quality(ca=ca, cid=cid, ticker=ticker)
    layers["financial_quality"] = score_financial(ca=ca)
    layers["management"] = score_management(ca=ca, iie=iie)
    layers["valuation"] = score_valuation(ca=ca, ve=ve)
    layers["market_expectations"] = score_expectations(
        ca=ca, val_layer_score=float(layers["valuation"].get("score") or 55)
    )
    layers["technical"] = score_technical(market=market if isinstance(market, dict) else {})
    layers["risk"] = score_risk(ca=ca, briefing=briefing, iie=iie)

    # Weighted overall from scoring layers only (company/market quality — not coverage)
    weighted = 0.0
    wsum = 0.0
    for key, weight in LAYER_WEIGHTS.items():
        sc = layers[key].get("score")
        if sc is None:
            continue
        weighted += float(sc) * weight
        wsum += weight
    overall = weighted / wsum if wsum else 55.0

    from decision_engine.readiness_gate import evaluate_readiness_gate

    readiness = evaluate_readiness_gate(
        layers=layers,
        company_analysis=ca,
        cid=cid,
        live_evidence=live_evidence,
        evidence_completion=evidence_completion,
        valuation_pack=ve,
        irp=irp if isinstance(irp, dict) else None,
        external_gate_blocked=gate_blocked,
        name=name,
    )

    layers["catalysts"] = build_catalysts(ca=ca, briefing=briefing, iie=iie)
    layers["probability"] = build_probability(ca=ca, iie=iie, overall=overall)
    layers["expected_return"] = build_expected_return(
        probability=layers["probability"],
        overall=overall,
        risk_score=float(layers["risk"].get("score") or 55),
    )
    layers["decision"] = build_decision(
        overall=overall,
        layers=layers,
        expected_return=layers["expected_return"],
        gate_blocked=gate_blocked,
        name=name,
        readiness_gate=readiness,
    )

    ordered = [layers[k] for k in LAYER_ORDER if k in layers]
    return {
        "layers": ordered,
        "layers_by_id": layers,
        "overall_score": round(overall, 1),
        "investment_grade": _grade(overall),
        "company_name": name,
        "ticker": ticker or cid.get("ticker"),
        "gate_blocked": bool(readiness.get("hard_fail") or gate_blocked),
        "institutional_readiness_gate": readiness,
        "never_skip_layer": True,
        "decision_last": True,
        "never_conflate_data_with_quality": True,
    }
