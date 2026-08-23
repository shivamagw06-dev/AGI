"""Persistent evidence store for live option-chain validation."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS collector_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    expiries_json TEXT NOT NULL DEFAULT '[]',
    counts_json TEXT NOT NULL DEFAULT '{}',
    error TEXT
);

CREATE TABLE IF NOT EXISTS option_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at TEXT NOT NULL,
    local_date TEXT NOT NULL,
    provider TEXT NOT NULL,
    underlying_key TEXT NOT NULL,
    underlying_symbol TEXT NOT NULL,
    spot REAL NOT NULL,
    expiry TEXT NOT NULL,
    instrument_key TEXT NOT NULL,
    trading_symbol TEXT,
    option_type TEXT NOT NULL CHECK(option_type IN ('CE', 'PE')),
    strike REAL NOT NULL,
    lot_size INTEGER,
    dte_days REAL NOT NULL,
    risk_free_rate_pct REAL NOT NULL,
    dividend_yield_pct REAL NOT NULL,
    ltp REAL,
    bid REAL,
    ask REAL,
    market_price REAL NOT NULL,
    close_price REAL,
    volume REAL,
    oi REAL,
    prev_oi REAL,
    iv_pct REAL,
    iv_source TEXT,
    delta REAL,
    gamma REAL,
    theta REAL,
    vega REAL,
    rho REAL,
    pop REAL,
    raw_json TEXT NOT NULL,
    UNIQUE(captured_at, instrument_key)
);

CREATE INDEX IF NOT EXISTS idx_option_snapshots_contract_time
ON option_snapshots(instrument_key, captured_at);

CREATE INDEX IF NOT EXISTS idx_option_snapshots_local_date
ON option_snapshots(local_date);

CREATE TABLE IF NOT EXISTS contract_iv_state (
    instrument_key TEXT PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES option_snapshots(id),
    observed_at TEXT NOT NULL,
    expiry TEXT NOT NULL,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL,
    iv_pct REAL NOT NULL,
    market_price REAL NOT NULL,
    spot REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prior_snapshot_id INTEGER NOT NULL REFERENCES option_snapshots(id),
    current_snapshot_id INTEGER NOT NULL REFERENCES option_snapshots(id),
    local_date TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    instrument_key TEXT NOT NULL,
    expiry TEXT NOT NULL,
    option_type TEXT NOT NULL,
    strike REAL NOT NULL,
    horizon_minutes REAL NOT NULL,
    dte_days REAL NOT NULL,
    dte_bucket TEXT NOT NULL,
    moneyness_bucket TEXT NOT NULL,
    premium_bucket TEXT NOT NULL,
    prior_iv_pct REAL NOT NULL,
    prior_market_price REAL NOT NULL,
    prior_spot REAL NOT NULL,
    current_spot REAL NOT NULL,
    actual_price REAL NOT NULL,
    predicted_price REAL NOT NULL,
    error_points REAL NOT NULL,
    absolute_error_points REAL NOT NULL,
    absolute_percentage_error REAL NOT NULL,
    tolerance_points REAL NOT NULL,
    within_tolerance INTEGER NOT NULL,
    pricing_method TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(prior_snapshot_id, current_snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_validation_local_date
ON validation_observations(local_date);

CREATE TABLE IF NOT EXISTS daily_reports (
    report_date TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    status TEXT NOT NULL,
    report_json TEXT NOT NULL,
    markdown_path TEXT,
    json_path TEXT
);
"""


