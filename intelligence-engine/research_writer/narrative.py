"""Section narratives — interpret intelligence; never invent facts; never dump raw metrics."""

from __future__ import annotations

from typing import Any

from research_writer.language_quality import (
    clamp_words,
    is_placeholder,
    natural_unavailable,
    scrub_leaks,
)
from research_writer.tone import apply_tone


def _op(opinions: dict[str, Any], role: str) -> dict[str, Any]:
    op = opinions.get(role) if isinstance(opinions, dict) else None
    return op if isinstance(op, dict) else {}


def _sec(op: dict[str, Any]) -> dict[str, Any]:
    s = op.get("sections")
    return s if isinstance(s, dict) else {}


def _join(*parts: str) -> str:
    return scrub_leaks(" ".join(p for p in parts if p and not is_placeholder(p)), limit=1200)


def write_executive(*, cio: dict[str, Any], committee: dict[str, Any], company: str, query: str) -> str:
    decision = committee.get("decision") if isinstance(committee.get("decision"), dict) else {}
    stance = decision.get("committee_position") or committee.get("committee_stance") or cio.get("committee_stance") or "Neutral"
    reason = committee.get("committee_reason") or ""
    conviction = committee.get("conviction") or (committee.get("vote") or {}).get("conviction") or ""
    what = scrub_leaks(cio.get("executive_summary") or "", limit=280)
    thesis = scrub_leaks(cio.get("investment_thesis") or "", limit=200)
    body = _join(
        f"{company}: institutional research concludes a {str(stance).lower()} stance"
        + (f" with {str(conviction).lower()} conviction" if conviction else "")
        + ".",
        what,
        reason,
        thesis,
        "The assessment weighs franchise quality, financial trajectory, valuation, macro transmission and residual risk.",
    )
    # Answer: what / why / why it matters / stance
    if query and "invest" in query.lower():
        body = _join(
            body,
            f"For investors asking whether to own {company}, the institutional stance is {str(stance).lower()} — "
            "an assessment of the research file, not a brokerage order instruction.",
        )
    return apply_tone(clamp_words(body, min_words=80, max_words=150))


