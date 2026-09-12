from __future__ import annotations

import sqlite3
from typing import Any

from institutional_warehouse.db import _SqliteBackend


class _ConnectionProxy:
    def __init__(self, connection: sqlite3.Connection, error: sqlite3.OperationalError) -> None:
        self.connection = connection
        self.error = error
        self.attempts = 0

    def execute(self, sql: str, params: Any = ()):
        self.attempts += 1
        if self.attempts == 1:
            raise self.error
        return self.connection.execute(sql, params)

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()


def test_sqlite_write_retries_transient_lock(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_SQLITE_BUSY_TIMEOUT_MS", "1000")
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_SQLITE_WRITE_RETRIES", "2")
    backend = _SqliteBackend(tmp_path / "warehouse.sqlite3")
    backend.execute("CREATE TABLE sample (value INTEGER)")

    proxy = _ConnectionProxy(backend._conn, sqlite3.OperationalError("database is locked"))
    backend._conn = proxy
    assert backend.execute("INSERT INTO sample (value) VALUES (?)", (7,)) == 1
    assert proxy.attempts == 2
    backend._conn = proxy.connection
    assert backend.query("SELECT value FROM sample") == [{"value": 7}]


def test_sqlite_write_does_not_retry_unrelated_operational_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_SQLITE_WRITE_RETRIES", "2")
    backend = _SqliteBackend(tmp_path / "warehouse.sqlite3")
    proxy = _ConnectionProxy(backend._conn, sqlite3.OperationalError("no such table: missing"))
    backend._conn = proxy
    try:
        backend.execute("INSERT INTO missing VALUES (?)", (1,))
    except sqlite3.OperationalError as exc:
        assert "no such table" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unrelated SQLite errors must propagate")
    assert proxy.attempts == 1
