"""Industry / business-type taxonomy and keyword classifiers (deterministic)."""

from __future__ import annotations

import re
from typing import Optional

# Canonical industry keys used across value-driver and unit-econ templates.
INDUSTRY_ALIASES: dict[str, str] = {
    "bank": "banks",
    "banks": "banks",
    "banking": "banks",
    "nbfc": "nbfc",
    "finance": "nbfc",
    "insurance": "insurance",
    "life insurance": "insurance",
    "saas": "saas",
    "software": "saas",
    "it services": "it_services",
    "information technology": "it_services",
    # Do not alias bare "it" — substring matches "profitable", "with", etc.
    "cement": "cement",
    "airline": "airlines",
    "airlines": "airlines",
    "aviation": "airlines",
    "passenger airlines": "airlines",
    "air india": "airlines",
    "indigo": "airlines",
    "interglobe": "airlines",
    "hospital": "hospitals",
    "hospitals": "hospitals",
    "healthcare": "hospitals",
    "retail": "retail",
    "paint": "retail",
    "paints": "retail",
    "fmcg": "retail",
    "membership": "retail",
    "warehouse club": "retail",
    "costco": "retail",
    "ferrari": "manufacturing",
    "toyota": "manufacturing",
    "apple": "platform",
    "reliance": "conglomerate",
    "reliance industries": "conglomerate",
    "marketplace": "marketplace",
    "e-commerce": "marketplace",
    "ecommerce": "marketplace",
    "manufacturer": "manufacturing",
    "manufacturing": "manufacturing",
    "auto": "manufacturing",
    "automobile": "manufacturing",
    "luxury auto": "manufacturing",
    "oil": "commodity",
    "oil & gas": "commodity",
    "oil and gas": "commodity",
    "commodity": "commodity",
    "utility": "utility",
    "utilities": "utility",
    "power": "utility",
    "telecom": "infrastructure",
    "telecommunications": "infrastructure",
    "infrastructure": "infrastructure",
    "platform": "platform",
    "conglomerate": "conglomerate",
    "diversified": "conglomerate",
    "restaurant": "restaurant",
    "subscription": "subscription",
}

BUSINESS_TYPE_BY_INDUSTRY: dict[str, str] = {
    "banks": "bank",
    "nbfc": "nbfc",
    "insurance": "insurance",
    "saas": "saas",
    "it_services": "it_services",
    "cement": "cement",
    "airlines": "airline",
    "hospitals": "hospital",
    "retail": "retail",
    "marketplace": "marketplace",
    "manufacturing": "manufacturer",
    "commodity": "commodity",
    "utility": "utility",
    "infrastructure": "infrastructure",
    "platform": "platform",
    "conglomerate": "conglomerate",
    "restaurant": "retail",
    "subscription": "subscription",
}

_SECTOR_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("banks", ("bank", "banking", "deposit", "casa", "nim", "npa", "credit cost")),
    ("nbfc", ("nbfc", "non-banking", "lending", "loan book")),
    ("insurance", ("insurance", "underwriting", "premium", "solvency")),
    ("saas", ("saas", "subscription software", "arr", "nrr", "churn")),
    ("it_services", ("it services", "software services", "outsourcing", "tcs", "infosys", "wipro")),
    ("cement", ("cement", "clinker", "realization", "utilization")),
    ("airlines", ("airline", "aviation", "load factor", "atf", "yield", "air india", "indigo", "interglobe")),
    ("hospitals", ("hospital", "arpob", "occupancy", "alos", "bed")),
    ("retail", ("retail", "store", "same-store", "merchandising", "paint", "fmcg", "membership", "costco", "warehouse")),
    ("marketplace", ("marketplace", "take rate", "gmv", "two-sided")),
    ("manufacturing", ("manufactur", "factory", "plant", "auto", "oem")),
    ("commodity", ("refining", "petrochemical", "crude", "commodity")),
    ("utility", ("utility", "power distribution", "regulated return")),
    ("infrastructure", ("telecom", "tower", "spectrum", "infrastructure")),
    ("conglomerate", ("conglomerate", "diversified", "multiple businesses")),
    ("platform", ("platform", "ecosystem", "network effects")),
    ("restaurant", ("restaurant", "qsr", "food service")),
    ("subscription", ("subscription", "recurring membership")),
]


