"""Production surface for the Institutional Data Warehouse.

Everything the API, the admin workspace and the intelligence engines call goes
through this module. Two audiences:

* admin workspace — workbook, sheet reads, edits, imports, versions, audit
* intelligence modules — ``read_company`` / ``read_table`` contract reads
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from institutional_warehouse import (
    audit,
    db,
    importer,
    permissions,
    refresh,
    search,
    store,
    validation,
    versions,
)
from institutional_warehouse.formulas import recalculate
from institutional_warehouse.schema import TABS, find_tab, tab as get_tab, workbook as workbook_schema
from institutional_warehouse.values import now_iso

ENGINE = "institutional_warehouse"
VERSION = "warehouse-v1.0.0"


# --------------------------------------------------------------------------
# Health / schema
# --------------------------------------------------------------------------


def health() -> dict[str, Any]:
    info = db.info()
    counts = info.get("row_counts", {})
    populated = [k for k, v in counts.items() if v]
    return {
        "ok": True,
        "engine": ENGINE,
        "version": VERSION,
        "status": "ok" if populated else "empty",
        "dialect": info.get("dialect"),
        "database": info.get("url"),
        "tabs": len(TABS),
        "total_rows": info.get("total_rows", 0),
        "populated_tabs": populated,
        "row_counts": counts,
        "last_refresh": (refresh.recent_runs(1).get("runs") or [{}])[0].get("finished_at"),
        "checked_at": now_iso(),
    }


def workbook() -> dict[str, Any]:
    schema = workbook_schema()
    counts = db.info().get("row_counts", {})
    for tab in schema["tabs"]:
        tab["rows"] = counts.get(tab["id"], 0)
    return schema


def tab_schema(tab_id: str) -> dict[str, Any]:
    tab = find_tab(tab_id)
    if not tab:
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    return {"ok": True, **tab.to_dict(), "rows": store.row_count(tab.id)}


# --------------------------------------------------------------------------
# Sheet reads
# --------------------------------------------------------------------------


def sheet(
    tab_id: str,
    *,
    entity: Optional[str] = None,
    filters: Optional[dict[str, Any]] = None,
    q: Optional[str] = None,
    sort: Optional[str] = None,
    order: str = "asc",
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    if tab_id == "sector_evidence_matrix":
        from institutional_warehouse.sector_evidence import sync
        sync()
    page = store.fetch(tab_id, entity=entity, filters=filters, search=q, sort=sort,
                       order=order, limit=limit, offset=offset)
    tab = get_tab(tab_id)
    return {**page, "columns": [c.to_dict() for c in tab.columns], "mode": tab.mode,
            "read_only": tab.read_only, "append_only": tab.append_only}


def row(tab_id: str, row_id: str) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    found = store.get(tab_id, row_id)
    if not found:
        return {"ok": False, "error": "row_not_found"}
    return {"ok": True, "tab": tab_id, "row": found}


def stats() -> dict[str, Any]:
    return {
        "ok": True,
        "tabs": [store.tab_stats(t.id) for t in TABS],
        "audit": audit.summary(),
        "imports": importer.recent_imports(limit=5),
        "refreshes": refresh.recent_runs(limit=5),
    }


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------


def edit(
    tab_id: str,
    edits: Sequence[dict[str, Any]],
    *,
    actor: str,
    reason: Optional[str] = None,
    recalc: bool = True,
) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    denied = permissions.require(actor, "edit")
    if denied:
        return denied
    result = store.set_cells(tab_id, list(edits or []), actor=actor, reason=reason)
    if result.get("ok") and result.get("applied") and recalc:
        result["recalculated"] = recalculate(actor=actor, stages=importer.stages_for(tab_id))
    return result


def create(tab_id: str, values: dict[str, Any], *, actor: str) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    denied = permissions.require(actor, "create")
    if denied:
        return denied
    report = validation.validate_payload(tab_id, [values or {}])
    if report["rejected"]:
        return {"ok": False, "error": "validation_failed", "issues": report["rejected"][0]["issues"]}
    return store.create_row(tab_id, values or {}, actor=actor)


def clear_override(tab_id: str, row_id: str, column: str, *, actor: str) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    denied = permissions.require(actor, "clear_override")
    if denied:
        return denied
    return store.clear_override(tab_id, row_id, column, actor=actor)


def delete(tab_id: str, row_ids: Sequence[str], *, actor: str, reason: Optional[str] = None) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    denied = permissions.require(actor, "delete")
    if denied:
        return denied
    return store.delete_rows(tab_id, list(row_ids or []), actor=actor, reason=reason)


def publish(tab_id: Optional[str] = None, *, actor: str) -> dict[str, Any]:
    denied = permissions.require(actor, "publish")
    if denied:
        return denied
    if tab_id:
        if not find_tab(tab_id):
            return {"ok": False, "error": f"unknown_tab:{tab_id}"}
        return store.publish(tab_id, actor=actor)
    return {"ok": True, "published": {t.id: store.publish(t.id, actor=actor)["published"] for t in TABS}}


# --------------------------------------------------------------------------
# Import / export
# --------------------------------------------------------------------------


def stage_import(
    tab_id: str,
    *,
    rows: Optional[Sequence[dict[str, Any]]] = None,
    text: Optional[str] = None,
    headers: Optional[Sequence[str]] = None,
    matrix: Optional[Sequence[Sequence[Any]]] = None,
    mapping: Optional[dict[str, Optional[str]]] = None,
    actor: str = "admin",
    source: str = "manual_import",
) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    denied = permissions.require(actor, "stage_import")
    if denied:
        return denied
    return importer.stage(tab_id, rows=rows, text=text, headers=headers, matrix=matrix,
                          mapping=mapping, actor=actor, source=source)


def commit_import(
    import_id: str,
    *,
    actor: str = "admin",
    recalculate: bool = True,
) -> dict[str, Any]:
    denied = permissions.require(actor, "commit_import")
    if denied:
        return denied
    return importer.commit(import_id, actor=actor, recalculate=recalculate)


def preview_mapping(tab_id: str, headers: Sequence[str]) -> dict[str, Any]:
    tab = find_tab(tab_id)
    if not tab:
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    return {"ok": True, "tab": tab.id, **importer.map_headers(tab, list(headers or []))}


def export(tab_id: str, **kwargs: Any) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    return importer.export_csv(tab_id, **kwargs)


def imports(tab_id: Optional[str] = None, limit: int = 25) -> dict[str, Any]:
    return importer.recent_imports(tab_id=tab_id, limit=limit)


# --------------------------------------------------------------------------
# Versions / audit
# --------------------------------------------------------------------------


def history(tab_id: str, row_id: str, *, column: Optional[str] = None) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    snapshots = versions.row_snapshots(tab_id, row_id)
    return {
        "ok": True,
        "tab": tab_id,
        "row_id": row_id,
        "current": store.get(tab_id, row_id),
        "cells": versions.cell_history(tab_id, row_id, column=column),
        "versions": snapshots,
        "latest_version": versions.latest_version(tab_id, row_id),
    }


def compare(tab_id: str, row_id: str, version_a: int, version_b: Optional[int] = None) -> dict[str, Any]:
    snapshots = {int(s["version"]): s for s in versions.row_snapshots(tab_id, row_id, limit=200)}
    if version_a not in snapshots:
        return {"ok": False, "error": f"version_not_found:{version_a}"}
    before = snapshots[version_a]["payload"]
    if version_b is None:
        current = store.get(tab_id, row_id) or {}
        after = {k: v for k, v in current.items() if k != "_meta"}
        label_b = "current"
    else:
        if version_b not in snapshots:
            return {"ok": False, "error": f"version_not_found:{version_b}"}
        after = snapshots[version_b]["payload"]
        label_b = str(version_b)
    return {
        "ok": True,
        "tab": tab_id,
        "row_id": row_id,
        "from": version_a,
        "to": label_b,
        "changes": versions.diff(before, after),
    }


def restore(tab_id: str, row_id: str, *, version: Optional[int] = None,
            snapshot_id: Optional[str] = None, actor: str) -> dict[str, Any]:
    if not find_tab(tab_id):
        return {"ok": False, "error": f"unknown_tab:{tab_id}"}
    denied = permissions.require(actor, "restore")
    if denied:
        return denied
    return store.restore(tab_id, row_id, version=version, snapshot_id=snapshot_id, actor=actor)


def audit_log(**kwargs: Any) -> dict[str, Any]:
    return audit.recent(**kwargs)


# --------------------------------------------------------------------------
# Validation / refresh / formulas
# --------------------------------------------------------------------------


def validate(tab_id: Optional[str] = None, *, sample: int = 300) -> dict[str, Any]:
    if tab_id:
        if not find_tab(tab_id):
            return {"ok": False, "error": f"unknown_tab:{tab_id}"}
        return validation.validate_tab(tab_id, sample=sample)
    report = validation.validate_all(sample=sample)
    report["duplicate_companies"] = validation.duplicate_companies()
    report["broken_references"] = validation.broken_references()
    return report


def run_refresh(**kwargs: Any) -> dict[str, Any]:
    denied = permissions.require(kwargs.get("actor"), "refresh")
    if denied:
        return denied
    return refresh.run(**kwargs)


def refresh_runs(limit: int = 20) -> dict[str, Any]:
    return refresh.recent_runs(limit=limit)


def quality_summary() -> dict[str, Any]:
    from institutional_warehouse.gateway import quality_summary as summary

    return summary()


def quarantined_rows(tab_id: Optional[str] = None, limit: int = 100) -> dict[str, Any]:
    from institutional_warehouse.gateway import quarantined

    return quarantined(tab_id, limit=limit)


def source_conflicts(**kwargs: Any) -> dict[str, Any]:
    from institutional_warehouse.conflicts import recent

    return recent(**kwargs)


def conflict_summary() -> dict[str, Any]:
    from institutional_warehouse.conflicts import summary

    return summary()


def remediate_zeros(*, actor: str, dry_run: bool = False) -> dict[str, Any]:
    from institutional_warehouse.gateway import remediate_missing_zeros

    denied = permissions.require(actor, "refresh")
    if denied:
        return denied
    return remediate_missing_zeros(actor=actor, dry_run=dry_run)


def statement_identity_coverage() -> dict[str, Any]:
    """Statement rows still carrying no statement type."""
    from institutional_warehouse import statement_identity

    return statement_identity.unidentified_summary()


def migrate_statement_identity(*, actor: str, dry_run: bool = True) -> dict[str, Any]:
    """Type and re-key statement rows written before statement_type was keyed."""
    from institutional_warehouse import statement_identity

    denied = permissions.require(actor, "refresh")
    if denied:
        return denied
    return statement_identity.backfill_identity(actor=actor, dry_run=dry_run)


def unit_coverage() -> dict[str, Any]:
    """How much of the warehouse has been through unit normalisation."""
    from institutional_warehouse import units

    return units.unstamped_summary()


def normalise_units(*, actor: str, dry_run: bool = True) -> dict[str, Any]:
    """Convert and stamp rows written before unit normalisation existed.

    Defaults to a dry run: this rescales stored values, so the plan should be
    read before it is applied.
    """
    from institutional_warehouse import units

    denied = permissions.require(actor, "refresh")
    if denied:
        return denied
    return units.backfill_units(actor=actor, dry_run=dry_run)


def scheduler_status() -> dict[str, Any]:
    from institutional_warehouse.scheduler import status

    return status()


# --------------------------------------------------------------------------
# Historical backfill (Phase 7.1a)
# --------------------------------------------------------------------------


def run_backfill(**kwargs: Any) -> dict[str, Any]:
    from institutional_warehouse.backfill.engine import run

    denied = permissions.require(kwargs.get("actor"), "refresh")
    if denied:
        return denied
    return run(**kwargs)


def backfill_status() -> dict[str, Any]:
    from institutional_warehouse.backfill.engine import status

    return status()


def backfill_jobs(limit: int = 20) -> dict[str, Any]:
    from institutional_warehouse.backfill.checkpoints import recent_jobs

    return {"ok": True, "jobs": recent_jobs(limit=limit)}


def historical_coverage(top: int = 25) -> dict[str, Any]:
    from institutional_warehouse.backfill.coverage import dashboard

    return dashboard(top=top)


# --------------------------------------------------------------------------
# Historical reads
# --------------------------------------------------------------------------


def history_series(symbol: str, metric: str, **kwargs: Any) -> dict[str, Any]:
    from institutional_warehouse.history import series

    return series(symbol, metric, **kwargs)


def history_company(symbol: str, **kwargs: Any) -> dict[str, Any]:
    from institutional_warehouse.history import company_history

    return company_history(symbol, **kwargs)


def history_as_at(symbol: str, on: str) -> dict[str, Any]:
    from institutional_warehouse.history import as_at

    return as_at(symbol, on)


def history_range(tab_id: str, **kwargs: Any) -> dict[str, Any]:
    from institutional_warehouse.history import range_query

    return range_query(tab_id, **kwargs)


def history_compare(symbols: Sequence[str], metric: str, **kwargs: Any) -> dict[str, Any]:
    from institutional_warehouse.history import compare

    return compare(symbols, metric, **kwargs)


def history_coverage(symbol: str) -> dict[str, Any]:
    from institutional_warehouse.history import coverage as company_coverage

    return company_coverage(symbol)


def recompute(**kwargs: Any) -> dict[str, Any]:
    denied = permissions.require(kwargs.get("actor"), "recalculate")
    if denied:
        return denied
    return recalculate(**kwargs)


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------


def global_search(query: str, **kwargs: Any) -> dict[str, Any]:
    return search.search(query, **kwargs)


def company(symbol: str, **kwargs: Any) -> dict[str, Any]:
    return search.company_view(symbol, **kwargs)


def suggest(prefix: str, limit: int = 10) -> dict[str, Any]:
    return search.suggest(prefix, limit=limit)


def whoami(actor: Optional[str]) -> dict[str, Any]:
    return permissions.describe(actor)


# --------------------------------------------------------------------------
# Contract reads for intelligence modules
# --------------------------------------------------------------------------


def read_table(tab_id: str, *, entity: Optional[str] = None, limit: int = 500) -> list[dict[str, Any]]:
    """Effective rows for engine consumers (UKO, Ask, valuation, hedge fund)."""
    if not find_tab(tab_id):
        return []
    return store.all_rows(tab_id, entity=entity, limit=limit)


def read_company(symbol: str) -> dict[str, Any]:
    """One company's warehouse record, shaped for the intelligence layer."""
    view = search.company_view(symbol, per_tab=8)
    if not view.get("ok"):
        return view
    sheets = view.get("sheets") or {}

    def _first(tab_id: str) -> Optional[dict[str, Any]]:
        rows = (sheets.get(tab_id) or {}).get("rows") or []
        return rows[0] if rows else None

    symbol_key = view.get("symbol") or symbol
    provider_ratios = None
    try:
        from valuation_ratios.ingest import latest_provider_ratios

        provider_ratios = latest_provider_ratios(str(symbol_key))
    except Exception:
        provider_ratios = None

    # The overview view is intentionally compact, so load the annual series
    # independently. This makes the choice stable even when many vendors have
    # written the same company-year to the append-only warehouse.
    annual_rows = store.all_rows("financials_annual", entity=str(symbol_key), limit=80)
    from institutional_warehouse.financials import canonical_statement_series
    annual_series = canonical_statement_series(
        annual_rows, period_key="fiscal_year", annual=True
    )

    return {
        "ok": True,
        "symbol": view.get("symbol"),
        "master": view.get("master"),
        "valuation": _first("historical_valuation"),
        "factors": _first("hedge_fund_factors"),
        "ratios": _first("historical_ratios"),
        "provider_ratios": provider_ratios,
        "consensus": _first("consensus"),
        "latest_price": _first("daily_market_history"),
        "latest_annual": annual_series[-1] if annual_series else _first("financials_annual"),
        "annual_history": annual_series,
        "latest_quarter": _first("financials_quarterly"),
        "ownership": _first("ownership"),
        "intelligence": _first("company_intelligence"),
        "timeline": (sheets.get("research_timeline") or {}).get("rows", [])[:6],
        "research": (sheets.get("research_intelligence") or {}).get("rows", [])[:4],
        "coverage": view.get("coverage"),
        "source": ENGINE,
    }


def coverage() -> dict[str, Any]:
    counts = db.info().get("row_counts", {})
    companies = len(store.entities("company_master"))
    return {
        "ok": True,
        "companies": companies,
        "row_counts": counts,
        "total_rows": sum(counts.values()),
        "quality": validation.validate_all(sample=100),
    }


def repair_upstox_quarterly(
    *, actor: str = "admin", apply: bool = False, row_ids: list[str] | None = None
) -> dict[str, Any]:
    from institutional_warehouse.upstox_repair import repair_annual_as_quarterly
    from observability import memory_stages as ms

    with ms.stage("price_repair_batch", apply=bool(apply),
                  explicit_rows=len(row_ids or [])) as detail:
        result = repair_annual_as_quarterly(actor=actor, apply=apply, row_ids=row_ids)
        if isinstance(result, dict):
            detail["rows"] = result.get("repaired") or result.get("rows")
            detail["examined"] = result.get("examined") or result.get("candidates")
        return result
