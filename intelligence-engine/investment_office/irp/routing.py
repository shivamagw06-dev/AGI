"""Question → package / module routing (deterministic intent matching)."""

from __future__ import annotations

import re
from typing import Any

from investment_office.irp.packages import modules_for_package
from investment_office.schema import (
    MODULE_FIRE01,
    MODULE_FIRE02,
    MODULE_FIRE03,
    MODULE_FIRE04,
    MODULE_FIRE05,
    MODULE_FIRE06,
    PACKAGE_BALANCE_SHEET,
    PACKAGE_BUSINESS_QUALITY,
    PACKAGE_CAPITAL_ALLOCATION,
    PACKAGE_CASH_FLOW,
    PACKAGE_EVIDENCE_REVIEW,
    PACKAGE_EXECUTION_REVIEW,
    PACKAGE_FINANCIAL_HEALTH,
    PACKAGE_GROWTH,
    PACKAGE_INSTITUTIONAL_BRIEF,
    PACKAGE_MANAGEMENT_REVIEW,
    PACKAGE_SNAPSHOT,
)

# Ordered rules: first match wins. Patterns are case-insensitive.
_ROUTE_RULES: list[tuple[re.Pattern[str], str, tuple[str, ...] | None, str]] = [
    # (pattern, package_type, override_modules_or_None, intent_label)
    (
        re.compile(r"balance\s+sheet|leverage|net\s+debt|solvency|liquidity\s+position", re.I),
        PACKAGE_BALANCE_SHEET,
        (MODULE_FIRE02, MODULE_FIRE06),
        "balance_sheet_strength",
    ),
    (
        re.compile(r"what\s+changed|this\s+year|trend|how\s+did\s+.+\s+change", re.I),
        PACKAGE_FINANCIAL_HEALTH,
        (MODULE_FIRE01, MODULE_FIRE02),
        "what_changed",
    ),
    (
        re.compile(r"has\s+management\s+delivered|execution|delivered\s+on|promises?", re.I),
        PACKAGE_EXECUTION_REVIEW,
        (MODULE_FIRE05,),
        "management_delivery",
    ),
    (
        re.compile(r"strategy\s+supported|management.?s?\s+strategy|supported\s+by\s+evidence|consistency", re.I),
        PACKAGE_EVIDENCE_REVIEW,
        (MODULE_FIRE03, MODULE_FIRE04),
        "strategy_support",
    ),
    (
        re.compile(r"cash\s+flow|cash\s+generation|fcf|free\s+cash", re.I),
        PACKAGE_CASH_FLOW,
        None,
        "cash_flow_review",
    ),
    (
        re.compile(r"capital\s+allocation|buyback|dividend|capex\s+priorit", re.I),
        PACKAGE_CAPITAL_ALLOCATION,
        None,
        "capital_allocation",
    ),
    (
        re.compile(r"\bgrowth\b|revenue\s+growth|top[- ]line", re.I),
        PACKAGE_GROWTH,
        None,
        "growth_review",
    ),
    (
        re.compile(r"business\s+quality|how\s+strong\s+is\s+the\s+business|quality\s+of\s+the\s+business", re.I),
        PACKAGE_BUSINESS_QUALITY,
        None,
        "business_quality",
    ),
    (
        re.compile(r"management\s+review|what\s+does\s+management\s+say|disclos", re.I),
        PACKAGE_MANAGEMENT_REVIEW,
        None,
        "management_review",
    ),
    (
        re.compile(r"evidence\s+review|do\s+(?:the\s+)?evidence\s+agree|reconcile", re.I),
        PACKAGE_EVIDENCE_REVIEW,
        None,
        "evidence_review",
    ),
    (
        re.compile(r"financial\s+health|how\s+healthy", re.I),
        PACKAGE_FINANCIAL_HEALTH,
        None,
        "financial_health",
    ),
    (
        re.compile(r"snapshot|overview|summar", re.I),
        PACKAGE_SNAPSHOT,
        None,
        "company_snapshot",
    ),
    (
        re.compile(r"explain|tell\s+me\s+about|institutional\s+brief|full\s+review|research\s+package", re.I),
        PACKAGE_INSTITUTIONAL_BRIEF,
        None,
        "institutional_brief",
    ),
]


def route_question(
    question: str | None,
    *,
    package_type: str | None = None,
) -> dict[str, Any]:
    """Determine package type + modules. Explicit package_type overrides routing."""
    q = (question or "").strip()
    if package_type:
        modules = modules_for_package(package_type)
        return {
            "intent": "explicit_package",
            "package_type": package_type,
            "modules": list(modules),
            "question": q or None,
            "matched_rule": "explicit_package_type",
            "orchestrates_only": True,
        }

    if not q:
        # Default company view → institutional brief
        return {
            "intent": "default_company_brief",
            "package_type": PACKAGE_INSTITUTIONAL_BRIEF,
            "modules": list(modules_for_package(PACKAGE_INSTITUTIONAL_BRIEF)),
            "question": None,
            "matched_rule": "default",
            "orchestrates_only": True,
        }

    for pat, pkg, override, intent in _ROUTE_RULES:
        if pat.search(q):
            modules = list(override) if override is not None else list(modules_for_package(pkg))
            return {
                "intent": intent,
                "package_type": pkg,
                "modules": modules,
                "question": q,
                "matched_rule": pat.pattern,
                "orchestrates_only": True,
            }

    # Fallback: institutional brief
    return {
        "intent": "fallback_institutional_brief",
        "package_type": PACKAGE_INSTITUTIONAL_BRIEF,
        "modules": list(modules_for_package(PACKAGE_INSTITUTIONAL_BRIEF)),
        "question": q,
        "matched_rule": "fallback",
        "orchestrates_only": True,
    }
