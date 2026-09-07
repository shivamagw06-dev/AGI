"""Warehouse database layer.

The warehouse is a real database, not a pile of JSON files. It runs on SQLite by
default (durable file under the shared data root) and on PostgreSQL/Supabase
when ``WAREHOUSE_DATABASE_URL`` is set. Everything above this module speaks one
dialect-neutral SQL subset with ``?`` placeholders.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from institutional_warehouse.schema import (
    BOOL,
    CURRENCY,
    DATE,
    DATETIME,
    INTEGER,
    JSON,
    NUMBER,
    PERCENT,
    TABS,
    TEXT,
    Tab,
)

# --------------------------------------------------------------------------
# Location
# --------------------------------------------------------------------------

_LOCK = threading.RLock()
_BACKEND: Optional["_Backend"] = None
_INITIALISED = False


def store_root() -> Path:
    raw = (os.getenv("INSTITUTIONAL_WAREHOUSE_ROOT") or "").strip()
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    if raw:
        root = Path(raw)
    elif kip:
        root = Path(kip) / "institutional_warehouse"
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "institutional_warehouse"
    root.mkdir(parents=True, exist_ok=True)
    return root


def database_url() -> str:
    for env in ("INSTITUTIONAL_WAREHOUSE_DATABASE_URL", "WAREHOUSE_DATABASE_URL"):
        raw = (os.getenv(env) or "").strip()
        if raw:
            return raw
    return f"sqlite:///{store_root() / 'warehouse.sqlite3'}"


def dialect() -> str:
    url = database_url()
    return "postgres" if url.startswith(("postgres://", "postgresql://", "postgresql+")) else "sqlite"


# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------


class _Backend:
    name = "base"

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        raise NotImplementedError

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        raise NotImplementedError

    def executemany(self, sql: str, rows: Iterable[Sequence[Any]]) -> int:
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - trivial
        return None


class _SqliteBackend(_Backend):
    name = "sqlite"

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._busy_timeout_ms = max(
            1_000,
            int(os.getenv("INSTITUTIONAL_WAREHOUSE_SQLITE_BUSY_TIMEOUT_MS", "30000")),
        )
        self._write_retries = max(
            0,
            int(os.getenv("INSTITUTIONAL_WAREHOUSE_SQLITE_WRITE_RETRIES", "3")),
        )
        self._conn = sqlite3.connect(
            str(path),
            check_same_thread=False,
            timeout=self._busy_timeout_ms / 1000.0,
        )
        self._conn.row_factory = sqlite3.Row
        with _LOCK:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")

    @staticmethod
    def _is_lock_error(exc: sqlite3.OperationalError) -> bool:
        message = str(exc).lower()
        return "database is locked" in message or "database table is locked" in message

    def _write(self, operation: Any) -> int:
        """Commit a SQLite write, retrying transient cross-process lock contention."""
        for attempt in range(self._write_retries + 1):
            cur = None
            try:
                cur = operation()
                self._conn.commit()
                return max(cur.rowcount, 0)
            except sqlite3.OperationalError as exc:
                self._conn.rollback()
                if not self._is_lock_error(exc) or attempt >= self._write_retries:
                    raise
                time.sleep(min(0.25 * (2**attempt), 2.0))
            finally:
                if cur is not None:
                    cur.close()
        return 0  # pragma: no cover - loop either returns or raises

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        with _LOCK:
            cur = self._conn.execute(sql, tuple(params))
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
        return rows

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        with _LOCK:
            return self._write(lambda: self._conn.execute(sql, tuple(params)))

    def executemany(self, sql: str, rows: Iterable[Sequence[Any]]) -> int:
        batch = [tuple(r) for r in rows]
        if not batch:
            return 0
        with _LOCK:
            return self._write(lambda: self._conn.executemany(sql, batch))

    def close(self) -> None:
        with _LOCK:
            try:
                self._conn.close()
            except Exception:
                pass


class _SqlAlchemyBackend(_Backend):
    """PostgreSQL / Supabase backend. ``?`` placeholders are rewritten to named binds."""

    name = "postgres"

    def __init__(self, url: str) -> None:
        from sqlalchemy import create_engine  # lazy: only needed off SQLite

        normalised = url
        if normalised.startswith("postgres://"):
            normalised = "postgresql://" + normalised[len("postgres://"):]
        self._engine = create_engine(normalised, pool_pre_ping=True, future=True)

    @staticmethod
    def _bind(sql: str, params: Sequence[Any]) -> tuple[str, dict[str, Any]]:
        out: list[str] = []
        binds: dict[str, Any] = {}
        idx = 0
        for ch in sql:
            if ch == "?":
                name = f"p{idx}"
                out.append(f":{name}")
                binds[name] = params[idx] if idx < len(params) else None
                idx += 1
            else:
                out.append(ch)
        return "".join(out), binds

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        from sqlalchemy import text

        stmt, binds = self._bind(sql, params)
        with self._engine.connect() as conn:
            result = conn.execute(text(stmt), binds)
            return [dict(r._mapping) for r in result]

    def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        from sqlalchemy import text

        stmt, binds = self._bind(sql, params)
        with self._engine.begin() as conn:
            result = conn.execute(text(stmt), binds)
            return max(result.rowcount or 0, 0)

    def executemany(self, sql: str, rows: Iterable[Sequence[Any]]) -> int:
        from sqlalchemy import text

        batch = list(rows)
        if not batch:
            return 0
        stmt, _ = self._bind(sql, batch[0])
        payload = []
        for row in batch:
            payload.append({f"p{i}": v for i, v in enumerate(row)})
        with self._engine.begin() as conn:
            result = conn.execute(text(stmt), payload)
            return max(result.rowcount or 0, 0)


def backend() -> _Backend:
    global _BACKEND
    with _LOCK:
        if _BACKEND is None:
            url = database_url()
            if url.startswith("sqlite:///"):
                _BACKEND = _SqliteBackend(Path(url[len("sqlite:///"):]))
            elif url.startswith("sqlite://"):
                _BACKEND = _SqliteBackend(Path(url[len("sqlite://"):]))
            else:
                _BACKEND = _SqlAlchemyBackend(url)
        return _BACKEND


def reset_backend() -> None:
    """Drop the cached connection (tests / store-root changes)."""
    global _BACKEND, _INITIALISED
    with _LOCK:
        if _BACKEND is not None:
            _BACKEND.close()
        _BACKEND = None
        _INITIALISED = False


# --------------------------------------------------------------------------
# DDL
# --------------------------------------------------------------------------

TABLE_PREFIX = "wh_"

_SQLITE_TYPES = {
    TEXT: "TEXT",
    DATE: "TEXT",
    DATETIME: "TEXT",
    JSON: "TEXT",
    NUMBER: "REAL",
    PERCENT: "REAL",
    CURRENCY: "REAL",
    INTEGER: "INTEGER",
    BOOL: "INTEGER",
}

_PG_TYPES = {
    TEXT: "TEXT",
    DATE: "TEXT",
    DATETIME: "TEXT",
    JSON: "TEXT",
    NUMBER: "DOUBLE PRECISION",
    PERCENT: "DOUBLE PRECISION",
    CURRENCY: "DOUBLE PRECISION",
    INTEGER: "BIGINT",
    BOOL: "INTEGER",
}

# System columns present on every warehouse tab table.
SYSTEM_DDL: tuple[tuple[str, str], ...] = (
    ("sys_version", INTEGER),
    ("sys_quality", TEXT),
    ("sys_confidence", TEXT),
    ("sys_confidence_score", NUMBER),
    ("sys_validation", TEXT),
    ("sys_validated_at", DATETIME),
    ("sys_created_at", DATETIME),
    ("sys_updated_at", DATETIME),
    ("sys_published", BOOL),
    ("sys_import_id", TEXT),
    ("sys_entity", TEXT),
    # Unit provenance. Currency aggregates are stored in INR million; these
    # record what the vendor reported and how the row got there, so an
    # unstamped legacy row is distinguishable from a normalised one.
    ("sys_reported_unit", TEXT),
    ("sys_unit_method", TEXT),
    ("sys_unit_scale", NUMBER),
)


def physical_table(tab_id: str) -> str:
    return f"{TABLE_PREFIX}{tab_id}"


def _sql_type(logical: str) -> str:
    table = _PG_TYPES if dialect() == "postgres" else _SQLITE_TYPES
    return table.get(logical, "TEXT")


def _create_tab_table(tab: Tab) -> None:
    be = backend()
    name = physical_table(tab.id)
    cols = ["row_id TEXT PRIMARY KEY"]
    for col in tab.columns:
        cols.append(f'"{col.key}" {_sql_type(col.type)}')
    for key, logical in SYSTEM_DDL:
        cols.append(f'"{key}" {_sql_type(logical)}')
    be.execute(f'CREATE TABLE IF NOT EXISTS {name} ({", ".join(cols)})')

    existing = {c.lower() for c in _table_columns(name)}
    for col in tab.columns:
        if col.key.lower() not in existing:
            be.execute(f'ALTER TABLE {name} ADD COLUMN "{col.key}" {_sql_type(col.type)}')
    for key, logical in SYSTEM_DDL:
        if key.lower() not in existing:
            be.execute(f'ALTER TABLE {name} ADD COLUMN "{key}" {_sql_type(logical)}')

    if tab.entity_column:
        be.execute(
            f'CREATE INDEX IF NOT EXISTS idx_{tab.id}_entity ON {name} (sys_entity)'
        )
    be.execute(f'CREATE INDEX IF NOT EXISTS idx_{tab.id}_updated ON {name} (sys_updated_at)')

    # Time-series reads are always "one company, ordered by period". At millions
    # of rows that has to be an index seek, not a scan.
    period_key = next((k for k in tab.key if k != tab.entity_column), None)
    if tab.entity_column and period_key:
        be.execute(
            f'CREATE INDEX IF NOT EXISTS idx_{tab.id}_entity_period'
            f' ON {name} (sys_entity, "{period_key}")'
        )
        be.execute(f'CREATE INDEX IF NOT EXISTS idx_{tab.id}_period ON {name} ("{period_key}")')


def _table_columns(name: str) -> list[str]:
    be = backend()
    if dialect() == "postgres":
        rows = be.query(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            (name,),
        )
        return [str(r.get("column_name")) for r in rows]
    rows = be.query(f"PRAGMA table_info({name})")
    return [str(r.get("name")) for r in rows]


_META_DDL = """
CREATE TABLE IF NOT EXISTS wh_audit (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    action TEXT,
    tab_id TEXT,
    row_id TEXT,
    entity TEXT,
    actor TEXT,
    detail TEXT,
    ok INTEGER
);
CREATE TABLE IF NOT EXISTS wh_cell_versions (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    tab_id TEXT,
    row_id TEXT,
    entity TEXT,
    column_key TEXT,
    old_value TEXT,
    new_value TEXT,
    actor TEXT,
    reason TEXT,
    source TEXT,
    version INTEGER
);
CREATE TABLE IF NOT EXISTS wh_row_snapshots (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    tab_id TEXT,
    row_id TEXT,
    entity TEXT,
    version INTEGER,
    payload TEXT,
    actor TEXT,
    reason TEXT,
    kind TEXT
);
CREATE TABLE IF NOT EXISTS wh_overrides (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    tab_id TEXT,
    row_id TEXT,
    entity TEXT,
    column_key TEXT,
    value TEXT,
    actor TEXT,
    reason TEXT,
    active INTEGER
);
CREATE TABLE IF NOT EXISTS wh_imports (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    tab_id TEXT,
    actor TEXT,
    source TEXT,
    rows_seen INTEGER,
    rows_accepted INTEGER,
    rows_rejected INTEGER,
    report TEXT,
    committed INTEGER
);
CREATE TABLE IF NOT EXISTS wh_refresh_runs (
    id TEXT PRIMARY KEY,
    started_at TEXT,
    finished_at TEXT,
    ok INTEGER,
    actor TEXT,
    stages TEXT,
    counts TEXT,
    errors TEXT
);
CREATE TABLE IF NOT EXISTS wh_quarantine (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    tab_id TEXT,
    source TEXT,
    actor TEXT,
    import_id TEXT,
    row_key TEXT,
    issues TEXT,
    payload TEXT
);
CREATE TABLE IF NOT EXISTS wh_conflicts (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    tab_id TEXT,
    row_id TEXT,
    entity TEXT,
    field TEXT,
    held_value TEXT,
    held_source TEXT,
    incoming_value TEXT,
    incoming_source TEXT,
    gap_pct REAL,
    actor TEXT,
    resolved INTEGER
);
CREATE TABLE IF NOT EXISTS wh_backfill_jobs (
    id TEXT PRIMARY KEY,
    created_at TEXT,
    updated_at TEXT,
    finished_at TEXT,
    kind TEXT,
    actor TEXT,
    status TEXT,
    params TEXT,
    stats TEXT,
    error TEXT
);
CREATE TABLE IF NOT EXISTS wh_backfill_checkpoints (
    id TEXT PRIMARY KEY,
    kind TEXT,
    entity TEXT,
    cursor TEXT,
    status TEXT,
    attempts INTEGER,
    rows_written INTEGER,
    first_period TEXT,
    last_period TEXT,
    last_error TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS wh_backfill_dates (
    id TEXT PRIMARY KEY,
    source TEXT,
    trade_date TEXT,
    status TEXT,
    rows INTEGER,
    checksum TEXT,
    attempts INTEGER,
    last_error TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS wh_capiq_import_jobs (
    job_id TEXT PRIMARY KEY,
    source_file TEXT,
    source_version TEXT,
    code_version TEXT,
    schema_version TEXT,
    started_at TEXT,
    completed_at TEXT,
    status TEXT,
    phase TEXT,
    total_rows INTEGER,
    approved_rows INTEGER,
    quarantined_rows INTEGER,
    processed_rows INTEGER,
    persisted_rows INTEGER,
    normalized_rows INTEGER,
    recalculated_rows INTEGER,
    verified_rows INTEGER,
    failed_rows INTEGER,
    current_chunk INTEGER,
    total_chunks INTEGER,
    error_count INTEGER,
    last_error TEXT,
    heartbeat_at TEXT,
    years TEXT,
    receipt TEXT
);
CREATE TABLE IF NOT EXISTS wh_capiq_import_chunks (
    chunk_id TEXT PRIMARY KEY,
    job_id TEXT,
    phase TEXT,
    row_start INTEGER,
    row_end INTEGER,
    status TEXT,
    attempt_count INTEGER,
    started_at TEXT,
    completed_at TEXT,
    processed_count INTEGER,
    persisted_count INTEGER,
    error_count INTEGER,
    last_error TEXT,
    heartbeat_at TEXT
);
"""

_META_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_audit_created ON wh_audit (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_audit_tab ON wh_audit (tab_id)",
    "CREATE INDEX IF NOT EXISTS idx_cellver_row ON wh_cell_versions (tab_id, row_id)",
    "CREATE INDEX IF NOT EXISTS idx_snap_row ON wh_row_snapshots (tab_id, row_id)",
    "CREATE INDEX IF NOT EXISTS idx_override_row ON wh_overrides (tab_id, row_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_ckpt_kind_entity ON wh_backfill_checkpoints (kind, entity)",
    "CREATE INDEX IF NOT EXISTS idx_ckpt_status ON wh_backfill_checkpoints (kind, status)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_bfdate_source_date ON wh_backfill_dates (source, trade_date)",
    "CREATE INDEX IF NOT EXISTS idx_bfdate_status ON wh_backfill_dates (source, status)",
    "CREATE INDEX IF NOT EXISTS idx_job_kind ON wh_backfill_jobs (kind, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_capiq_job_status ON wh_capiq_import_jobs (status, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_capiq_chunk_job ON wh_capiq_import_chunks (job_id, phase, row_start)",
    "CREATE INDEX IF NOT EXISTS idx_quarantine_tab ON wh_quarantine (tab_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_conflicts_row ON wh_conflicts (tab_id, row_id)",
    "CREATE INDEX IF NOT EXISTS idx_conflicts_entity ON wh_conflicts (entity)",
)


def init(force: bool = False) -> dict[str, Any]:
    """Create/upgrade every warehouse table. Cheap and idempotent."""
    global _INITIALISED
    with _LOCK:
        if _INITIALISED and not force:
            return {"ok": True, "already": True, "dialect": dialect()}
        be = backend()
        for stmt in _META_DDL.strip().split(";"):
            if stmt.strip():
                be.execute(stmt.strip())
        for stmt in _META_INDEXES:
            be.execute(stmt)
        for tab in TABS:
            _create_tab_table(tab)
        _INITIALISED = True
        return {
            "ok": True,
            "dialect": dialect(),
            "url": _redacted_url(),
            "tables": [physical_table(t.id) for t in TABS],
        }


def _redacted_url() -> str:
    url = database_url()
    if url.startswith("sqlite"):
        return url
    if "@" in url:
        head, tail = url.split("@", 1)
        scheme = head.split("://", 1)[0]
        return f"{scheme}://***@{tail}"
    return url


# --------------------------------------------------------------------------
# Thin helpers used by the store
# --------------------------------------------------------------------------


def query(sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    init()
    return backend().query(sql, params)


def execute(sql: str, params: Sequence[Any] = ()) -> int:
    init()
    return backend().execute(sql, params)


def executemany(sql: str, rows: Iterable[Sequence[Any]]) -> int:
    init()
    return backend().executemany(sql, rows)


def count(table: str, where: str = "", params: Sequence[Any] = ()) -> int:
    clause = f" WHERE {where}" if where else ""
    rows = query(f"SELECT COUNT(*) AS n FROM {table}{clause}", params)
    if not rows:
        return 0
    return int(rows[0].get("n") or 0)


def info() -> dict[str, Any]:
    init()
    tables = {}
    for tab in TABS:
        try:
            tables[tab.id] = count(physical_table(tab.id))
        except Exception:
            tables[tab.id] = 0
    return {
        "ok": True,
        "dialect": dialect(),
        "url": _redacted_url(),
        "root": str(store_root()),
        "row_counts": tables,
        "total_rows": sum(tables.values()),
    }
