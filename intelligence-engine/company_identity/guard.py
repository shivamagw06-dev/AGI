"""Cross-industry leakage guard — the automatic-fail rules.

A Financials company may never be described with GRM. A bank may never be
handed oil production drivers. These checks run over generated text and over
structured classification claims.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from company_identity.schema import (
    PRIMARY_SECTORS,
    ClassificationViolation,
    CompanyIdentity,
    ValidationReport,
)
from company_identity.taxonomy import owning_family

# Sector + term combinations that are always wrong (spec: AUTOMATIC FAIL).
_SECTOR_FORBIDDEN: dict[str, tuple[str, ...]] = {
    "Financials": ("grm", "gross refining margin", "reserve replacement", "crack spread",
                   "refining complexity", "oil production", "rask", "cask", "arpob"),
    "Information Technology": ("reserve replacement", "grm", "casa", "gnpa", "arpob", "rask"),
    "Health Care": ("casa", "gnpa", "grm", "reserve replacement", "rask", "cask"),
    "Consumer Discretionary": ("casa", "gnpa", "grm", "reserve replacement"),
    "Consumer Staples": ("casa", "gnpa", "grm", "reserve replacement"),
    "Real Estate": ("casa", "gnpa", "grm", "reserve replacement", "rask"),
    "Utilities": ("casa", "gnpa", "grm", "reserve replacement", "arpob"),
    "Materials": ("casa", "gnpa", "arpob", "rask"),
    "Communication Services": ("casa", "gnpa", "grm", "reserve replacement", "arpob"),
    "Industrials": ("casa", "gnpa", "grm", "reserve replacement"),
}

# Business types that must never be produced for a given sector.
_SECTOR_FORBIDDEN_TYPES: dict[str, tuple[str, ...]] = {
    "Financials": ("conglomerate", "integrated energy company", "refiner and marketer",
                   "commodity", "oil", "airline"),
    "Information Technology": ("conglomerate", "integrated energy company", "bank"),
    "Health Care": ("conglomerate", "bank", "integrated energy company"),
}

_WORD_TERMS = {"grm", "casa", "gnpa", "nnpa", "cet1", "rask", "cask", "arpob", "alos", "ask", "rpk"}


def _mentions(text: str, term: str) -> bool:
    if term in _WORD_TERMS:
        return re.search(rf"\b{re.escape(term)}\b", text) is not None
    return term in text


def validate_text(
    identity: Optional[CompanyIdentity],
    text: str,
    *,
    where: str = "answer",
) -> ValidationReport:
    """Fail when text mixes another industry's exclusive vocabulary in."""
    if identity is None or not identity.resolved:
        return ValidationReport(ok=True, ticker=None)
    blob = str(text or "").lower()
    if not blob.strip():
        return ValidationReport(ok=True, ticker=identity.ticker)

    violations: list[ClassificationViolation] = []
    sector = identity.primary_sector or ""
    dna = identity.industry_dna

    for term in _SECTOR_FORBIDDEN.get(sector, ()):  # sector-level automatic fails
        if _mentions(blob, term):
            owner = owning_family(term) or "another industry"
            violations.append(
                ClassificationViolation(
                    rule=f"{sector}+{term}",
                    detail=(
                        f"{where}: '{term}' belongs to {owner}; "
                        f"{identity.company_name} is {sector} / {identity.primary_industry}."
                    ),
                )
            )

    for term in identity.forbidden_valuation:  # DNA-level exclusive vocabulary
        if _mentions(blob, term) and not any(v.rule.endswith(term) for v in violations):
            owner = owning_family(term)
            if owner and owner != dna:
                violations.append(
                    ClassificationViolation(
                        rule=f"{dna}+{term}",
                        detail=(
                            f"{where}: '{term}' is exclusive to {owner}; "
                            f"{identity.company_name} maps to {dna}."
                        ),
                    )
                )

    for bad_type in _SECTOR_FORBIDDEN_TYPES.get(sector, ()):
        if re.search(rf"business type[:\s]+{re.escape(bad_type)}", blob):
            violations.append(
                ClassificationViolation(
                    rule=f"{sector}+business_type:{bad_type}",
                    detail=f"{where}: business type '{bad_type}' is impossible for {sector}.",
                )
            )

    return ValidationReport(ok=not violations, ticker=identity.ticker, violations=violations)


def validate_classification(
    identity: Optional[CompanyIdentity],
    *,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
    business_type: Optional[str] = None,
    industry_dna: Optional[str] = None,
) -> ValidationReport:
    """Fail when a downstream engine claims a different classification."""
    if identity is None or not identity.resolved:
        return ValidationReport(ok=True, ticker=None)
    violations: list[ClassificationViolation] = []

    if sector and identity.primary_sector and sector.strip() != identity.primary_sector:
        violations.append(
            ClassificationViolation(
                rule="wrong_primary_sector",
                detail=f"claimed '{sector}', canonical '{identity.primary_sector}'.",
            )
        )
    if sector and sector.strip() not in PRIMARY_SECTORS:
        violations.append(
            ClassificationViolation(
                rule="non_canonical_sector",
                detail=f"'{sector}' is not one of the 11 Capital IQ primary sectors.",
            )
        )
    if industry and identity.primary_industry and industry.strip() != identity.primary_industry:
        violations.append(
            ClassificationViolation(
                rule="wrong_primary_industry",
                detail=f"claimed '{industry}', canonical '{identity.primary_industry}'.",
            )
        )
    if business_type and identity.business_type and business_type.strip() != identity.business_type:
        violations.append(
            ClassificationViolation(
                rule="wrong_business_type",
                detail=f"claimed '{business_type}', canonical '{identity.business_type}'.",
            )
        )
    if industry_dna and identity.industry_dna and industry_dna.strip() != identity.industry_dna:
        violations.append(
            ClassificationViolation(
                rule="wrong_industry_dna",
                detail=f"claimed '{industry_dna}', canonical '{identity.industry_dna}'.",
            )
        )
    return ValidationReport(ok=not violations, ticker=identity.ticker, violations=violations)


def filter_leaked_lines(
    identity: Optional[CompanyIdentity],
    lines: Iterable[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    """Drop any line that carries another industry's exclusive vocabulary."""
    kept: list[str] = []
    dropped: list[dict[str, Any]] = []
    for line in lines or []:
        report = validate_text(identity, str(line), where="line")
        if report.ok:
            kept.append(line)
        else:
            dropped.append(
                {"line": str(line)[:220], "violations": [v.rule for v in report.violations]}
            )
    return kept, dropped
