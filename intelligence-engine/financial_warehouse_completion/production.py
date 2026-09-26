"""API-facing FWCP surface."""

from __future__ import annotations

from typing import Any, Optional

from financial_warehouse_completion import audit, coverage, import_runtime, upstox_fill, yahoo_fill
from financial_warehouse_completion.capital_iq_import import import_framework_status, run_capital_iq_stage
from financial_warehouse_completion.models import ENGINE_CODE, PROGRAMME_CODE, PROGRAMME_VERSION, TARGETS
from financial_warehouse_completion.share_count import sync_symbol as sync_share_count


def health() -> dict[str, Any]:
    st = import_runtime.status()
    return {
        "ok": True,
        "programme": PROGRAMME_CODE,
        "engine": ENGINE_CODE,
        "version": PROGRAMME_VERSION,
        "role": "institutional_financial_warehouse_completion",
        "creates_intelligence": False,
        "vendor_historical_multiples": False,
        "primary_sources": ["capital_iq", "upstox", "financial_connector"],
        "secondary_sources": ["yahoo_finance", "warehouse_history"],
        "validation": ["formula_engine", "dqiv", "fwcp_dqiv_rules"],
        "targets": TARGETS,
        "runtime": st.get("runtime"),
        "endpoints": [
            "/v1/warehouse/financial-coverage",
            "/v1/warehouse/financial-audit",
            "/v1/warehouse/coverage/summary",
            "/v1/warehouse/coverage/sector",
            "/v1/warehouse/missing-financials",
            "/v1/warehouse/company/{symbol}/coverage",
            "/v1/warehouse/missing-statements",
            "/v1/warehouse/missing-share-count",
            "/v1/warehouse/yahoo-fill/status",
            "/v1/warehouse/yahoo-fill/board",
            "/v1/warehouse/yahoo-fill/queue",
            "/v1/warehouse/yahoo-fill/probe",
            "/v1/warehouse/yahoo-fill/start",
            "/v1/warehouse/yahoo-fill/run",
            "/v1/warehouse/yahoo-fill/stop",
            "/v1/warehouse/upstox-fill/queue",
            "/v1/warehouse/upstox-fill/board",
            "/v1/warehouse/import/start",
            "/v1/warehouse/import/retry",
            "/v1/warehouse/import/status",
            "/v1/warehouse/import/run",
            "/v1/warehouse/import/stop",
            "/v1/warehouse/import/board",
            "/v1/fwcp/health",
        ],
    }


def financial_coverage() -> dict[str, Any]:
    return coverage.financial_coverage()


def financial_audit() -> dict[str, Any]:
    """Phase 7.4F Step 0 — full read-only coverage board."""
    return audit.run_audit()


def coverage_summary() -> dict[str, Any]:
    return audit.audit_summary()


def coverage_sector() -> dict[str, Any]:
    return audit.audit_sector()


def missing_financials(limit: int = 500, classification: Optional[str] = None) -> dict[str, Any]:
    return audit.missing_financials(limit=limit, classification=classification)


def company_coverage(symbol: str) -> dict[str, Any]:
    base = coverage.company_coverage(symbol)
    try:
        detail = audit.company_audit(symbol)
        base["audit"] = {
            "classification": detail.get("classification"),
            "annual": {
                "earliest": (detail.get("annual") or {}).get("earliest"),
                "latest": (detail.get("annual") or {}).get("latest"),
                "years": (detail.get("annual") or {}).get("years"),
                "missing_years": (detail.get("annual") or {}).get("missing_years"),
                "has_consolidated": (detail.get("annual") or {}).get("has_consolidated"),
                "has_standalone": (detail.get("annual") or {}).get("has_standalone"),
            },
            "quarterly": {
                "earliest": (detail.get("quarterly") or {}).get("earliest"),
                "latest": (detail.get("quarterly") or {}).get("latest"),
                "quarters": (detail.get("quarterly") or {}).get("quarters"),
            },
            "share_count": detail.get("share_count"),
            "missing_fields": detail.get("missing_fields"),
            "needs_backfill": detail.get("needs_backfill"),
            "agib_standard": detail.get("agib_standard"),
        }
        base["phase"] = "7.4F-step0"
        base["read_only"] = True
    except Exception as exc:
        base["audit"] = {"ok": False, "error": str(exc)[:200]}
    return base


def missing_statements(limit: int = 500) -> dict[str, Any]:
    return coverage.missing_statements(limit=limit)


def missing_share_count(limit: int = 500) -> dict[str, Any]:
    return coverage.missing_share_count(limit=limit)


def import_status() -> dict[str, Any]:
    return import_runtime.status()


def import_board() -> dict[str, Any]:
    return import_runtime.board()


