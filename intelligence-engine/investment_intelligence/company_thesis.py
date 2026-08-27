"""Company Thesis Intelligence — synthesis layer inside Investment Intelligence.

Not another knowledge provider. This composes a company's own institutional
thesis from evidence that already exists: canonical identity, CapIQ profile,
financials, market consensus, and the company's position relative to its
industry peers.

Uniqueness is structural, not stylistic. Two banks differ because their scale
rank, margin, coverage, dispersion, momentum and named competitors differ, and
every section is written from those numbers.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Optional

_LOCK = threading.RLock()
_PEERS: dict[str, list[dict[str, Any]]] | None = None

THESIS_SECTIONS: tuple[str, ...] = (
    "business_overview",
    "competitive_position",
    "business_quality",
    "growth_drivers",
    "financial_quality",
    "capital_allocation",
    "industry_position",
    "valuation_context",
    "key_risks",
    "key_catalysts",
    "evidence_summary",
    "bottom_line",
)


def _num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _fmt(value: Any, suffix: str = "") -> str:
    n = _num(value)
    if n is None:
        return "n/a"
    if abs(n) >= 1000:
        return f"{n:,.0f}{suffix}"
    if abs(n) >= 10:
        return f"{n:,.1f}{suffix}"
    return f"{n:,.2f}{suffix}"


def _count(value: Any) -> str:
    """Analyst and broker counts are whole numbers, not 40.0."""
    n = _num(value)
    return "n/a" if n is None else f"{int(round(n)):,}"


# "u" words in this vocabulary take "a" (a Universal Bank, a Utility).
_VOWEL_START = re.compile(r"^[aeio]", re.I)


def _article(word: str) -> str:
    return "an" if _VOWEL_START.match(str(word or "")) else "a"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def _ikt(ticker: str) -> dict[str, Any]:
    """Company profile facts from the CapIQ screener tables."""
    out: dict[str, Any] = {}
    try:
        from institutional_knowledge_tables.store import get_table

        def cell(row: dict[str, Any], key: str) -> Any:
            c = (row or {}).get(key)
            return c.get("value") if isinstance(c, dict) else None

        master = get_table(ticker, "company_master").get("row") or {}
        biz = get_table(ticker, "business_model").get("row") or {}
        comp = get_table(ticker, "competitors").get("row") or {}
        market_rows = get_table(ticker, "market_data").get("rows") or []
        fin_rows = get_table(ticker, "financial_statements").get("rows") or []
        market = market_rows[0] if market_rows else {}
        fin = fin_rows[0] if fin_rows else {}

        out = {
            "description": cell(biz, "description") or cell(biz, "description_short"),
            "products": cell(biz, "products"),
            "investors": cell(biz, "investors"),
            "subsidiaries": cell(biz, "subsidiaries_count"),
            "parent": cell(master, "parent_company"),
            "competitors": cell(comp, "peer"),
            "market_cap": cell(market, "market_cap"),
            "enterprise_value": cell(market, "enterprise_value"),
            "revenue": cell(fin, "revenue"),
            "ebitda": cell(fin, "ebitda"),
        }
    except Exception:
        out = {}
    return out


def _peer_table() -> dict[str, list[dict[str, Any]]]:
    """Industry → peer rows, for relative positioning."""
    global _PEERS
    with _LOCK:
        if _PEERS is not None:
            return _PEERS
    table: dict[str, list[dict[str, Any]]] = {}
    try:
        from valuation_consensus.store import load_live

        for ticker, row in (load_live().get("rows") or {}).items():
            industry = str(row.get("industry") or "").strip()
            if not industry:
                continue
            table.setdefault(industry, []).append({"ticker": ticker, **row})
    except Exception:
        table = {}
    with _LOCK:
        _PEERS = table
    return table


def invalidate_cache() -> None:
    global _PEERS
    with _LOCK:
        _PEERS = None


def _rank(values: list[tuple[str, float]], ticker: str) -> tuple[Optional[int], int]:
    """(rank, population) by descending value."""
    ranked = sorted(values, key=lambda kv: kv[1], reverse=True)
    for i, (tk, _v) in enumerate(ranked, 1):
        if tk == ticker:
            return i, len(ranked)
    return None, len(ranked)


def _peer_context(ticker: str, industry: str, profile: dict[str, Any]) -> dict[str, Any]:
    peers = _peer_table().get(industry) or []
    ctx: dict[str, Any] = {"peer_count": max(0, len(peers) - 1), "industry": industry}
    if not peers:
        return ctx

    def _series(field: str) -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = []
        for p in peers:
            v = _num(p.get(field))
            if v is not None:
                out.append((p["ticker"], v))
        return out

    cov_rank, cov_n = _rank(_series("coverage"), ticker)
    ctx["coverage_rank"], ctx["coverage_population"] = cov_rank, cov_n

    ups = _series("upside")
    up_rank, up_n = _rank(ups, ticker)
    ctx["upside_rank"], ctx["upside_population"] = up_rank, up_n
    if ups:
        vals = sorted(v for _t, v in ups)
        ctx["peer_median_upside"] = vals[len(vals) // 2]

    ret = _series("return_1y")
    r_rank, r_n = _rank(ret, ticker)
    ctx["return_rank"], ctx["return_population"] = r_rank, r_n
    if ret:
        vals = sorted(v for _t, v in ret)
        ctx["peer_median_return_1y"] = vals[len(vals) // 2]

    # Scale rank uses the screener market cap, which the consensus export lacks.
    scale: list[tuple[str, float]] = []
    for p in peers:
        v = _num(p.get("market_cap"))
        if v is None and p["ticker"] == ticker:
            v = _num(profile.get("market_cap"))
        if v is not None:
            scale.append((p["ticker"], v))
    if not scale:
        for p in peers:
            tk = p["ticker"]
            v = _num(_ikt(tk).get("market_cap")) if tk == ticker else None
            if v is not None:
                scale.append((tk, v))
    s_rank, s_n = _rank(scale, ticker)
    ctx["scale_rank"], ctx["scale_population"] = s_rank, s_n
    return ctx


def _sentences(text: Any, limit: int = 2) -> str:
    body = re.split(r"\n\s*\n", str(text or "").strip())[0]
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if s.strip()]
    return " ".join(parts[:limit])


def build_thesis(ticker: str) -> dict[str, Any]:
    """Twelve-section institutional thesis for one company."""
    from company_identity.service import identity_for

    tk = str(ticker or "").strip().upper()
    identity = identity_for(tk)
    if not identity.resolved:
        return {"ok": False, "error": "unresolved_company", "ticker": tk}

    from valuation_consensus.store import get_row

    consensus = get_row(tk) or {}
    profile = _ikt(tk)
    peers = _peer_context(tk, identity.primary_industry or "", profile)
    name = identity.company_name

    revenue = _num(profile.get("revenue"))
    ebitda = _num(profile.get("ebitda"))
    market_cap = _num(profile.get("market_cap")) or _num(consensus.get("market_cap"))
    margin = round((ebitda / revenue) * 100.0, 1) if revenue and ebitda else None
    cmp_price = _num(consensus.get("cmp"))
    target = _num(consensus.get("target_price"))
    upside = _num(consensus.get("upside"))
    coverage = _num(consensus.get("coverage"))
    buy = _num(consensus.get("buy_count")) or 0
    hold = _num(consensus.get("hold_count")) or 0
    sell = _num(consensus.get("sell_count")) or 0
    high, low = _num(consensus.get("target_high")), _num(consensus.get("target_low"))
    dispersion = (
        round(((high - low) / target) * 100.0, 1) if high and low and target else None
    )
    ret_1y = _num(consensus.get("return_1y"))
    ret_3y = _num(consensus.get("return_3y"))

    competitors = [
        c.strip().split(" (")[0]
        for c in str(profile.get("competitors") or "").split(";")
        if c.strip()
    ][:4]

    sections: dict[str, str] = {}

    # 1 — Business Overview
    description = _sentences(profile.get("description"), 2)
    sections["business_overview"] = (
        f"{name} is {_article(identity.business_type or 'listed')} {identity.business_type or 'listed company'} in "
        f"{identity.primary_industry or identity.primary_sector}. "
        + (description or f"It operates within {identity.primary_sector}.")
    )

    # 2 — Competitive Position
    scale_line = ""
    if peers.get("scale_rank") and peers.get("scale_population", 0) > 1:
        scale_line = (
            f"It ranks {_ordinal(peers['scale_rank'])} of {peers['scale_population']} "
            f"by market value among its {identity.primary_industry} peers"
        )
        if market_cap:
            scale_line += f" at ${_fmt(market_cap)}mm"
        scale_line += ". "
    comp_line = (
        f"Named competitors include {', '.join(competitors)}. " if competitors else ""
    )
    sections["competitive_position"] = (
        scale_line + comp_line
        or f"{name} competes within {identity.primary_industry or 'its industry'}."
    ).strip()

    # 3 — Business Quality
    quality_bits: list[str] = []
    if margin is not None:
        quality_bits.append(f"an EBITDA margin of {margin}% on ${_fmt(revenue)}mm of revenue")
    if ret_3y is not None:
        quality_bits.append(f"a three-year share price change of {_fmt(ret_3y)}%")
    sections["business_quality"] = (
        f"On the numbers the business shows " + " and ".join(quality_bits) + ". "
        if quality_bits
        else f"Reported financials for {name} are thin in the current dataset. "
    ) + (
        f"Quality for {identity.business_type or 'this model'} is judged on "
        f"{', '.join(identity.kpis[:4])}."
        if identity.kpis
        else ""
    )

    # 4 — Growth Drivers
    sections["growth_drivers"] = (
        f"Growth for {name} is driven by {', '.join(identity.kpis[:3])}"
        if identity.kpis
        else f"Growth for {name} follows its industry's volume and pricing cycle"
    ) + (
        f". Over the last year the shares moved {_fmt(ret_1y)}%"
        + (
            f" against a peer median of {_fmt(peers.get('peer_median_return_1y'))}%."
            if peers.get("peer_median_return_1y") is not None
            else "."
        )
        if ret_1y is not None
        else "."
    )

    # 5 — Financial Quality
    fin_bits: list[str] = []
    if revenue:
        fin_bits.append(f"revenue of ${_fmt(revenue)}mm")
    if ebitda:
        fin_bits.append(f"EBITDA of ${_fmt(ebitda)}mm")
    if market_cap:
        fin_bits.append(f"a market value of ${_fmt(market_cap)}mm")
    sections["financial_quality"] = (
        f"{name} reports " + ", ".join(fin_bits) + ". "
        if fin_bits
        else f"Financial disclosure for {name} is limited in the current dataset. "
    ) + (
        f"For this business the metrics that matter are {', '.join(identity.kpis[:4])}."
        if identity.kpis
        else ""
    )

    # 6 — Capital Allocation
    parent = profile.get("parent")
    investors = _sentences(profile.get("investors"), 1)
    cap_bits: list[str] = []
    if parent and str(parent).split(" (")[0] != name:
        cap_bits.append(f"ultimate parent is {str(parent).split(' (')[0]}")
    if profile.get("subsidiaries"):
        cap_bits.append(f"{profile['subsidiaries']} investments or subsidiaries on file")
    if investors:
        cap_bits.append(f"disclosed investors include {investors[:120]}")
    sections["capital_allocation"] = (
        f"On ownership and reinvestment, {'; '.join(cap_bits)}."
        if cap_bits
        else f"{name} is independently held with no parent on file; reinvestment is "
        f"judged against returns on the capital it already employs."
    )

    # 7 — Industry Position
    pos_bits: list[str] = []
    if peers.get("peer_count"):
        pos_bits.append(f"{peers['peer_count']} listed peers sit in {identity.primary_industry}")
    if peers.get("coverage_rank") and coverage is not None:
        pos_bits.append(
            f"{name} is {_ordinal(peers['coverage_rank'])} most covered with "
            f"{_count(coverage)} analysts"
        )
    sections["industry_position"] = (
        "; ".join(pos_bits).capitalize() + "."
        if pos_bits
        else f"{name} sits within {identity.primary_industry or identity.primary_sector}."
    )

    # 8 — Valuation Context
    frameworks = ", ".join(identity.allowed_valuation[:3]) if identity.allowed_valuation else "DCF"
    val_bits = [
        f"The market values {name} on {frameworks}, the frame that fits "
        f"{identity.business_type or 'this model'}"
    ]
    if target and cmp_price:
        val_bits.append(
            f"the Capital IQ consensus target of {_fmt(target)} sits against a last price of "
            f"{_fmt(cmp_price)}, an implied {_fmt(upside)}%"
        )
    if dispersion is not None:
        val_bits.append(f"the target range spans {dispersion}% of the mean, a measure of disagreement")
    expansion = (
        "Multiple expansion would require the return profile to improve faster than peers"
    )
    compression = "compression would follow deteriorating returns or a fading growth path"
    sections["valuation_context"] = ". ".join(val_bits) + f". {expansion}; {compression}."

    # 9 — Key Risks (company-specific, from this company's own position)
    risks: list[str] = []
    if upside is not None and peers.get("peer_median_upside") is not None:
        if upside > peers["peer_median_upside"]:
            risks.append(
                f"the {_fmt(upside)}% implied upside is above the {_fmt(peers['peer_median_upside'])}% "
                f"peer median, so expectations already assume delivery"
            )
        else:
            risks.append(
                f"implied upside of {_fmt(upside)}% trails the peer median, suggesting the market "
                f"sees less room in {name} than in its industry"
            )
    if coverage is not None and coverage < 10:
        risks.append(f"only {_count(coverage)} analysts cover it, so estimate revisions move the price hard")
    if sell and sell > 0:
        risks.append(f"{_count(sell)} brokers carry a sell rating, a live disagreement on the story")
    if margin is not None and margin < 15:
        risks.append(f"an EBITDA margin of {margin}% leaves little absorption for cost shocks")
    if ret_1y is not None and ret_1y < 0:
        risks.append(f"the shares are down {_fmt(abs(ret_1y))}% over a year, which usually reflects a real concern")
    if not risks:
        risks.append(
            f"the main risk is execution against the {', '.join(identity.kpis[:2]) or 'operating'} "
            f"metrics the market is paying for"
        )
    sections["key_risks"] = "Company-specific risks: " + "; ".join(risks[:4]) + "."

    # 10 — Key Catalysts
    catalysts: list[str] = []
    if identity.kpis:
        catalysts.append(f"movement in {identity.kpis[0]} and {identity.kpis[1] if len(identity.kpis) > 1 else 'margins'}")
    if buy and coverage:
        catalysts.append(
            f"{_count(buy)} of {_count(coverage)} brokers already positive — upgrades from the "
            f"remaining {_count(max(0.0, coverage - buy))} would re-rate it"
        )
    if dispersion is not None and dispersion > 40:
        catalysts.append(
            f"a target range spanning {dispersion}% means resolution of the disagreement is itself the catalyst"
        )
    if peers.get("scale_rank") and peers.get("scale_population", 0) > 3 and peers["scale_rank"] > 3:
        catalysts.append("share gain against the larger names in its industry")
    if ret_1y is not None and ret_1y > 20:
        catalysts.append(f"momentum is with it, up {_fmt(ret_1y)}% over a year")
    sections["key_catalysts"] = "Company-specific catalysts: " + "; ".join(catalysts[:4]) + "."

    # 11 — Evidence Summary
    evidence_bits = ["Capital IQ classification and profile"]
    if consensus:
        evidence_bits.append(f"broker consensus from {_count(coverage)} analysts")
    if revenue or ebitda:
        evidence_bits.append("reported revenue and EBITDA")
    if peers.get("peer_count"):
        evidence_bits.append(f"relative position against {peers['peer_count']} listed peers")
    sections["evidence_summary"] = "This rests on " + ", ".join(evidence_bits) + "."

    # 12 — Bottom Line
    stance_bits: list[str] = []
    if peers.get("scale_rank"):
        rank_label = (
            f"the largest {identity.primary_industry} name on this list"
            if peers["scale_rank"] == 1
            else f"the {_ordinal(peers['scale_rank'])}-largest {identity.primary_industry} name on this list"
        )
        stance_bits.append(rank_label)
    if margin is not None:
        stance_bits.append(f"a {margin}% EBITDA margin")
    if upside is not None:
        stance_bits.append(f"{_fmt(upside)}% of implied upside already in the consensus")
    sections["bottom_line"] = (
        f"Bottom line: {name} is "
        + (", ".join(stance_bits) if stance_bits else "a covered company in this universe")
        + f". What decides the outcome is {identity.kpis[0] if identity.kpis else 'execution'}"
        + (
            f" and whether it closes the gap to the {_fmt(peers.get('peer_median_upside'))}% peer median."
            if peers.get("peer_median_upside") is not None
            else "."
        )
    )

    return {
        "ok": True,
        "ticker": tk,
        "company_name": name,
        "identity": identity.context(),
        "sections": sections,
        "section_order": list(THESIS_SECTIONS),
        "evidence": [
            {"source": "company_identity", "title": f"{tk}.capital_iq_registry"},
            {"source": "valuation_consensus", "title": f"{tk}.market_consensus"},
            {"source": "institutional_knowledge_tables", "title": f"{tk}.company_profile"},
        ],
        "metrics": {
            "market_cap": market_cap,
            "revenue": revenue,
            "ebitda": ebitda,
            "ebitda_margin_pct": margin,
            "cmp": cmp_price,
            "target_price": target,
            "upside_pct": upside,
            "coverage": coverage,
            "buy": buy,
            "hold": hold,
            "sell": sell,
            "target_dispersion_pct": dispersion,
            "return_1y": ret_1y,
            **{k: v for k, v in peers.items() if v is not None},
        },
    }


def thesis_narrative(ticker: str, *, max_sections: int = 12) -> Optional[dict[str, Any]]:
    """Executive-style narrative: why this company matters, then the case."""
    pack = build_thesis(ticker)
    if not pack.get("ok"):
        return None
    sections = pack["sections"]
    lead = f"{sections['business_overview']} {sections['competitive_position']}".strip()
    body = [
        sections[key]
        for key in THESIS_SECTIONS[2:max_sections]
        if sections.get(key)
    ]
    return {
        "summary": lead,
        "why": body,
        "sections": sections,
        "evidence": pack["evidence"],
        "metrics": pack["metrics"],
        "company_name": pack["company_name"],
        "ticker": pack["ticker"],
    }
