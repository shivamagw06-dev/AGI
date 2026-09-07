"""Valuation Terminal — market data plus AGI interpretation.

Two layers, never mixed:
  market   — Yahoo Finance multiples and Capital IQ consensus, reported as-is
  agi      — how to read them: which metric governs, peer position, what would
             change the rating

No BUY/SELL. No price targets of AGI's own.
"""

from __future__ import annotations

import statistics as stats
from typing import Any, Optional

from valuation_terminal import store
from valuation_terminal.sector_lens import (
    METRIC_LABELS,
    explain,
    is_meaningful,
    lens_for,
    visible_metrics_for,
)

PRIMARY_SECTORS: tuple[str, ...] = (
    "Financials",
    "Information Technology",
    "Industrials",
    "Health Care",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Materials",
    "Utilities",
    "Real Estate",
    "Communication Services",
)


def _num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _median(values: list[Any]) -> Optional[float]:
    clean = [v for v in (_num(x) for x in values) if v is not None]
    return round(stats.median(clean), 2) if clean else None


def _consensus(ticker: str) -> dict[str, Any]:
    try:
        from valuation_consensus.store import get_row

        row = get_row(ticker) or {}
    except Exception:
        row = {}
    return {
        "target_price": row.get("target_price"),
        "target_high": row.get("target_high"),
        "target_low": row.get("target_low"),
        "upside": row.get("upside"),
        "coverage": row.get("coverage"),
        "buy": row.get("buy_count"),
        "outperform": row.get("outperform_count"),
        "hold": row.get("hold_count"),
        "sell": row.get("sell_count"),
        "no_opinion": row.get("no_opinion_count"),
        "cmp": row.get("cmp"),
        "return_1y": row.get("return_1y"),
        "return_5y": row.get("return_5y"),
    }


def _enriched_rows() -> list[dict[str, Any]]:
    """Stored rows with manual overrides applied and consensus attached."""
    from valuation_terminal import overrides

    rows = []
    for ticker, row in store.all_rows().items():
        merged = overrides.apply_to(ticker, dict(row))
        merged["ticker"] = ticker
        merged["consensus"] = _consensus(ticker)
        rows.append(merged)
    return rows


def _industry_population(rows: list[dict[str, Any]], industry: Optional[str]) -> dict[str, list[Any]]:
    """Every value of every metric within one industry, for percentile ranking."""
    from valuation_terminal.sector_lens import ALL_METRICS

    members = [r for r in rows if r.get("primary_industry") == industry]
    return {metric: [m.get(metric) for m in members] for metric in ALL_METRICS}


