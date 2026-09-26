"""Incremental learning — structured old vs new diffs."""

from __future__ import annotations

from app.aoi.models import ExtractedFact, StructuredDiff
from app.aoi.store import AoiStore
from app.aoi.versioning import latest_facts_by_field


_WATCH_FIELDS = {
    "guidance",
    "risks",
    "opportunities",
    "margins",
    "capex",
    "shareholding",
    "management",
    "promoters",
    "board",
    "capacity",
    "expansion",
    "m&a",
}


def detect_diffs(
    store: AoiStore,
    *,
    company_id: str,
    new_facts: list[ExtractedFact],
    source_document_id: str = "",
) -> list[StructuredDiff]:
    prior = latest_facts_by_field(store, company_id)
    # Exclude the facts we are about to add from "prior" by comparing values
    diffs: list[StructuredDiff] = []
    for fact in new_facts:
        if fact.company_id != company_id:
            continue
        field = fact.field
        old = prior.get(field)
        old_text = (old.value_text if old else "") or ""
        new_text = fact.value_text or ""
        if not old:
            if field in _WATCH_FIELDS or field.startswith("macro_") or "guidance" in field:
                diff = StructuredDiff(
                    company_id=company_id,
                    field=field,
                    old_value="",
                    new_value=new_text[:500],
                    change_type="new",
                    source_document_id=source_document_id or fact.document_id,
                )
                diffs.append(diff)
                store.add_diff(diff)
            continue
        if old_text.strip() and new_text.strip() and old_text.strip() != new_text.strip():
            change_type = "updated"
            if "guidance" in field:
                change_type = "guidance_revision"
            elif "shareholding" in field or "promoter" in field:
                change_type = "promoter_or_shareholding_change"
            elif "board" in field or "management" in field:
                change_type = "board_or_management_change"
            elif "acquisition" in new_text.lower() or "m&a" in field:
                change_type = "acquisition"
            diff = StructuredDiff(
                company_id=company_id,
                field=field,
                old_value=old_text[:500],
                new_value=new_text[:500],
                change_type=change_type,
                source_document_id=source_document_id or fact.document_id,
            )
            diffs.append(diff)
            store.add_diff(diff)
            # Link version lineage
            fact.previous_fact_id = old.fact_id
            fact.version = int(old.version or 1) + 1
    return diffs
