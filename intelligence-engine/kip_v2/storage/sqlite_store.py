"""Default KnowledgeStore backend — real on-disk SQLite persistence.

No external services required, so this is what runs in this environment and
in any deployment that hasn't wired up ``KIP_V2_DATABASE_URL``. It implements
the exact same contract as :mod:`kip_v2.storage.postgres_store`, so switching
to Postgres/pgvector in production is a one-line environment-variable change,
not a rewrite.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from kip_v2.schema import (
    ChangeDelta,
    Document,
    Evidence,
    Fact,
    FactStatus,
    GraphEdge,
    GraphNode,
    Paragraph,
)
from kip_v2.storage.base import KnowledgeStore

_DEFAULT_PATH = Path(
    os.environ.get("KIP_V2_STORE_ROOT", str(Path(__file__).resolve().parents[2] / "data" / "kip_v2"))
) / "kip_v2.sqlite3"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    period TEXT,
    title TEXT,
    source TEXT,
    page_count INTEGER,
    published_at TEXT,
    ingested_at REAL,
    version INTEGER
);

CREATE TABLE IF NOT EXISTS paragraphs (
    paragraph_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    section TEXT,
    page INTEGER,
    idx INTEGER,
    text TEXT,
    is_table INTEGER,
    entities TEXT,
    importance_score REAL,
    embedding TEXT,
    evidence_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_paragraphs_doc ON paragraphs(document_id);
CREATE INDEX IF NOT EXISTS idx_paragraphs_company ON paragraphs(company_id);
CREATE INDEX IF NOT EXISTS idx_paragraphs_evhash ON paragraphs(document_id, evidence_hash);

CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    period TEXT,
    unit TEXT,
    currency TEXT,
    confidence REAL,
    evidence TEXT,
    source_document_id TEXT,
    timestamp REAL,
    version INTEGER,
    status TEXT,
    superseded_by TEXT,
    extra TEXT
);
CREATE INDEX IF NOT EXISTS idx_facts_company ON facts(company_id, category, status);
CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(company_id, key);

CREATE TABLE IF NOT EXISTS graph_nodes (
    node_id TEXT PRIMARY KEY,
    node_type TEXT,
    name TEXT,
    attributes TEXT
);

CREATE TABLE IF NOT EXISTS graph_edges (
    edge_id TEXT PRIMARY KEY,
    source_id TEXT,
    target_id TEXT,
    relation TEXT,
    confidence REAL,
    evidence_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_id);

CREATE TABLE IF NOT EXISTS deltas (
    delta_id TEXT PRIMARY KEY,
    company_id TEXT,
    category TEXT,
    key TEXT,
    change_type TEXT,
    from_period TEXT,
    to_period TEXT,
    old_value TEXT,
    new_value TEXT,
    old_evidence TEXT,
    new_evidence TEXT,
    magnitude_pct REAL,
    detected_at REAL
);
CREATE INDEX IF NOT EXISTS idx_deltas_company ON deltas(company_id);

CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    errors TEXT,
    at REAL
);
"""


