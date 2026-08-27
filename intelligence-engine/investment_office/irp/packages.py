"""Research package definitions — module sets only (no analysis)."""

from __future__ import annotations

from typing import Any

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
    PACKAGE_TYPES,
)

# Package → ordered modules to invoke (orchestration only)
PACKAGE_MODULES: dict[str, tuple[str, ...]] = {
    PACKAGE_FINANCIAL_HEALTH: (MODULE_FIRE01, MODULE_FIRE02, MODULE_FIRE06),
    PACKAGE_BUSINESS_QUALITY: (MODULE_FIRE06, MODULE_FIRE01, MODULE_FIRE03),
    PACKAGE_MANAGEMENT_REVIEW: (MODULE_FIRE03, MODULE_FIRE05, MODULE_FIRE04),
    PACKAGE_EVIDENCE_REVIEW: (MODULE_FIRE03, MODULE_FIRE04, MODULE_FIRE01),
    PACKAGE_EXECUTION_REVIEW: (MODULE_FIRE05, MODULE_FIRE03),
    PACKAGE_CAPITAL_ALLOCATION: (MODULE_FIRE01, MODULE_FIRE03, MODULE_FIRE04, MODULE_FIRE06),
    PACKAGE_CASH_FLOW: (MODULE_FIRE01, MODULE_FIRE02, MODULE_FIRE06),
    PACKAGE_BALANCE_SHEET: (MODULE_FIRE02, MODULE_FIRE06),
    PACKAGE_GROWTH: (MODULE_FIRE01, MODULE_FIRE02, MODULE_FIRE06),
    PACKAGE_SNAPSHOT: (MODULE_FIRE06, MODULE_FIRE01, MODULE_FIRE03, MODULE_FIRE05),
    PACKAGE_INSTITUTIONAL_BRIEF: (
        MODULE_FIRE06,
        MODULE_FIRE01,
        MODULE_FIRE02,
        MODULE_FIRE03,
        MODULE_FIRE04,
        MODULE_FIRE05,
    ),
}

# IRP sections populated per package (subset for focused packages)
PACKAGE_SECTIONS: dict[str, tuple[str, ...]] = {
    PACKAGE_FINANCIAL_HEALTH: (
        "executive_summary",
        "financial_trends",
        "financial_relationships",
        "business_quality",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_BUSINESS_QUALITY: (
        "executive_summary",
        "business_quality",
        "key_strengths",
        "key_risks",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_MANAGEMENT_REVIEW: (
        "executive_summary",
        "business_strategy",
        "management_execution",
        "evidence_consistency",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_EVIDENCE_REVIEW: (
        "executive_summary",
        "evidence_consistency",
        "business_strategy",
        "financial_trends",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_EXECUTION_REVIEW: (
        "executive_summary",
        "management_execution",
        "outstanding_questions",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_CAPITAL_ALLOCATION: (
        "executive_summary",
        "financial_trends",
        "business_strategy",
        "evidence_consistency",
        "business_quality",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_CASH_FLOW: (
        "executive_summary",
        "financial_trends",
        "financial_relationships",
        "business_quality",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_BALANCE_SHEET: (
        "executive_summary",
        "financial_relationships",
        "business_quality",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_GROWTH: (
        "executive_summary",
        "financial_trends",
        "financial_relationships",
        "business_quality",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_SNAPSHOT: (
        "executive_summary",
        "company_snapshot",
        "business_quality",
        "financial_trends",
        "business_strategy",
        "management_execution",
        "confidence_summary",
        "evidence_references",
    ),
    PACKAGE_INSTITUTIONAL_BRIEF: (
        "executive_summary",
        "company_snapshot",
        "business_quality",
        "financial_trends",
        "financial_relationships",
        "business_strategy",
        "management_execution",
        "evidence_consistency",
        "key_strengths",
        "key_risks",
        "outstanding_questions",
        "confidence_summary",
        "evidence_references",
    ),
}


def normalize_package_type(package_type: str | None) -> str:
    raw = (package_type or "").strip()
    if not raw:
        return PACKAGE_INSTITUTIONAL_BRIEF
    if raw in PACKAGE_MODULES:
        return raw
    # Accept snake / kebab / case-insensitive aliases
    key = raw.lower().replace("_", " ").replace("-", " ").strip()
    for name in PACKAGE_TYPES:
        if name.lower() == key or name.lower().replace(" ", "") == key.replace(" ", ""):
            return name
    return PACKAGE_INSTITUTIONAL_BRIEF


def modules_for_package(package_type: str) -> tuple[str, ...]:
    pkg = normalize_package_type(package_type)
    return PACKAGE_MODULES.get(pkg) or PACKAGE_MODULES[PACKAGE_INSTITUTIONAL_BRIEF]


def sections_for_package(package_type: str) -> tuple[str, ...]:
    pkg = normalize_package_type(package_type)
    return PACKAGE_SECTIONS.get(pkg) or PACKAGE_SECTIONS[PACKAGE_INSTITUTIONAL_BRIEF]


def package_catalog() -> list[dict[str, Any]]:
    return [
        {
            "package_type": name,
            "modules": list(PACKAGE_MODULES[name]),
            "sections": list(PACKAGE_SECTIONS[name]),
            "orchestrates_only": True,
        }
        for name in PACKAGE_MODULES
    ]
