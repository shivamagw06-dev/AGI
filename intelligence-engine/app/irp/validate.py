"""Step 13 — Self-check before returning an answer."""

from __future__ import annotations

from app.irp.models import (
    InstitutionalReasoning,
    RankedEvidenceItem,
    ResolvedEntityPack,
    ValidationReport,
)


def validate_package(
    question: str,
    *,
    entities: ResolvedEntityPack,
    ranked: list[RankedEvidenceItem],
    rejected: list[RankedEvidenceItem],
    reasoning: InstitutionalReasoning,
) -> ValidationReport:
    issues: list[str] = []
    answered = bool(reasoning.what_is_happening or reasoning.outlook)
    if not answered:
        issues.append("Missing core outlook / what-is-happening statement.")

    unrelated = any(r.reject_reason for r in rejected[:20]) and not ranked
    # Flag if accepted evidence looks off-universe while reject list is large
    if entities.sector_key and ranked:
        sector_hits = sum(
            1
            for r in ranked
            if entities.sector_label
            and entities.sector_label.lower().split()[0] in (r.title + " " + r.snippet).lower()
        )
        if sector_hits == 0 and len(ranked) >= 3:
            unrelated = True
            issues.append("Accepted evidence may be weakly tied to the resolved sector.")

    missing_cos = False
    if entities.sector_key and len(entities.companies) >= 5 and not reasoning.company_leaders:
        missing_cos = True
        issues.append("Sector universe leaders were not attached to the briefing.")

    missing_drivers = False
    if not reasoning.key_drivers and not reasoning.macro_drivers and not reasoning.sector_drivers:
        missing_drivers = True
        issues.append("No key/macro/sector drivers identified.")

    conf_ok = 0.2 <= float(reasoning.confidence or 0) <= 0.98
    if not conf_ok:
        issues.append("Confidence outside a justifiable institutional range.")

    consistent = True
    stance = (reasoning.stance or "").lower()
    blob = f"{reasoning.what_is_happening} {reasoning.outlook}".lower()
    if "bull" in stance and any(w in blob for w in ("weak growth", "muted", "demand weakness")):
        # Allow if bull case explicitly offsets — otherwise inconsistent
        if not reasoning.bull_case:
            consistent = False
            issues.append("Bullish stance conflicts with cautious thesis language.")
    if "bear" in stance and any(w in blob for w in ("strong acceleration", "beat and raise")) and not reasoning.bear_case:
        consistent = False
        issues.append("Bearish stance conflicts with strongly constructive language.")

    passed = answered and not missing_drivers and conf_ok and consistent and not (unrelated and not ranked)
    return ValidationReport(
        answered_question=answered,
        unrelated_evidence=bool(unrelated),
        missing_major_companies=missing_cos,
        missing_major_drivers=missing_drivers,
        confidence_justified=conf_ok,
        internally_consistent=consistent,
        issues=issues,
        rebuilt=False,
        passed=passed,
    )