def sector_statistics() -> dict[str, Any]:
    """Median statistics per sector and per industry, recomputed from raw values."""
    from valuation_terminal.calc import median_of

    rows = _enriched_rows()
    metrics = ("pe", "forward_pe", "pb", "ev_ebitda", "ev_sales", "roe", "dividend_yield", "market_cap")

    def block(members: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {"companies": len(members)}
        for metric in metrics:
            out[f"median_{metric}"] = median_of([m.get(metric) for m in members])
        out["median_consensus_upside"] = median_of(
            [m["consensus"].get("upside") for m in members]
        )
        return out

    by_sector = {
        sector: block([r for r in rows if r.get("primary_sector") == sector])
        for sector in PRIMARY_SECTORS
    }
    industries = {r.get("primary_industry") for r in rows if r.get("primary_industry")}
    by_industry = {
        industry: block([r for r in rows if r.get("primary_industry") == industry])
        for industry in sorted(industries)
    }
    return {"ok": True, "sectors": by_sector, "industries": by_industry}


def health() -> dict[str, Any]:
    base = store.health()
    rows = store.all_rows()
    sectors = {r.get("primary_sector") for r in rows.values() if r.get("primary_sector")}
    base["sectors_covered"] = len(sectors)
    base["page"] = "Valuation Intelligence Terminal"
    return base


# ---------------------------------------------------------------------------
# Section 1 — Market Valuation Dashboard
# ---------------------------------------------------------------------------
def market_overview() -> dict[str, Any]:
    rows = _enriched_rows()
    if not rows:
        return {"ok": False, "error": "no_metrics_loaded"}

    total_mcap = sum(v for v in (_num(r.get("market_cap")) for r in rows) if v is not None)
    sector_medians = {
        sector: {
            "pe": _median([r.get("pe") for r in rows if r.get("primary_sector") == sector]),
            "pb": _median([r.get("pb") for r in rows if r.get("primary_sector") == sector]),
            "count": sum(1 for r in rows if r.get("primary_sector") == sector),
        }
        for sector in PRIMARY_SECTORS
    }
    priced = {s: v["pe"] for s, v in sector_medians.items() if v["pe"] and v["count"] >= 5}
    most_expensive = max(priced, key=priced.get) if priced else None
    cheapest = min(priced, key=priced.get) if priced else None

    upsides = [
        (r["ticker"], _num(r["consensus"].get("upside")))
        for r in rows
        if _num(r["consensus"].get("upside")) is not None
    ]
    top_upside = max(upsides, key=lambda kv: kv[1]) if upsides else None

    return {
        "ok": True,
        "companies_covered": len(rows),
        "total_market_cap": round(total_mcap, 0) if total_mcap else None,
        "median_pe": _median([r.get("pe") for r in rows]),
        "median_pb": _median([r.get("pb") for r in rows]),
        "median_ev_ebitda": _median(
            [r.get("ev_ebitda") for r in rows if is_meaningful("ev_ebitda", r.get("industry_dna"))]
        ),
        "median_dividend_yield": _median([r.get("dividend_yield") for r in rows]),
        "median_roe": _median([r.get("roe") for r in rows]),
        "median_profit_margin": _median([r.get("profit_margin") for r in rows]),
        "highest_consensus_upside": (
            {"ticker": top_upside[0], "upside": top_upside[1]} if top_upside else None
        ),
        "most_expensive_sector": (
            {"sector": most_expensive, "median_pe": priced.get(most_expensive)}
            if most_expensive
            else None
        ),
        "cheapest_sector": (
            {"sector": cheapest, "median_pe": priced.get(cheapest)} if cheapest else None
        ),
        "updated_at": store.load().get("updated_at"),
        "market_data_source": store.load().get("source"),
    }


# ---------------------------------------------------------------------------
# Section 2 — Sector cards
# ---------------------------------------------------------------------------
def sectors() -> dict[str, Any]:
    rows = _enriched_rows()
    cards: list[dict[str, Any]] = []
    for sector in PRIMARY_SECTORS:
        members = [r for r in rows if r.get("primary_sector") == sector]
        if not members:
            continue
        dna_counts: dict[str, int] = {}
        for member in members:
            key = member.get("industry_dna") or ""
            dna_counts[key] = dna_counts.get(key, 0) + 1
        dominant_dna = max(dna_counts, key=dna_counts.get) if dna_counts else None
        lens = lens_for(dominant_dna, sector)
        card = {
            "sector": sector,
            "companies": len(members),
            "median_market_cap": _median([m.get("market_cap") for m in members]),
            "median_pe": _median([m.get("pe") for m in members]),
            "median_pb": _median([m.get("pb") for m in members]),
            "median_ev_ebitda": (
                _median([m.get("ev_ebitda") for m in members])
                if is_meaningful("ev_ebitda", dominant_dna)
                else None
            ),
            "median_roe": _median([m.get("roe") for m in members]),
            "median_dividend_yield": _median([m.get("dividend_yield") for m in members]),
            "median_consensus_upside": _median(
                [m["consensus"].get("upside") for m in members]
            ),
            "median_coverage": _median([m["consensus"].get("coverage") for m in members]),
            "primary_metric": lens["primary_metric"],
            "primary_metric_label": lens["primary_metric_label"],
            "ev_ebitda_meaningful": is_meaningful("ev_ebitda", dominant_dna),
        }
        cards.append(card)
    cards.sort(key=lambda c: -(c["companies"] or 0))
    return {"ok": True, "sectors": cards, "count": len(cards)}


# ---------------------------------------------------------------------------
# Section 3 — AGI Sector Intelligence
# ---------------------------------------------------------------------------
_SECTOR_DNA_NOTE: dict[str, str] = {
    "Financials": (
        "Banks and lenders create value by deploying a balance sheet, not by "
        "manufacturing assets. The multiple attaches to book equity and is earned "
        "by the return on it."
    ),
    "Information Technology": (
        "Services firms convert people into billable output. Value comes from "
        "utilisation, pricing and retention rather than from installed capital."
    ),
    "Consumer Staples": (
        "Demand is repeat and largely non-discretionary, so cash flows are "
        "predictable and the market pays a premium for that certainty."
    ),
    "Energy": (
        "Earnings track commodity spreads the company does not control, so the "
        "market capitalises them cautiously and rewards cash returns."
    ),
    "Utilities": (
        "Returns are regulated and largely fixed, so the question is asset base "
        "growth and the reliability of the payout rather than growth optionality."
    ),
    "Materials": (
        "Cyclical volumes and realisations dominate. Multiples compress at the top "
        "of the cycle precisely when earnings look best."
    ),
    "Health Care": (
        "Pipeline, approvals and pricing power drive value, and the market pays "
        "ahead of realised earnings where the pipeline is credible."
    ),
    "Consumer Discretionary": (
        "Demand is cyclical and brand-led. Operating leverage cuts both ways, so "
        "multiples track confidence in the demand cycle."
    ),
    "Industrials": (
        "Order books convert into revenue with a lag, so the market pays for "
        "execution and book-to-bill rather than for reported earnings alone."
    ),
    "Real Estate": (
        "Value sits in land, pre-sales and collections, so net asset value and "
        "book anchor the multiple more than reported profit."
    ),
    "Communication Services": (
        "Subscriber economics and spectrum costs dominate. Enterprise value against "
        "cash operating profit is the comparable frame given heavy leverage."
    ),
}


def sector_intelligence(sector: str) -> dict[str, Any]:
    """Market picture plus AGI interpretation for one sector."""
    name = str(sector or "").strip()
    canonical = next((s for s in PRIMARY_SECTORS if s.lower() == name.lower()), None)
    if not canonical:
        return {"ok": False, "error": "unknown_sector", "sector": sector}

    rows = [r for r in _enriched_rows() if r.get("primary_sector") == canonical]
    if not rows:
        return {"ok": False, "error": "no_companies", "sector": canonical}

    dna_counts: dict[str, int] = {}
    for r in rows:
        key = r.get("industry_dna") or ""
        dna_counts[key] = dna_counts.get(key, 0) + 1
    dominant = max(dna_counts, key=dna_counts.get) if dna_counts else None
    lens = lens_for(dominant, canonical)

    primary = lens["primary_metric"]
    median_primary = _median([r.get(primary) for r in rows])
    median_roe = _median([r.get(primary if primary == "roe" else "roe") for r in rows])
    median_yield = _median([r.get("dividend_yield") for r in rows])
    median_upside = _median([r["consensus"].get("upside") for r in rows])

    # AGI interpretation, written from this sector's own numbers.
    interpretation: list[str] = []
    label = lens["primary_metric_label"]
    if median_primary is not None:
        interpretation.append(
            f"The median {canonical} company trades at {median_primary} on {label}, "
            f"which is the frame this industry is judged on. {lens['rationale']}"
        )
    if primary == "pb" and median_roe is not None:
        interpretation.append(
            f"That multiple has to be earned: median return on equity is {median_roe}%. "
            "Where the return sits above the cost of equity the market pays above book; "
            "where it does not, it pays below."
        )
    elif median_roe is not None:
        interpretation.append(
            f"Median return on equity is {median_roe}%, which is what ultimately supports "
            "or undermines the multiple."
        )
    if median_yield is not None and median_yield > 1.5:
        interpretation.append(
            f"A median dividend yield of {median_yield}% says a meaningful part of the "
            "return is being paid out rather than reinvested."
        )
    if median_upside is not None:
        interpretation.append(
            f"Sell-side consensus implies a median {median_upside}% upside across the "
            "sector — an expectation, not a forecast AGI endorses."
        )

    rerating = {
        "pb": "a durable improvement in return on equity relative to the cost of equity",
        "pe": "earnings growth the market believes is repeatable, not a one-off",
        "ev_ebitda": "a step-change in cash operating profit or a fall in leverage",
        "ev_sales": "margin delivery that converts revenue into profit",
    }.get(primary, "returns improving faster than peers")

    return {
        "ok": True,
        "sector": canonical,
        "companies": len(rows),
        "industry_dna": dominant,
        "dna_note": _SECTOR_DNA_NOTE.get(canonical),
        "primary_metric": primary,
        "primary_metric_label": label,
        "supporting_metrics": [
            {"metric": m, "label": METRIC_LABELS.get(m, m)} for m in lens["supporting_metrics"]
        ],
        "avoid_metrics": [
            {"metric": m, "label": METRIC_LABELS.get(m, m)} for m in lens["suppressed_metrics"]
        ],
        "market_picture": {
            f"median_{primary}": median_primary,
            "median_pe": _median([r.get("pe") for r in rows]),
            "median_pb": _median([r.get("pb") for r in rows]),
            "median_roe": median_roe,
            "median_dividend_yield": median_yield,
            "median_consensus_upside": median_upside,
            "median_market_cap": _median([r.get("market_cap") for r in rows]),
        },
        "agi_interpretation": interpretation,
        "what_drives_rerating": rerating,
        "bottom_line": (
            f"{canonical} is valued on {label}. "
            + (f"The median sits at {median_primary}. " if median_primary is not None else "")
            + f"What moves it is {rerating}."
        ),
        "layer": {"market": "yahoo_finance + capital_iq", "interpretation": "agi"},
    }


def all_sector_intelligence() -> dict[str, Any]:
    packs = [sector_intelligence(s) for s in PRIMARY_SECTORS]
    return {"ok": True, "sectors": [p for p in packs if p.get("ok")]}


# ---------------------------------------------------------------------------
# Section 4 — Company table
# ---------------------------------------------------------------------------
_SORTABLE = {
    "company": "company_name",
    "ticker": "ticker",
    "market_cap": "market_cap",
    "price": "price",
    "pe": "pe",
    "forward_pe": "forward_pe",
    "pb": "pb",
    "ev_ebitda": "ev_ebitda",
    "ev_sales": "ev_sales",
    "roe": "roe",
    "eps": "eps",
    "book_value": "book_value",
    "dividend_yield": "dividend_yield",
    "profit_margin": "profit_margin",
    "debt_to_equity": "debt_to_equity",
}


def companies(
    *,
    q: str = "",
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    sort: str = "market_cap",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 50,
    filters: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    rows = _enriched_rows()
    query = str(q or "").strip().lower()
    filt = filters or {}

    def keep(row: dict[str, Any]) -> bool:
        if query:
            blob = f"{row.get('ticker')} {row.get('company_name')} {row.get('primary_industry')}".lower()
            if query not in blob:
                return False
        if sector and str(row.get("primary_sector") or "").lower() != sector.lower():
            return False
        if industry and industry.lower() not in str(row.get("primary_industry") or "").lower():
            return False
        for field, bound in (
            ("pe", "pe_max"),
            ("pb", "pb_max"),
            ("ev_ebitda", "ev_ebitda_max"),
        ):
            limit = _num(filt.get(bound))
            if limit is not None:
                value = _num(row.get(field))
                if value is None or value > limit:
                    return False
        for field, bound in (
            ("roe", "roe_min"),
            ("dividend_yield", "dividend_yield_min"),
        ):
            limit = _num(filt.get(bound))
            if limit is not None:
                value = _num(row.get(field))
                if value is None or value < limit:
                    return False
        mcap_min = _num(filt.get("market_cap_min"))
        if mcap_min is not None and (_num(row.get("market_cap")) or 0) < mcap_min:
            return False
        upside_min = _num(filt.get("upside_min"))
        if upside_min is not None:
            value = _num(row["consensus"].get("upside"))
            if value is None or value < upside_min:
                return False
        coverage_min = _num(filt.get("coverage_min"))
        if coverage_min is not None:
            value = _num(row["consensus"].get("coverage"))
            if value is None or value < coverage_min:
                return False
        return True

    filtered = [r for r in rows if keep(r)]
    key = _SORTABLE.get(str(sort or "market_cap").lower(), "market_cap")
    descending = str(sort_dir or "desc").lower() != "asc"

    def sort_value(row: dict[str, Any]):
        value = row.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return str(value).lower() if value else None

    with_value = [r for r in filtered if sort_value(r) is not None]
    without = [r for r in filtered if sort_value(r) is None]
    with_value.sort(key=sort_value, reverse=descending)
    ordered = with_value + without

    page = max(1, int(page or 1))
    page_size = max(1, min(200, int(page_size or 50)))
    start = (page - 1) * page_size
    chunk = ordered[start : start + page_size]

    items = []
    for row in chunk:
        dna = row.get("industry_dna")
        visible = visible_metrics_for(dna)
        item = {
            "ticker": row["ticker"],
            "company_name": row.get("company_name"),
            "primary_sector": row.get("primary_sector"),
            "primary_industry": row.get("primary_industry"),
            "industry_dna": dna,
            "visible_metrics": visible,
            "price": row.get("price"),
            "market_cap": row.get("market_cap"),
            "consensus": row["consensus"],
        }
        for metric in _SORTABLE.values():
            if metric in {"company_name", "ticker"}:
                continue
            item[metric] = row.get(metric) if is_meaningful(metric, dna) else None
        items.append(item)

    return {
        "ok": True,
        "total": len(filtered),
        "page": page,
        "page_size": page_size,
        "pages": (len(filtered) + page_size - 1) // page_size if page_size else 0,
        "sort": sort,
        "sort_dir": "desc" if descending else "asc",
        "items": items,
    }


# ---------------------------------------------------------------------------
# Company detail — peers, AGI summary
# ---------------------------------------------------------------------------
def peers(ticker: str, limit: int = 6) -> dict[str, Any]:
    tk = str(ticker or "").strip().upper()
    row = store.get(tk)
    if not row:
        return {"ok": False, "error": "not_found", "ticker": tk}
    industry = row.get("primary_industry")
    group = [
        r
        for r in _enriched_rows()
        if r.get("primary_industry") == industry and r["ticker"] != tk
    ]
    group.sort(key=lambda r: -(_num(r.get("market_cap")) or 0))
    metric = lens_for(row.get("industry_dna"))["primary_metric"]
    return {
        "ok": True,
        "ticker": tk,
        "industry": industry,
        "primary_metric": metric,
        "primary_metric_label": METRIC_LABELS.get(metric, metric),
        "peer_median": _median([r.get(metric) for r in group]),
        "company_value": row.get(metric),
        "peers": [
            {
                "ticker": p["ticker"],
                "company_name": p.get("company_name"),
                "market_cap": p.get("market_cap"),
                metric: p.get(metric),
                "roe": p.get("roe"),
                "dividend_yield": p.get("dividend_yield"),
                "consensus_upside": p["consensus"].get("upside"),
                "coverage": p["consensus"].get("coverage"),
            }
            for p in group[:limit]
        ],
    }


def company(ticker: str) -> dict[str, Any]:
    tk = str(ticker or "").strip().upper()
    row = store.get(tk)
    if not row:
        return {"ok": False, "error": "not_found", "ticker": tk}

    from valuation_terminal import overrides
    from valuation_terminal.calc import derive_company

    row = overrides.apply_to(tk, dict(row))
    consensus = _consensus(tk)
    dna = row.get("industry_dna")
    lens = lens_for(dna, row.get("primary_sector"))
    peer_pack = peers(tk)
    metric = lens["primary_metric"]
    value = _num(row.get(metric))
    peer_median = _num(peer_pack.get("peer_median"))

    all_rows = _enriched_rows()
    stats_pack = sector_statistics()
    derived = derive_company(
        row,
        consensus,
        (stats_pack["industries"].get(row.get("primary_industry")) or {}),
        _industry_population(all_rows, row.get("primary_industry")),
        metric,
    )

    # AGI valuation summary — comparison and drivers, never a call.
    parts: list[str] = []
    name = row.get("company_name") or tk
    label = lens["primary_metric_label"]
    if value is not None and peer_median:
        gap = round(((value - peer_median) / peer_median) * 100.0, 1)
        stance = "a premium to" if gap > 0 else "a discount to"
        parts.append(
            f"{name} trades at {value} on {label} against a {row.get('primary_industry')} "
            f"median of {peer_median} — {stance} the peer group of {abs(gap)}%."
        )
    elif value is not None:
        parts.append(f"{name} trades at {value} on {label}.")
    roe = _num(row.get("roe"))
    if roe is not None and metric == "pb":
        parts.append(
            f"Return on equity of {roe}% is what has to justify that multiple; book-value "
            "ratings follow the return earned on book, not the book itself."
        )
    elif roe is not None:
        parts.append(f"Return on equity is {roe}%.")
    # Recompute against the current market price rather than quoting the
    # upside CapIQ published against its own (older) close.
    live_upside = derived.get("upside_pct")
    if live_upside is not None:
        parts.append(
            f"The Capital IQ consensus target of {consensus.get('target_price')} implies "
            f"{live_upside}% against the latest price, on {consensus.get('coverage')} "
            "analysts — market expectation, not an AGI view."
        )
    score = derived.get("relative_valuation") or {}
    if score.get("band"):
        parts.append(
            f"Against its industry the market has placed it in the {score['band'].lower()} "
            f"part of the range ({score['score']}/100 on sector position, consensus and "
            "profitability) — a description of where it sits, not a call."
        )
    parts.append(
        "Watch "
        + ", ".join(
            METRIC_LABELS.get(m, m) for m in lens["supporting_metrics"][:3]
        )
        + f"; those are what move the {label} the market is willing to pay."
    )

    return {
        "ok": True,
        "ticker": tk,
        "company_name": name,
        "derived": derived,
        "relative_valuation": score,
        "field_provenance": row.get("field_provenance") or {},
        "identity": {
            "primary_sector": row.get("primary_sector"),
            "primary_industry": row.get("primary_industry"),
            "business_type": row.get("business_type"),
            "industry_dna": dna,
        },
        "market_metrics": {
            m: (row.get(m) if is_meaningful(m, dna) else None)
            for m in (
                "price",
                "market_cap",
                "pe",
                "forward_pe",
                "pb",
                "ev_ebitda",
                "ev_sales",
                "ps",
                "roe",
                "eps",
                "book_value",
                "dividend_yield",
                "profit_margin",
                "debt_to_equity",
            )
        },
        "lens": lens,
        "consensus": consensus,
        "peers": peer_pack,
        "agi_valuation_summary": " ".join(parts),
        "layer": {"market": "yahoo_finance + capital_iq", "interpretation": "agi"},
    }


# ---------------------------------------------------------------------------
# Institutional insights
# ---------------------------------------------------------------------------
def insights() -> dict[str, Any]:
    cards = sectors().get("sectors") or []
    sized = [c for c in cards if (c.get("companies") or 0) >= 5]
    out: list[str] = []
    if not sized:
        return {"ok": True, "insights": out}

    by_roe = [c for c in sized if c.get("median_roe") is not None]
    if by_roe:
        best = max(by_roe, key=lambda c: c["median_roe"])
        out.append(
            f"{best['sector']} has the highest median return on equity at "
            f"{best['median_roe']}%, on a median P/E of {best.get('median_pe')}."
        )
    by_pe = [c for c in sized if c.get("median_pe") is not None]
    if by_pe:
        cheap = min(by_pe, key=lambda c: c["median_pe"])
        rich = max(by_pe, key=lambda c: c["median_pe"])
        out.append(
            f"{cheap['sector']} is the cheapest major sector on earnings at "
            f"{cheap['median_pe']}× against {rich['sector']} at {rich['median_pe']}×."
        )
    by_yield = [c for c in sized if c.get("median_dividend_yield") is not None]
    if by_yield:
        payer = max(by_yield, key=lambda c: c["median_dividend_yield"])
        out.append(
            f"{payer['sector']} pays the most, a median {payer['median_dividend_yield']}% "
            "dividend yield, which usually signals limited reinvestment opportunity."
        )
    financials = next((c for c in sized if c["sector"] == "Financials"), None)
    if financials:
        out.append(
            "Financials are valued on price-to-book rather than EV/EBITDA — banks have no "
            "conventional enterprise value, so that metric is suppressed for them here."
        )
    by_upside = [c for c in sized if c.get("median_consensus_upside") is not None]
    if by_upside:
        top = max(by_upside, key=lambda c: c["median_consensus_upside"])
        out.append(
            f"Sell-side expectations are highest in {top['sector']}, a median "
            f"{top['median_consensus_upside']}% implied upside."
        )
    return {"ok": True, "insights": out}


def metric_explainer(metric: str) -> dict[str, Any]:
    return explain(metric)
