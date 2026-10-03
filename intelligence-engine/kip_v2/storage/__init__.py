"""KIP v2 storage backends.

``get_store()`` returns the active :class:`KnowledgeStore`. The default is the
SQLite-backed store (real on-disk persistence, zero external dependencies).
When ``KIP_V2_DATABASE_URL`` (a Postgres/Supabase connection string) is set,
the Postgres/pgvector-backed store is used instead — same interface, same
callers, no code changes required anywhere else in the package.
"""

from __future__ import annotations

import os
import threading

from kip_v2.storage.base import KnowledgeStore

_lock = threading.Lock()
_instance: KnowledgeStore | None = None


def get_store() -> KnowledgeStore:
    global _instance
    with _lock:
        if _instance is not None:
            return _instance
        database_url = os.environ.get("KIP_V2_DATABASE_URL", "").strip()
        if database_url:
            from kip_v2.storage.postgres_store import PostgresKnowledgeStore

            _instance = PostgresKnowledgeStore(database_url)
        else:
            from kip_v2.storage.sqlite_store import SqliteKnowledgeStore

            _instance = SqliteKnowledgeStore()
        return _instance


def reset_store_for_tests(store: KnowledgeStore | None = None) -> KnowledgeStore:
    """Test-only helper: swap in a fresh store instance (e.g. an in-memory
    SQLite store) so tests don't share state or touch the real database."""

    global _instance
    with _lock:
        if store is not None:
            _instance = store
        else:
            from kip_v2.storage.sqlite_store import SqliteKnowledgeStore

            _instance = SqliteKnowledgeStore(path=":memory:")
        return _instance


__all__ = ["KnowledgeStore", "get_store", "reset_store_for_tests"]
