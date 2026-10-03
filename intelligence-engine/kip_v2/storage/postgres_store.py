"""Production KnowledgeStore backend — Postgres + pgvector (e.g. Supabase).

Implements the exact same :class:`~kip_v2.storage.base.KnowledgeStore`
contract as the default SQLite store, against the schema in ``schema.sql``.

This repo's Supabase credentials (``SUPABASE_URL`` / ``SUPABASE_SERVICE_ROLE_KEY``)
are a REST/PostgREST + Auth API key pair, not a raw Postgres connection
string — there is no live asyncpg-reachable database configured in this
environment (see ``schema.sql`` header for the one-time DDL step required).
This backend activates only when an operator explicitly sets
``KIP_V2_DATABASE_URL`` to a real ``postgresql://`` connection string in a
deployment that has actually applied ``schema.sql``.

``asyncpg`` is async-only; the rest of KIP v2 (and this repo's ``production.py``
facade convention) is synchronous, so this class bridges the two with a
single dedicated background event loop thread and blocking ``run_coroutine_threadsafe``
calls — a standard pattern for embedding an async driver behind a sync API.
"""

from __future__ import annotations

import asyncio
import json
import threading
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


class PostgresKnowledgeStore(KnowledgeStore):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True, name="kip-v2-pg-loop")
        self._thread.start()
        self._pool = None

    def _run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    async def _ensure_pool(self):
        if self._pool is None:
            import asyncpg  # type: ignore

            self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=5)
        return self._pool

    def _vec_literal(self, embedding: list[float]) -> str:
        return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]" if embedding else "[]"

    # ---- documents -------------------------------------------------
    def store_document(self, document: Document) -> None:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO kip_v2_documents
                       (document_id, company_id, doc_type, period, title, source, page_count,
                        published_at, ingested_at, version)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                       ON CONFLICT (document_id) DO UPDATE SET
                         company_id=EXCLUDED.company_id, doc_type=EXCLUDED.doc_type,
                         period=EXCLUDED.period, title=EXCLUDED.title, source=EXCLUDED.source,
                         page_count=EXCLUDED.page_count, published_at=EXCLUDED.published_at,
                         version=EXCLUDED.version""",
                    document.document_id, document.company_id, document.doc_type, document.period,
                    document.title, document.source, document.page_count, document.published_at,
                    document.ingested_at, document.version,
                )
        self._run(_go())

    def get_document(self, document_id: str) -> Optional[Document]:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetchrow("SELECT * FROM kip_v2_documents WHERE document_id=$1", document_id)
        row = self._run(_go())
        return Document(**dict(row)) if row else None

    def list_documents(self, company_id: str) -> list[Document]:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetch(
                    "SELECT * FROM kip_v2_documents WHERE company_id=$1 ORDER BY ingested_at", company_id
                )
        rows = self._run(_go())
        return [Document(**dict(r)) for r in rows]

    # ---- paragraphs --------------------------------------------------
    def paragraph_exists(self, document_id: str, evidence_hash: str) -> bool:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetchval(
                    "SELECT 1 FROM kip_v2_paragraphs WHERE document_id=$1 AND evidence_hash=$2",
                    document_id, evidence_hash,
                )
        return self._run(_go()) is not None

    def store_paragraph(self, paragraph: Paragraph) -> bool:
        if self.paragraph_exists(paragraph.document_id, paragraph.evidence_hash):
            return False

        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO kip_v2_paragraphs
                       (paragraph_id, document_id, company_id, section, page, idx, text, is_table,
                        entities, importance_score, embedding, evidence_hash)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::vector,$12)
                       ON CONFLICT DO NOTHING""",
                    paragraph.paragraph_id, paragraph.document_id, paragraph.company_id, paragraph.section,
                    paragraph.page, paragraph.index, paragraph.text, paragraph.is_table,
                    json.dumps(paragraph.entities), paragraph.importance_score,
                    self._vec_literal(paragraph.embedding), paragraph.evidence_hash,
                )
        self._run(_go())
        return True

    def list_paragraphs(self, document_id: str) -> list[Paragraph]:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetch(
                    "SELECT * FROM kip_v2_paragraphs WHERE document_id=$1 ORDER BY idx", document_id
                )
        rows = self._run(_go())
        return [self._row_to_paragraph(r) for r in rows]

    def all_paragraphs(self, company_id: str) -> list[Paragraph]:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetch(
                    "SELECT * FROM kip_v2_paragraphs WHERE company_id=$1 ORDER BY document_id, idx", company_id
                )
        rows = self._run(_go())
        return [self._row_to_paragraph(r) for r in rows]

    def _row_to_paragraph(self, row) -> Paragraph:
        d = dict(row)
        entities = d.get("entities")
        entities = json.loads(entities) if isinstance(entities, str) else (entities or [])
        embedding_raw = d.get("embedding")
        embedding = []
        if embedding_raw:
            s = str(embedding_raw).strip("[]")
            embedding = [float(x) for x in s.split(",") if x.strip()] if s else []
        return Paragraph(
            paragraph_id=d["paragraph_id"], document_id=d["document_id"], company_id=d["company_id"],
            section=d["section"], page=d["page"], index=d["idx"], text=d["text"],
            is_table=bool(d["is_table"]), entities=entities, importance_score=d["importance_score"],
            embedding=embedding, evidence_hash=d["evidence_hash"],
        )

    # ---- facts -----------------------------------------------------------
    def _persist_fact(self, fact: Fact) -> None:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO kip_v2_facts
                       (fact_id, company_id, category, key, value, period, unit, currency, confidence,
                        evidence, source_document_id, timestamp, version, status, superseded_by, extra)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                       ON CONFLICT (fact_id) DO UPDATE SET
                         value=EXCLUDED.value, confidence=EXCLUDED.confidence, evidence=EXCLUDED.evidence,
                         timestamp=EXCLUDED.timestamp, version=EXCLUDED.version, status=EXCLUDED.status,
                         superseded_by=EXCLUDED.superseded_by, extra=EXCLUDED.extra""",
                    fact.fact_id, fact.company_id, fact.category, fact.key, json.dumps(fact.value),
                    fact.period, fact.unit, fact.currency, fact.confidence,
                    json.dumps(fact.evidence.to_dict()), fact.source_document_id, fact.timestamp,
                    fact.version, fact.status, fact.superseded_by, json.dumps(fact.extra),
                )
        self._run(_go())

    def get_facts(
        self,
        company_id: str,
        category: Optional[str] = None,
        key: Optional[str] = None,
        period: Optional[str] = None,
        status: Optional[str] = FactStatus.ACTIVE.value,
    ) -> list[Fact]:
        clauses = ["company_id=$1"]
        params: list[Any] = [company_id]
        if category:
            params.append(category)
            clauses.append(f"category=${len(params)}")
        if key:
            params.append(key)
            clauses.append(f"key=${len(params)}")
        if period:
            params.append(period)
            clauses.append(f"period=${len(params)}")
        if status:
            params.append(status)
            clauses.append(f"status=${len(params)}")
        query = f"SELECT * FROM kip_v2_facts WHERE {' AND '.join(clauses)} ORDER BY timestamp DESC"

        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetch(query, *params)
        rows = self._run(_go())
        return [self._row_to_fact(r) for r in rows]

    def get_fact(self, fact_id: str) -> Optional[Fact]:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetchrow("SELECT * FROM kip_v2_facts WHERE fact_id=$1", fact_id)
        row = self._run(_go())
        return self._row_to_fact(row) if row else None

    def supersede_fact(self, old_fact_id: str, new_fact_id: str) -> None:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE kip_v2_facts SET status=$1, superseded_by=$2 WHERE fact_id=$3",
                    FactStatus.ARCHIVED.value, new_fact_id, old_fact_id,
                )
        self._run(_go())

    def record_rejection(self, category: str, errors: list[str]) -> None:
        import time

        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO kip_v2_rejections (category, errors, at) VALUES ($1,$2,$3)",
                    category, json.dumps(errors), time.time(),
                )
        self._run(_go())

    def _row_to_fact(self, row) -> Fact:
        d = dict(row)
        value = d.get("value")
        value = json.loads(value) if isinstance(value, str) else value
        ev = d.get("evidence")
        ev = json.loads(ev) if isinstance(ev, str) else ev
        extra = d.get("extra")
        extra = json.loads(extra) if isinstance(extra, str) else (extra or {})
        evidence = Evidence(
            document_id=ev["document_id"], page=ev["page"], paragraph_id=ev["paragraph_id"],
            snippet=ev["snippet"], evidence_hash=ev["evidence_hash"], created_at=ev.get("created_at", 0.0),
        )
        return Fact(
            fact_id=d["fact_id"], company_id=d["company_id"], category=d["category"], key=d["key"],
            value=value, period=d["period"], unit=d["unit"], currency=d["currency"],
            confidence=d["confidence"], evidence=evidence, source_document_id=d["source_document_id"],
            timestamp=d["timestamp"], version=d["version"], status=d["status"],
            superseded_by=d["superseded_by"], extra=extra,
        )

    # ---- knowledge graph -------------------------------------------------
    def upsert_node(self, node: GraphNode) -> None:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO kip_v2_graph_nodes (node_id, node_type, name, attributes)
                       VALUES ($1,$2,$3,$4)
                       ON CONFLICT (node_id) DO UPDATE SET
                         node_type=EXCLUDED.node_type, name=EXCLUDED.name, attributes=EXCLUDED.attributes""",
                    node.node_id, node.node_type, node.name, json.dumps(node.attributes),
                )
        self._run(_go())

    def upsert_edge(self, edge: GraphEdge) -> None:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO kip_v2_graph_edges (edge_id, source_id, target_id, relation, confidence, evidence_hash)
                       VALUES ($1,$2,$3,$4,$5,$6)
                       ON CONFLICT (edge_id) DO UPDATE SET confidence=EXCLUDED.confidence""",
                    edge.edge_id, edge.source_id, edge.target_id, edge.relation, edge.confidence, edge.evidence_hash,
                )
        self._run(_go())

    def get_graph(self, node_id: str) -> tuple[list[GraphNode], list[GraphEdge]]:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                edge_rows = await conn.fetch(
                    "SELECT * FROM kip_v2_graph_edges WHERE source_id=$1 OR target_id=$1", node_id
                )
                node_ids = {node_id}
                for r in edge_rows:
                    node_ids.add(r["source_id"])
                    node_ids.add(r["target_id"])
                node_rows = await conn.fetch(
                    "SELECT * FROM kip_v2_graph_nodes WHERE node_id = ANY($1::text[])", list(node_ids)
                )
                return edge_rows, node_rows
        edge_rows, node_rows = self._run(_go())
        edges = [GraphEdge(edge_id=r["edge_id"], source_id=r["source_id"], target_id=r["target_id"],
                            relation=r["relation"], confidence=r["confidence"], evidence_hash=r["evidence_hash"])
                 for r in edge_rows]
        nodes = []
        for r in node_rows:
            attrs = r["attributes"]
            attrs = json.loads(attrs) if isinstance(attrs, str) else (attrs or {})
            nodes.append(GraphNode(node_id=r["node_id"], node_type=r["node_type"], name=r["name"], attributes=attrs))
        return nodes, edges

    # ---- deltas -----------------------------------------------------------
    def store_delta(self, delta: ChangeDelta) -> None:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO kip_v2_deltas
                       (delta_id, company_id, category, key, change_type, from_period, to_period,
                        old_value, new_value, old_evidence, new_evidence, magnitude_pct, detected_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                       ON CONFLICT (delta_id) DO UPDATE SET new_value=EXCLUDED.new_value""",
                    delta.delta_id, delta.company_id, delta.category, delta.key, delta.change_type,
                    delta.from_period, delta.to_period, json.dumps(delta.old_value), json.dumps(delta.new_value),
                    json.dumps(delta.old_evidence), json.dumps(delta.new_evidence), delta.magnitude_pct,
                    delta.detected_at,
                )
        self._run(_go())

    def get_deltas(
        self, company_id: str, from_period: Optional[str] = None, to_period: Optional[str] = None
    ) -> list[ChangeDelta]:
        clauses = ["company_id=$1"]
        params: list[Any] = [company_id]
        if from_period:
            params.append(from_period)
            clauses.append(f"from_period=${len(params)}")
        if to_period:
            params.append(to_period)
            clauses.append(f"to_period=${len(params)}")
        query = f"SELECT * FROM kip_v2_deltas WHERE {' AND '.join(clauses)} ORDER BY detected_at DESC"

        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                return await conn.fetch(query, *params)
        rows = self._run(_go())
        out = []
        for r in rows:
            d = dict(r)
            for f in ("old_value", "new_value", "old_evidence", "new_evidence"):
                if isinstance(d.get(f), str):
                    d[f] = json.loads(d[f])
            out.append(ChangeDelta(**d))
        return out

    # ---- observability -----------------------------------------------------
    def stats(self) -> dict[str, Any]:
        async def _go():
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                async def count(table: str, where: str = "") -> int:
                    return await conn.fetchval(f"SELECT COUNT(*) FROM {table} {where}")

                return {
                    "backend": "postgres",
                    "documents": await count("kip_v2_documents"),
                    "paragraphs": await count("kip_v2_paragraphs"),
                    "facts_active": await count("kip_v2_facts", "WHERE status='active'"),
                    "facts_archived": await count("kip_v2_facts", "WHERE status='archived'"),
                    "graph_nodes": await count("kip_v2_graph_nodes"),
                    "graph_edges": await count("kip_v2_graph_edges"),
                    "deltas": await count("kip_v2_deltas"),
                    "rejections": await count("kip_v2_rejections"),
                }
        return self._run(_go())
