"""Version history — never overwrite; append reconstructable snapshots."""

from __future__ import annotations

import datetime as _dt

from app.aoi.models import ExtractedFact, KnowledgeVersion
from app.aoi.store import AoiStore


def label_for_artifact(doc_type: str, title: str = "") -> str:
    dt = (doc_type or "").lower()
    year = _dt.datetime.now(_dt.timezone.utc).year
    if "annual" in dt:
        return f"Annual FY{str(year)[2:]}"
    if "quarter" in dt or "result" in dt:
        # Heuristic quarter label
        month = _dt.datetime.now(_dt.timezone.utc).month
        q = (month - 1) // 3 + 1
        return f"Q{q} FY{str(year)[2:]}"
    if title:
        return title[:80]
    return dt or "update"


def append_version(
    store: AoiStore,
    *,
    company_id: str,
    fact_ids: list[str],
    artifact_ids: list[str],
    label: str,
    change_summary: list[str],
) -> KnowledgeVersion:
    version = KnowledgeVersion(
        company_id=company_id,
        label=label,
        period=label,
        fact_ids=fact_ids,
        artifact_ids=artifact_ids,
        change_summary=change_summary[:20],
    )
    store.add_version(version)
    store.audit_event(
        "knowledge_version_created",
        object_kind="company",
        object_id=company_id,
        detail=label,
    )
    return version


def company_timeline(store: AoiStore, company_id: str) -> list[KnowledgeVersion]:
    return list(store.versions.get(company_id) or [])


def latest_facts_by_field(store: AoiStore, company_id: str) -> dict[str, ExtractedFact]:
    latest: dict[str, ExtractedFact] = {}
    for fact in store.fact_history:
        if fact.company_id != company_id:
            continue
        prev = latest.get(fact.field)
        if prev is None or fact.version >= prev.version:
            latest[fact.field] = fact
    return latest
