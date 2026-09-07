"""Sector lens — which valuation metrics are meaningful, and why.

A bank has no meaningful EV/EBITDA and an asset-light software firm has no
meaningful price-to-book. The terminal must never print a number that the
industry itself does not use, so metric visibility is driven by the canonical
Industry DNA rather than by whatever the data vendor happened to return.
"""

from __future__ import annotations

from typing import Any

# Metric keys the terminal can display.
ALL_METRICS: tuple[str, ...] = (
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
    "market_cap",
    "price",
)

METRIC_LABELS: dict[str, str] = {
    "pe": "P/E",
    "forward_pe": "Forward P/E",
    "pb": "P/B",
    "ev_ebitda": "EV/EBITDA",
    "ev_sales": "EV/Sales",
    "ps": "P/S",
    "roe": "ROE %",
    "eps": "EPS",
    "book_value": "Book Value",
    "dividend_yield": "Dividend Yield %",
    "profit_margin": "Profit Margin %",
    "debt_to_equity": "Debt / Equity",
    "market_cap": "Market Cap",
    "price": "Price",
}

# Industry DNA → (primary metric, supporting metrics, suppressed metrics)
# Baseline only — Valuation Policy & Applicability Engine (VPAE) may override
# by instrument type, profitability, coverage and DQIV before any consumer
# displays a multiple.
_LENS: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]] = {
    "banks": ("pb", ("roe", "roa", "pe", "dividend_yield", "eps", "book_value"), ("ev_ebitda", "ev_sales", "ps")),
    "nbfc": ("pb", ("roe", "pe", "dividend_yield", "book_value"), ("ev_ebitda", "ev_sales", "ps")),
    "asset_management": ("pe", ("roe", "dividend_yield", "profit_margin"), ("ev_ebitda", "ev_sales")),
    "insurance": ("pb", ("roe", "pe", "dividend_yield"), ("ev_ebitda", "ev_sales", "ps")),
    "oil_gas": ("ev_ebitda", ("pe", "pb", "dividend_yield", "debt_to_equity"), ()),
    "mining": ("ev_ebitda", ("pe", "pb", "dividend_yield"), ()),
    "metals": ("ev_ebitda", ("pe", "pb", "debt_to_equity", "dividend_yield"), ()),
    "cement": ("ev_ebitda", ("pe", "pb", "profit_margin"), ()),
    "chemicals": ("ev_ebitda", ("pe", "roe", "profit_margin"), ()),
    "it_services": ("pe", ("ev_ebitda", "roe", "roce", "dividend_yield", "profit_margin"), ("pb",)),
    "software": ("ev_sales", ("pe", "profit_margin", "ps"), ("pb",)),
    "internet_platforms": ("ev_sales", ("ps", "profit_margin", "pe"), ("pb",)),
    "telecom": ("ev_ebitda", ("ev_sales", "ps", "debt_to_equity"), ("pb",)),
    "media": ("ev_ebitda", ("pe", "ps", "profit_margin"), ()),
    "hospitals": ("ev_ebitda", ("pe", "roe", "profit_margin"), ()),
    "pharma": ("pe", ("ev_ebitda", "roe", "profit_margin"), ()),
    "diagnostics": ("ev_ebitda", ("pe", "roe", "profit_margin"), ()),
    "airlines": ("ev_ebitda", ("ev_sales", "ps", "debt_to_equity"), ("pb", "pe")),
    "logistics": ("ev_ebitda", ("pe", "roe", "profit_margin"), ()),
    "shipping": ("ev_ebitda", ("pb", "pe", "dividend_yield"), ()),
    "infrastructure": ("ev_ebitda", ("pe", "pb", "debt_to_equity"), ()),
    "capital_goods": ("ev_ebitda", ("pe", "roe", "roce", "profit_margin"), ()),
    "automobile": ("pe", ("ev_ebitda", "roe", "profit_margin"), ()),
    "auto_components": ("pe", ("ev_ebitda", "roe", "profit_margin"), ()),
    "consumer_durables": ("pe", ("ev_ebitda", "roe", "profit_margin"), ()),
    "retail": ("pe", ("ev_ebitda", "ev_sales", "ps", "profit_margin"), ()),
    "qsr": ("ev_ebitda", ("ps", "pe"), ("pb",)),
    "fmcg": ("pe", ("ev_ebitda", "roe", "roce", "dividend_yield", "profit_margin"), ()),
    "hotels": ("ev_ebitda", ("pe", "ps"), ()),
    "power": ("ev_ebitda", ("pb", "pe", "dividend_yield", "debt_to_equity"), ()),
    "utilities": ("ev_ebitda", ("pb", "pe", "dividend_yield", "debt_to_equity"), ()),
    "renewables": ("ev_ebitda", ("pb", "debt_to_equity"), ()),
    "real_estate": ("pb", ("pe", "ps", "debt_to_equity"), ("ev_ebitda",)),
    "reit": ("pb", ("dividend_yield", "roe"), ("pe", "ev_ebitda", "ev_sales")),
    "invit": ("pb", ("dividend_yield",), ("pe", "ev_ebitda", "ev_sales")),
    "etf": ("price", ("market_cap",), ("pe", "pb", "ev_ebitda", "ev_sales", "ps", "roe", "roa", "roce")),
    "education": ("pe", ("ev_ebitda", "profit_margin"), ()),
    "agriculture": ("pe", ("ev_ebitda", "pb"), ()),
    "data_centers": ("ev_ebitda", ("ps", "debt_to_equity"), ()),
}

