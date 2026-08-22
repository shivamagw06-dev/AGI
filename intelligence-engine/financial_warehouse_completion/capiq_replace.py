"""Audited full replacement of FY2017-FY2026 annual statements.

The module is intentionally not exposed over HTTP. Run it from an authenticated
Render shell after reviewing the read-only plan:

    python -m financial_warehouse_completion.capiq_replace plan
    python -m financial_warehouse_completion.capiq_replace apply \
        --plan-hash <hash> --confirm REPLACE_ANNUAL_FY2017_FY2026
"""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import uuid
from collections import Counter
from typing import Any, Iterable

from financial_warehouse_completion.capiq_normalization import audit_and_prepare, persist
from financial_warehouse_completion.capiq_workbook import (
    MASTER_FIELD_MAP,
    SOURCE,
    WORKBOOK_PATH,
    _master_rows,
)
from institutional_warehouse import audit, db, gateway
from institutional_warehouse.formulas import recalculate
from institutional_warehouse.values import now_iso


YEARS = tuple(range(2017, 2027))
CONFIRMATION = "REPLACE_ANNUAL_FY2017_FY2026"
ROLLBACK_CONFIRMATION = "ROLLBACK_ANNUAL_REPLACEMENT"
CHUNK_SIZE = 250
_LOCK = threading.Lock()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _slice_where() -> tuple[str, tuple[str, ...]]:
    tokens = tuple(str(year) for year in YEARS) + tuple(str(year)[-2:] for year in YEARS)
    marks = ",".join("?" for _ in tokens)
    return (
        "REPLACE(UPPER(TRIM(COALESCE(fiscal_year, ''))), 'FY', '') "
        f"IN ({marks})",
        tokens,
    )


def _init_tables() -> None:
    db.init()
    db.execute(
        "CREATE TABLE IF NOT EXISTS wh_capiq_annual_replacement_runs ("
        "run_id TEXT PRIMARY KEY, plan_hash TEXT NOT NULL, actor TEXT NOT NULL, "
        "status TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT, "
        "years TEXT NOT NULL, removed_rows BIGINT NOT NULL DEFAULT 0, "
        "inserted_rows BIGINT NOT NULL DEFAULT 0, receipt TEXT, error TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS wh_capiq_annual_replacement_backup ("
        "run_id TEXT NOT NULL, row_id TEXT NOT NULL, payload TEXT NOT NULL, "
        "active_override INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (run_id, row_id))"
    )


def _build() -> dict[str, Any]:
    if not WORKBOOK_PATH.is_file():
        raise RuntimeError(f"workbook_not_found:{WORKBOOK_PATH.name}")
    rows = [
        row for row in _master_rows(path=WORKBOOK_PATH)
        if int(str(row.get("fiscal_year") or "").replace("FY", "")) in YEARS
    ]
    prepared = audit_and_prepare(
        rows,
        field_map=MASTER_FIELD_MAP,
        source_file=WORKBOOK_PATH.name,
    )
    accepted = list(prepared["accepted"])
    source_by_year = Counter(str(row.get("fiscal_year")) for row in rows)
    ready_by_year = Counter(str(row.get("fiscal_year")) for row in accepted)
    missing_source = [year for year in YEARS if not source_by_year.get(f"FY{year}")]
    missing_ready = [year for year in YEARS if not ready_by_year.get(f"FY{year}")]
    if missing_source:
        raise RuntimeError(f"workbook_missing_years:{','.join(map(str, missing_source))}")
    if missing_ready:
        raise RuntimeError(f"no_verified_rows_for_years:{','.join(map(str, missing_ready))}")

    workbook_hash = hashlib.sha256(WORKBOOK_PATH.read_bytes()).hexdigest()
    digest = hashlib.sha256(workbook_hash.encode("ascii"))
    for row in sorted(accepted, key=lambda item: (str(item.get("symbol")), str(item.get("fiscal_year")))):
        digest.update(_json(row).encode("utf-8"))
    return {
        "rows": rows,
        "prepared": prepared,
        "accepted": accepted,
        "workbook_sha256": workbook_hash,
        "plan_hash": digest.hexdigest(),
        "source_by_year": dict(sorted(source_by_year.items())),
        "ready_by_year": dict(sorted(ready_by_year.items())),
    }


def _current_rows() -> list[dict[str, Any]]:
    db.init()
    where, params = _slice_where()
    return db.query(f"SELECT * FROM wh_financials_annual WHERE {where}", params)


