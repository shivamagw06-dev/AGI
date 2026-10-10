"""Indian Industry Registry — every Nifty 500 company maps to a structured industry."""

from __future__ import annotations

from typing import Any

# industry_id -> registry metadata (sector parent = KF sector key where applicable)
INDUSTRY_REGISTRY: dict[str, dict[str, Any]] = {
    "it_services": {"name": "IT Services", "sector": "it_services", "sub_industry": "IT Consulting & Other Services", "lifecycle": "mature_growth"},
    "software_products": {"name": "Software Products", "sector": "it_services", "sub_industry": "Software Products", "lifecycle": "growth"},
    "private_banks": {"name": "Private Banks", "sector": "banks", "sub_industry": "Private Sector Banks", "lifecycle": "mature"},
    "psu_banks": {"name": "PSU Banks", "sector": "banks", "sub_industry": "Public Sector Banks", "lifecycle": "mature"},
    "nbfc": {"name": "NBFC", "sector": "nbfc", "sub_industry": "Non-Banking Financial Companies", "lifecycle": "growth"},
    "life_insurance": {"name": "Life Insurance", "sector": "insurance", "sub_industry": "Life Insurance", "lifecycle": "growth"},
    "general_insurance": {"name": "General Insurance", "sector": "insurance", "sub_industry": "General / Health Insurance", "lifecycle": "growth"},
    "asset_management": {"name": "Asset Management", "sector": "capital_markets", "sub_industry": "Mutual Funds / AMC", "lifecycle": "growth"},
    "brokerages": {"name": "Brokerages", "sector": "capital_markets", "sub_industry": "Broking / Wealth", "lifecycle": "growth"},
    "capital_markets": {"name": "Capital Markets", "sector": "capital_markets", "sub_industry": "Exchanges / Market Infra", "lifecycle": "mature"},
    "retail": {"name": "Retail", "sector": "retail", "sub_industry": "Organised Retail", "lifecycle": "growth"},
    "ecommerce": {"name": "E-commerce", "sector": "consumer_internet", "sub_industry": "E-commerce / Marketplace", "lifecycle": "growth"},
    "consumer_internet": {"name": "Consumer Internet", "sector": "consumer_internet", "sub_industry": "Internet Platforms", "lifecycle": "growth"},
    "hospitals": {"name": "Hospitals", "sector": "healthcare", "sub_industry": "Hospital Services", "lifecycle": "growth"},
    "diagnostics": {"name": "Diagnostics", "sector": "healthcare", "sub_industry": "Diagnostics", "lifecycle": "growth"},
    "healthcare": {"name": "Healthcare", "sector": "healthcare", "sub_industry": "Healthcare Services", "lifecycle": "growth"},
    "api_manufacturers": {"name": "API Manufacturers", "sector": "pharma", "sub_industry": "Active Pharmaceutical Ingredients", "lifecycle": "mature"},
    "crams": {"name": "CRAMS", "sector": "pharma", "sub_industry": "Contract Research & Manufacturing", "lifecycle": "growth"},
    "generics": {"name": "Generics", "sector": "pharma", "sub_industry": "Generic Pharmaceuticals", "lifecycle": "mature"},
    "pharma": {"name": "Pharmaceuticals", "sector": "pharma", "sub_industry": "Pharmaceuticals", "lifecycle": "mature"},
    "specialty_chem": {"name": "Speciality Chemicals", "sector": "specialty_chem", "sub_industry": "Speciality Chemicals", "lifecycle": "growth"},
    "commodity_chem": {"name": "Commodity Chemicals", "sector": "specialty_chem", "sub_industry": "Commodity Chemicals", "lifecycle": "mature"},
    "cement": {"name": "Cement", "sector": "cement", "sub_industry": "Cement", "lifecycle": "mature"},
    "steel": {"name": "Steel", "sector": "metals", "sub_industry": "Steel", "lifecycle": "mature"},
    "aluminium": {"name": "Aluminium", "sector": "metals", "sub_industry": "Aluminium", "lifecycle": "mature"},
    "copper": {"name": "Copper", "sector": "metals", "sub_industry": "Copper", "lifecycle": "mature"},
    "metals": {"name": "Metals & Mining", "sector": "metals", "sub_industry": "Metals", "lifecycle": "mature"},
    "power_generation": {"name": "Power Generation", "sector": "utilities", "sub_industry": "Power Generation", "lifecycle": "mature"},
    "power_transmission": {"name": "Power Transmission", "sector": "utilities", "sub_industry": "Power Transmission", "lifecycle": "mature"},
    "power_distribution": {"name": "Power Distribution", "sector": "utilities", "sub_industry": "Power Distribution", "lifecycle": "mature"},
    "renewables": {"name": "Renewables", "sector": "utilities", "sub_industry": "Renewable Energy", "lifecycle": "growth"},
    "utilities": {"name": "Utilities", "sector": "utilities", "sub_industry": "Utilities", "lifecycle": "mature"},
    "oil_marketing": {"name": "Oil Marketing", "sector": "energy", "sub_industry": "Oil Marketing Companies", "lifecycle": "mature"},
    "refining": {"name": "Refining", "sector": "energy", "sub_industry": "Refining", "lifecycle": "mature"},
    "gas_distribution": {"name": "Gas Distribution", "sector": "energy", "sub_industry": "City Gas Distribution", "lifecycle": "growth"},
    "energy": {"name": "Energy", "sector": "energy", "sub_industry": "Energy", "lifecycle": "mature"},
    "energy_conglomerate": {"name": "Energy Conglomerate", "sector": "energy_conglomerate", "sub_industry": "Diversified Energy", "lifecycle": "mature"},
    "mining": {"name": "Mining", "sector": "metals", "sub_industry": "Mining", "lifecycle": "mature"},
    "defence": {"name": "Defence", "sector": "industrials", "sub_industry": "Defence", "lifecycle": "growth"},
    "railways": {"name": "Railways", "sector": "industrials", "sub_industry": "Railways / Rail Infra", "lifecycle": "growth"},
    "logistics": {"name": "Logistics", "sector": "logistics", "sub_industry": "Logistics", "lifecycle": "growth"},
    "ports": {"name": "Ports", "sector": "infrastructure", "sub_industry": "Ports", "lifecycle": "mature"},
    "airlines": {"name": "Airlines", "sector": "aviation", "sub_industry": "Airlines", "lifecycle": "mature"},
    "aviation": {"name": "Aviation", "sector": "aviation", "sub_industry": "Aviation", "lifecycle": "mature"},
    "hotels": {"name": "Hotels", "sector": "consumer", "sub_industry": "Hotels / Hospitality", "lifecycle": "mature"},
    "telecom": {"name": "Telecom", "sector": "telecom", "sub_industry": "Telecom Services", "lifecycle": "mature"},
    "media": {"name": "Media", "sector": "consumer", "sub_industry": "Media", "lifecycle": "mature"},
    "education": {"name": "Education", "sector": "consumer", "sub_industry": "Education", "lifecycle": "growth"},
    "real_estate": {"name": "Real Estate", "sector": "real_estate", "sub_industry": "Real Estate Development", "lifecycle": "mature"},
    "construction": {"name": "Construction", "sector": "infrastructure", "sub_industry": "Construction", "lifecycle": "mature"},
    "infrastructure": {"name": "Infrastructure", "sector": "infrastructure", "sub_industry": "Infrastructure", "lifecycle": "mature"},
    "capital_goods": {"name": "Capital Goods", "sector": "industrials", "sub_industry": "Capital Goods", "lifecycle": "mature"},
    "industrial_machinery": {"name": "Industrial Machinery", "sector": "industrials", "sub_industry": "Industrial Machinery", "lifecycle": "mature"},
    "industrials": {"name": "Industrials", "sector": "industrials", "sub_industry": "Industrials", "lifecycle": "mature"},
    "auto": {"name": "Auto", "sector": "auto", "sub_industry": "Automobiles", "lifecycle": "mature"},
    "passenger_vehicles": {"name": "Passenger Vehicles", "sector": "auto", "sub_industry": "Passenger Vehicles", "lifecycle": "mature"},
    "commercial_vehicles": {"name": "Commercial Vehicles", "sector": "auto", "sub_industry": "Commercial Vehicles", "lifecycle": "mature"},
    "tyres": {"name": "Tyres", "sector": "auto", "sub_industry": "Tyres", "lifecycle": "mature"},
    "bearings": {"name": "Bearings", "sector": "auto", "sub_industry": "Bearings", "lifecycle": "mature"},
    "auto_components": {"name": "Auto Components", "sector": "auto", "sub_industry": "Auto Components", "lifecycle": "mature"},
    "ev_ecosystem": {"name": "EV Ecosystem", "sector": "auto", "sub_industry": "Electric Vehicles / Ecosystem", "lifecycle": "growth"},
    "textiles": {"name": "Textiles", "sector": "consumer", "sub_industry": "Textiles", "lifecycle": "mature"},
    "paper": {"name": "Paper", "sector": "consumer", "sub_industry": "Paper", "lifecycle": "mature"},
    "packaging": {"name": "Packaging", "sector": "consumer", "sub_industry": "Packaging", "lifecycle": "mature"},
    "fmcg": {"name": "FMCG", "sector": "fmcg", "sub_industry": "Fast Moving Consumer Goods", "lifecycle": "mature"},
    "consumer_durables": {"name": "Consumer Durables", "sector": "consumer_durables", "sub_industry": "Consumer Durables", "lifecycle": "growth"},
    "consumer": {"name": "Consumer Discretionary", "sector": "consumer", "sub_industry": "Consumer", "lifecycle": "mature"},
    "qsr": {"name": "Quick Service Restaurants", "sector": "consumer", "sub_industry": "QSR", "lifecycle": "growth"},
    "agriculture": {"name": "Agriculture", "sector": "fmcg", "sub_industry": "Agriculture", "lifecycle": "mature"},
    "seeds": {"name": "Seeds", "sector": "fmcg", "sub_industry": "Seeds", "lifecycle": "mature"},
    "fertilizers": {"name": "Fertilizers", "sector": "specialty_chem", "sub_industry": "Fertilizers", "lifecycle": "mature"},
    "sugar": {"name": "Sugar", "sector": "fmcg", "sub_industry": "Sugar", "lifecycle": "mature"},
    "distilleries": {"name": "Distilleries", "sector": "fmcg", "sub_industry": "Distilleries / Spirits", "lifecycle": "mature"},
    "conglomerate": {"name": "Conglomerate", "sector": "conglomerate", "sub_industry": "Conglomerate", "lifecycle": "mature"},
    "diversified": {"name": "Diversified", "sector": "diversified", "sub_industry": "Diversified", "lifecycle": "mature"},
}

