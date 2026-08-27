"""Module 4 — Source Ranking / rejection of empty-stale-duplicate results."""

from __future__ import annotations

from knowledge_unification.schema import ProviderResult

_PRIORITY_BONUS = {
    "historical_intelligence": 0,
    "institutional_warehouse": 0,
    "research_intelligence": 0,
    "portfolio_intelligence": 0,
    "investment_intelligence": 0,
    "industry_intelligence": 0,
    "business_intelligence": 0,
    "company_memory": 0,
    "ikl": 1,
    "valuation_consensus": 1,
    "capiq_ikt": 2,
    "financial_concepts": 0,
    "financial_foundations": 1,
    "financial_statement_intelligence": 2,
    "knowledge_factory": 3,
    "cgl": 4,
    "academy": 5,
    "legacy_kip": 9,
}

# Hard providers carry distinct fact surfaces even when narrative text overlaps
# (e.g. BI how-it-makes-money vs CapIQ description paraphrase). Never drop them
# solely for summary similarity — fusion needs multi-source evidence.
_DEDUP_EXEMPT = frozenset(
    {
        "historical_intelligence",
        "institutional_warehouse",
        "research_intelligence",
        "portfolio_intelligence",
        "investment_intelligence",
        "industry_intelligence",
        "business_intelligence",
        "valuation_consensus",
        "capiq_ikt",
        "company_memory",
        "ikl",
        "financial_concepts",
        "financial_foundations",
        "financial_statement_intelligence",
    }
)


def rank_and_filter(results: list[ProviderResult]) -> list[ProviderResult]:
    kept: list[ProviderResult] = []
    seen_summaries: set[str] = set()
    for r in results:
        if not r.ok:
            r.rejected_reason = r.rejected_reason or "error"
            continue
        if r.empty:
            r.rejected_reason = r.rejected_reason or "empty"
            continue
        if not (r.summary or r.why or r.facts):
            r.rejected_reason = "no_content"
            continue
        # Near-duplicate summary rejection (soft sources only).
        norm = " ".join((r.summary or "").lower().split())[:180]
        if norm and norm in seen_summaries and r.provider_id not in _DEDUP_EXEMPT:
            r.rejected_reason = "duplicate"
            continue
        if norm:
            seen_summaries.add(norm)
        kept.append(r)

    kept.sort(
        key=lambda r: (
            _PRIORITY_BONUS.get(r.provider_id, 5),
            -r.confidence,
            r.latency_ms,
        )
    )
    return kept
