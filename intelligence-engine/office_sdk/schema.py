"""Office SDK constants."""

from __future__ import annotations

SDK_WORKSTREAM_ID = "OFFICE-SDK"
SDK_PRODUCT = "Office SDK"
SDK_VERSION = "office-sdk-v1.0.0"
SDK_SUBSYSTEM = "application_office_contract"
SDK_SPEC = "docs/OFFICE_SDK_SHARED_CONTRACT.md"
SDK_RECOMMENDATION_POLICY = "orchestration_only_no_buy_sell_no_new_analysis"

# Application domains (homes for offices)
DOMAIN_RESEARCH = "research"
DOMAIN_PORTFOLIO = "portfolio"
DOMAIN_MARKET = "market"
DOMAIN_EXECUTION = "execution"
DOMAIN_KNOWLEDGE = "knowledge"

DOMAINS = (
    DOMAIN_RESEARCH,
    DOMAIN_PORTFOLIO,
    DOMAIN_MARKET,
    DOMAIN_EXECUTION,
    DOMAIN_KNOWLEDGE,
)

DOMAIN_LABELS = {
    DOMAIN_RESEARCH: "Research Domain",
    DOMAIN_PORTFOLIO: "Portfolio Domain",
    DOMAIN_MARKET: "Market Domain",
    DOMAIN_EXECUTION: "Execution Domain",
    DOMAIN_KNOWLEDGE: "Knowledge Domain",
}
