"""Deterministic company recommendation inputs for integration tests (no LLM)."""

from __future__ import annotations

from institutional_reporting.models import EvidenceItem, InstitutionalReportInput


def _ev(*rows: tuple[str, str, str, tuple[str, ...]]) -> tuple[EvidenceItem, ...]:
    return tuple(
        EvidenceItem(evidence_id=a, label=b, source_type=c, section_keys=d) for a, b, c, d in rows
    )


COMMON_SECTIONS = (
    "investment_thesis",
    "business_quality",
    "financial_quality",
    "valuation",
    "risk_assessment",
    "bull_case",
    "bear_case",
    "bottom_line",
    "confidence",
)


FIXTURES: dict[str, InstitutionalReportInput] = {
    "AXISBANK": InstitutionalReportInput(
        ticker="AXISBANK",
        company_name="Axis Bank",
        sector="Banking",
        recommendation="HOLD",
        conviction="LOW",
        confidence=67,
        horizon="Medium",
        business_quality=91,
        financial_quality="Stable",
        valuation="Fair",
        overall_risk="Moderate",
        thesis=(
            "Franchise deposit franchise improving but still mid-cycle",
            "Fee income diversification supports earnings resilience",
        ),
        risks=(
            "Credit cost normalization uncertainty",
            "Competitive intensity in retail liabilities",
        ),
        catalysts=(
            "Sustained CASA improvement",
            "Stable asset quality through the next two quarters",
        ),
        watch_items=(
            "Slippage ratio trend",
            "NIM trajectory vs peers",
        ),
        evidence=_ev(
            ("FIRE-06", "Business Quality Pack", "Annual Report", COMMON_SECTIONS),
            ("AR-FY25", "Annual Report", "Annual Report", ("business_quality", "financial_quality", "bottom_line")),
            ("CC-Q4", "Conference Call", "Conference Call", ("investment_thesis", "risk_assessment", "bull_case")),
            ("QR-Q4", "Quarterly Results", "Quarterly Results", ("valuation", "bear_case", "confidence")),
        ),
        positive_drivers=("Strong business quality score", "Stable financial quality"),
        negative_drivers=("Moderate overall risk", "Credit cost uncertainty"),
        unknowns=("Duration of liability cost pressure",),
        bull_points=("Deposit mix improvement continues", "Operating leverage expands"),
        bear_points=("Asset quality surprise", "NIM compression vs peers"),
        business_quality_reasons=("high FIRE-06 franchise score", "stable liability franchise signals"),
        financial_quality_reasons=("stable reported earnings quality", "controlled credit costs in recent prints"),
        valuation_reasons=("multiples sit near peer median", "no clear margin of safety or premium extreme"),
        risk_reasons=("credit costs remain the dominant swing factor", "liability competition persists"),
        as_of="2026-07-30",
    ),
    "KOTAKBANK": InstitutionalReportInput(
        ticker="KOTAKBANK",
        company_name="Kotak Mahindra Bank",
        sector="Banking",
        recommendation="HOLD",
        conviction="MEDIUM",
        confidence=72,
        horizon="Long",
        business_quality=93,
        financial_quality="Strong",
        valuation="Expensive",
        overall_risk="Moderate",
        thesis=(
            "High-quality liability franchise with disciplined underwriting",
            "Premium valuation already discounts quality",
        ),
        risks=("Regulatory overhang on growth pace", "Valuation leaves limited error margin"),
        catalysts=("Clearer growth authorization path", "Sustained premium deposit franchise"),
        watch_items=("Loan growth authorization", "Fee/other income mix"),
        evidence=_ev(
            ("FIRE-06", "Business Quality Pack", "Annual Report", COMMON_SECTIONS),
            ("AR-FY25", "Annual Report", "Annual Report", COMMON_SECTIONS),
            ("CC-Q4", "Conference Call", "Conference Call", COMMON_SECTIONS),
            ("QR-Q4", "Quarterly Results", "Quarterly Results", COMMON_SECTIONS),
        ),
        positive_drivers=("Excellent business quality", "Strong financial quality"),
        negative_drivers=("Expensive valuation", "Growth authorization uncertainty"),
        unknowns=("Timing of full growth normalization",),
        as_of="2026-07-30",
    ),
    "ICICIBANK": InstitutionalReportInput(
        ticker="ICICIBANK",
        company_name="ICICI Bank",
        sector="Banking",
        recommendation="BUY",
        conviction="MEDIUM",
        confidence=74,
        horizon="Medium",
        business_quality=90,
        financial_quality="Strong",
        valuation="Fair",
        overall_risk="Moderate",
        thesis=(
            "Consistent retail liability momentum",
            "Return ratios support compounding through the cycle",
        ),
        risks=("Unsecured retail mix vigilance", "Competitive deposit pricing"),
        catalysts=("Sustained ROA durability", "Stable credit costs"),
        watch_items=("Unsecured mix", "Opex efficiency"),
        evidence=_ev(
            ("FIRE-06", "Business Quality Pack", "Annual Report", COMMON_SECTIONS),
            ("AR-FY25", "Annual Report", "Annual Report", COMMON_SECTIONS),
            ("CC-Q4", "Conference Call", "Conference Call", COMMON_SECTIONS),
            ("QR-Q4", "Quarterly Results", "Quarterly Results", COMMON_SECTIONS),
        ),
        positive_drivers=("Strong franchise economics", "Fair valuation vs quality"),
        negative_drivers=("Moderate risk from retail mix"),
        unknowns=("Cycle sensitivity of unsecured book",),
        as_of="2026-07-30",
    ),
    "HDFCBANK": InstitutionalReportInput(
        ticker="HDFCBANK",
        company_name="HDFC Bank",
        sector="Banking",
        recommendation="HOLD",
        conviction="MEDIUM",
        confidence=70,
        horizon="Long",
        business_quality=94,
        financial_quality="Strong",
        valuation="Fair",
        overall_risk="Moderate",
        thesis=(
            "Systemically important franchise with deep liability advantage",
            "Merger integration still shapes near-term optics",
        ),
        risks=("Integration and LDR normalization path", "Margin rebuilding timeline"),
        catalysts=("LDR normalization", "Sustained deposit market share"),
        watch_items=("LDR", "Margin rebuild", "Loan mix"),
        evidence=_ev(
            ("FIRE-06", "Business Quality Pack", "Annual Report", COMMON_SECTIONS),
            ("AR-FY25", "Annual Report", "Annual Report", COMMON_SECTIONS),
            ("CC-Q4", "Conference Call", "Conference Call", COMMON_SECTIONS),
            ("QR-Q4", "Quarterly Results", "Quarterly Results", COMMON_SECTIONS),
        ),
        positive_drivers=("Top-tier business quality", "Strong financial quality"),
        negative_drivers=("Integration optics", "Margin rebuild uncertainty"),
        unknowns=("Pace of LDR normalization",),
        as_of="2026-07-30",
    ),
}


def get_fixture(ticker: str) -> InstitutionalReportInput | None:
    key = str(ticker or "").strip().upper().replace(".NS", "").replace(".BO", "")
    aliases = {
        "KOTAK": "KOTAKBANK",
        "ICICI": "ICICIBANK",
        "HDFC": "HDFCBANK",
        "AXIS": "AXISBANK",
    }
    key = aliases.get(key, key)
    return FIXTURES.get(key)