_DEFAULT = ("pe", ("pb", "ev_ebitda", "roe", "dividend_yield"), ())

# Why each primary metric is the right lens.
_RATIONALE: dict[str, str] = {
    "pb": (
        "Value is created by deploying a balance sheet rather than manufacturing "
        "assets, so the multiple attaches to book equity and is justified by the "
        "return earned on it."
    ),
    "pe": (
        "Earnings are the cleanest recurring output of the business, so the market "
        "pays a multiple of profit rather than of assets or revenue."
    ),
    "ev_ebitda": (
        "Capital structure and depreciation policy differ widely across these "
        "companies, so enterprise value against cash operating profit compares "
        "them on the same footing."
    ),
    "ev_sales": (
        "Profit is still being reinvested into growth, so revenue is the more "
        "stable denominator until margins mature."
    ),
}


def lens_for(industry_dna: str | None, primary_sector: str | None = None) -> dict[str, Any]:
    """Metric visibility and rationale for one industry."""
    dna = str(industry_dna or "").strip()
    primary, supporting, suppressed = _LENS.get(dna, _DEFAULT)
    visible = [primary, *[m for m in supporting if m != primary]]
    return {
        "industry_dna": dna or None,
        "primary_sector": primary_sector,
        "primary_metric": primary,
        "primary_metric_label": METRIC_LABELS.get(primary, primary),
        "supporting_metrics": list(supporting),
        "suppressed_metrics": list(suppressed),
        "visible_metrics": visible,
        "rationale": _RATIONALE.get(primary, _RATIONALE["pe"]),
    }


def is_meaningful(metric: str, industry_dna: str | None) -> bool:
    """False when the metric is not used for this industry."""
    _p, _s, suppressed = _LENS.get(str(industry_dna or "").strip(), _DEFAULT)
    return metric not in suppressed


def visible_metrics_for(industry_dna: str | None) -> list[str]:
    return list(lens_for(industry_dna)["visible_metrics"])


