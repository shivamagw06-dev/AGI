"""Evidence-to-Conclusion Ratio (ECR).

How many independent evidence classes support a conclusion?
A conclusion backed by one weak source should carry less confidence
than one backed by multiple independent sources.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

# Independent evidence classes (institutional hierarchy-aware).
EVIDENCE_CLASSES: dict[str, tuple[str, ...]] = {
    "financial_statements": (
        r"\bfinancial\s+statements?\b",
        r"\bincome\s+statement\b",
        r"\bbalance\s+sheet\b",
        r"\bcash[- ]flow\s+statement\b",
        r"\baudited\b",
    ),
    "company_filing": (
        r"\b(nse|bse)\s+filing\b",
        r"\bexchange\s+filing\b",
        r"\bofficial\s+filing\b",
        r"\bcompany\s+filing\b",
        r"\bdisclosure\b",
    ),
    "company_announcement": (
        r"\bpress\s+release\b",
        r"\bcompany\s+announcement\b",
        r"\binvestor\s+presentation\b",
    ),
    "macro_data": (
        r"\bmacro\b",
        r"\binflation\b",
        r"\binterest\s+rates?\b",
        r"\brbi\b",
        r"\boil\s+prices?\b",
        r"\bbond\s+yields?\b",
    ),
    "market_data": (
        r"\bshare\s+price\b",
        r"\bmarket\s+data\b",
        r"\btrading\b",
        r"\bquoted\b",
    ),
    "operating_metrics": (
        r"\bvolume\b",
        r"\border\s+book\b",
        r"\butilization\b",
        r"\bcustomers?\b",
        r"\bcharter\b",
        r"\bspot\s+rates?\b",
    ),
    "news_media": (
        r"\breuters\b",
        r"\bnews\b",
        r"\barticle\b",
        r"\bwire\b",
    ),
    "management_commentary": (
        r"\bmanagement\b",
        r"\bceo\b",
        r"\bguidance\b",
        r"\bcommentary\b",
        r"\binterview\b",
    ),
}

# Relative strength for confidence mapping (not a portfolio recommendation).
CLASS_STRENGTH = {
    "financial_statements": 1.0,
    "company_filing": 1.0,
    "company_announcement": 0.7,
    "macro_data": 0.8,
    "market_data": 0.6,
    "operating_metrics": 0.85,
    "news_media": 0.4,
    "management_commentary": 0.45,
}


def detect_evidence_classes(text: str, explicit: Iterable[str] | None = None) -> list[str]:
    found: list[str] = []
    blob = str(text or "")
    for cls, patterns in EVIDENCE_CLASSES.items():
        if any(re.search(p, blob, re.I) for p in patterns):
            found.append(cls)
    if explicit:
        for item in explicit:
            key = str(item or "").strip().lower().replace(" ", "_")
            if key in EVIDENCE_CLASSES and key not in found:
                found.append(key)
    return found


def compute_ecr(
    *,
    conclusion: str,
    answer_text: str = "",
    explicit_sources: Iterable[str] | None = None,
    claimed_support: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Compute Evidence-to-Conclusion Ratio for a conclusion."""
    text = f"{conclusion}\n{answer_text}"
    classes = detect_evidence_classes(text, explicit=explicit_sources)
    if claimed_support:
        for src in claimed_support:
            key = str(src or "").strip().lower().replace(" ", "_")
            if key and key not in classes:
                # Accept human-readable labels.
                mapped = {
                    "financial statements": "financial_statements",
                    "company filing": "company_filing",
                    "macro data": "macro_data",
                }.get(key, key)
                if mapped in EVIDENCE_CLASSES and mapped not in classes:
                    classes.append(mapped)
                elif key not in classes:
                    classes.append(key)

    ecr = len(classes)
    strength = sum(CLASS_STRENGTH.get(c, 0.5) for c in classes)
    if ecr <= 0:
        confidence_band = "unsupported"
    elif ecr == 1 and strength < 0.7:
        confidence_band = "weak_single_source"
    elif ecr == 1:
        confidence_band = "single_source"
    elif ecr == 2:
        confidence_band = "moderate"
    else:
        confidence_band = "multi_source"

    return {
        "metric": "evidence_to_conclusion_ratio",
        "abbreviation": "ECR",
        "conclusion": str(conclusion or "")[:400],
        "supported_by": classes,
        "ecr": ecr,
        "strength_score": round(strength, 3),
        "confidence_band": confidence_band,
        "rule": (
            "A conclusion supported by one weak source should carry less confidence "
            "than one supported by multiple independent sources."
        ),
    }


def attach_ecr_to_package(packaged: dict[str, Any]) -> dict[str, Any]:
    """Soft-attach ECR diagnostics onto a reasoning package."""
    out = dict(packaged or {})
    conclusion = (
        out.get("direct_answer")
        or (out.get("structured") or {}).get("conclusion")
        or ""
    )
    answer = out.get("executive") or out.get("answer") or ""
    ecr = compute_ecr(conclusion=str(conclusion), answer_text=str(answer))
    out["ecr"] = ecr
    out["evidence_to_conclusion_ratio"] = ecr.get("ecr")
    return out
