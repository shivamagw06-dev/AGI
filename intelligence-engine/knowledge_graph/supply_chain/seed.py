"""Supply-chain graph — materials → suppliers → manufacturers → retail → consumers."""

from __future__ import annotations

from knowledge_graph.graph._edge import e, n

SUPPLY_NODES = [
    n("raw_agri", "Agricultural Inputs", "supplier", role="raw_material"),
    n("packaging", "Packaging Materials", "supplier", role="intermediate"),
    n("petchem", "Petrochemicals", "supplier", role="intermediate"),
    n("semiconductor", "Semiconductors", "technology", role="critical_input"),
    n("ai_infra", "AI Infrastructure", "technology"),
    n("tsmc", "TSMC", "supplier", aliases=["Taiwan Semiconductor"], role="foundry"),
    n("asml", "ASML", "supplier", role="equipment"),
    n("nvidia", "NVIDIA", "company", ticker="NVDA", role="accelerator"),
    n("apple", "Apple", "company", ticker="AAPL"),
    n("retail_modern", "Modern Trade Retail", "customer"),
    n("consumers_india", "Indian Consumers", "customer"),
    n("enterprise_us", "US Enterprise IT Buyers", "customer"),
]

SUPPLY_EDGES = [
    e("raw_agri", "NESTLEIND", "supplies", strength=0.75, confidence=0.88, note="Agri inputs into Nestlé India"),
    e("packaging", "NESTLEIND", "supplies", strength=0.7, confidence=0.86),
    e("packaging", "HINDUNILVR", "supplies", strength=0.72, confidence=0.87),
    e("petchem", "packaging", "supplies", strength=0.8, confidence=0.9),
    e("RELIANCE", "petchem", "produces", strength=0.85, confidence=0.92),
    e("oil", "petchem", "drives", strength=0.78, confidence=0.9),
    e("NESTLEIND", "retail_modern", "customer_of", strength=0.7, confidence=0.85),
    e("HINDUNILVR", "retail_modern", "customer_of", strength=0.75, confidence=0.88),
    e("retail_modern", "consumers_india", "customer_of", strength=0.8, confidence=0.9),
    e("asml", "tsmc", "supplies", strength=0.9, confidence=0.95, note="Lithography equipment to foundry"),
    e("tsmc", "nvidia", "supplies", strength=0.88, confidence=0.94),
    e("tsmc", "apple", "supplies", strength=0.9, confidence=0.95),
    e("nvidia", "ai_infra", "drives", strength=0.92, confidence=0.96),
    e("semiconductor", "TCS", "depends_on", strength=0.45, confidence=0.78, note="IT services demand linked to digital/AI infra"),
    e("ai_infra", "TCS", "drives", strength=0.55, confidence=0.8),
    e("enterprise_us", "TCS", "customer_of", strength=0.82, confidence=0.91),
    e("enterprise_us", "INFY", "customer_of", strength=0.8, confidence=0.9),
    e("steel", "TATAMOTORS", "supplies", strength=0.7, confidence=0.88),
    e("TATASTEEL", "steel", "produces", strength=0.9, confidence=0.95),
]