def replacement_plan() -> dict[str, Any]:
    built = _build()
    current = _current_rows()
    by_source = Counter(str(row.get("source") or "(unset)") for row in current)
    return {
        "ok": True,
        "dry_run": True,
        "operation": "replace_all_annual_fy2017_fy2026",
        "years": list(YEARS),
        "workbook": WORKBOOK_PATH.name,
        "workbook_sha256": built["workbook_sha256"],
        "plan_hash": built["plan_hash"],
        "confirmation_required": CONFIRMATION,
        "existing_rows_to_remove": len(current),
        "existing_by_source": dict(sorted(by_source.items())),
        "workbook_rows_seen": len(built["rows"]),
        "workbook_rows_ready": len(built["accepted"]),
        "workbook_rows_quarantined": len(built["rows"]) - len(built["accepted"]),
        "source_by_year": built["source_by_year"],
        "ready_by_year": built["ready_by_year"],
        "quarterly_touched": False,
        "prices_touched": False,
    }


def _backup(run_id: str, rows: list[dict[str, Any]]) -> None:
    active = {
        str(row["row_id"])
        for row in db.query(
            "SELECT row_id FROM wh_overrides WHERE tab_id = ? AND active = 1",
            ("financials_annual",),
        )
    }
    payload = [
        (run_id, str(row["row_id"]), _json(row), 1 if str(row["row_id"]) in active else 0)
        for row in rows
    ]
    for start in range(0, len(payload), CHUNK_SIZE):
        db.executemany(
            "INSERT INTO wh_capiq_annual_replacement_backup "
            "(run_id, row_id, payload, active_override) VALUES (?, ?, ?, ?)",
            payload[start:start + CHUNK_SIZE],
        )


def _deactivate_overrides(row_ids: Iterable[str]) -> None:
    ids = list(dict.fromkeys(str(row_id) for row_id in row_ids if row_id))
    for start in range(0, len(ids), CHUNK_SIZE):
        batch = ids[start:start + CHUNK_SIZE]
        marks = ",".join("?" for _ in batch)
        db.execute(
            f"UPDATE wh_overrides SET active = 0 WHERE tab_id = ? AND row_id IN ({marks})",
            ("financials_annual", *batch),
        )


def _delete_slice() -> int:
    where, params = _slice_where()
    return db.execute(f"DELETE FROM wh_financials_annual WHERE {where}", params)


def _stamp_declared_units() -> int:
    """Persist the workbook's declared INR-million provenance on the landed slice."""
    where, params = _slice_where()
    return db.execute(
        "UPDATE wh_financials_annual SET sys_reported_unit = ?, "
        "sys_unit_scale = ?, sys_unit_method = ? "
        f"WHERE source = ? AND {where}",
        ("inr_million", 1.0, "declared", SOURCE, *params),
    )


def _restore_payloads(payloads: list[dict[str, Any]]) -> int:
    if not payloads:
        return 0
    rows = [json.loads(str(item["payload"])) for item in payloads]
    columns = list(rows[0].keys())
    quoted = ",".join(f'"{column}"' for column in columns)
    marks = ",".join("?" for _ in columns)
    values = [tuple(row.get(column) for column in columns) for row in rows]
    for start in range(0, len(values), CHUNK_SIZE):
        db.executemany(
            f"INSERT INTO wh_financials_annual ({quoted}) VALUES ({marks})",
            values[start:start + CHUNK_SIZE],
        )
    active_ids = [
        str(item["row_id"]) for item in payloads
        if int(item.get("active_override") or 0)
    ]
    for start in range(0, len(active_ids), CHUNK_SIZE):
        batch = active_ids[start:start + CHUNK_SIZE]
        marks = ",".join("?" for _ in batch)
        db.execute(
            f"UPDATE wh_overrides SET active = 1 WHERE tab_id = ? AND row_id IN ({marks})",
            ("financials_annual", *batch),
        )
    return len(rows)


def _restore_run(run_id: str) -> int:
    payloads = db.query(
        "SELECT row_id, payload, active_override "
        "FROM wh_capiq_annual_replacement_backup WHERE run_id = ? ORDER BY row_id",
        (run_id,),
    )
    current = _current_rows()
    _deactivate_overrides(str(row.get("row_id")) for row in current)
    _delete_slice()
    return _restore_payloads(payloads)


