"""Production façades for Institutional Knowledge Tables (IKT)."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_tables.schema import IKT_SPEC, IKT_VERSION, IKT_WORKSTREAM_ID, TABLE_DEFS
from institutional_knowledge_tables.store import (
    company_record,
    get_field_history,
    get_table,
    list_companies,
    upsert_fact,
)
from institutional_knowledge_tables.sync import (
    sync_company_master,
    sync_knowledge_metadata,
    sync_universe_company_master,
)
from institutional_knowledge_tables.bulk_sheet import ingest_company_sheet
from institutional_knowledge_tables.seed_capital_iq import seed_if_needed


def health() -> dict[str, Any]:
    companies = list_companies()
    return {
        "ok": True,
        "workstream_id": IKT_WORKSTREAM_ID,
        "version": IKT_VERSION,
        "spec": IKT_SPEC,
        "table_count": len(TABLE_DEFS),
        "companies_with_facts": len(companies),
        "mission": (
            "Documents are evidence; these tables are the memory. Never fabricate — "
            "missing fields stay NULL with lineage to the source that would fill them."
        ),
    }


def tables_catalog() -> dict[str, Any]:
    return {
        "ok": True,
        "version": IKT_VERSION,
        "tables": [
            {
                "table": name,
                "label": meta.get("label"),
                "fields": list(meta.get("fields") or []),
                "keyed_by_period": bool(meta.get("keyed_by_period")),
            }
            for name, meta in TABLE_DEFS.items()
        ],
    }


def get_company_tables(ticker: str) -> dict[str, Any]:
    return company_record(ticker)


def get_company_table(ticker: str, table: str, *, period: str | None = None) -> dict[str, Any]:
    return get_table(ticker, table, period=period)


def get_field_timeline(ticker: str, table: str, field: str, *, period: str | None = None) -> dict[str, Any]:
    history = get_field_history(ticker, table, field, period=period)
    return {
        "ok": True,
        "ticker": str(ticker or "").upper(),
        "table": table,
        "field": field,
        "period": period,
        "history": history,
        "version_count": len(history),
    }


def record_fact(
    ticker: str,
    table: str,
    field: str,
    value: Any,
    *,
    source: str,
    effective_date: str | None = None,
    period: str | None = None,
    trigger: str = "manual",
) -> dict[str, Any]:
    """Admin / collector write path — always requires an evidence source."""
    return upsert_fact(
        ticker,
        table,
        field,
        value,
        source=source,
        effective_date=effective_date,
        period=period,
        trigger=trigger,
    )


def soft_slice_for_ask_agi(question: str = "", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Metadata only — Ask AGI should read structured tables, not raw PDFs."""
    _ = question
    ticker = (payload or {}).get("ticker")
    if not ticker:
        return {"institutional_knowledge_tables": {"enabled": True, "table_count": len(TABLE_DEFS)}}
    rec = company_record(ticker)
    return {
        "institutional_knowledge_tables": {
            "enabled": True,
            "ticker": rec.get("ticker"),
            "populated_tables": rec.get("populated_tables"),
            "coverage_of_24": f"{len(rec.get('populated_tables') or [])}/{len(TABLE_DEFS)}",
        }
    }


def rebuild_company_tables(ticker: str) -> dict[str, Any]:
    """Ops action — refresh company_master (real) + knowledge_metadata (soft) for one ticker."""
    master = sync_company_master(ticker)
    metadata = sync_knowledge_metadata(ticker)
    return {"ok": bool(master.get("ok")), "ticker": str(ticker or "").upper(), "master": master, "metadata": metadata}


def onboard_universe(*, scope: str = "nifty500", limit: int | None = None) -> dict[str, Any]:
    """Onboard every company in the uploaded universe file into IKT company_master."""
    return sync_universe_company_master(scope=scope, limit=limit)


def seed_capital_iq_status(*, force: bool = False) -> dict[str, Any]:
    """Ops action — (re-)run the committed Capital IQ export seed. Runs
    synchronously (unlike the background-threaded boot-time call in
    app/main.py) so an operator gets the real resolved/unresolved counts
    back immediately. Safe to call repeatedly; idempotent unless force=True."""
    return seed_if_needed(force=force)


def upload_company_sheet(
    *,
    filename: str,
    content_base64: str | None = None,
    content_bytes: bytes | None = None,
    sheet_name: Any = 0,
    dry_run: bool = False,
    actor: str | None = None,
    column_names: list[str] | None = None,
) -> dict[str, Any]:
    """Bulk-ingest a company-info Excel/CSV into IKT. Never fabricates a
    ticker match — unresolved rows are reported, not guessed.

    `column_names`: reuse the header row from a sibling upload when this
    file is a headerless continuation batch of the same export.
    """
    import base64

    if content_bytes is None:
        if not content_base64:
            return {"ok": False, "error": "content_base64 or content_bytes required"}
        try:
            content_bytes = base64.b64decode(content_base64)
        except Exception as exc:
            return {"ok": False, "error": f"invalid_base64:{exc}"}
    result = ingest_company_sheet(
        content_bytes,
        filename,
        sheet_name=sheet_name,
        dry_run=dry_run,
        source_label=f"bulk_upload:{filename}" + (f" (by {actor})" if actor else ""),
        column_names=column_names,
    )
    return result


__all__ = [
    "get_company_table",
    "get_company_tables",
    "get_field_timeline",
    "health",
    "onboard_universe",
    "rebuild_company_tables",
    "record_fact",
    "soft_slice_for_ask_agi",
    "tables_catalog",
    "upload_company_sheet",
]
