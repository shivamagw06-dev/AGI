"""Intent / question-type → framework overlays."""

from __future__ import annotations

# intent_v2 (Track A) → additional frameworks with roles
INTENT_FRAMEWORKS: dict[str, list[tuple[str, str]]] = {
    "Explain": [
        ("FW_FRAMEWORK_EXPLANATION", "primary"),
        ("FW_ACCOUNTING_QUALITY", "supporting"),
    ],
    "Education": [
        ("FW_FRAMEWORK_EXPLANATION", "primary"),
        ("FW_ACCOUNTING_QUALITY", "supporting"),
    ],
    "Compare": [
        ("FW_PEER_COMPARISON", "primary"),
        ("FW_HISTORICAL_VALUATION", "secondary"),
    ],
    "Analyse": [
        ("FW_BUSINESS_QUALITY", "secondary"),
        ("FW_CASH_FLOW_QUALITY", "supporting"),
    ],
    "Valuation": [
        ("FW_HISTORICAL_VALUATION", "secondary"),
    ],
    "Industry": [
        ("FW_INDUSTRY_STRUCTURE", "primary"),
        ("FW_PORTERS_FIVE", "secondary"),
    ],
    "Macro": [
        ("FW_MACRO_TRANSMISSION", "primary"),
        ("FW_SCENARIO", "secondary"),
    ],
    "Government": [
        ("FW_POLICY", "primary"),
        ("FW_MACRO_TRANSMISSION", "secondary"),
    ],
    "Documents": [
        ("FW_RISK", "secondary"),
        ("FW_CORPORATE_GOVERNANCE", "supporting"),
        ("FW_CAPITAL_ALLOCATION", "supporting"),
    ],
    "HistoricalReplay": [
        ("FW_HISTORICAL_VALUATION", "primary"),
    ],
    "CrossDomain": [
        ("FW_MACRO_TRANSMISSION", "primary"),
        ("FW_SCENARIO", "secondary"),
        ("FW_INDUSTRY_STRUCTURE", "supporting"),
    ],
    "Accounting": [
        ("FW_ACCOUNTING_QUALITY", "primary"),
        ("FW_CASH_FLOW_QUALITY", "primary"),
    ],
    "Risk": [
        ("FW_RISK", "primary"),
    ],
    "Portfolio": [
        ("FW_SCENARIO", "primary"),
        ("FW_RISK", "secondary"),
        ("FW_PEER_COMPARISON", "supporting"),
    ],
    "CorporateEvents": [
        ("FW_CAPITAL_ALLOCATION", "primary"),
    ],
}

# question_type (governance soft override) → overlays
QUESTION_TYPE_FRAMEWORKS: dict[str, list[tuple[str, str]]] = {
    "education": [("FW_FRAMEWORK_EXPLANATION", "primary")],
    "valuation": [("FW_HISTORICAL_VALUATION", "supporting")],
    "investment_decision": [("FW_RISK", "supporting"), ("FW_SCENARIO", "supporting")],
}
