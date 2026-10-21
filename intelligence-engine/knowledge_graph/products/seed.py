"""Product / segment graph."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

PRODUCT_NODES = [
    n("prod_hdfc_loans", "HDFC Bank Loans / Retail Credit", "product"),
    n("prod_hdfc_deposits", "HDFC Bank Deposits / CASA", "product"),
    n("prod_tcs_bfs", "TCS Banking & Financial Services", "product"),
    n("prod_tcs_cloud", "TCS Cloud & AI Services", "product"),
    n("prod_nestle_maggi", "Maggi", "brand"),
    n("prod_nestle_dairy", "Nestlé Dairy & Nutrition", "product"),
    n("region_india", "India Region", "country"),
    n("region_us", "United States Region", "country"),
]

PRODUCT_EDGES = [
    e("HDFCBANK", "prod_hdfc_loans", "produces", strength=0.9, confidence=0.95),
    e("HDFCBANK", "prod_hdfc_deposits", "produces", strength=0.9, confidence=0.95),
    e("TCS", "prod_tcs_bfs", "produces", strength=0.85, confidence=0.93),
    e("TCS", "prod_tcs_cloud", "produces", strength=0.8, confidence=0.9),
    e("NESTLEIND", "prod_nestle_maggi", "produces", strength=0.9, confidence=0.95),
    e("NESTLEIND", "prod_nestle_dairy", "produces", strength=0.85, confidence=0.92),
    e("prod_nestle_maggi", "consumers_india", "customer_of", strength=0.8, confidence=0.9),
    e("prod_tcs_bfs", "enterprise_us", "customer_of", strength=0.7, confidence=0.86),
    e("prod_tcs_cloud", "ai_infra", "depends_on", strength=0.6, confidence=0.82),
    e("NESTLEIND", "region_india", "exports_to", strength=0.5, confidence=0.75, note="Domestic-heavy franchise"),
    e("TCS", "region_us", "exports_to", strength=0.85, confidence=0.93),
]
