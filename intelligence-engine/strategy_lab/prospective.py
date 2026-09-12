"""Prospective point-in-time capture and daily strategy readiness reporting.

Legacy rows are never backdated. If AGI first observed a fact in 2026, its
``available_from`` is 2026 even when the financial period ended years earlier.
That rule turns useful legacy data into honest forward evidence without
pretending it was available to a historical backtest.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from institutional_warehouse import db, store
from strategy_lab.contracts import content_hash, utc_now
from strategy_lab.definitions import all_definitions


CONFIRMATION = "CAPTURE_PROSPECTIVE_EVIDENCE"
SOURCE = "strategy_prospective_capture"
FUNDAMENTAL_METRICS = (
    "revenue", "gross_profit", "ebitda", "ebit", "pbt", "pat", "assets",
    "equity", "debt", "cash", "capex", "cfo", "free_cash_flow",
    "shares_outstanding", "book_value",
)
VALUATION_METRICS = (
    "cmp", "market_cap", "enterprise_value", "pe", "forward_pe", "pb",
    "ev_ebitda", "ev_sales", "price_sales", "dividend_yield", "roe",
    "roce", "roa", "beta",
)


def _today(value: str | None = None) -> str:
    return str(value or datetime.now(timezone.utc).date().isoformat())[:10]


def _query(tab_id: str, where: str = "1=1", params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    db.init()
    return db.query(f"SELECT * FROM {db.physical_table(tab_id)} WHERE {where}", params)


def _scalar(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    rows = db.query(sql, params)
    return rows[0] if rows else {}


def _availability(row: Mapping[str, Any]) -> str:
    # sys_created_at is the first defensible claim about when AGI possessed a
    # legacy row. A later warehouse revision is available from sys_updated_at.
    # Never substitute period_end or filing_date here.
    return str(row.get("sys_updated_at") or row.get("sys_created_at") or row.get("last_updated") or utc_now())


def _chunks(rows: list[dict[str, Any]], size: int = 1000) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def _write(tab_id: str, rows: list[dict[str, Any]], *, actor: str, reason: str) -> dict[str, int]:
    totals = {"inserted": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for chunk in _chunks(rows):
        result = store.upsert(tab_id, chunk, source=SOURCE, actor=actor, reason=reason)
        for key in totals:
            totals[key] += int(result.get(key) or 0)
    return totals


def _fundamental_observations() -> list[dict[str, Any]]:
    rows = _query(
        "financials_annual",
        "source = ? AND sys_unit_method = ? AND fiscal_year IS NOT NULL",
        ("capital_iq_workbook", "declared"),
    )
    output = []
    for row in rows:
        available = _availability(row)
        period_end = row.get("fiscal_end_date") or row.get("period_key")
        if not period_end:
            fiscal = str(row.get("fiscal_year") or "")
            digits = "".join(character for character in fiscal if character.isdigit())
            period_end = f"{digits[-4:]}-03-31" if len(digits) >= 4 else available[:10]
        for metric in FUNDAMENTAL_METRICS:
            value = row.get(metric)
            if value is None:
                continue
            identity = {
                "source_row_id": row.get("row_id"),
                "source_version": row.get("sys_version"),
                "metric": metric,
                "available_from": available,
            }
            output.append({
                "observation_id": content_hash(identity)[:32],
                "company_id": row.get("symbol"),
                "metric_id": metric,
                "period_end": str(period_end)[:10],
                "value": value,
                "currency": "INR",
                "unit": row.get("sys_reported_unit") or "inr_million",
                "announcement_date": row.get("filing_date") or row.get("effective_date"),
                "available_from": available,
                "source": row.get("source"),
                "source_document": row.get("source_document"),
                "revision_id": f"warehouse-v{row.get('sys_version') or 1}",
                "is_restatement": bool(row.get("restated")),
                "provider": "capital_iq",
                "parser_path": "master_10y_workbook",
            })
    return output


def _valuation_observations(as_of: str) -> list[dict[str, Any]]:
    latest = _scalar(
        f"SELECT MAX(date) AS day FROM {db.physical_table('historical_valuation')} WHERE date <= ?",
        (as_of,),
    ).get("day")
    if not latest:
        return []
    rows = _query("historical_valuation", "date = ?", (latest,))
    output = []
    for row in rows:
        available = _availability(row)
        for metric in VALUATION_METRICS:
            value = row.get(metric)
            if value is None:
                continue
            output.append({
                "observation_id": content_hash({
                    "source_row_id": row.get("row_id"), "source_version": row.get("sys_version"),
                    "metric": metric, "available_from": available,
                })[:32],
                "company_id": row.get("symbol"),
                "metric_id": f"valuation.{metric}",
                "period_end": str(latest)[:10],
                "value": value,
                "currency": "INR" if metric in {"cmp", "market_cap", "enterprise_value"} else None,
                "unit": "ratio_or_reported_value",
                "announcement_date": None,
                "available_from": available,
                "source": row.get("source"),
                "source_document": None,
                "revision_id": f"warehouse-v{row.get('sys_version') or 1}",
                "is_restatement": False,
                "provider": "warehouse",
                "parser_path": "daily_valuation_snapshot",
            })
    return output


def _corporate_action_observations() -> list[dict[str, Any]]:
    rows = _query("corporate_actions")
    output = []
    for row in rows:
        kind = str(row.get("action_type") or "unknown").lower()
        value = next((row.get(field) for field in ("dividend", "split", "bonus", "rights", "buyback") if row.get(field) is not None), 1.0)
        available = _availability(row)
        effective = row.get("effective_date") or row.get("action_date") or available[:10]
        output.append({
            "observation_id": content_hash({
                "source_row_id": row.get("row_id"), "source_version": row.get("sys_version"),
                "kind": kind, "available_from": available,
            })[:32],
            "company_id": row.get("symbol"),
            "metric_id": f"corporate_action.{kind}",
            "period_end": str(effective)[:10],
            "value": value,
            "currency": "INR" if kind in {"dividend", "buyback"} else None,
            "unit": "per_share" if kind == "dividend" else "action_ratio",
            "announcement_date": row.get("announcement_date"),
            "available_from": available,
            "source": row.get("source"),
            "source_document": row.get("details"),
            "revision_id": f"warehouse-v{row.get('sys_version') or 1}",
            "is_restatement": False,
            "provider": row.get("source"),
            "parser_path": "corporate_actions_warehouse",
        })
    return output


def _update_universe(as_of: str, *, actor: str, apply: bool) -> dict[str, Any]:
    current_rows = _query("company_master", "active = 1")
    current = {str(row.get("symbol")): row for row in current_rows if row.get("symbol")}
    existing = _query("universe_membership_history", "index_id = ? AND effective_to IS NULL", ("NSE_INVESTABLE_PROSPECTIVE",))
    open_by_company = {str(row.get("company_id")): row for row in existing}
    additions = []
    closures = []
    for symbol, row in current.items():
        if symbol in open_by_company:
            continue
        additions.append({
            "company_id": symbol,
            "index_id": "NSE_INVESTABLE_PROSPECTIVE",
            "effective_from": as_of,
            "effective_to": None,
            "investable": True,
            "status": row.get("market_status") or "ACTIVE",
            "security_id": row.get("instrument_key"),
            "isin": row.get("isin"),
            "source": SOURCE,
            "source_document": "daily_company_master_snapshot",
        })
    previous_day = (date.fromisoformat(as_of) - timedelta(days=1)).isoformat()
    for symbol, row in open_by_company.items():
        if symbol in current:
            continue
        closures.append({
            "company_id": symbol,
            "index_id": row.get("index_id"),
            "effective_from": row.get("effective_from"),
            "effective_to": previous_day,
            "investable": False,
            "status": "REMOVED_OR_INACTIVE",
            "security_id": row.get("security_id"),
            "isin": row.get("isin"),
            "source": SOURCE,
            "source_document": "daily_company_master_snapshot",
        })
    result = {"current": len(current), "additions": len(additions), "closures": len(closures)}
    if apply:
        result["write"] = _write(
            "universe_membership_history", additions + closures, actor=actor,
            reason="prospective_effective_dated_universe_snapshot",
        )
    return result


def readiness(as_of: str | None = None) -> dict[str, Any]:
    day = _today(as_of)
    db.init()
    annual = _scalar(
        f"SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN source = 'capital_iq_workbook' AND sys_unit_method = 'declared' THEN 1 ELSE 0 END) AS declared, "
        "SUM(CASE WHEN filing_date IS NOT NULL OR effective_date IS NOT NULL THEN 1 ELSE 0 END) AS dated, "
        "SUM(CASE WHEN pit_status = 'PIT_VALIDATED' THEN 1 ELSE 0 END) AS pit_validated "
        f"FROM {db.physical_table('financials_annual')}"
    )
    pit = _scalar(
        f"SELECT COUNT(*) AS total, COUNT(DISTINCT company_id) AS companies, "
        "MIN(substr(available_from,1,10)) AS first_available, MAX(substr(available_from,1,10)) AS last_available "
        f"FROM {db.physical_table('point_in_time_observations')}"
    )
    universe = _scalar(
        f"SELECT COUNT(*) AS total, COUNT(DISTINCT company_id) AS companies, "
        "MIN(effective_from) AS first_effective, MAX(effective_from) AS last_effective, "
        "SUM(CASE WHEN effective_to IS NOT NULL THEN 1 ELSE 0 END) AS closed_memberships "
        f"FROM {db.physical_table('universe_membership_history')}"
    )
    prices = _scalar(
        f"SELECT COUNT(*) AS total, COUNT(DISTINCT symbol) AS companies, MIN(date) AS first_date, MAX(date) AS last_date, "
        "SUM(CASE WHEN adjusted_close IS NOT NULL OR price_basis = 'ADJUSTED' THEN 1 ELSE 0 END) AS adjusted_rows "
        f"FROM {db.physical_table('daily_market_history')}"
    )
    actions = _scalar(
        f"SELECT COUNT(*) AS total, COUNT(DISTINCT symbol) AS companies, MIN(action_date) AS first_date, MAX(action_date) AS last_date, "
        "SUM(CASE WHEN confidence >= 0.8 THEN 1 ELSE 0 END) AS high_confidence "
        f"FROM {db.physical_table('corporate_actions')}"
    )
    valuation = _scalar(
        f"SELECT COUNT(*) AS total, COUNT(DISTINCT symbol) AS companies, MIN(date) AS first_date, MAX(date) AS last_date, "
        "SUM(CASE WHEN source LIKE 'warehouse_reconstruction%' THEN 1 ELSE 0 END) AS reconstructed "
        f"FROM {db.physical_table('historical_valuation')}"
    )
    first_pit = pit.get("first_available")
    pit_days = (date.fromisoformat(day) - date.fromisoformat(first_pit)).days if first_pit else 0
    first_universe = universe.get("first_effective")
    universe_days = (date.fromisoformat(day) - date.fromisoformat(first_universe)).days if first_universe else 0
    gates = {
        "data_completeness": "PASSED" if int(annual.get("declared") or 0) >= 10_000 else "PARTIAL",
        "point_in_time": "PASSED" if pit_days >= 5 * 365 and int(pit.get("companies") or 0) >= 500 else ("PARTIAL" if int(pit.get("total") or 0) else "MISSING"),
        "universe_integrity": "PASSED" if universe_days >= 5 * 365 and int(universe.get("closed_memberships") or 0) > 0 else ("PARTIAL" if int(universe.get("total") or 0) else "MISSING"),
        "corporate_actions": "PASSED" if int(actions.get("high_confidence") or 0) >= 1_000 else ("PARTIAL" if int(actions.get("total") or 0) else "MISSING"),
        "price_history": "PASSED" if int(prices.get("companies") or 0) >= 500 and int(prices.get("adjusted_rows") or 0) > 0 else "PARTIAL",
        "valuation_point_in_time": "PARTIAL" if int(valuation.get("total") or 0) else "MISSING",
    }
    strategies = []
    for item in all_definitions():
        strategies.append({
            "strategy_id": item.strategy_id,
            "role": item.role,
            "data_gate": "PASSED" if all(gates.get(key) == "PASSED" for key in ("data_completeness", "point_in_time", "universe_integrity", "corporate_actions", "price_history")) else "BLOCKED",
            "capital_allocation_allowed": False,
            "blockers": [key for key, state in gates.items() if state != "PASSED"],
        })
    report = {
        "ok": True,
        "as_of": day,
        "gates": gates,
        "counts": {"annual": annual, "point_in_time": pit, "universe": universe, "prices": prices, "corporate_actions": actions, "valuation": valuation},
        "strategies": strategies,
        "legacy_policy": "PIT_LIMITED and reconstructed history is excluded from validation; it remains available for descriptive research.",
        "capital_allocation_allowed": False,
    }
    report["report_hash"] = content_hash(report)
    return report


def capture(
    *,
    as_of: str | None = None,
    actor: str = "daily_validation_cron",
    confirm: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    day = _today(as_of)
    apply = not dry_run
    if apply and confirm != CONFIRMATION:
        raise ValueError(f"explicit_confirmation_required:{CONFIRMATION}")
    fundamentals = _fundamental_observations()
    valuations = _valuation_observations(day)
    actions = _corporate_action_observations()
    universe = _update_universe(day, actor=actor, apply=apply)
    result: dict[str, Any] = {
        "ok": True,
        "as_of": day,
        "mode": "APPLY" if apply else "DRY_RUN",
        "candidates": {"fundamentals": len(fundamentals), "valuation": len(valuations), "corporate_actions": len(actions)},
        "universe": universe,
    }
    if apply:
        result["writes"] = {
            "fundamentals": _write("point_in_time_observations", fundamentals, actor=actor, reason="prospective_fundamental_capture"),
            "valuation": _write("point_in_time_observations", valuations, actor=actor, reason="prospective_valuation_capture"),
            "corporate_actions": _write("point_in_time_observations", actions, actor=actor, reason="prospective_corporate_action_capture"),
        }
    report = readiness(day)
    result["readiness"] = report
    if apply:
        readiness_rows = [{
            "as_of": day,
            "strategy_id": item["strategy_id"],
            "report_hash": report["report_hash"],
            "data_gate": item["data_gate"],
            "gate_states_json": report["gates"],
            "blockers_json": item["blockers"],
            "counts_json": report["counts"],
            "created_at": utc_now(),
        } for item in report["strategies"]]
        result["readiness_write"] = _write(
            "strategy_data_readiness", readiness_rows, actor=actor,
            reason="append_daily_strategy_readiness_report",
        )
    return result
