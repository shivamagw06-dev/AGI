"""VE configuration — models, default assumptions, peers."""

from __future__ import annotations

SUPPORTED_MODELS = (
    "dcf_fcff",
    "dcf_fcfe",
    "relative_pe",
    "relative_ev_ebitda",
    "relative_ev_sales",
    "relative_pb",
    "relative_peg",
    "relative_pcf",
    "sotp",
    "ddm",
    "residual_income",
    "asset_based",
    "replacement_cost",
)

PRIMARY_MODELS = ("dcf_fcff", "relative_pe", "relative_ev_ebitda", "sotp", "ddm")

# Default institutional assumptions (overridden by structured engine inputs)
DEFAULT_ASSUMPTIONS: dict[str, float] = {
    "revenue_growth": 0.12,
    "ebit_margin": 0.22,
    "tax_rate": 0.25,
    "capex_pct_sales": 0.04,
    "nwc_pct_sales": 0.08,
    "wacc": 0.11,
    "cost_of_equity": 0.13,
    "cost_of_debt": 0.08,
    "beta": 1.0,
    "risk_free_rate": 0.07,
    "terminal_growth": 0.04,
    "dividend_payout": 0.40,
    "roe": 0.18,
    "shares_outstanding_cr": 400.0,  # crore shares (illustrative)
    "net_debt_cr": 0.0,
    "book_equity_cr": 80000.0,
    "tangible_assets_cr": 50000.0,
    "replacement_premium": 1.15,
}

DEFAULT_MARKET_PRICE = 1500.0  # INR illustrative when market price unknown

DEFAULT_PEERS: dict[str, list[str]] = {
    "INFY": ["TCS", "WIPRO", "HCLTECH"],
    "TCS": ["INFY", "WIPRO", "HCLTECH"],
    "RELIANCE": ["ONGC", "IOC", "BPCL"],
    "DEFAULT": ["PEER_A", "PEER_B", "PEER_C"],
}

# Soft peer multiples (illustrative structured defaults — not from raw docs)
PEER_MULTIPLES: dict[str, dict[str, float]] = {
    "INFY": {"pe": 24.0, "ev_ebitda": 16.0, "ev_sales": 4.5, "pb": 7.0, "roe": 0.28, "roce": 0.32, "growth": 0.12, "margin": 0.22, "leverage": 0.05, "fcf_yield": 0.04},
    "TCS": {"pe": 28.0, "ev_ebitda": 18.0, "ev_sales": 5.2, "pb": 11.0, "roe": 0.42, "roce": 0.48, "growth": 0.10, "margin": 0.25, "leverage": 0.02, "fcf_yield": 0.035},
    "WIPRO": {"pe": 20.0, "ev_ebitda": 12.0, "ev_sales": 2.8, "pb": 3.5, "roe": 0.15, "roce": 0.18, "growth": 0.08, "margin": 0.16, "leverage": 0.08, "fcf_yield": 0.045},
    "HCLTECH": {"pe": 22.0, "ev_ebitda": 14.0, "ev_sales": 3.5, "pb": 5.5, "roe": 0.22, "roce": 0.26, "growth": 0.11, "margin": 0.19, "leverage": 0.06, "fcf_yield": 0.042},
    "DEFAULT": {"pe": 18.0, "ev_ebitda": 12.0, "ev_sales": 2.5, "pb": 3.0, "roe": 0.15, "roce": 0.16, "growth": 0.10, "margin": 0.15, "leverage": 0.25, "fcf_yield": 0.04},
}

SUGGESTED_MOS = 0.25  # 25% institutional margin of safety target
HORIZON_YEARS = 5
