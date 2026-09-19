"""Knowledge completeness check — never invent missing evidence."""

from __future__ import annotations

from typing import Any

from institutional_forecast_intelligence.schema import CompletenessStatus, KnowledgeCompleteness


def _status(present: bool, *, rich: bool = False) -> CompletenessStatus:
    if present and rich:
        return CompletenessStatus.COMPLETE
    if present:
        return CompletenessStatus.PARTIAL
    return CompletenessStatus.MISSING


def assess_completeness(sections: dict[str, Any]) -> KnowledgeCompleteness:
    """Score which IFI inputs are present. Missing → reduced completeness, not invention."""
    missing: list[str] = []

    def has(key: str, *, min_n: int = 1) -> tuple[bool, bool]:
        val = sections.get(key)
        if val is None:
            missing.append(key)
            return False, False
        if isinstance(val, list):
            ok = len(val) >= min_n
            if not ok:
                missing.append(key)
            return ok, len(val) >= max(min_n, 3)
        if isinstance(val, dict):
            ok = bool(val) and not val.get("missing")
            if not ok:
                missing.append(key)
            return ok, ok and len(val) >= 3
        ok = bool(val)
        if not ok:
            missing.append(key)
        return ok, ok

    ck, ck_rich = has("current_knowledge")
    hi, hi_rich = has("historical_intelligence")
    si, si_rich = has("sector_intelligence")
    mi, mi_rich = has("macro_intelligence")
    rel, rel_rich = has("relationship_intelligence", min_n=1)
    mon, mon_rich = has("monitoring_events", min_n=1)
    res, res_rich = has("research_intelligence")
    ana, ana_rich = has("historical_analogues", min_n=1)
    # Pattern intelligence is Sprint 8.5 — expected missing until then
    pat_val = sections.get("pattern_intelligence") or {}
    pat_present = bool(pat_val) and not pat_val.get("missing") and not pat_val.get("deferred")
    if not pat_present:
        missing.append("pattern_intelligence")

    statuses = [
        _status(ck, rich=ck_rich),
        _status(hi, rich=hi_rich),
        _status(si, rich=si_rich),
        _status(mi, rich=mi_rich),
        _status(rel, rich=rel_rich),
        _status(mon, rich=mon_rich),
        _status(res, rich=res_rich),
        _status(ana, rich=ana_rich),
        CompletenessStatus.COMPLETE if pat_present else CompletenessStatus.MISSING,
    ]
    rank = {
        CompletenessStatus.COMPLETE: 1.0,
        CompletenessStatus.PARTIAL: 0.6,
        CompletenessStatus.SPARSE: 0.3,
        CompletenessStatus.MISSING: 0.0,
    }
    score = round(sum(rank[s] for s in statuses) / len(statuses), 4)
    if score >= 0.85:
        overall = CompletenessStatus.COMPLETE
    elif score >= 0.55:
        overall = CompletenessStatus.PARTIAL
    elif score >= 0.25:
        overall = CompletenessStatus.SPARSE
    else:
        overall = CompletenessStatus.MISSING

    # Dedup missing while preserving order
    seen: set[str] = set()
    missing_unique = []
    for m in missing:
        if m not in seen:
            seen.add(m)
            missing_unique.append(m)

    return KnowledgeCompleteness(
        company_knowledge=_status(ck, rich=ck_rich),
        historical_coverage=_status(hi, rich=hi_rich),
        sector_intelligence=_status(si, rich=si_rich),
        macro_intelligence=_status(mi, rich=mi_rich),
        relationships=_status(rel, rich=rel_rich),
        monitoring_current=_status(mon, rich=mon_rich),
        research_current=_status(res, rich=res_rich),
        historical_analogues=_status(ana, rich=ana_rich),
        pattern_intelligence=(
            CompletenessStatus.COMPLETE if pat_present else CompletenessStatus.MISSING
        ),
        overall=overall,
        missing_evidence=missing_unique,
        score=score,
    )
