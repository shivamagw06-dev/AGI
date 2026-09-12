"""Frozen golden questions v1 — identical questions every release. IMMUTABLE."""

from __future__ import annotations

from academy.regression.schema import GoldenQuestion

GOLDEN_QUESTIONS: list[GoldenQuestion] = [
    # Business
    GoldenQuestion("gq_biz_hdfc_great", "business", "business", "Is HDFC Bank a great business?", "HDFC Bank", "HDFCBANK", ["business"]),
    GoldenQuestion("gq_biz_nestle_premium", "business", "business", "Why does Nestlé deserve premium valuation?", "Nestlé India", "NESTLEIND", ["business", "valuation_bridge"]),
    GoldenQuestion("gq_biz_nokia_moat", "business", "business", "Why did Nokia lose its moat?", "Nokia", "NOKIA", ["business", "failure"]),
    GoldenQuestion("gq_biz_amzn_costco", "business", "business", "Compare Amazon vs Costco.", "Amazon", "AMZN", ["business", "case_transfer"]),
    # Financial
    GoldenQuestion("gq_fin_tcs_cash", "financial", "financial", "Does TCS convert accounting earnings into cash?", "TCS", "TCS", ["financial"]),
    GoldenQuestion("gq_fin_ultratech_ev", "financial", "financial", "Is UltraTech creating economic value?", "UltraTech", "ULTRACEMCO", ["financial"]),
    GoldenQuestion("gq_fin_apple_roic", "financial", "financial", "Why has Apple maintained high ROIC?", "Apple", "AAPL", ["financial"]),
    # Valuation
    GoldenQuestion("gq_val_apple_premium", "valuation", "valuation", "Why does Apple deserve a premium multiple?", "Apple", "AAPL", ["valuation"]),
    GoldenQuestion("gq_val_nvidia_exp", "valuation", "valuation", "Explain Nvidia valuation expectations.", "Nvidia", "NVDA", ["valuation"]),
    GoldenQuestion("gq_val_asian_growth", "valuation", "valuation", "What growth is embedded in Asian Paints?", "Asian Paints", "ASIANPAINT", ["valuation"]),
    # Risk
    GoldenQuestion("gq_risk_eternal", "risk", "risk", "What breaks Eternal's thesis?", "Eternal", "ETERNAL", ["risk"]),
    # Management
    GoldenQuestion("gq_mgmt_brk", "management", "management", "Evaluate Berkshire capital allocation.", "Berkshire", "BRK.B", ["management"]),
    # Macro
    GoldenQuestion("gq_macro_hdfc_rates", "macro", "macro", "How do higher interest rates affect HDFC Bank?", "HDFC Bank", "HDFCBANK", ["macro"]),
    # Sector
    GoldenQuestion("gq_sec_indian_it", "sector", "sector", "Is Indian IT becoming structurally stronger?", None, None, ["sector", "it"]),
    # Portfolio
    GoldenQuestion(
        "gq_port_diversified",
        "portfolio",
        "portfolio",
        "Should this company improve a diversified Indian equity portfolio?",
        "HDFC Bank",
        "HDFCBANK",
        ["portfolio"],
    ),
    # Retention / case transfer extras (same every release)
    GoldenQuestion("gq_ret_roic", "financial", "financial", "How should I interpret high ROIC?", None, None, ["retention", "synthesis"]),
    GoldenQuestion("gq_xfer_nokia_bb", "business", "business", "Transfer Nokia lessons to BlackBerry. Similarities, differences, lessons.", "Nokia", "NOKIA", ["case_transfer"]),
    GoldenQuestion("gq_xfer_nestle_hul", "business", "business", "Transfer Nestlé lessons to HUL. Similarities, differences, lessons.", "Nestlé India", "NESTLEIND", ["case_transfer"]),
    GoldenQuestion("gq_xfer_amzn_meli", "business", "business", "Transfer Amazon lessons to MercadoLibre. Similarities, differences, lessons.", "Amazon", "AMZN", ["case_transfer"]),
    GoldenQuestion("gq_xfer_wirecard", "risk", "risk", "Transfer Wirecard lessons to other accounting failures.", "Wirecard", "WIRECARD", ["case_transfer", "failure"]),
]
