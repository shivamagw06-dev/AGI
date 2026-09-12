"""CIO research-note prose helpers — soft-wire only.

Translate dossiers / academy / market snapshots into equity-research language.
Never emit framework codes, snake_case concept IDs, or placeholder status text.
"""

from __future__ import annotations

import re
from typing import Any

from company_analysis.cid_bridge import market_snapshot, ownership_snapshot

_STATUS_RE = re.compile(
    r"(?i)\b("
    r"unknown|n/?a|not available|insufficient evidence|recommendation withheld|"
    r"living (company )?dossier|intelligence construction|company analysis applied|"
    r"academy concepts attached|quality scaffold|not a trade signal|"
    r"coverage|research grade|data grade|missing:"
    r")\b"
)
_FRAMEWORK_RE = re.compile(
    r"(?i)\b(CID|IRP|LEO|SIF|ECP|DVC|FAPI|CAE|CMS|KF|IOC|AWS|AIP|KIP|RSP|RMS|CRE)\b"
)
_SNAKE_ID_RE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+){1,}\b")


def _clean(text: Any, limit: int = 520) -> str | None:
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    s = _FRAMEWORK_RE.sub("institutional research", s)
    s = re.sub(r"\s+", " ", s)
    if _STATUS_RE.search(s) and len(s) < 120:
        return None
    if _SNAKE_ID_RE.fullmatch(s.lower()):
        return None
    return s[:limit]


def _fmt_num(v: Any, *, pct: bool = False, money: bool = False) -> str | None:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    if pct:
        if abs(n) <= 1.5:
            n *= 100
        return f"{n:.1f}%"
    if money:
        abs_n = abs(n)
        if abs_n >= 1e12:
            return f"{n/1e12:.2f}T"
        if abs_n >= 1e9:
            return f"{n/1e9:.2f}B"
        if abs_n >= 1e7:
            return f"{n/1e7:.2f}Cr" if n > 0 else f"{n/1e7:.2f}Cr"
        if abs_n >= 1e6:
            return f"{n/1e6:.2f}M"
        return f"{n:,.0f}"
    if abs(n) >= 100:
        return f"{n:,.0f}"
    return f"{n:.2f}"


def translate_academy_concept(concept_id: Any) -> str | None:
    """Convert an Academy concept id into plain institutional language."""
    cid = str(concept_id or "").strip()
    if not cid:
        return None
    lesson: dict[str, Any] = {}
    try:
        from academy.catalog import teach

        lesson = teach(cid) or {}
    except Exception:
        try:
            from academy.teaching import teach

            lesson = teach(cid) or {}
        except Exception:
            lesson = {}
    bit = (
        lesson.get("why_it_matters")
        or lesson.get("what_it_is")
        or lesson.get("definition")
        or lesson.get("investment_implication")
    )
    cleaned = _clean(bit, 280)
    if cleaned:
        return cleaned
    # Last resort: humanise the id without exposing snake_case as a label token
    words = cid.replace("-", "_").split("_")
    if len(words) >= 2 and all(w.isalpha() for w in words):
        phrase = " ".join(words)
        return f"Assess whether {phrase} is improving or deteriorating for the equity story."
    return None


def academy_reasoning_bullets(academy: dict[str, Any] | None, *, limit: int = 4) -> list[str]:
    academy = academy if isinstance(academy, dict) else {}
    out: list[str] = []
    for hint in academy.get("answer_hints") or []:
        t = _clean(hint, 260)
        if t and t not in out and not _SNAKE_ID_RE.search(t):
            out.append(t)
        if len(out) >= limit:
            return out
    for cid in (academy.get("concept_ids") or academy.get("concepts") or [])[:8]:
        if isinstance(cid, dict):
            cid = cid.get("id") or cid.get("concept_id") or cid.get("name")
        t = translate_academy_concept(cid)
        if t and t not in out:
            out.append(t)
        if len(out) >= limit:
            break
    applied = ((academy.get("applied_concepts") or []) if isinstance(academy.get("applied_concepts"), list) else [])
    # Also read company-analysis academy_application shape
    return out[:limit]