def _recalculate(actor: str) -> dict[str, Any]:
    result = recalculate(
        actor=actor,
        stages=(
            "statement_derivations",
            "ratios",
            "valuation",
            "factors",
            "quality",
            "annual_sector_ratios",
        ),
    )
    failures = [
        name for name, receipt in (result.get("stages") or {}).items()
        if isinstance(receipt, dict) and receipt.get("ok") is False
    ]
    if failures:
        result["ok"] = False
        result.setdefault("errors", []).extend(
            {"stage": name, "error": "stage_reported_failure"} for name in failures
        )
    return result


def replace_all(*, confirm: str, plan_hash: str, actor: str) -> dict[str, Any]:
    if confirm != CONFIRMATION:
        return {"ok": False, "error": "confirmation_required", "required": CONFIRMATION}
    built = _build()
    if not plan_hash or plan_hash != built["plan_hash"]:
        return {
            "ok": False,
            "error": "plan_hash_mismatch",
            "expected": built["plan_hash"],
            "instruction": "run a fresh plan before applying",
        }

    _init_tables()
    with _LOCK:
        active = db.query(
            "SELECT run_id FROM wh_capiq_annual_replacement_runs "
            "WHERE status IN ('RUNNING', 'ROLLING_BACK') LIMIT 1"
        )
        if active:
            return {"ok": False, "error": "replacement_already_active", "run_id": active[0]["run_id"]}

        evidence = persist(
            built["prepared"],
            field_map=MASTER_FIELD_MAP,
            actor=actor,
            source_file=WORKBOOK_PATH.name,
            write_financials=False,
        )
        failed = [name for name, receipt in evidence.items() if not receipt.get("ok")]
        if failed:
            return {"ok": False, "error": "evidence_persistence_failed", "stages": failed}

        current = _current_rows()
        run_id = f"capiq_replace_{uuid.uuid4().hex[:16]}"
        db.execute(
            "INSERT INTO wh_capiq_annual_replacement_runs "
            "(run_id, plan_hash, actor, status, started_at, years) "
            "VALUES (?, ?, ?, 'RUNNING', ?, ?)",
            (run_id, built["plan_hash"], actor, now_iso(), _json(YEARS)),
        )
        _backup(run_id, current)
        try:
            _deactivate_overrides(str(row.get("row_id")) for row in current)
            removed = _delete_slice()
            inserted = 0
            for start in range(0, len(built["accepted"]), CHUNK_SIZE):
                batch = built["accepted"][start:start + CHUNK_SIZE]
                receipt = gateway.write(
                    "financials_annual",
                    batch,
                    source=SOURCE,
                    actor=actor,
                    reason=f"capiq_full_replacement:{run_id}",
                    import_id=run_id,
                    reported_unit="inr_million",
                )
                landed = int(receipt.get("written") or 0)
                if not receipt.get("ok") or receipt.get("quarantined") or landed != len(batch):
                    raise RuntimeError(
                        f"batch_failed:start={start}:landed={landed}:expected={len(batch)}:"
                        f"error={receipt.get('error')}"
                    )
                inserted += landed

            unit_rows_stamped = _stamp_declared_units()
            if unit_rows_stamped != inserted:
                raise RuntimeError(
                    f"unit_stamp_failed:stamped={unit_rows_stamped}:expected={inserted}"
                )

            where, params = _slice_where()
            verification = db.query(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN source IS NULL OR source != ? THEN 1 ELSE 0 END) AS foreign_rows, "
                "SUM(CASE WHEN sys_reported_unit = 'inr_million' "
                "AND sys_unit_method = 'declared' THEN 1 ELSE 0 END) AS declared_rows "
                f"FROM wh_financials_annual WHERE {where}",
                (SOURCE, *params),
            )[0]
            total = int(verification.get("total") or 0)
            foreign = int(verification.get("foreign_rows") or 0)
            declared = int(verification.get("declared_rows") or 0)
            if total != len(built["accepted"]) or foreign or declared != total:
                raise RuntimeError(
                    f"verification_failed:total={total}:expected={len(built['accepted'])}:"
                    f"foreign={foreign}:declared={declared}"
                )
        except Exception as exc:
            restored = _restore_run(run_id)
            db.execute(
                "UPDATE wh_capiq_annual_replacement_runs "
                "SET status='FAILED_ROLLED_BACK', completed_at=?, error=?, "
                "removed_rows=?, inserted_rows=0 WHERE run_id=?",
                (now_iso(), str(exc)[:1000], len(current), run_id),
            )
            return {
                "ok": False,
                "error": "replacement_failed_and_rolled_back",
                "run_id": run_id,
                "restored_rows": restored,
                "detail": str(exc)[:500],
            }

        rebuilt = _recalculate(actor)
        status = "COMPLETED" if rebuilt.get("ok") else "COMPLETED_DERIVED_FAILED"
        receipt = {
            "run_id": run_id,
            "plan_hash": built["plan_hash"],
            "workbook": WORKBOOK_PATH.name,
            "workbook_sha256": built["workbook_sha256"],
            "years": list(YEARS),
            "removed_rows": removed,
            "inserted_rows": inserted,
            "unit_rows_stamped": unit_rows_stamped,
            "source": SOURCE,
            "unit": "inr_million",
            "quarterly_touched": False,
            "prices_touched": False,
            "recalculated": rebuilt,
        }
        db.execute(
            "UPDATE wh_capiq_annual_replacement_runs SET status=?, completed_at=?, "
            "removed_rows=?, inserted_rows=?, receipt=?, error=? WHERE run_id=?",
            (
                status, now_iso(), removed, inserted, _json(receipt),
                None if rebuilt.get("ok") else _json(rebuilt.get("errors") or [])[:1000],
                run_id,
            ),
        )
        audit.record(
            "import",
            tab_id="financials_annual",
            actor=actor,
            detail=receipt,
            ok=bool(rebuilt.get("ok")),
        )
        return {"ok": bool(rebuilt.get("ok")), "status": status, **receipt}