class OptionEvidenceStore:
    """SQLite-backed snapshots, rolling IV state, observations, and reports."""

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def start_run(self, run_id: str, started_at: str, expiries: Iterable[str]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO collector_runs(run_id, started_at, status, expiries_json)
                VALUES (?, ?, 'running', ?)
                """,
                (run_id, started_at, json.dumps(list(expiries))),
            )

    def finish_run(
        self,
        run_id: str,
        completed_at: str,
        status: str,
        counts: dict[str, Any],
        error: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE collector_runs
                SET completed_at = ?, status = ?, counts_json = ?, error = ?
                WHERE run_id = ?
                """,
                (completed_at, status, json.dumps(counts, sort_keys=True), error, run_id),
            )

    def persist_snapshots(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Insert a batch and return each inserted row with its prior IV state."""
        inserted: list[dict[str, Any]] = []
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for row in rows:
                prior = connection.execute(
                    "SELECT * FROM contract_iv_state WHERE instrument_key = ?",
                    (row["instrument_key"],),
                ).fetchone()
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO option_snapshots(
                        captured_at, local_date, provider, underlying_key,
                        underlying_symbol, spot, expiry, instrument_key,
                        trading_symbol, option_type, strike, lot_size, dte_days,
                        risk_free_rate_pct, dividend_yield_pct, ltp, bid, ask,
                        market_price, close_price, volume, oi, prev_oi, iv_pct,
                        iv_source, delta, gamma, theta, vega, rho, pop, raw_json
                    ) VALUES (
                        :captured_at, :local_date, :provider, :underlying_key,
                        :underlying_symbol, :spot, :expiry, :instrument_key,
                        :trading_symbol, :option_type, :strike, :lot_size, :dte_days,
                        :risk_free_rate_pct, :dividend_yield_pct, :ltp, :bid, :ask,
                        :market_price, :close_price, :volume, :oi, :prev_oi, :iv_pct,
                        :iv_source, :delta, :gamma, :theta, :vega, :rho, :pop, :raw_json
                    )
                    """,
                    row,
                )
                if cursor.rowcount == 0:
                    continue
                snapshot_id = int(cursor.lastrowid)
                item = dict(row)
                item["snapshot_id"] = snapshot_id
                item["prior_state"] = dict(prior) if prior else None
                inserted.append(item)
                if row.get("iv_pct") is not None:
                    connection.execute(
                        """
                        INSERT INTO contract_iv_state(
                            instrument_key, snapshot_id, observed_at, expiry,
                            strike, option_type, iv_pct, market_price, spot, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(instrument_key) DO UPDATE SET
                            snapshot_id = excluded.snapshot_id,
                            observed_at = excluded.observed_at,
                            expiry = excluded.expiry,
                            strike = excluded.strike,
                            option_type = excluded.option_type,
                            iv_pct = excluded.iv_pct,
                            market_price = excluded.market_price,
                            spot = excluded.spot,
                            updated_at = excluded.updated_at
                        """,
                        (
                            row["instrument_key"],
                            snapshot_id,
                            row["captured_at"],
                            row["expiry"],
                            row["strike"],
                            row["option_type"],
                            row["iv_pct"],
                            row["market_price"],
                            row["spot"],
                            row["captured_at"],
                        ),
                    )
        return inserted

    def add_validation(self, row: dict[str, Any]) -> bool:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO validation_observations(
                    prior_snapshot_id, current_snapshot_id, local_date, observed_at,
                    instrument_key, expiry, option_type, strike, horizon_minutes,
                    dte_days, dte_bucket, moneyness_bucket, premium_bucket,
                    prior_iv_pct, prior_market_price, prior_spot, current_spot,
                    actual_price, predicted_price, error_points,
                    absolute_error_points, absolute_percentage_error,
                    tolerance_points, within_tolerance, pricing_method, created_at
                ) VALUES (
                    :prior_snapshot_id, :current_snapshot_id, :local_date, :observed_at,
                    :instrument_key, :expiry, :option_type, :strike, :horizon_minutes,
                    :dte_days, :dte_bucket, :moneyness_bucket, :premium_bucket,
                    :prior_iv_pct, :prior_market_price, :prior_spot, :current_spot,
                    :actual_price, :predicted_price, :error_points,
                    :absolute_error_points, :absolute_percentage_error,
                    :tolerance_points, :within_tolerance, :pricing_method, :created_at
                )
                """,
                row,
            )
            return cursor.rowcount == 1

    def validations(self, *, through_date: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM validation_observations"
        parameters: tuple[Any, ...] = ()
        if through_date:
            sql += " WHERE local_date <= ?"
            parameters = (through_date,)
        sql += " ORDER BY observed_at, instrument_key"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, parameters).fetchall()]

    def save_report(
        self,
        report_date: str,
        generated_at: str,
        status: str,
        report: dict[str, Any],
        markdown_path: str,
        json_path: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO daily_reports(
                    report_date, generated_at, status, report_json,
                    markdown_path, json_path
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_date) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    status = excluded.status,
                    report_json = excluded.report_json,
                    markdown_path = excluded.markdown_path,
                    json_path = excluded.json_path
                """,
                (
                    report_date,
                    generated_at,
                    status,
                    json.dumps(report, sort_keys=True),
                    markdown_path,
                    json_path,
                ),
            )

    def status(self) -> dict[str, Any]:
        with self.connect() as connection:
            result: dict[str, Any] = {"database": str(self.path)}
            for table in (
                "option_snapshots",
                "contract_iv_state",
                "validation_observations",
                "daily_reports",
            ):
                result[table] = connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
            result["latest_snapshot_at"] = connection.execute(
                "SELECT MAX(captured_at) FROM option_snapshots"
            ).fetchone()[0]
            return result
