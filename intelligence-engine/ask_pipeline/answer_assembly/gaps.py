"""Stage 3 — Gap detection before reasoning."""

from __future__ import annotations

from typing import Any

# Required domains by intent (minimum institutional coverage)
_REQUIRED_DOMAINS: dict[str, tuple[str, ...]] = {
    "Explain": ("Accounting", "BusinessModel", "ValuationFramework"),
    "Education": ("ValuationFramework", "Accounting"),
    "Compare": ("Financial", "Industry"),
    "Analyse": ("Financial", "Documents"),
    "Valuation": ("Financial", "Historical", "ValuationFramework"),
    "Industry": ("Industry",),
    "Macro": ("Macro",),
    "Government": ("Government",),
    "Documents": ("Documents",),
    "HistoricalReplay": ("Historical",),
    "CrossDomain": ("Macro", "Government", "Industry"),
    "Accounting": ("Accounting", "Financial"),
    "Risk": ("Risk",),
    "CorporateEvents": ("CorporateEvents",),
    "Portfolio": ("Financial",),
    "Unknown": ("Financial",),
}

# Soft alternatives — if alt present, required gap is softened
_ALTERNATES: dict[str, tuple[str, ...]] = {
    "ValuationFramework": ("Financial", "Historical"),
    "BusinessModel": ("Industry", "Financial"),
    "Accounting": ("Financial", "Documents"),
    "Documents": ("Financial", "Risk"),
    "Historical": ("Financial", "CorporateEvents"),
}


def detect_gaps(
    classified: dict[str, Any],
    *,
    intent_v2: str,
    evidence_types_required: list[str] | None = None,
) -> dict[str, Any]:
    present_domains = set((classified.get("by_domain") or {}).keys())
    required = list(_REQUIRED_DOMAINS.get(intent_v2) or _REQUIRED_DOMAINS["Unknown"])

    missing: list[str] = []
    softened: list[str] = []
    for domain in required:
        if domain in present_domains:
            continue
        alts = _ALTERNATES.get(domain) or ()
        if any(a in present_domains for a in alts):
            softened.append(domain)
            continue
        missing.append(domain)

    # Also check IRL evidence type requirements soft coverage
    type_gaps: list[str] = []
    present_types = {str(i.get("evidence_type")) for i in (classified.get("items") or [])}
    for et in evidence_types_required or []:
        if et not in present_types:
            type_gaps.append(et)

    coverage = 1.0
    if required:
        covered = len(required) - len(missing)
        coverage = round(max(0.0, covered / len(required)), 4)

    return {
        "stage": "gap_detection",
        "intent_v2": intent_v2,
        "required_domains": required,
        "present_domains": sorted(present_domains),
        "missing_domains": missing,
        "softened_domains": softened,
        "missing_evidence_types": type_gaps[:12],
        "coverage": coverage,
        "confidence_penalty": round(min(0.45, 0.12 * len(missing) + 0.03 * len(type_gaps)), 4),
        "tell_reasoning": (
            f"Missing domains: {', '.join(missing)}; reduce confidence."
            if missing
            else "Required domains present or softened."
        ),
        "fabricated": False,
    }