# Explicit ticker overrides for finer industry assignment
_TICKER_INDUSTRY: dict[str, str] = {
    # Private banks
    "HDFCBANK": "private_banks", "ICICIBANK": "private_banks", "AXISBANK": "private_banks",
    "KOTAKBANK": "private_banks", "INDUSINDBK": "private_banks", "YESBANK": "private_banks",
    "FEDERALBNK": "private_banks", "IDFCFIRSTB": "private_banks", "BANDHANBNK": "private_banks",
    "AUBANK": "private_banks", "RBLBANK": "private_banks", "KARURVYSYA": "private_banks",
    "CUB": "private_banks", "J&KBANK": "private_banks", "UJJIVANSFB": "private_banks",
    "EQUITASBNK": "private_banks", "SURYODAY": "private_banks", "ESAF": "private_banks",
    # PSU banks
    "SBIN": "psu_banks", "BANKBARODA": "psu_banks", "CANBK": "psu_banks", "PNB": "psu_banks",
    "UNIONBANK": "psu_banks", "INDIANB": "psu_banks", "BANKINDIA": "psu_banks",
    "MAHABANK": "psu_banks", "IOB": "psu_banks", "UCOBANK": "psu_banks",
    "CENTRALBK": "psu_banks", "SOUTHBANK": "psu_banks",
    # Insurance
    "SBILIFE": "life_insurance", "HDFCLIFE": "life_insurance", "ICICIPRULI": "life_insurance",
    "MFSL": "life_insurance", "STARHEALTH": "general_insurance",
    "ICICIGI": "general_insurance", "GICRE": "general_insurance", "NIACL": "general_insurance",
    # Metals
    "TATASTEEL": "steel", "JSWSTEEL": "steel", "SAIL": "steel", "JINDALSTEL": "steel",
    "HINDALCO": "aluminium", "NATIONALUM": "aluminium", "VEDL": "metals",
    "HINDCOPPER": "copper", "COALINDIA": "mining",
    # Power / utilities
    "NTPC": "power_generation", "POWERGRID": "power_transmission",
    "ADANIGREEN": "renewables", "ADANIENSOL": "renewables", "TATAPOWER": "power_generation",
    # Energy
    "BPCL": "oil_marketing", "IOC": "oil_marketing", "HPCL": "oil_marketing",
    "RELIANCE": "energy_conglomerate", "ONGC": "energy", "GAIL": "gas_distribution",
    # Auto
    "MARUTI": "passenger_vehicles", "M&M": "passenger_vehicles", "TATAMOTORS": "commercial_vehicles",
    "BAJAJ-AUTO": "passenger_vehicles", "EICHERMOT": "passenger_vehicles", "HEROMOTOCO": "passenger_vehicles",
    "APOLLOTYRE": "tyres", "MRF": "tyres", "BALKRISIND": "tyres",
    # Healthcare / pharma
    "APOLLOHOSP": "hospitals", "MAXHEALTH": "hospitals", "FORTIS": "hospitals",
    "SUNPHARMA": "generics", "CIPLA": "generics", "DRREDDY": "generics",
    "DIVISLAB": "api_manufacturers", "LAURUSLABS": "api_manufacturers",
    # Cement
    "ULTRACEMCO": "cement", "AMBUJACEM": "cement", "SHREECEM": "cement", "ACC": "cement",
    # Telecom / retail / internet
    "BHARTIARTL": "telecom", "IDEA": "telecom",
    "DMART": "retail", "TRENT": "retail",
    "ZOMATO": "ecommerce", "NAUKRI": "consumer_internet",
    # Infra / logistics / aviation
    "ADANIPORTS": "ports", "INDIGO": "airlines",
    "CONCOR": "logistics", "DELHIVERY": "logistics",
    # IT
    "INFY": "it_services", "TCS": "it_services", "HCLTECH": "it_services",
    "WIPRO": "it_services", "TECHM": "it_services", "PERSISTENT": "it_services",
    # FMCG
    "HINDUNILVR": "fmcg", "ITC": "fmcg", "NESTLEIND": "fmcg", "BRITANNIA": "fmcg",
    "TATACONSUM": "fmcg", "GODREJCP": "fmcg",
    # Real estate
    "DLF": "real_estate", "GODREJPROP": "real_estate",
    # Industrials
    "LT": "construction", "SIEMENS": "capital_goods", "ABB": "capital_goods", "BEL": "defence",
}

