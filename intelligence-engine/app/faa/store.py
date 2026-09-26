"""FAA immutable document version store — never overwrite."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any

from app.faa.models import DocumentVersion, utc_now
from app.fre.models import FreDocument


class FaaStore:
    def __init__(self) -> None:
        self.versions: dict[str, DocumentVersion] = {}  # document_id -> version record
        self.by_url: dict[str, list[str]] = {}  # url -> [document_ids] chronological
        default_path = "/var/data/kip/faa_documents.sqlite3" if os.path.isdir("/var/data") else ":memory:"
        self.document_store_path = os.environ.get("FAA_DOCUMENT_STORE_PATH", default_path).strip() or default_path
        self._lock = threading.RLock()
        if self.document_store_path != ":memory:":
            os.makedirs(os.path.dirname(self.document_store_path), exist_ok=True)
        self._db = sqlite3.connect(self.document_store_path, check_same_thread=False, timeout=30)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS faa_documents (
                checksum TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                symbol TEXT,
                company TEXT,
                retrieved_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
        """)
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_faa_documents_symbol ON faa_documents(symbol, retrieved_at DESC)")
        self._db.commit()

    def put_document(self, document: FreDocument) -> None:
        document.ensure_checksum()
        payload = json.dumps(document.to_dict(), ensure_ascii=True, separators=(",", ":"), default=str)
        with self._lock:
            self._db.execute(
                """INSERT INTO faa_documents(checksum,url,symbol,company,retrieved_at,payload_json)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(checksum) DO UPDATE SET
                     url=excluded.url, symbol=excluded.symbol, company=excluded.company,
                     retrieved_at=excluded.retrieved_at, payload_json=excluded.payload_json""",
                (document.checksum, document.url, document.symbol, document.company,
                 document.retrieved_at.isoformat(), payload),
            )
            self._db.commit()

    def durable_documents(self, *, symbol: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            if symbol:
                rows = self._db.execute(
                    "SELECT payload_json FROM faa_documents WHERE upper(symbol)=? ORDER BY retrieved_at DESC LIMIT ?",
                    (symbol.upper(), max(1, min(limit, 500))),
                ).fetchall()
            else:
                rows = self._db.execute(
                    "SELECT payload_json FROM faa_documents ORDER BY retrieved_at DESC LIMIT ?",
                    (max(1, min(limit, 500)),),
                ).fetchall()
        documents = []
        for row in rows:
            try:
                documents.append(json.loads(row[0]))
            except (TypeError, json.JSONDecodeError):
                continue
        return documents

    def put_version(self, version: DocumentVersion) -> DocumentVersion:
        url = version.url
        prior_ids = self.by_url.get(url) or []
        if prior_ids:
            latest_id = prior_ids[-1]
            latest = self.versions.get(latest_id)
            if latest and latest.checksum == version.checksum and latest.status == "active":
                return latest
            if latest and latest.status == "active":
                latest.status = "superseded"
                latest.superseded_by = version.document_id
                version.version = int(latest.version) + 1
        self.versions[version.document_id] = version
        self.by_url.setdefault(url, []).append(version.document_id)
        return version

    def active_for_url(self, url: str) -> DocumentVersion | None:
        ids = self.by_url.get(url) or []
        for doc_id in reversed(ids):
            v = self.versions.get(doc_id)
            if v and v.status == "active":
                return v
        return None

    def snapshot(self) -> dict[str, Any]:
        active = sum(1 for v in self.versions.values() if v.status == "active")
        superseded = sum(1 for v in self.versions.values() if v.status == "superseded")
        with self._lock:
            durable_count = int(self._db.execute("SELECT count(*) FROM faa_documents").fetchone()[0])
        return {
            "versions": len(self.versions),
            "active": active,
            "superseded": superseded,
            "urls": len(self.by_url),
            "durable_documents": durable_count,
            "durable": self.document_store_path != ":memory:",
            "latest": [
                self.versions[ids[-1]].to_dict()
                for ids in list(self.by_url.values())[-20:]
                if ids and ids[-1] in self.versions
            ],
        }

    def mark_fre_link(self, document_id: str, fre_document_id: str) -> None:
        v = self.versions.get(document_id)
        if v:
            v.fre_document_id = fre_document_id
            v.retrieved_at = v.retrieved_at or utc_now()
