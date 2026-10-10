"""Thesis graph — analyst opinion → committee → CIO → portfolio → outcome."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

THESIS_NODES = [
    n("thesis_hdfcbank_quality", "HDFC Bank Quality Compounder Thesis", "thesis", ticker="HDFCBANK"),
    n("opinion_business_hdfc", "Business Analyst Opinion — HDFC Bank", "analyst_opinion", ticker="HDFCBANK"),
    n("opinion_financial_hdfc", "Financial Analyst Opinion — HDFC Bank", "analyst_opinion", ticker="HDFCBANK"),
    n("committee_hdfc", "Investment Committee Decision — HDFC Bank", "committee_decision", ticker="HDFCBANK"),
    n("cio_hdfc", "CIO View — HDFC Bank", "research_report", ticker="HDFCBANK"),
    n("portfolio_agib_core", "AGIB Core India Portfolio", "portfolio_holding"),
    n("filing_hdfc_ar", "HDFC Bank Annual Report / Filings Corpus", "filing", ticker="HDFCBANK"),
]

THESIS_EDGES = [
    e("opinion_business_hdfc", "thesis_hdfcbank_quality", "thesis_of", strength=0.8, confidence=0.9,
      note="Business desk feeds institutional thesis"),
    e("opinion_financial_hdfc", "thesis_hdfcbank_quality", "thesis_of", strength=0.8, confidence=0.9),
    e("thesis_hdfcbank_quality", "committee_hdfc", "decided_on", strength=0.85, confidence=0.92),
    e("committee_hdfc", "cio_hdfc", "drives", strength=0.88, confidence=0.93),
    e("cio_hdfc", "portfolio_agib_core", "invests_in", strength=0.7, confidence=0.86,
      note="CIO view informs portfolio suitability context — not an order"),
    e("portfolio_agib_core", "HDFCBANK", "owns", strength=0.75, confidence=0.9),
    e("filing_hdfc_ar", "thesis_hdfcbank_quality", "drives", strength=0.7, confidence=0.88,
      evidence_kind="official_filing", note="Filings evidence the thesis"),
    e("HDFCBANK", "thesis_hdfcbank_quality", "thesis_of", strength=0.9, confidence=0.95),
]