def normalize_industry(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    low = re.sub(r"\s+", " ", str(text).strip().lower())
    if low in INDUSTRY_ALIASES:
        return INDUSTRY_ALIASES[low]
    # Prefer longer aliases first; require word boundaries so short tokens
    # like "oil" don't misfire inside unrelated words, and "it" never matches
    # inside "profitable" / "with".
    for alias, key in sorted(INDUSTRY_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if len(alias) <= 2:
            continue
        if re.search(rf"\b{re.escape(alias)}\b", low):
            return key
    return None


# Canonical Industry DNA key → BI industry key. BI keeps its own template
# vocabulary, but the *choice* of template is owned by Company Identity.
_DNA_TO_BI_KEY: dict[str, str] = {
    "banks": "banks",
    "nbfc": "nbfc",
    "asset_management": "nbfc",
    "insurance": "insurance",
    "it_services": "it_services",
    "software": "saas",
    "internet_platforms": "platform",
    "telecom": "infrastructure",
    "media": "infrastructure",
    "hospitals": "hospitals",
    "diagnostics": "hospitals",
    "pharma": "manufacturing",
    "airlines": "airlines",
    "logistics": "infrastructure",
    "shipping": "infrastructure",
    "infrastructure": "infrastructure",
    "capital_goods": "manufacturing",
    "automobile": "manufacturing",
    "auto_components": "manufacturing",
    "consumer_durables": "manufacturing",
    "cement": "cement",
    "metals": "commodity",
    "mining": "commodity",
    "chemicals": "commodity",
    "oil_gas": "commodity",
    "retail": "retail",
    "fmcg": "retail",
    "qsr": "restaurant",
    "hotels": "retail",
    "power": "utility",
    "utilities": "utility",
    "renewables": "utility",
    "real_estate": "infrastructure",
    "education": "retail",
    "agriculture": "commodity",
    "data_centers": "infrastructure",
}


def canonical_industry_key(ticker: Optional[str]) -> Optional[str]:
    """BI template key derived from the canonical Company Identity Service.

    Capital IQ classification is authoritative — BI must not re-infer an
    industry from a business description ("Diversified Banks" once matched
    the "diversified" alias and produced conglomerate/oil & gas drivers).
    """
    if not ticker:
        return None
    try:
        from company_identity.service import identity_for
    except Exception:
        return None
    identity = identity_for(ticker)
    if not identity.resolved or not identity.industry_dna:
        return None
    return _DNA_TO_BI_KEY.get(identity.industry_dna)


def classify_industry(
    *,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    description: Optional[str] = None,
    question: Optional[str] = None,
    ticker: Optional[str] = None,
) -> str:
    canonical = canonical_industry_key(ticker)
    if canonical:
        return canonical
    blob = " ".join(x for x in (sector, industry, description, question) if x).lower()
    if not blob.strip():
        return "unknown"
    direct = (
        normalize_industry(industry)
        or normalize_industry(sector)
        or normalize_industry(question)
        or normalize_industry(description)
    )
    if direct:
        return direct
    best_key = "unknown"
    best_hits = 0
    for key, hints in _SECTOR_HINTS:
        hits = sum(1 for h in hints if h in blob)
        if hits > best_hits:
            best_hits = hits
            best_key = key
    return best_key if best_hits else "unknown"


def business_type_for_industry(industry_key: str) -> str:
    return BUSINESS_TYPE_BY_INDUSTRY.get(industry_key, "unknown")
