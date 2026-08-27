"""P3.2 Investment Knowledge Graph — relationship intelligence façade."""

from __future__ import annotations

from typing import Any

ENGINE_CODE = "investment_knowledge_graph"
ENGINE_NAME = "Investment Knowledge Graph"
VERSION = "p3.2-investment-kg-v1.0.0"
PROGRAMME = "AGIB_PHASE3_CONTINUOUSLY_LEARNING_INVESTMENT_OFFICE"
WORKSTREAM_ID = "P3.2"
MILESTONE = "phase_3_2"

NODE_TYPES = (
    "Company",
    "Sector",
    "Industry",
    "Promoter",
    "Director",
    "Institution",
    "Product",
    "Country",
    "Currency",
    "Commodity",
    "Supplier",
    "Customer",
    "Technology",
    "Theme",
    "Risk",
    "MacroVariable",
    "Document",
    "Event",
)

EDGE_TYPES = (
    "BELONGS_TO",
    "COMPETES_WITH",
    "GENERATES",
    "EXPOSED_TO",
    "USES",
    "SERVES",
    "OWNS",
    "SUPPLIES",
    "AFFECTED_BY",
    "DRIVES",
    "DISCUSSES",
    "MEMBER_OF",
    "RELATED_THEME",
)

SECTOR_CHAINS: dict[str, list[str]] = {
    "banks": ["CASA", "NIM", "Credit Growth", "GNPA", "PCR", "Deposit Franchise", "ROA", "Valuation"],
    "it_services": ["Utilisation", "Deal Wins", "Pricing", "EBIT Margin", "EPS", "Valuation"],
    "cement": ["Capacity", "Utilisation", "Fuel Cost", "Realisation", "EBITDA", "Valuation"],
    "pharma": ["US Exposure", "ANDA", "Inspections", "Margins", "Valuation"],
    "power": ["PLF", "Generation Mix", "Capex", "Regulated Returns", "Valuation"],
    "auto": ["Volumes", "Mix", "Commodity Costs", "Margins", "Valuation"],
}

MACRO_CHAINS: list[dict[str, Any]] = [
    {
        "id": "repo_to_banks",
        "nodes": ["RBI Repo", "Bank NIM", "Bank ROA", "Bank Valuation"],
        "edges": ["DRIVES", "DRIVES", "DRIVES"],
    },
    {
        "id": "steel_to_auto",
        "nodes": ["Steel Prices", "Auto Margins", "Commercial Vehicles", "Tyre Demand"],
        "edges": ["AFFECTED_BY", "DRIVES", "DRIVES"],
    },
    {
        "id": "rates_broad",
        "nodes": ["Lower Interest Rates", "Banks", "NBFCs", "Real Estate", "Autos"],
        "edges": ["DRIVES", "RELATED_THEME", "RELATED_THEME", "RELATED_THEME"],
    },
]

THEME_MAP: dict[str, tuple[str, ...]] = {
    "AI": ("TCS", "INFY", "PERSISTENT", "LTIM", "HCLTECH"),
    "Defence": ("HAL", "BEL", "BEML", "MAZDOCK", "GRSE"),
    "Cement": ("ULTRACEMCO", "AMBUJACEM", "ACC", "SHREECEM", "DALBHARAT"),
    "Private Banks": ("HDFCBANK", "ICICIBANK", "AXISBANK", "KOTAKBANK"),
}
