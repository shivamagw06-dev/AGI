"""Module 12 — Unsupported Coverage Policy.

AFI Acceptance Test v1.0 found 3 hallucinations (D30 Visa, D31 Costco, D32
Ferrari/Toyota — see PR #448): questions about real, well-known global
companies outside this platform's verified retrieval universe (heavily
India-equity-focused) were answered with irrelevant generic evidence
("Based on retrieved evidence for the subject: Indian Stock Market Q&A...")
instead of an honest "I don't have verified coverage" refusal.

This module is deliberately narrow and additive: it detects a CURATED list
of prominent global companies that are NOT already in
app.ui.executive_composer's ``_ALIAS_SCAN`` (Meta/Apple/Microsoft/Google/
Amazon/Nvidia already have some alias-based handling and existing tests —
e.g. tests/test_executive_composer.py, ask_product_test/founder_evaluation_v1.py
FE-04/FE-05 — depend on that path continuing to work, so this policy does
not touch them). Genuinely fictitious/unknown entities ("XYZ Quantum
Robotics") continue to go through the existing, already-100%-passing
unknown-entity hard stop in service.py — this module only closes the gap
for REAL companies outside the verified universe.
"""

from __future__ import annotations

import re
from typing import Optional

from app.ui.executive_composer import alias_ticker_from_question

# Real, well-known global companies outside this platform's verified
# coverage universe. Deliberately excludes anything already in
# executive_composer._ALIAS_SCAN (Meta, Apple, Microsoft, Google, Amazon,
# Nvidia, and the covered Indian names) to avoid touching a working path.
UNSUPPORTED_COMPANIES: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"\bvisa\b(?!\s+(?:card|application|status|requirement))", re.I), "Visa"),
    (re.compile(r"\bcostco\b", re.I), "Costco"),
    (re.compile(r"\bferrari\b", re.I), "Ferrari"),
    (re.compile(r"\btoyota\b", re.I), "Toyota"),
    (re.compile(r"\bhonda\b", re.I), "Honda"),
    (re.compile(r"\bnetflix\b", re.I), "Netflix"),
    (re.compile(r"\btesla\b", re.I), "Tesla"),
    (re.compile(r"\bwalmart\b", re.I), "Walmart"),
    (re.compile(r"\bmastercard\b", re.I), "Mastercard"),
    (re.compile(r"\bpaypal\b", re.I), "PayPal"),
    (re.compile(r"\bmcdonald'?s\b", re.I), "McDonald's"),
    (re.compile(r"\bstarbucks\b", re.I), "Starbucks"),
    (re.compile(r"\bnike\b", re.I), "Nike"),
    (re.compile(r"\bdisney\b", re.I), "Disney"),
    (re.compile(r"\bboeing\b", re.I), "Boeing"),
    (re.compile(r"\bintel\b", re.I), "Intel"),
    (re.compile(r"\b(?:ibm|international business machines)\b", re.I), "IBM"),
    (re.compile(r"\boracle\b", re.I), "Oracle"),
    (re.compile(r"\bsalesforce\b", re.I), "Salesforce"),
    (re.compile(r"\badobe\b", re.I), "Adobe"),
    (re.compile(r"\bjpmorgan\b|\bjp morgan\b", re.I), "JPMorgan"),
    (re.compile(r"\bgoldman sachs\b", re.I), "Goldman Sachs"),
    (re.compile(r"\bberkshire hathaway\b", re.I), "Berkshire Hathaway"),
    (re.compile(r"\bunitedhealth\b", re.I), "UnitedHealth"),
    (re.compile(r"\bexxon(?:mobil)?\b", re.I), "ExxonMobil"),
    (re.compile(r"\bchevron\b", re.I), "Chevron"),
    (re.compile(r"\bpfizer\b", re.I), "Pfizer"),
    (re.compile(r"\bjohnson\s*&\s*johnson\b|\bj&j\b", re.I), "Johnson & Johnson"),
    (re.compile(r"\bprocter\s*&\s*gamble\b|\bp&g\b", re.I), "Procter & Gamble"),
    (re.compile(r"\bcoca-?cola\b", re.I), "Coca-Cola"),
    (re.compile(r"\bpepsico\b", re.I), "PepsiCo"),
    (re.compile(r"\bsamsung\b", re.I), "Samsung"),
    (re.compile(r"\bsony\b", re.I), "Sony"),
    (re.compile(r"\balibaba\b", re.I), "Alibaba"),
    (re.compile(r"\btencent\b", re.I), "Tencent"),
    (re.compile(r"\bvolkswagen\b", re.I), "Volkswagen"),
    (re.compile(r"\b(?:bmw|bayerische motoren)\b", re.I), "BMW"),
    (re.compile(r"\bmercedes-?benz\b|\bdaimler\b", re.I), "Mercedes-Benz"),
)

_REFUSAL_TEMPLATE = (
    "I do not currently have verified company coverage for {company}. "
    "I can explain the underlying financial concept or business economics generally, "
    "but I will not invent company-specific analysis."
)


def detect_unsupported_company(question: str) -> Optional[str]:
    """Returns the display name of a detected, well-known-but-unsupported
    company, or None. Deterministic pattern match only — no LLM, no
    retrieval. Companies already handled via executive_composer's alias
    path are excluded by construction (not in UNSUPPORTED_COMPANIES)."""

    q = question or ""
    if alias_ticker_from_question(q):
        # Already a supported/aliased entity — not this policy's concern.
        return None
    for pattern, display_name in UNSUPPORTED_COMPANIES:
        if pattern.search(q):
            return display_name
    return None


def unsupported_coverage_executive(company: str) -> str:
    return _REFUSAL_TEMPLATE.format(company=company)


def unsupported_coverage_why(company: str) -> list[str]:
    return [
        f"{company} is not in this platform's verified company-coverage universe.",
        "AGIB will not substitute generic or unrelated evidence for a company it cannot verify.",
        "Ask about the underlying financial concept (e.g. 'What creates pricing power?') for a general, "
        "non-company-specific explanation, or ask about a covered company for full research.",
    ]
