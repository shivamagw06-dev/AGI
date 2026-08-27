"""RW-01 evidence browser — filings and documents linked to dependent objects."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_workspace.models import EvidenceItem


_SOURCE_TYPES = (
    "SEC/NSE filings",
    "Annual Reports",
    "Quarterly Results",
    "Conference Calls",
    "Investor Presentations",
    "Corporate Actions",
    "Internal Notes",
)


def browse_evidence(
    *,
    ticker: str = "",
    portfolio_id: str = "",
    external_evidence: Sequence[dict[str, Any]] = (),
    linked_decision_id: str = "",
    linked_risk_id: str = "",
) -> tuple[EvidenceItem, ...]:
    items: list[EvidenceItem] = []

    for raw in external_evidence:
        items.append(
            EvidenceItem(
                evidence_id=str(raw.get("evidence_id") or raw.get("id") or raw.get("title") or "ev"),
                source_type=str(raw.get("source_type") or raw.get("kind") or "Internal Notes"),
                title=str(raw.get("title") or "Evidence"),
                date=str(raw.get("date") or ""),
                href=str(raw.get("href") or ""),
                linked_object_ids=tuple(raw.get("linked_object_ids") or ()),
                snippet=str(raw.get("snippet") or raw.get("detail") or ""),
            )
        )

    # Deterministic institutional stubs so the browser is navigable without live filings
    subject = ticker or portfolio_id or "AGI"
    seeds = (
        ("Quarterly Results", f"{subject} latest quarterly results", "Results commentary and KPIs"),
        ("Conference Calls", f"{subject} earnings call", "Management Q&A highlights"),
        ("Annual Reports", f"{subject} annual report", "Business description and risk factors"),
        ("Investor Presentations", f"{subject} investor deck", "Strategy and capital allocation slides"),
        ("Corporate Actions", f"{subject} corporate actions", "Dividends, buybacks, and capital events"),
        ("SEC/NSE filings", f"{subject} regulatory filings", "Exchange / regulator disclosures"),
        ("Internal Notes", f"{subject} desk research note", "Analyst-owned note (non-system)"),
    )
    linked = tuple(
        x for x in (linked_decision_id, linked_risk_id, ticker, portfolio_id) if x
    )
    for i, (stype, title, snippet) in enumerate(seeds):
        if any(e.source_type == stype for e in items):
            continue
        items.append(
            EvidenceItem(
                evidence_id=f"ev-{subject.lower()}-{i}",
                source_type=stype,
                title=title,
                date="",
                href=f"/agi/companies/{ticker}?tab=evidence_references" if ticker else "/agi/research",
                linked_object_ids=linked,
                snippet=snippet,
            )
        )

    return tuple(items)


def source_types() -> tuple[str, ...]:
    return _SOURCE_TYPES
