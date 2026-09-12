"""AGIB Institutional Committee Certification (IC-10 v2.0) — schema & rubric."""

from __future__ import annotations

CERT_VERSION = "committee-certification-ic10-v2.0.0"
PROGRAMME = "AGIB_INSTITUTIONAL_COMMITTEE_CERTIFICATION"
ARCHITECTURE_VERSION = "v1.0.1"
MILESTONE = "phase_2_committee_cert_v2"

# Display ticker → market/filing resolve ticker (post NSE rename)
IC10_V2_ROWS: tuple[tuple[str, str, str], ...] = (
    ("HDFCBANK", "HDFCBANK", "banks"),
    ("RELIANCE", "RELIANCE", "energy_conglomerate"),
    ("TCS", "TCS", "it_services"),
    ("ETERNAL", "ETERNAL", "consumer_internet"),
    ("TATAMOTORS", "TMPV", "auto"),
    ("SUNPHARMA", "SUNPHARMA", "pharma"),
    ("NTPC", "NTPC", "power"),
    ("HAL", "HAL", "defence"),
    ("ASIANPAINT", "ASIANPAINT", "paints"),
    ("ULTRACEMCO", "ULTRACEMCO", "cement"),
)

IC10_V2_UNIVERSE = tuple(r[0] for r in IC10_V2_ROWS)

# Sector analytical vocabulary (Test 2)
SECTOR_VOCAB: dict[str, tuple[str, ...]] = {
    "banks": ("casa", "nim", "gnpa", "nnpa", "pcr", "credit growth", "cet1", "deposit", "roe", "liability"),
    "it_services": ("utilisation", "utilization", "deal", "attrition", "margin", "ai", "pricing", "pipeline", "tcv"),
    "pharma": ("anda", "us exposure", "us ", "inspection", "fda", "pipeline", "formulation", "api", "specialty"),
    "cement": ("capacity", "utilisation", "utilization", "fuel", "petcoke", "realization", "volume", "clinker"),
    "power": ("plf", "generation", "capex", "thermal", "renewable", "regulated", "plant load"),
    "auto": ("volume", "ev", "export", "asu", "pv ", "cv ", "mix", "dealer", "jlr"),
    "paints": ("decorative", "volume", "realization", "distributor", "rural", "premium", "gross margin"),
    "defence": ("order book", "order", "defence", "defense", "indigen", "offset", "execution", "government"),
    "energy_conglomerate": ("refining", "petchem", "retail", "jio", "upstream", "downstream", "segment"),
    "consumer_internet": ("gmv", "unit economics", "contribution", "take rate", "cohort", "burn", "order"),
}

# Rubric weights (sum = 100)
AREA_WEIGHTS: dict[str, float] = {
    "evidence_completeness": 20.0,
    "financial_intelligence": 15.0,
    "ownership_intelligence": 10.0,
    "valuation_intelligence": 15.0,
    "sector_differentiation": 15.0,
    "decision_quality": 10.0,
    "governance_integrity": 10.0,
    "narrative_quality": 5.0,
}

GRADE_BANDS: tuple[tuple[float, str], ...] = (
    (95.0, "Institutional Ready"),
    (90.0, "Production Ready"),
    (80.0, "Strong Beta"),
    (70.0, "Research Platform"),
    (0.0, "Not Committee Ready"),
)

COMMITTEE_VERDICTS = ("Committee Ready", "Watchlist", "Deferred", "Research Required")

# Expected evidence dimensions (Test 1)
EVIDENCE_DIMENSIONS = (
    "live_market_context",
    "financial_statements",
    "ownership",
    "valuation",
    "peer_universe",
    "historical_valuation",
    "ttm",
    "cid_attached",
)

# Governance frozen constants that must match readiness_gate (Test 7)
EXPECTED_GATE_THRESHOLDS = {
    "high_conviction_coverage_pct": 95.0,
    "moderate_conviction_coverage_pct": 80.0,
    "watchlist_coverage_pct": 60.0,
    "high_conviction_evidence_floor_pct": 80.0,
}

FORBIDDEN_REC_TOKENS = (
    "buy",
    "sell",
    "accumulate",
    "reduce",
    "overweight",
    "underweight",
    "strong buy",
    "strong sell",
)

BOILERPLATE_PHRASES = (
    "as an ai",
    "it depends",
    "cannot provide financial advice",
    "please consult",
    "in conclusion, more research is needed without",
    "generic placeholder",
    "pe = 18",
    "historical pe 20",
)