def write_business(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    strengths = list(op.get("strengths") or [])
    model = sec.get("business_model") or ""
    advantages = sec.get("competitive_advantages") or strengths
    pricing = sec.get("pricing_power") or ""
    growth = sec.get("growth_opportunities") or ""
    if isinstance(advantages, list):
        adv_text = ", ".join(str(a) for a in advantages[:3] if not is_placeholder(a))
    else:
        adv_text = str(advantages)
    body = _join(
        f"{company} continues to demonstrate a durable competitive position"
        + (f" supported by {adv_text}" if adv_text else "")
        + ".",
        scrub_leaks(model, limit=220),
        scrub_leaks(pricing, limit=160),
        f"Growth optionality centres on {growth}." if growth and not is_placeholder(growth) else "",
        scrub_leaks(op.get("summary") or "", limit=200),
    )
    if not body:
        body = natural_unavailable("business quality")
    return apply_tone(body, limit=700)


def write_financial(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    quality = sec.get("financial_quality") or ""
    trend = sec.get("trend") or ""
    # Interpret — do not dump ROE/margins as a list
    body = _join(
        f"For {company}, financial quality should be judged through earnings durability, cash conversion and balance-sheet resilience.",
        scrub_leaks(quality, limit=200),
        scrub_leaks(trend, limit=160),
        "Returns on capital and margin resilience matter more than any single print; "
        "the trajectory of cash generation remains the practical test of value creation.",
        scrub_leaks(op.get("summary") or "", limit=180),
    )
    # Soft interpret known metrics without raw dumps
    roe = sec.get("roe")
    margins = sec.get("margins")
    revenue = sec.get("revenue")
    interpret = []
    if roe and not is_placeholder(roe) and str(roe).lower() != "n/a":
        interpret.append(
            "Returns on equity remain a core marker of whether the franchise continues to earn above its opportunity cost of capital."
        )
    if margins and not is_placeholder(margins):
        interpret.append(
            "Operating margins deserve monitoring for resilience through cost and mix cycles rather than as a one-period snapshot."
        )
    if revenue and not is_placeholder(revenue):
        interpret.append(
            "Revenue momentum should be read alongside mix and pricing to judge whether growth is durable."
        )
    body = _join(body, *interpret[:2])
    return apply_tone(body, limit=700)


def write_valuation(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    mos = sec.get("margin_of_safety") or ""
    peer = sec.get("peer_comparison") or ""
    hist = sec.get("historical_valuation") or ""
    body = _join(
        f"For {company}, valuation attractiveness depends on whether today's price already discounts the expected operating path.",
        scrub_leaks(hist, limit=180),
        scrub_leaks(peer, limit=160),
        scrub_leaks(mos, limit=180),
        "Multiples are a language for expectations — not a verdict in isolation. "
        "The institutional question is whether expected returns compensate for earnings and multiple risk.",
        scrub_leaks(op.get("summary") or "", limit=160),
    )
    return apply_tone(body, limit=700)


def write_market(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    trend = sec.get("price_trend") or ""
    rng = sec.get("range_52w") or ""
    liq = sec.get("liquidity") or ""
    body = _join(
        f"Shares in {company} should be read as a timing overlay on the fundamental case, not as a substitute for it.",
        scrub_leaks(trend, limit=180),
        "Price location within the twelve-month range and liquidity conditions inform staging, "
        "while intrinsic value remains the primary ownership test.",
        scrub_leaks(rng, limit=140),
        scrub_leaks(liq, limit=120),
    )
    # Never print raw ₹ price dumps — scrub currency-heavy fragments lightly
    body = body.replace("₹", "")
    return apply_tone(body, limit=600)


def write_sector(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    structure = sec.get("industry_structure") or ""
    growth = sec.get("sector_growth") or ""
    regulation = sec.get("regulation") or ""
    competition = sec.get("competition") or ""
    body = _join(
        f"Industry structure around {company} shapes pricing power, capital intensity and the durability of returns.",
        scrub_leaks(structure, limit=200),
        scrub_leaks(growth, limit=160),
        scrub_leaks(competition, limit=140),
        scrub_leaks(regulation, limit=140),
        "Sector KPIs matter only insofar as they discriminate winners from the pack over a full cycle.",
    )
    return apply_tone(body, limit=650)


def write_macro(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    rates = sec.get("interest_rates") or ""
    transmission = sec.get("transmission") or ""
    outlook = sec.get("macro_outlook") or ""
    body = _join(
        f"Macro conditions transmit to {company} through funding costs, demand, liquidity and currency — not as abstract headlines.",
        scrub_leaks(transmission, limit=220),
        scrub_leaks(rates, limit=160),
        scrub_leaks(outlook, limit=160),
        "The institutional task is to judge whether the external regime helps or hurts the franchise over the investment horizon.",
    )
    return apply_tone(body, limit=650)


def write_management(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    body = _join(
        f"Trust in {company}'s leadership rests on governance, capital allocation and communication consistency.",
        scrub_leaks(sec.get("governance"), limit=160),
        scrub_leaks(sec.get("capital_allocation"), limit=160),
        scrub_leaks(sec.get("execution"), limit=140),
        scrub_leaks(op.get("summary") or "", limit=160),
    )
    return apply_tone(body or natural_unavailable("management quality"), limit=500)


def write_ownership(op: dict[str, Any], *, company: str) -> str:
    sec = _sec(op)
    body = _join(
        f"Ownership structure for {company} signals alignment, free-float dynamics and the balance between promoter and institutional holders.",
        scrub_leaks(sec.get("promoters"), limit=120),
        scrub_leaks(sec.get("institutions"), limit=120),
        scrub_leaks(sec.get("ownership_trend"), limit=160),
    )
    return apply_tone(body or natural_unavailable("ownership"), limit=450)


def write_risks(op: dict[str, Any], *, cio: dict[str, Any]) -> list[dict[str, str]]:
    sec = _sec(op)
    items = list(sec.get("business_risks") or op.get("weaknesses") or cio.get("key_risks") or [])
    monitoring = list(sec.get("monitoring") or ["Next earnings", "Guidance", "Asset quality / margins"])
    out = []
    for i, r in enumerate(items[:6]):
        text = scrub_leaks(r, limit=140)
        if not text:
            continue
        out.append(
            {
                "description": text,
                "probability": "High" if i == 0 else "Medium" if i < 3 else "Low",
                "potential_impact": "High" if i < 2 else "Medium",
                "mitigation": "Active monitoring and thesis invalidation rules",
                "monitoring_trigger": scrub_leaks(monitoring[min(i, len(monitoring) - 1)], limit=100),
            }
        )
    if not out:
        out.append(
            {
                "description": "Evidence incompleteness itself remains a risk to conviction.",
                "probability": "Medium",
                "potential_impact": "Medium",
                "mitigation": "Raise conviction only as the evidence file thickens",
                "monitoring_trigger": "Next material disclosure",
            }
        )
    return out


def write_scenarios(cio: dict[str, Any]) -> dict[str, dict[str, Any]]:
    def _scenario(name: str, items: list[Any], probability: str) -> dict[str, Any]:
        assumptions = [scrub_leaks(x, limit=160) for x in (items or []) if not is_placeholder(x)]
        assumptions = [a for a in assumptions if a][:4]
        return {
            "probability": probability,
            "assumptions": assumptions or [f"{name.capitalize()} path pending richer confirmation."],
            "catalysts": list(cio.get("key_catalysts") or [])[:2]
            if name != "bear"
            else ["Earnings miss", "Multiple compression"],
            "investment_implication": {
                "bull": "Supports adding or holding risk budget if valuation cushion is acceptable.",
                "base": "Supports a measured institutional holding with standard monitoring.",
                "bear": "Argues for reduced conviction and tighter risk limits.",
            }.get(name, "Monitor."),
        }

    return {
        "bull": _scenario("bull", list(cio.get("bull_case") or []), "35%"),
        "base": _scenario("base", list(cio.get("base_case") or []), "45%"),
        "bear": _scenario("bear", list(cio.get("bear_case") or []), "20%"),
    }


def write_conclusion(*, cio: dict[str, Any], committee: dict[str, Any], company: str) -> str:
    decision = committee.get("decision") if isinstance(committee.get("decision"), dict) else {}
    stance = decision.get("committee_position") or committee.get("committee_stance") or "Neutral"
    reason = committee.get("committee_reason") or ""
    follow = (committee.get("minutes") or {}).get("follow_up") or "the next earnings print and management commentary"
    body = _join(
        scrub_leaks(cio.get("institutional_conclusion") or "", limit=220),
        f"What is happening: {company} is held at a {str(stance).lower()} institutional stance.",
        f"Why: {reason}" if reason else "",
        "What matters most is whether franchise quality and financial trajectory justify today's entry after macro transmission.",
        f"Institutional investors should monitor next: {scrub_leaks(follow, limit=160)}.",
    )
    return apply_tone(clamp_words(body, max_words=250), limit=900)


def write_institutional_view(committee: dict[str, Any]) -> str:
    decision = committee.get("decision") if isinstance(committee.get("decision"), dict) else {}
    vote = committee.get("vote") if isinstance(committee.get("vote"), dict) else {}
    stance = decision.get("committee_position") or committee.get("committee_stance") or "Neutral"
    conviction = vote.get("conviction") or committee.get("conviction") or ""
    tally = vote.get("tally") or committee.get("vote_tally") or ""
    reason = committee.get("committee_reason") or ""
    minority = committee.get("minority_opinions") or []
    minority_view = ""
    if minority and isinstance(minority[0], dict):
        minority_view = scrub_leaks(minority[0].get("view"), limit=160)
    body = _join(
        f"Investment Committee position: {stance}"
        + (f" · {conviction} conviction" if conviction else "")
        + (f" · Vote {tally}" if tally else "")
        + ".",
        reason,
        f"Minority view: {minority_view}." if minority_view else "",
        scrub_leaks(committee.get("committee_summary") or "", limit=220),
    )
    return apply_tone(body, limit=700)


def write_thesis(cio: dict[str, Any], *, company: str) -> str:
    body = _join(
        scrub_leaks(cio.get("investment_thesis") or "", limit=280),
        f"The ownership case for {company} rests on durable franchise economics, financial quality and an acceptable entry after risk adjustment.",
    )
    return apply_tone(body, limit=500)


def detect_report_type(query: str) -> str:
    q = (query or "").lower()
    if "committee minutes" in q or "minutes" in q:
        return "Investment Committee Minutes"
    if "earnings" in q or "quarterly" in q:
        return "Quarterly Earnings Review"
    if "sector" in q:
        return "Sector Research"
    if "macro" in q or "rates" in q or "inflation" in q:
        return "Macro Research"
    if "theme" in q:
        return "Theme Research"
    if "portfolio" in q:
        return "Portfolio Review"
    if "morning" in q:
        return "Morning Brief"
    if "evening" in q:
        return "Evening Brief"
    if "initiat" in q:
        return "Company Initiation"
    return "Company Update"
