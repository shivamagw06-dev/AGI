"""Governed G20 macro source catalogue.

This is a collection plan, not evidence. A catalogue row becomes observed only
when a persisted warehouse observation is mapped to it.
"""

from __future__ import annotations

from typing import Any


MODULES: dict[str, dict[str, Any]] = {
    "central_bank": {"label": "Central Bank", "indicators": ["policy rate", "policy corridor", "balance sheet", "reserves", "operations", "forward guidance"], "frequency": "event/weekly"},
    "fiscal": {"label": "Fiscal", "indicators": ["fiscal balance", "primary balance", "revenue", "expenditure", "government debt", "issuance", "interest expense"], "frequency": "monthly/quarterly"},
    "inflation": {"label": "Inflation", "indicators": ["headline CPI", "core CPI", "producer prices", "food", "energy", "services", "wages", "expectations"], "frequency": "monthly"},
    "growth": {"label": "Growth", "indicators": ["real GDP", "nominal GDP", "consumption", "investment", "industrial production", "retail sales", "business surveys"], "frequency": "monthly/quarterly"},
    "rates": {"label": "Rates & Curve", "indicators": ["1M yield", "3M yield", "1Y yield", "2Y yield", "5Y yield", "10Y yield", "30Y yield", "real yield"], "frequency": "daily"},
    "liquidity": {"label": "Liquidity", "indicators": ["central-bank assets", "bank reserves", "repo operations", "money supply", "funding spreads", "global liquidity"], "frequency": "daily/monthly"},
    "credit": {"label": "Credit", "indicators": ["bank credit", "household credit", "corporate credit", "government credit", "external credit", "NPL ratio", "debt-service ratio"], "frequency": "monthly/quarterly"},
    "fx_external": {"label": "FX & External", "indicators": ["spot FX", "forward FX", "FX reserves", "REER", "NEER", "current account", "balance of payments", "capital flows"], "frequency": "daily/monthly"},
    "commodities": {"label": "Commodities", "indicators": ["energy", "industrial metals", "precious metals", "agriculture", "inventories", "supply and demand"], "frequency": "daily/monthly"},
}


COUNTRY_SOURCES: dict[str, dict[str, str]] = {
    "ARG": {"country": "Argentina", "central_bank": "BCRA", "statistics": "INDEC", "fiscal": "Ministry of Economy"},
    "AUS": {"country": "Australia", "central_bank": "Reserve Bank of Australia", "statistics": "Australian Bureau of Statistics", "fiscal": "Australian Treasury"},
    "BRA": {"country": "Brazil", "central_bank": "Banco Central do Brasil", "statistics": "IBGE", "fiscal": "Ministry of Finance"},
    "CAN": {"country": "Canada", "central_bank": "Bank of Canada", "statistics": "Statistics Canada", "fiscal": "Finance Canada"},
    "CHN": {"country": "China", "central_bank": "People's Bank of China", "statistics": "National Bureau of Statistics", "fiscal": "Ministry of Finance"},
    "FRA": {"country": "France", "central_bank": "Banque de France / ECB", "statistics": "INSEE / Eurostat", "fiscal": "Ministry of Economy and Finance"},
    "DEU": {"country": "Germany", "central_bank": "Bundesbank / ECB", "statistics": "Destatis / Eurostat", "fiscal": "Federal Ministry of Finance"},
    "IND": {"country": "India", "central_bank": "RBI", "statistics": "MoSPI / NSO", "fiscal": "Ministry of Finance"},
    "IDN": {"country": "Indonesia", "central_bank": "Bank Indonesia", "statistics": "BPS", "fiscal": "Ministry of Finance"},
    "ITA": {"country": "Italy", "central_bank": "Bank of Italy / ECB", "statistics": "Istat / Eurostat", "fiscal": "Ministry of Economy and Finance"},
    "JPN": {"country": "Japan", "central_bank": "Bank of Japan", "statistics": "Statistics Bureau / Cabinet Office", "fiscal": "Ministry of Finance"},
    "MEX": {"country": "Mexico", "central_bank": "Banxico", "statistics": "INEGI", "fiscal": "SHCP"},
    "RUS": {"country": "Russia", "central_bank": "Bank of Russia", "statistics": "Rosstat", "fiscal": "Ministry of Finance"},
    "SAU": {"country": "Saudi Arabia", "central_bank": "SAMA", "statistics": "GASTAT", "fiscal": "Ministry of Finance"},
    "ZAF": {"country": "South Africa", "central_bank": "SARB", "statistics": "Statistics South Africa", "fiscal": "National Treasury"},
    "KOR": {"country": "South Korea", "central_bank": "Bank of Korea", "statistics": "KOSTAT", "fiscal": "Ministry of Economy and Finance"},
    "TUR": {"country": "Turkiye", "central_bank": "CBRT", "statistics": "TURKSTAT", "fiscal": "Ministry of Treasury and Finance"},
    "GBR": {"country": "United Kingdom", "central_bank": "Bank of England", "statistics": "Office for National Statistics", "fiscal": "HM Treasury"},
    "USA": {"country": "United States", "central_bank": "Federal Reserve", "statistics": "BEA / BLS / Census", "fiscal": "US Treasury"},
}


def _primary_source(country: dict[str, str], module: str) -> str:
    if module in {"central_bank", "rates", "liquidity", "credit", "fx_external"}:
        return country["central_bank"]
    if module == "fiscal":
        return country["fiscal"]
    if module == "commodities":
        return "Official national agency / market feed"
    return country["statistics"]


def _validation_sources(module: str) -> list[str]:
    if module in {"liquidity", "credit", "rates", "fx_external"}:
        return ["BIS", "IMF", "OECD"]
    if module == "commodities":
        return ["World Bank", "EIA / IEA / FAO", "market feed"]
    if module == "fiscal":
        return ["IMF", "OECD", "World Bank"]
    return ["OECD", "IMF", "World Bank"]


def catalogue() -> list[dict[str, Any]]:
    rows = []
    for iso3, country in COUNTRY_SOURCES.items():
        for module, spec in MODULES.items():
            rows.append({
                "catalogue_id": f"g20:{iso3.lower()}:{module}",
                "iso3": iso3,
                "country": country["country"],
                "module": module,
                "module_label": spec["label"],
                "indicators": list(spec["indicators"]),
                "target_frequency": spec["frequency"],
                "primary_source": _primary_source(country, module),
                "source_priority": "S1_OFFICIAL_PRIMARY",
                "validation_sources": _validation_sources(module),
                "market_feed_required": module in {"rates", "fx_external", "commodities"},
                "pit_required": True,
            })
    return rows