# Sector fallback when no ticker override
_SECTOR_DEFAULT_INDUSTRY: dict[str, str] = {
    "it_services": "it_services",
    "banks": "private_banks",  # overridden for PSUs via ticker map
    "nbfc": "nbfc",
    "insurance": "life_insurance",
    "fmcg": "fmcg",
    "auto": "auto",
    "pharma": "pharma",
    "cement": "cement",
    "metals": "metals",
    "utilities": "utilities",
    "energy": "energy",
    "energy_conglomerate": "energy_conglomerate",
    "telecom": "telecom",
    "retail": "retail",
    "consumer_internet": "consumer_internet",
    "healthcare": "healthcare",
    "specialty_chem": "specialty_chem",
    "industrials": "industrials",
    "infrastructure": "infrastructure",
    "real_estate": "real_estate",
    "logistics": "logistics",
    "aviation": "aviation",
    "consumer": "consumer",
    "consumer_durables": "consumer_durables",
    "capital_markets": "capital_markets",
    "conglomerate": "conglomerate",
    "diversified": "diversified",
}


def list_industries() -> list[dict[str, Any]]:
    out = []
    for iid, meta in sorted(INDUSTRY_REGISTRY.items()):
        out.append({"industry_id": iid, **meta, "fabricated": False})
    return out


def build_company_industry_map() -> dict[str, str]:
    """Map every Nifty 500 ticker → industry_id (complete coverage)."""
    from knowledge_factory.nifty500_universe import NIFTY_500_MEMBERS

    mapping: dict[str, str] = {}
    for m in NIFTY_500_MEMBERS:
        t = str(m["ticker"]).upper()
        if t in _TICKER_INDUSTRY:
            mapping[t] = _TICKER_INDUSTRY[t]
        else:
            sector = str(m.get("sector") or "")
            mapping[t] = _SECTOR_DEFAULT_INDUSTRY.get(sector, sector if sector in INDUSTRY_REGISTRY else "diversified")
        # Ensure industry exists
        if mapping[t] not in INDUSTRY_REGISTRY:
            mapping[t] = "diversified"
    return mapping