def academy_from_company_analysis(ca: dict[str, Any] | None) -> list[str]:
    ca = ca if isinstance(ca, dict) else {}
    app = ca.get("academy_application") or {}
    out: list[str] = []
    for c in (app.get("applied_concepts") or [])[:6]:
        if not isinstance(c, dict):
            continue
        bit = c.get("application") or c.get("why_it_matters") or translate_academy_concept(c.get("concept_id") or c.get("id"))
        t = _clean(bit, 260)
        if t and t not in out:
            out.append(t)
    return out


def business_intelligence_narrative(
    *,
    cid: dict[str, Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    sector_intelligence: dict[str, Any] | None = None,
) -> dict[str, str]:
    """CIO-style Business Intelligence blocks — hide empties by omitting keys."""
    cid = cid if isinstance(cid, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    sif = sector_intelligence if isinstance(sector_intelligence, dict) else {}
    identity = ca.get("identity") or cid.get("identity") or {}
    name = identity.get("company_name") or cid.get("ticker") or "The company"
    sector = identity.get("sector") or identity.get("industry") or sif.get("sector_name") or "its industry"
    industry = identity.get("industry") or sector
    model = _clean(identity.get("business_model") or (cid.get("business_profile") or {}).get("business_model"), 360)
    overview = _clean(ca.get("business_overview") or (cid.get("business_profile") or {}).get("overview"), 420)
    bq = ca.get("business_quality") or {}

    out: dict[str, str] = {}

    # Business model
    if model or overview:
        bits = [f"{name} operates as {model}." if model and not str(model).lower().startswith(str(name).lower()) else (model or "")]
        if overview and overview not in bits[0]:
            bits.append(overview)
        bits.append(
            f"Understanding the business model matters because it determines how revenue is earned, "
            f"where margins are made, and which competitive pressures can actually impair intrinsic value in {industry}."
        )
        out["business_model"] = _clean(" ".join(b for b in bits if b), 700) or ""

    # Industry structure
    sector_n = _clean(sif.get("reasoning") or sif.get("narrative") or (ca.get("sector_intelligence") or {}).get("narrative"), 360)
    industry_bits = [
        f"{name} sits within {industry}.",
        sector_n,
        (
            "Industry structure matters because it shapes pricing power, capital intensity and the durability "
            "of returns — more than any single quarterly print."
        ),
    ]
    out["industry_structure"] = _clean(" ".join(b for b in industry_bits if b), 650) or ""

    # Competitive advantages / moat
    moat_bits: list[str] = []
    for key in ("moat", "competitive_advantage", "competitive_position", "advantages"):
        for src in (bq, cid.get("business_profile") or {}, ca):
            if isinstance(src, dict) and src.get(key):
                t = _clean(src.get(key), 280)
                if t:
                    moat_bits.append(t)
    if bq.get("business_quality_score") is not None:
        score = bq.get("business_quality_score")
        grade = bq.get("grade")
        moat_bits.append(
            f"AGI's structured business-quality assessment places {name} around {score}/100"
            + (f" (grade {grade})" if grade else "")
            + ", useful as a quality scaffold for franchise durability rather than a trading signal."
        )
    if not moat_bits:
        moat_bits.append(
            f"Competitive advantage for {name} should be judged through switching costs, scale, brand and "
            f"distribution — the variables that decide whether growth compounds or is competed away."
        )
    moat_bits.append(
        "Moat assessment matters because valuation only works if excess returns can persist beyond the next cycle."
    )
    out["competitive_advantages"] = _clean(" ".join(moat_bits), 700) or ""

    # Revenue drivers
    drivers = []
    for d in (ca.get("catalysts") or [])[:3]:
        t = _clean(d, 160)
        if t:
            drivers.append(t)
    fin = ca.get("financial_intelligence") or {}
    for d in (fin.get("what_improved") or [])[:3]:
        label = str(d).replace("_", " ")
        if not _SNAKE_ID_RE.fullmatch(str(d).lower()):
            drivers.append(f"Improving {label} is supporting the near-term growth narrative.")
        else:
            drivers.append(f"Improving {label} is supporting the near-term growth narrative.")
    if not drivers:
        drivers.append(
            f"Key revenue drivers in {industry} typically include volume growth, pricing/mix and adjacency expansion — "
            f"each should be tracked against competitive intensity."
        )
    drivers.append(
        "Revenue-driver clarity matters because it separates cyclical noise from structural compounding."
    )
    out["revenue_drivers"] = _clean(" ".join(drivers), 650) or ""

    # Operating metrics / financial quality bridge
    fin_n = _clean(fin.get("narrative"), 400)
    if fin_n:
        out["operating_metrics"] = (
            fin_n
            + " Operating metrics matter because they reveal whether growth is translating into cash and returns."
        )[:700]
    else:
        out["operating_metrics"] = (
            f"Even where full statement history is still being completed, the investment debate for {name} "
            "centres on unit economics, incremental returns on capital and cash conversion — the metrics that "
            "decide whether scale creates value."
        )

    # Risks
    risk_bits = [_clean(r, 180) for r in (ca.get("risks") or [])[:4]]
    risk_bits = [r for r in risk_bits if r]
    if not risk_bits:
        risk_bits = [
            f"Competitive intensity and execution risk remain material for {name}.",
            "Regulatory or platform-policy shifts can reprice growth assumptions quickly.",
        ]
    risk_bits.append(
        "Risk framing matters because institutional position sizing should reflect path dependency, not just the base case."
    )
    out["risks"] = _clean(" ".join(risk_bits), 650) or ""

    # Long-term growth narrative
    thesis = _clean(ca.get("investment_thesis"), 400)
    growth_bits = [
        thesis,
        _clean(((ca.get("bull_case") or [None])[0]), 220) if ca.get("bull_case") else None,
        (
            f"The long-term equity story for {name} depends on whether category growth, competitive position and "
            "capital allocation continue to reinforce each other over a multi-year horizon."
        ),
    ]
    out["long_term_growth"] = _clean(" ".join(b for b in growth_bits if b), 700) or ""

    # Combined narrative for executive use
    combined = " ".join(
        out[k]
        for k in (
            "business_model",
            "competitive_advantages",
            "industry_structure",
            "revenue_drivers",
            "long_term_growth",
        )
        if out.get(k)
    )
    if combined:
        out["narrative"] = combined[:900]
    return {k: v for k, v in out.items() if v}


def market_intelligence_pack(cid: dict[str, Any] | None = None, company_analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    """Always attempt to populate market context from validated CID market data."""
    cid = cid if isinstance(cid, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    snap = market_snapshot(cid) or {}
    md = cid.get("market_data") or {}
    # Soft fill from raw market_data if snapshot sparse
    if snap.get("current_price") is None and md.get("current_price") is not None:
        snap["current_price"] = md.get("current_price")
    if snap.get("fifty_two_week_high") is None:
        snap["fifty_two_week_high"] = md.get("fifty_two_week_high") or md.get("fiftyTwoWeekHigh")
    if snap.get("fifty_two_week_low") is None:
        snap["fifty_two_week_low"] = md.get("fifty_two_week_low") or md.get("fiftyTwoWeekLow")
    if snap.get("market_cap") is None:
        snap["market_cap"] = md.get("market_cap")
    if snap.get("currency") is None:
        snap["currency"] = md.get("currency")
    if snap.get("volume") is None:
        snap["volume"] = md.get("volume") or md.get("average_volume")
    if snap.get("range_position_0_1") is None:
        try:
            px = float(snap.get("current_price"))
            hi = float(snap.get("fifty_two_week_high"))
            lo = float(snap.get("fifty_two_week_low"))
            if hi > lo:
                snap["range_position_0_1"] = max(0.0, min(1.0, (px - lo) / (hi - lo)))
        except (TypeError, ValueError):
            pass

    name = ((ca.get("identity") or {}).get("company_name") or cid.get("ticker") or "The shares")
    bits: list[str] = []
    px = _fmt_num(snap.get("current_price"))
    if px:
        ccy = snap.get("currency") or ""
        bits.append(f"{name} currently trade near {px}{(' ' + ccy) if ccy else ''}.")
    mcap = _fmt_num(snap.get("market_cap"), money=True)
    if mcap:
        bits.append(f"Market capitalisation is about {mcap}, anchoring peer and ownership context.")
    hi = _fmt_num(snap.get("fifty_two_week_high"))
    lo = _fmt_num(snap.get("fifty_two_week_low"))
    pos = snap.get("range_position_0_1")
    if hi and lo:
        bits.append(f"The observed 52-week range runs from about {lo} to {hi}.")
    momentum = None
    if isinstance(pos, (int, float)):
        if pos >= 0.75:
            momentum = "Constructive"
            bits.append(
                "Price sits toward the upper end of the 52-week range, signalling constructive market momentum "
                "while reducing valuation comfort for fresh capital."
            )
        elif pos <= 0.35:
            momentum = "Soft"
            bits.append(
                "Price remains in the lower half of the 52-week range, reflecting cautious positioning and a wider "
                "path for either recovery or further stress."
            )
        else:
            momentum = "Mixed"
            bits.append(
                "Price occupies a mid-range 52-week position — neither extreme momentum nor deep distress — so "
                "fundamental evidence should lead the debate."
            )
    if snap.get("volume") is not None:
        bits.append("Recent volume provides a liquidity check rather than a standalone investment signal.")
    bits.append(
        "Market context matters because it frames entry timing and risk — it does not replace business or valuation analysis."
    )
    narrative = _clean(" ".join(bits), 750)

    cards: list[dict[str, str]] = []
    if px:
        cards.append({"label": "Price", "value": f"{px}{(' ' + str(snap.get('currency'))) if snap.get('currency') else ''}", "hint": "Last institutional market print"})
    if mcap:
        cards.append({"label": "Market Cap", "value": mcap, "hint": "Scale for peer context"})
    if lo and hi:
        cards.append({"label": "52-Week Range", "value": f"{lo} – {hi}", "hint": "Trading band"})
    if momentum:
        cards.append({"label": "Momentum", "value": momentum, "hint": "Range-position context"})

    return {
        "narrative": narrative,
        "snapshot": {k: v for k, v in snap.items() if v is not None},
        "cards": cards,
        "momentum": momentum,
    }


def research_takeaways(
    *,
    business: dict[str, str] | None = None,
    market: dict[str, Any] | None = None,
    financial_n: str | None = None,
    valuation_n: str | None = None,
    academy_bits: list[str] | None = None,
    risks: list[str] | None = None,
) -> list[str]:
    """Replace pipeline-status 'What AGI Learned' with research takeaways."""
    out: list[str] = []
    if business and business.get("business_model"):
        out.append(business["business_model"].split(".")[0] + ".")
    if market and market.get("narrative"):
        first = market["narrative"].split(".")[0] + "."
        out.append(first)
    if financial_n:
        out.append(financial_n.split(".")[0] + ".")
    if valuation_n:
        out.append(valuation_n.split(".")[0] + ".")
    for a in academy_bits or []:
        if a not in out:
            out.append(a)
        if len(out) >= 6:
            break
    if risks:
        out.append(f"Key risk to monitor: {risks[0]}")
    # Deduplicate / clean
    cleaned: list[str] = []
    for item in out:
        t = _clean(item, 280)
        if t and t not in cleaned:
            cleaned.append(t)
    return cleaned[:6]
