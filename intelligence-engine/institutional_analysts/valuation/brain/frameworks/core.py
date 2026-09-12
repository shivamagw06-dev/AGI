"""Valuation frameworks 1–8 — interpretation over calculation."""

from __future__ import annotations

from typing import Any

from institutional_analysts.valuation.brain._text import as_list, blob_of, parse_num, txt


def _mos_band(mos: str, pe: float | None) -> str:
    m = (mos or "").lower()
    if any(w in m for w in ("high", "wide", "attractive", "ample", "deep")):
        return "Discount / wider cushion"
    if any(w in m for w in ("modest", "thin", "limited", "rich", "low", "premium")):
        return "Premium / thinner cushion"
    if pe is not None and pe >= 28:
        return "Premium / thinner cushion"
    if pe is not None and pe <= 14:
        return "Discount / wider cushion"
    return "Fair / mixed cushion"


def market_expectations(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    pe = parse_num(evidence.get("pe") or evidence.get("forward_pe"))
    mos = txt(evidence.get("margin_of_safety"))
    narrative = txt(evidence.get("narrative"))
    band = _mos_band(mos, pe)
    premium = "Premium" in band

    growth = (
        "Above-average multi-year growth appears embedded in today's price"
        if premium or (pe is not None and pe >= 22)
        else "More moderate growth appears sufficient to support today's price"
    )
    margins = (
        "Investors appear to assume margin durability / selective expansion"
        if premium
        else "Market pricing does not clearly require aggressive margin expansion"
    )
    roic = (
        "Sustained high capital efficiency appears priced in"
        if premium or (pe is not None and pe >= 20)
        else "Capital efficiency expectations look closer to historical norms"
    )
    cash = (
        "Cash-flow delivery must stay consistent with high-quality compounding assumptions"
        if premium
        else "Cash-flow delivery can support the price under base-case assumptions"
    )

    assessment = (
        f"Today's market price for {name} appears to embed {growth.lower()}. {margins} "
        f"{roic}. Future shareholder returns therefore depend more on whether those expectations "
        f"are delivered than on further multiple expansion."
        if premium
        else f"Today's market price for {name} does not clearly price heroic growth. {growth}. "
        f"{margins} {roic}. Attractiveness improves if cash flows exceed these embedded assumptions."
    )

    return {
        "framework": "Market Expectations",
        "completed": bool(pe is not None or mos or narrative),
        "implied_growth": growth,
        "implied_margins": margins,
        "implied_roic": roic,
        "implied_cash_flow": cash,
        "premium_or_discount": band,
        "assessment": assessment,
    }


def relative_valuation(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    pe = parse_num(evidence.get("pe"))
    fpe = parse_num(evidence.get("forward_pe"))
    pb = parse_num(evidence.get("pb"))
    peg = parse_num(evidence.get("peg"))
    dy = txt(evidence.get("dividend_yield"))
    peers = txt(evidence.get("peer_comparison"))

    multiples = {
        "pe": evidence.get("pe"),
        "forward_pe": evidence.get("forward_pe"),
        "pb": evidence.get("pb"),
        "ps": evidence.get("ps"),
        "ev": evidence.get("ev"),
        "ev_ebitda": evidence.get("ev_ebitda"),
        "ev_sales": evidence.get("ev_sales"),
        "dividend_yield": dy or None,
        "peg": evidence.get("peg"),
    }

    if pe is not None and pe >= 28:
        interpretation = (
            f"The market is currently assigning a premium earnings multiple to {name}, implying confidence "
            "in sustained high-quality growth and continued capital efficiency. Future shareholder returns "
            "are therefore likely to depend more on execution than multiple expansion."
        )
    elif pe is not None and pe <= 14:
        interpretation = (
            f"The current earnings multiple for {name} sits toward a more depressed band, implying that "
            "investors are embedding lower growth or higher risk. Upside exists if cash flows prove more "
            "resilient than those discounted assumptions."
        )
    else:
        interpretation = (
            f"Relative multiples for {name} sit nearer mid-cycle / peer-normal territory. Interpretation "
            "hinges on whether growth, returns and cash conversion can persist at levels consistent with "
            "that mid-band pricing — not on the multiple print alone."
        )

    if fpe is not None and pe is not None and fpe < pe:
        interpretation += " Forward earnings multiples are lower than trailing, suggesting near-term growth is partly recognised."

    return {
        "framework": "Relative Valuation",
        "completed": any(v is not None and v != "" for v in multiples.values()) or bool(peers),
        "multiples": multiples,
        "peer_context": peers or "Peer multiples used as a cross-check, not a verdict",
        "peg_view": (
            f"PEG context ({peg}) helps judge whether growth fully justifies the earnings multiple"
            if peg is not None
            else "PEG not available — growth-versus-multiple judgement remains qualitative"
        ),
        "assessment": interpretation,
    }


def intrinsic_value(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    intrinsic = txt(evidence.get("intrinsic_value") or evidence.get("fair_value"))
    expected = evidence.get("expected_return")
    mos = txt(evidence.get("margin_of_safety"))

    assessment = (
        f"Intrinsic value for {name} is best expressed as a range under explicit assumptions — not a false point estimate. "
        + (
            f"Available intrinsic context: {intrinsic}. "
            if intrinsic
            else "No precise intrinsic point is fabricated when inputs are incomplete. "
        )
        + "DCF / residual-income / economic-profit lenses are used to discuss whether price is supported by long-term cash flows."
    )
    if expected is not None:
        assessment += f" Scenario-weighted expected-return context: {expected}."

    return {
        "framework": "Intrinsic Value",
        "completed": bool(intrinsic or mos or expected is not None or evidence.get("pe") is not None),
        "approaches": ["DCF discussion", "Residual income / economic profit lens", "SOTP where relevant", "Asset value cross-check"],
        "intrinsic_range_discussion": intrinsic or "Intrinsic band remains an estimate under uncertainty",
        "precision_warning": "Do not fabricate precision — ranges and assumptions dominate point estimates",
        "assessment": assessment,
        "margin_of_safety_input": mos or "n/a",
    }


def reverse_dcf(evidence: dict[str, Any], expectations: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    pe = parse_num(evidence.get("pe") or evidence.get("forward_pe"))
    premium = "Premium" in str(expectations.get("premium_or_discount") or "")

    growth_needed = (
        "Material above-trend growth must occur to justify today's price"
        if premium or (pe is not None and pe >= 24)
        else "Moderate growth is sufficient if returns on capital remain intact"
    )
    margin_needed = (
        "Meaningful margin expansion or unusually durable margins are required"
        if premium
        else "Aggressive margin expansion is not clearly required"
    )
    realistic = (
        "Those embedded expectations are demanding and leave limited room for disappointment"
        if premium or (pe is not None and pe >= 24)
        else "Embedded expectations look more attainable under base-case cash-flow delivery"
    )

    return {
        "framework": "Reverse DCF",
        "completed": True,
        "growth_required": growth_needed,
        "margin_expansion_required": margin_needed,
        "expectations_realistic": realistic,
        "assessment": (
            f"Reverse-DCF reading for {name}: {growth_needed}. {margin_needed}. {realistic}."
        ),
    }


def historical_valuation(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    hist = txt(evidence.get("historical") or evidence.get("history"))
    pe = parse_num(evidence.get("pe"))
    mos = txt(evidence.get("margin_of_safety")).lower()

    if any(w in mos for w in ("rich", "thin", "modest", "premium")) or (pe is not None and pe >= 24):
        vs_history = "Rich versus own history / mid-cycle norms"
    elif any(w in mos for w in ("high", "wide", "ample", "attractive")) or (pe is not None and pe <= 14):
        vs_history = "Depressed versus own history / mid-cycle norms"
    else:
        vs_history = "Fair / near historical mid-band"

    return {
        "framework": "Historical Valuation",
        "completed": bool(hist or pe is not None or mos),
        "current_vs_history": vs_history,
        "historical_context": hist or "Compare current multiples with the company's own history",
        "cycle_highs_lows": "Cycle highs/lows used qualitatively when explicit bands are unavailable",
        "assessment": (
            f"Relative to history, {name}'s valuation looks {vs_history.lower()}. "
            "Richness or depression should be judged against growth and return persistence, not nostalgia for old multiples alone."
        ),
    }


def peer_comparison(evidence: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    peers = txt(evidence.get("peer_comparison") or evidence.get("peers"))
    indian = as_list(evidence.get("indian_peers"), limit=4)
    global_p = as_list(evidence.get("global_peers"), limit=4)
    growth = txt(evidence.get("growth_context"))
    returns = txt(evidence.get("capital_efficiency_context"))

    assessment = (
        f"Peer comparison for {name} must combine multiples with growth quality and capital efficiency — "
        "never multiples alone. "
        + (f"Peer context: {peers}. " if peers else "")
        + (f"Growth context: {growth}. " if growth else "")
        + (f"Capital efficiency context: {returns}." if returns else "Capital efficiency versus peers remains a qualitative overlay.")
    )
    return {
        "framework": "Peer Comparison",
        "completed": bool(peers or indian or global_p or evidence.get("pe") is not None),
        "indian_peers": indian or ["Domestic sector peers"],
        "global_peers": global_p or ["Global category peers"],
        "peer_multiples_context": peers or "Peer multiples as cross-check",
        "quality_overlay": "Adjust relative valuation for growth quality and capital efficiency differences",
        "assessment": assessment,
    }


def margin_of_safety_fw(evidence: dict[str, Any], expectations: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    mos = txt(evidence.get("margin_of_safety"))
    band = str(expectations.get("premium_or_discount") or _mos_band(mos, parse_num(evidence.get("pe"))))
    premium = "Premium" in band or "thinner" in band.lower()

    assessment = (
        f"Margin of safety for {name} looks {('limited' if premium else 'more constructive')}. "
        + (
            "Downside protection is thinner because today's price already embeds optimistic growth and return assumptions; "
            "execution shortfalls would likely compress the multiple as well as earnings."
            if premium
            else "Downside protection improves when price embeds more cautious assumptions; residual risk remains if cash flows deteriorate."
        )
    )
    return {
        "framework": "Margin of Safety",
        "completed": bool(mos or evidence.get("pe") is not None),
        "current_discount_or_premium": band,
        "downside_protection": "Thinner" if premium else "Wider",
        "execution_risk": "High dependency on delivering embedded expectations" if premium else "Moderate dependency on base-case delivery",
        "stated_mos": mos or "n/a",
        "assessment": assessment,
    }


def scenario_valuation(evidence: dict[str, Any], expectations: dict[str, Any]) -> dict[str, Any]:
    name = evidence.get("company") or "the company"
    premium = "Premium" in str(expectations.get("premium_or_discount") or "")
    expected = evidence.get("expected_return")

    bull = {
        "name": "Bull",
        "assumptions": "Growth and returns exceed embedded expectations; cash conversion stays strong",
        "drivers": "Operating delivery + possible multiple support",
        "valuation_implications": "Price can be justified and shareholder returns improve via earnings compounding",
        "probability": "Lower" if premium else "Moderate",
    }
    base = {
        "name": "Base",
        "assumptions": "Company delivers roughly what is priced in today",
        "drivers": "Steady cash flows / returns near assumptions",
        "valuation_implications": (
            "Returns driven mainly by earnings growth rather than multiple expansion"
            if premium
            else "Balanced contribution from cash delivery and valuation normalisation"
        ),
        "probability": "Highest",
    }
    bear = {
        "name": "Bear",
        "assumptions": "Growth or returns undershoot embedded expectations",
        "drivers": "Earnings miss and/or multiple compression",
        "valuation_implications": "Limited cushion if today's price was already optimistic",
        "probability": "Material" if premium else "Lower-to-moderate",
    }

    return {
        "framework": "Scenario Valuation",
        "completed": True,
        "bull": bull,
        "base": base,
        "bear": bear,
        "expected_return_context": expected,
        "assessment": (
            f"Scenario valuation for {name}: base case assumes delivery of currently embedded expectations; "
            f"bull requires outperformance; bear highlights {'multiple compression risk' if premium else 'cash-flow undershoot risk'}."
        ),
    }


def apply_all(evidence: dict[str, Any]) -> dict[str, Any]:
    exp = market_expectations(evidence)
    rel = relative_valuation(evidence)
    intrinsic = intrinsic_value(evidence)
    rev = reverse_dcf(evidence, exp)
    hist = historical_valuation(evidence)
    peers = peer_comparison(evidence)
    mos = margin_of_safety_fw(evidence, exp)
    scenarios = scenario_valuation(evidence, exp)

    return {
        "applied": [
            exp["framework"],
            rel["framework"],
            intrinsic["framework"],
            rev["framework"],
            hist["framework"],
            peers["framework"],
            mos["framework"],
            scenarios["framework"],
            "Valuation DNA",
            "Case Library",
            "Memory",
            "Benchmarks",
        ],
        "market_expectations": exp,
        "relative_valuation": rel,
        "multiple_analysis": rel,
        "intrinsic_value": intrinsic,
        "dcf_discussion": {
            "framework": "DCF Discussion",
            "assessment": intrinsic.get("assessment"),
            "reverse_dcf": rev.get("assessment"),
            "precision_warning": intrinsic.get("precision_warning"),
        },
        "reverse_dcf": rev,
        "historical_valuation": hist,
        "peer_comparison": peers,
        "margin_of_safety": mos,
        "scenario_valuation": scenarios,
    }