# ---------------------------------------------------------------------------
# Metric pedagogy — "explain every metric"
# ---------------------------------------------------------------------------
METRIC_EXPLAINERS: dict[str, dict[str, str]] = {
    "pb": {
        "what": "Price-to-book compares market value with the accounting equity on the balance sheet.",
        "why": "It anchors valuation to capital actually invested, which matters when the balance sheet is the business.",
        "where": "Banks, NBFCs, insurers and real estate.",
        "interpret": "Read it with return on equity: a bank earning 16% deserves a higher multiple of book than one earning 11%. Below 1× implies the market expects returns under the cost of equity.",
    },
    "pe": {
        "what": "Price-to-earnings is the market value of one rupee of trailing profit.",
        "why": "Earnings are the recurring output most businesses are bought for.",
        "where": "FMCG, pharma, IT services, capital goods, autos.",
        "interpret": "High is not expensive by itself — it must be paid for by growth and returns. Compare with the company's own history and its peers, and check whether earnings are depressed.",
    },
    "forward_pe": {
        "what": "Forward P/E uses consensus earnings for the coming year instead of the trailing year.",
        "why": "It shows what the market is paying on expected rather than reported profit.",
        "where": "Any company with meaningful analyst coverage.",
        "interpret": "A wide gap between trailing and forward P/E signals expected earnings recovery — or that trailing profit was depressed.",
    },
    "ev_ebitda": {
        "what": "Enterprise value against cash operating profit before depreciation.",
        "why": "It neutralises differences in leverage and depreciation policy.",
        "where": "Energy, metals, cement, telecom, utilities, hospitals, infrastructure.",
        "interpret": "Best for capital-heavy businesses. Meaningless for banks and insurers, which have no conventional enterprise value.",
    },
    "ev_sales": {
        "what": "Enterprise value against revenue.",
        "why": "Revenue is the stable denominator while margins are still developing.",
        "where": "Software, internet platforms, early-stage growth.",
        "interpret": "Only comparable between businesses with similar margin potential; a 30% margin business cannot be compared with a 5% margin one.",
    },
    "roe": {
        "what": "Return on equity is profit as a percentage of shareholders' funds.",
        "why": "It is the engine behind book-value multiples and compounding.",
        "where": "Every sector, decisively for financials.",
        "interpret": "Sustained ROE above the cost of equity creates value. Check whether it is driven by genuine profitability or by leverage.",
    },
    "dividend_yield": {
        "what": "Dividend per share as a percentage of price.",
        "why": "It shows how much of the return is being paid out rather than reinvested.",
        "where": "Utilities, PSUs, energy, mature staples.",
        "interpret": "A very high yield often signals the market doubts the payout is sustainable, not that the stock is cheap.",
    },
    "ps": {
        "what": "Price-to-sales compares market value with revenue.",
        "why": "It is usable when earnings are negative or distorted.",
        "where": "Growth companies and turnarounds.",
        "interpret": "Ignores profitability entirely, so use only alongside a margin figure.",
    },
    "profit_margin": {
        "what": "Net profit as a percentage of revenue.",
        "why": "It shows how much of each rupee of sales survives to the bottom line.",
        "where": "All sectors, compared within an industry.",
        "interpret": "Compare only against the same industry — an 8% margin is strong in retail and weak in software.",
    },
    "debt_to_equity": {
        "what": "Borrowings relative to shareholders' funds.",
        "why": "Leverage amplifies both returns and risk.",
        "where": "Capital-heavy sectors; not meaningful for banks, where debt is raw material.",
        "interpret": "Read with interest coverage and the stability of cash flows, not in isolation.",
    },
    "eps": {
        "what": "Earnings per share.",
        "why": "It is the per-share profit the P/E multiple is applied to.",
        "where": "All sectors.",
        "interpret": "Watch for share count changes; EPS can grow through buybacks without the business improving.",
    },
    "book_value": {
        "what": "Shareholders' funds per share.",
        "why": "It is the denominator of price-to-book.",
        "where": "Financials and asset-heavy businesses.",
        "interpret": "Only as good as the assets behind it — book value in a bank depends on honest provisioning.",
    },
}


def explain(metric: str) -> dict[str, Any]:
    body = METRIC_EXPLAINERS.get(metric)
    if not body:
        return {"ok": False, "metric": metric, "error": "no_explainer"}
    return {"ok": True, "metric": metric, "label": METRIC_LABELS.get(metric, metric), **body}