def rollback(*, run_id: str, confirm: str, actor: str) -> dict[str, Any]:
    if confirm != ROLLBACK_CONFIRMATION:
        return {"ok": False, "error": "confirmation_required", "required": ROLLBACK_CONFIRMATION}
    _init_tables()
    with _LOCK:
        runs = db.query(
            "SELECT * FROM wh_capiq_annual_replacement_runs WHERE run_id = ?",
            (run_id,),
        )
        if not runs:
            return {"ok": False, "error": "replacement_run_not_found", "run_id": run_id}
        if str(runs[0].get("status") or "") not in {"COMPLETED", "COMPLETED_DERIVED_FAILED"}:
            return {
                "ok": False,
                "error": "replacement_run_not_rollback_eligible",
                "status": runs[0].get("status"),
            }
        db.execute(
            "UPDATE wh_capiq_annual_replacement_runs SET status='ROLLING_BACK' WHERE run_id=?",
            (run_id,),
        )
        try:
            restored = _restore_run(run_id)
            rebuilt = _recalculate(actor)
            status = "ROLLED_BACK" if rebuilt.get("ok") else "ROLLED_BACK_DERIVED_FAILED"
            db.execute(
                "UPDATE wh_capiq_annual_replacement_runs "
                "SET status=?, completed_at=?, receipt=? WHERE run_id=?",
                (status, now_iso(), _json({"restored_rows": restored, "recalculated": rebuilt}), run_id),
            )
            return {
                "ok": bool(rebuilt.get("ok")),
                "status": status,
                "run_id": run_id,
                "restored_rows": restored,
                "recalculated": rebuilt,
            }
        except Exception as exc:
            db.execute(
                "UPDATE wh_capiq_annual_replacement_runs "
                "SET status='ROLLBACK_FAILED', completed_at=?, error=? WHERE run_id=?",
                (now_iso(), str(exc)[:1000], run_id),
            )
            return {"ok": False, "error": "rollback_failed", "run_id": run_id, "detail": str(exc)[:500]}


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--plan-hash", required=True)
    apply_parser.add_argument("--confirm", required=True)
    apply_parser.add_argument("--actor", default="render_shell")
    rollback_parser = sub.add_parser("rollback")
    rollback_parser.add_argument("--run-id", required=True)
    rollback_parser.add_argument("--confirm", required=True)
    rollback_parser.add_argument("--actor", default="render_shell")
    args = parser.parse_args()
    if args.command == "plan":
        result = replacement_plan()
    elif args.command == "apply":
        result = replace_all(confirm=args.confirm, plan_hash=args.plan_hash, actor=args.actor)
    else:
        result = rollback(run_id=args.run_id, confirm=args.confirm, actor=args.actor)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