class SqliteKnowledgeStore(KnowledgeStore):
    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or str(_DEFAULT_PATH)
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---- documents -------------------------------------------------
    def store_document(self, document: Document) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO documents
                   (document_id, company_id, doc_type, period, title, source, page_count,
                    published_at, ingested_at, version)
                   VALUES (?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(document_id) DO UPDATE SET
                     company_id=excluded.company_id, doc_type=excluded.doc_type,
                     period=excluded.period, title=excluded.title, source=excluded.source,
                     page_count=excluded.page_count, published_at=excluded.published_at,
                     version=excluded.version""",
                (
                    document.document_id, document.company_id, document.doc_type, document.period,
                    document.title, document.source, document.page_count, document.published_at,
                    document.ingested_at, document.version,
                ),
            )
            self._conn.commit()

    def get_document(self, document_id: str) -> Optional[Document]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM documents WHERE document_id=?", (document_id,)).fetchone()
        return self._row_to_document(row) if row else None

    def list_documents(self, company_id: str) -> list[Document]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM documents WHERE company_id=? ORDER BY ingested_at", (company_id,)
            ).fetchall()
        return [self._row_to_document(r) for r in rows]

    def _row_to_document(self, row) -> Document:
        cols = [d[0] for d in self._conn.execute("SELECT * FROM documents LIMIT 0").description]
        d = dict(zip(cols, row))
        return Document(**d)

    # ---- paragraphs --------------------------------------------------
    def paragraph_exists(self, document_id: str, evidence_hash: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM paragraphs WHERE document_id=? AND evidence_hash=?",
                (document_id, evidence_hash),
            ).fetchone()
        return row is not None

    def store_paragraph(self, paragraph: Paragraph) -> bool:
        if self.paragraph_exists(paragraph.document_id, paragraph.evidence_hash):
            return False
        with self._lock:
            self._conn.execute(
                """INSERT OR IGNORE INTO paragraphs
                   (paragraph_id, document_id, company_id, section, page, idx, text, is_table,
                    entities, importance_score, embedding, evidence_hash)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    paragraph.paragraph_id, paragraph.document_id, paragraph.company_id, paragraph.section,
                    paragraph.page, paragraph.index, paragraph.text, int(paragraph.is_table),
                    json.dumps(paragraph.entities), paragraph.importance_score,
                    json.dumps(paragraph.embedding), paragraph.evidence_hash,
                ),
            )
            self._conn.commit()
        return True

    def list_paragraphs(self, document_id: str) -> list[Paragraph]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM paragraphs WHERE document_id=? ORDER BY idx", (document_id,)
            ).fetchall()
        return [self._row_to_paragraph(r) for r in rows]

    def all_paragraphs(self, company_id: str) -> list[Paragraph]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM paragraphs WHERE company_id=? ORDER BY document_id, idx", (company_id,)
            ).fetchall()
        return [self._row_to_paragraph(r) for r in rows]

    def _row_to_paragraph(self, row) -> Paragraph:
        cols = [d[0] for d in self._conn.execute("SELECT * FROM paragraphs LIMIT 0").description]
        d = dict(zip(cols, row))
        return Paragraph(
            paragraph_id=d["paragraph_id"], document_id=d["document_id"], company_id=d["company_id"],
            section=d["section"], page=d["page"], index=d["idx"], text=d["text"],
            is_table=bool(d["is_table"]), entities=json.loads(d["entities"] or "[]"),
            importance_score=d["importance_score"], embedding=json.loads(d["embedding"] or "[]"),
            evidence_hash=d["evidence_hash"],
        )

    # ---- facts ---------------------------------------------------------
    def _persist_fact(self, fact: Fact) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO facts
                   (fact_id, company_id, category, key, value, period, unit, currency, confidence,
                    evidence, source_document_id, timestamp, version, status, superseded_by, extra)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(fact_id) DO UPDATE SET
                     value=excluded.value, confidence=excluded.confidence, evidence=excluded.evidence,
                     timestamp=excluded.timestamp, version=excluded.version, status=excluded.status,
                     superseded_by=excluded.superseded_by, extra=excluded.extra""",
                (
                    fact.fact_id, fact.company_id, fact.category, fact.key, json.dumps(fact.value),
                    fact.period, fact.unit, fact.currency, fact.confidence,
                    json.dumps(fact.evidence.to_dict()), fact.source_document_id, fact.timestamp,
                    fact.version, fact.status, fact.superseded_by, json.dumps(fact.extra),
                ),
            )
            self._conn.commit()

    def get_facts(
        self,
        company_id: str,
        category: Optional[str] = None,
        key: Optional[str] = None,
        period: Optional[str] = None,
        status: Optional[str] = FactStatus.ACTIVE.value,
    ) -> list[Fact]:
        query = "SELECT * FROM facts WHERE company_id=?"
        params: list[Any] = [company_id]
        if category:
            query += " AND category=?"
            params.append(category)
        if key:
            query += " AND key=?"
            params.append(key)
        if period:
            query += " AND period=?"
            params.append(period)
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY timestamp DESC"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_fact(r) for r in rows]

    def get_fact(self, fact_id: str) -> Optional[Fact]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM facts WHERE fact_id=?", (fact_id,)).fetchone()
        return self._row_to_fact(row) if row else None

    def supersede_fact(self, old_fact_id: str, new_fact_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE facts SET status=?, superseded_by=? WHERE fact_id=?",
                (FactStatus.ARCHIVED.value, new_fact_id, old_fact_id),
            )
            self._conn.commit()

    def record_rejection(self, category: str, errors: list[str]) -> None:
        import time

        with self._lock:
            self._conn.execute(
                "INSERT INTO rejections (category, errors, at) VALUES (?,?,?)",
                (category, json.dumps(errors), time.time()),
            )
            self._conn.commit()

    def _row_to_fact(self, row) -> Fact:
        cols = [d[0] for d in self._conn.execute("SELECT * FROM facts LIMIT 0").description]
        d = dict(zip(cols, row))
        ev = json.loads(d["evidence"])
        evidence = Evidence(
            document_id=ev["document_id"], page=ev["page"], paragraph_id=ev["paragraph_id"],
            snippet=ev["snippet"], evidence_hash=ev["evidence_hash"], created_at=ev.get("created_at", 0.0),
        )
        return Fact(
            fact_id=d["fact_id"], company_id=d["company_id"], category=d["category"], key=d["key"],
            value=json.loads(d["value"]), period=d["period"], unit=d["unit"], currency=d["currency"],
            confidence=d["confidence"], evidence=evidence, source_document_id=d["source_document_id"],
            timestamp=d["timestamp"], version=d["version"], status=d["status"],
            superseded_by=d["superseded_by"], extra=json.loads(d["extra"] or "{}"),
        )

    # ---- knowledge graph -------------------------------------------------
    def upsert_node(self, node: GraphNode) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO graph_nodes (node_id, node_type, name, attributes) VALUES (?,?,?,?)
                   ON CONFLICT(node_id) DO UPDATE SET
                     node_type=excluded.node_type, name=excluded.name, attributes=excluded.attributes""",
                (node.node_id, node.node_type, node.name, json.dumps(node.attributes)),
            )
            self._conn.commit()

    def upsert_edge(self, edge: GraphEdge) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO graph_edges (edge_id, source_id, target_id, relation, confidence, evidence_hash)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(edge_id) DO UPDATE SET confidence=excluded.confidence""",
                (edge.edge_id, edge.source_id, edge.target_id, edge.relation, edge.confidence, edge.evidence_hash),
            )
            self._conn.commit()

    def get_graph(self, node_id: str) -> tuple[list[GraphNode], list[GraphEdge]]:
        with self._lock:
            edge_rows = self._conn.execute(
                "SELECT * FROM graph_edges WHERE source_id=? OR target_id=?", (node_id, node_id)
            ).fetchall()
            node_ids = {node_id}
            edges = []
            for r in edge_rows:
                cols = [d[0] for d in self._conn.execute("SELECT * FROM graph_edges LIMIT 0").description]
                d = dict(zip(cols, r))
                edges.append(GraphEdge(**d))
                node_ids.add(d["source_id"])
                node_ids.add(d["target_id"])
            nodes = []
            for nid in node_ids:
                row = self._conn.execute("SELECT * FROM graph_nodes WHERE node_id=?", (nid,)).fetchone()
                if row:
                    cols = [d[0] for d in self._conn.execute("SELECT * FROM graph_nodes LIMIT 0").description]
                    d = dict(zip(cols, row))
                    d["attributes"] = json.loads(d["attributes"] or "{}")
                    nodes.append(GraphNode(**d))
        return nodes, edges

    # ---- deltas -----------------------------------------------------------
    def store_delta(self, delta: ChangeDelta) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO deltas
                   (delta_id, company_id, category, key, change_type, from_period, to_period,
                    old_value, new_value, old_evidence, new_evidence, magnitude_pct, detected_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(delta_id) DO UPDATE SET new_value=excluded.new_value""",
                (
                    delta.delta_id, delta.company_id, delta.category, delta.key, delta.change_type,
                    delta.from_period, delta.to_period, json.dumps(delta.old_value), json.dumps(delta.new_value),
                    json.dumps(delta.old_evidence), json.dumps(delta.new_evidence), delta.magnitude_pct,
                    delta.detected_at,
                ),
            )
            self._conn.commit()

    def get_deltas(
        self, company_id: str, from_period: Optional[str] = None, to_period: Optional[str] = None
    ) -> list[ChangeDelta]:
        query = "SELECT * FROM deltas WHERE company_id=?"
        params: list[Any] = [company_id]
        if from_period:
            query += " AND from_period=?"
            params.append(from_period)
        if to_period:
            query += " AND to_period=?"
            params.append(to_period)
        query += " ORDER BY detected_at DESC"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        out = []
        for r in rows:
            cols = [d[0] for d in self._conn.execute("SELECT * FROM deltas LIMIT 0").description]
            d = dict(zip(cols, r))
            d["old_value"] = json.loads(d["old_value"]) if d["old_value"] else None
            d["new_value"] = json.loads(d["new_value"]) if d["new_value"] else None
            d["old_evidence"] = json.loads(d["old_evidence"]) if d["old_evidence"] else None
            d["new_evidence"] = json.loads(d["new_evidence"]) if d["new_evidence"] else None
            out.append(ChangeDelta(**d))
        return out

    # ---- observability -----------------------------------------------------
    def stats(self) -> dict[str, Any]:
        with self._lock:
            def count(table: str, where: str = "") -> int:
                q = f"SELECT COUNT(*) FROM {table} {where}"
                return self._conn.execute(q).fetchone()[0]

            return {
                "backend": "sqlite",
                "path": self._path,
                "documents": count("documents"),
                "paragraphs": count("paragraphs"),
                "facts_active": count("facts", "WHERE status='active'"),
                "facts_archived": count("facts", "WHERE status='archived'"),
                "graph_nodes": count("graph_nodes"),
                "graph_edges": count("graph_edges"),
                "deltas": count("deltas"),
                "rejections": count("rejections"),
            }