def import_start(batch: int = 15, actor: str = "fwcp") -> dict[str, Any]:
    return import_runtime.start(batch=batch, actor=actor)


def import_stop() -> dict[str, Any]:
    return import_runtime.stop()


def import_resume(batch: int = 15, actor: str = "fwcp") -> dict[str, Any]:
    return import_runtime.resume(batch=batch, actor=actor)


def import_retry(limit: int = 50, actor: str = "fwcp") -> dict[str, Any]:
    return import_runtime.retry(limit=limit, actor=actor)


def import_run(
    *,
    batch: int = 10,
    symbols: Optional[list[str]] = None,
    actor: str = "fwcp",
    include_capital_iq: bool = False,
) -> dict[str, Any]:
    return import_runtime.run_batch(
        batch=batch,
        symbols=symbols,
        actor=actor,
        include_capital_iq=include_capital_iq,
    )


def capital_iq() -> dict[str, Any]:
    return import_framework_status()


def run_capital_iq(limit: Optional[int] = None, actor: str = "fwcp") -> dict[str, Any]:
    return run_capital_iq_stage(limit=limit, actor=actor)


def capiq_workbook_status() -> dict[str, Any]:
    from financial_warehouse_completion.capiq_workbook import preview
    return preview()


def stage_capiq_workbook(*, years: Optional[list[int]] = None) -> dict[str, Any]:
    from financial_warehouse_completion.capiq_workbook import audit_preview
    return audit_preview(years=years or tuple(range(2017, 2027)))


def run_capiq_workbook(*, years: Optional[list[int]] = None, actor: str = "fwcp") -> dict[str, Any]:
    from financial_warehouse_completion.capiq_workbook import import_completed_years
    return import_completed_years(years=years, actor=actor)


def sector_ratio_workbook_status() -> dict[str, Any]:
    from financial_warehouse_completion.sector_ratio_workbook import preview
    return preview()


def run_sector_ratio_workbook(*, actor: str = "fwcp") -> dict[str, Any]:
    from financial_warehouse_completion.sector_ratio_workbook import import_history
    return import_history(actor=actor)


def sync_shares(symbol: str, actor: str = "fwcp") -> dict[str, Any]:
    return sync_share_count(symbol, actor=actor)


# ---------------------------------------------------------------------------
# Yahoo-first fill (fast path for EMPTY / thin — not CapIQ 10y depth)
# ---------------------------------------------------------------------------


def yahoo_fill_status() -> dict[str, Any]:
    return yahoo_fill.status()


def yahoo_fill_board() -> dict[str, Any]:
    return yahoo_fill.board()


def yahoo_fill_queue(limit: int = 200, include_thin: bool = True) -> dict[str, Any]:
    return yahoo_fill.queue_candidates(limit=limit, include_thin=include_thin)


def yahoo_fill_start(
    *,
    batch: int = 25,
    actor: str = "yahoo_fill",
    pause_seconds: float = 0.35,
    include_thin: bool = True,
) -> dict[str, Any]:
    return yahoo_fill.start(
        batch=batch,
        actor=actor,
        pause_seconds=pause_seconds,
        include_thin=include_thin,
    )


def yahoo_fill_stop() -> dict[str, Any]:
    return yahoo_fill.stop()


def yahoo_fill_resume(
    *,
    batch: int = 25,
    actor: str = "yahoo_fill",
    pause_seconds: float = 0.35,
    include_thin: bool = True,
) -> dict[str, Any]:
    return yahoo_fill.resume(
        batch=batch,
        actor=actor,
        pause_seconds=pause_seconds,
        include_thin=include_thin,
    )


def yahoo_fill_run(
    *,
    batch: int = 25,
    symbols: Optional[list[str]] = None,
    actor: str = "yahoo_fill",
    pause_seconds: float = 0.35,
    include_thin: bool = True,
) -> dict[str, Any]:
    return yahoo_fill.run_batch(
        batch=batch,
        symbols=symbols,
        actor=actor,
        pause_seconds=pause_seconds,
        include_thin=include_thin,
    )


def yahoo_fill_company(symbol: str, actor: str = "yahoo_fill") -> dict[str, Any]:
    return yahoo_fill.fill_company(symbol, actor=actor)


def yahoo_fill_probe(symbol: str = "RELIANCE") -> dict[str, Any]:
    return yahoo_fill.probe(symbol)


def upstox_fill_queue(
    limit: int = 200,
    include_thin: bool = True,
    exclude: list[str] | None = None,
) -> dict[str, Any]:
    return upstox_fill.queue_candidates(limit=limit, include_thin=include_thin, exclude=exclude)


def upstox_fill_board() -> dict[str, Any]:
    return upstox_fill.board()
