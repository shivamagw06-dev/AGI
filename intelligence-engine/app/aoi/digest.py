"""Daily learning digest — permanent institutional summary."""

from __future__ import annotations

import datetime as _dt

from app.aoi.models import DailyLearningDigest
from app.aoi.store import AoiStore


def build_daily_digest(store: AoiStore, *, as_of: str | None = None) -> DailyLearningDigest:
    day = as_of or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    companies = {a.company_id for a in store.artifacts.values() if a.company_id}
    earnings = sum(1 for a in store.artifacts.values() if "earnings" in a.doc_type or "quarter" in a.doc_type)
    macro = sum(1 for a in store.artifacts.values() if (a.metadata or {}).get("macro") or a.company_id is None)
    guidance = sum(1 for d in store.diffs if "guidance" in d.change_type or d.field == "guidance")
    promoter = sum(1 for d in store.diffs if "promoter" in d.change_type or "shareholding" in d.field)
    board = sum(1 for d in store.diffs if "board" in d.change_type or d.field in {"board", "management"})
    acquisitions = sum(1 for d in store.diffs if d.change_type == "acquisition" or "acquisition" in (d.new_value or "").lower())

    highlights = [
        f"{len(companies)} companies updated",
        f"{earnings} earnings-related documents",
        f"{acquisitions} acquisitions detected",
        f"{guidance} guidance revisions",
        f"{promoter} promoter/shareholding changes",
        f"{board} board appointments / management changes",
        f"{macro} macro releases",
        f"{len(store.facts)} structured facts in corpus",
    ]
    digest = DailyLearningDigest(
        as_of=day,
        companies_updated=len(companies),
        earnings_released=earnings,
        acquisitions=acquisitions,
        guidance_revisions=guidance,
        promoter_changes=promoter,
        board_appointments=board,
        macro_releases=macro,
        documents_ingested=len(store.artifacts),
        facts_extracted=len(store.facts),
        highlights=highlights,
    )
    store.digests.append(digest)
    store.audit_event("daily_digest_created", object_kind="digest", object_id=digest.digest_id, detail=day)
    return digest
