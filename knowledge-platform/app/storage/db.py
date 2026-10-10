"""SQLite storage for KAIP/IKO — append-only versions, never overwrite history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.contracts.models import (
    Confidence,
    EntityRefs,
    KnowledgeMetadata,
    KnowledgeObject,
    KnowledgeObjectType,
    LearningCategory,
    LearningEvent,
    Importance,
    PublicationEnvelope,
    Source,
)

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class KaipStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self._conn.executescript(sql)
        self._migrate_operate_columns()
        self._conn.commit()

    def _migrate_operate_columns(self) -> None:
        """Additive migrations for Sprint 6.5 KFE/KCE on existing DBs."""
        freshness_cols = {
            row[1] for row in self._conn.execute("PRAGMA table_info(freshness_registry)").fetchall()
        }
        for col, decl in (
            ("status", "TEXT"),
            ("age_seconds", "INTEGER"),
            ("sla_label", "TEXT"),
            ("current_as_of", "TEXT"),
        ):
            if col not in freshness_cols:
                self._conn.execute(f"ALTER TABLE freshness_registry ADD COLUMN {col} {decl}")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS confidence_registry (
                object_type TEXT NOT NULL,
                subject_key TEXT NOT NULL,
                confidence_pct REAL NOT NULL,
                label TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (object_type, subject_key)
            )
            """
        )

    def close(self) -> None:
        self._conn.close()

    # ----- raw events -----

    def insert_raw_event(self, event) -> None:
        now = _iso(datetime.now(timezone.utc))
        self._conn.execute(
            """
            INSERT INTO raw_events (
                event_id, source, collector_id, endpoint, company_symbol,
                payload_json, timestamp, checksum, validation_status,
                validation_errors_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.source.value,
                event.collector_id,
                event.endpoint,
                event.company_symbol,
                json.dumps(event.payload, default=str),
                _iso(event.timestamp),
                event.checksum,
                event.validation_status.value if event.validation_status else None,
                json.dumps(event.validation_errors),
                now,
            ),
        )
        self._conn.commit()

    def update_raw_validation(self, event) -> None:
        self._conn.execute(
            """
            UPDATE raw_events
            SET validation_status = ?, validation_errors_json = ?
            WHERE event_id = ?
            """,
            (
                event.validation_status.value if event.validation_status else None,
                json.dumps(event.validation_errors),
                event.event_id,
            ),
        )
        self._conn.commit()

    def find_duplicate(
        self,
        *,
        source: str,
        company_symbol: str | None,
        checksum: str,
        window_seconds: int,
        now: datetime | None = None,
    ) -> bool:
        now = now or datetime.now(timezone.utc)
        rows = self._conn.execute(
            """
            SELECT timestamp FROM raw_events
            WHERE source = ? AND checksum = ?
              AND IFNULL(company_symbol, '') = IFNULL(?, '')
              AND validation_status IN ('accepted', 'duplicate')
            ORDER BY timestamp DESC
            LIMIT 20
            """,
            (source, checksum, company_symbol),
        ).fetchall()
        for row in rows:
            ts = _parse_dt(row["timestamp"])
            if ts is None:
                continue
            if abs((now - ts).total_seconds()) <= window_seconds:
                return True
        return False

    # ----- entity registry -----

    def upsert_entity(
        self,
        *,
        company_symbol: str,
        company_id: str,
        company_name: str,
        sector: str | None,
        industry: str | None,
        indexes: list[str],
        peers: list[str],
        clients: list[str] | None = None,
        aliases: list[str] | None = None,
    ) -> EntityRefs:
        now = _iso(datetime.now(timezone.utc))
        self._conn.execute(
            """
            INSERT INTO entity_registry (
                company_symbol, company_id, company_name, sector, industry,
                indexes_json, peers_json, clients_json, aliases_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_symbol) DO UPDATE SET
                company_id = excluded.company_id,
                company_name = excluded.company_name,
                sector = excluded.sector,
                industry = excluded.industry,
                indexes_json = excluded.indexes_json,
                peers_json = excluded.peers_json,
                clients_json = excluded.clients_json,
                aliases_json = excluded.aliases_json,
                updated_at = excluded.updated_at
            """,
            (
                company_symbol.upper(),
                company_id,
                company_name,
                sector,
                industry,
                json.dumps(indexes),
                json.dumps(peers),
                json.dumps(clients or []),
                json.dumps(aliases or []),
                now,
            ),
        )
        self._conn.commit()
        return EntityRefs(
            company_id=company_id,
            company_name=company_name,
            company_symbol=company_symbol.upper(),
            sector=sector,
            industry=industry,
            indexes=indexes,
            peers=peers,
            clients=list(clients or []),
            sector_key=(sector.lower().replace(" ", "_") if sector else None),
        )

    def get_entity(self, company_symbol: str) -> EntityRefs | None:
        row = self._conn.execute(
            "SELECT * FROM entity_registry WHERE company_symbol = ?",
            (company_symbol.upper(),),
        ).fetchone()
        if not row:
            return None
        clients = []
        try:
            clients = json.loads(row["clients_json"] or "[]")
        except (KeyError, TypeError, json.JSONDecodeError):
            clients = []
        return EntityRefs(
            company_id=row["company_id"],
            company_name=row["company_name"],
            company_symbol=row["company_symbol"],
            sector=row["sector"],
            industry=row["industry"],
            indexes=json.loads(row["indexes_json"] or "[]"),
            peers=json.loads(row["peers_json"] or "[]"),
            clients=clients,
            sector_key=(row["sector"].lower().replace(" ", "_") if row["sector"] else None),
        )

    def update_entity_relationships(
        self,
        company_symbol: str,
        *,
        sector: str | None = None,
        industry: str | None = None,
        indexes: list[str] | None = None,
        peers: list[str] | None = None,
        clients: list[str] | None = None,
    ) -> EntityRefs | None:
        current = self.get_entity(company_symbol)
        if not current:
            return None
        return self.upsert_entity(
            company_symbol=current.company_symbol or company_symbol,
            company_id=current.company_id or f"co_{company_symbol.lower()}",
            company_name=current.company_name or company_symbol,
            sector=sector if sector is not None else current.sector,
            industry=industry if industry is not None else current.industry,
            indexes=indexes if indexes is not None else current.indexes,
            peers=peers if peers is not None else current.peers,
            clients=clients if clients is not None else current.clients,
        )

    def upsert_relationship_edge(
        self,
        *,
        from_type: str,
        from_key: str,
        edge_type: str,
        to_type: str,
        to_key: str,
    ) -> None:
        now = _iso(datetime.now(timezone.utc))
        edge_id = f"{from_type}:{from_key}:{edge_type}:{to_type}:{to_key}"
        self._conn.execute(
            """
            INSERT INTO relationship_edges (
                edge_id, from_type, from_key, edge_type, to_type, to_key, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(edge_id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (edge_id, from_type, from_key, edge_type, to_type, to_key, now),
        )
        self._conn.commit()

    def list_relationships(self, from_type: str, from_key: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM relationship_edges
            WHERE from_type = ? AND from_key = ?
            ORDER BY edge_type, to_key
            """,
            (from_type, from_key),
        ).fetchall()
        return [dict(r) for r in rows]

    # ----- knowledge objects -----

    def latest_ko(self, object_type: KnowledgeObjectType, subject_key: str) -> KnowledgeObject | None:
        row = self._conn.execute(
            """
            SELECT * FROM knowledge_objects
            WHERE object_type = ? AND subject_key = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (object_type.value, subject_key.upper() if object_type not in {
                KnowledgeObjectType.SECTOR_KNOWLEDGE,
                KnowledgeObjectType.MARKET_KNOWLEDGE,
            } else subject_key),
        ).fetchone()
        if not row:
            # fallback for company symbols stored uppercased
            row = self._conn.execute(
                """
                SELECT * FROM knowledge_objects
                WHERE object_type = ? AND (subject_key = ? OR company_symbol = ?)
                ORDER BY version DESC
                LIMIT 1
                """,
                (object_type.value, subject_key, subject_key.upper()),
            ).fetchone()
        if not row:
            return None
        return self._row_to_ko(row)

    def list_versions(self, object_type: KnowledgeObjectType, subject_key: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT object_id, version, previous_object_id, changed_fields_json,
                   change_summary, created_at, published_at
            FROM knowledge_objects
            WHERE object_type = ? AND (subject_key = ? OR company_symbol = ?)
            ORDER BY version ASC
            """,
            (object_type.value, subject_key, subject_key.upper()),
        ).fetchall()
        return [
            {
                "object_id": r["object_id"],
                "version": r["version"],
                "previous_object_id": r["previous_object_id"],
                "changed_fields": json.loads(r["changed_fields_json"] or "[]"),
                "change_summary": r["change_summary"],
                "created_at": r["created_at"],
                "published_at": r["published_at"],
            }
            for r in rows
        ]

    def insert_knowledge_object(self, ko: KnowledgeObject) -> None:
        knowledge = ko.knowledge or ko.payload
        self._conn.execute(
            """
            INSERT INTO knowledge_objects (
                object_id, object_type, subject_key, company_symbol, sector_key, market_key,
                version, previous_object_id, changed_fields_json, change_summary,
                knowledge_json, payload_json, metadata_json, entity_refs_json,
                source_event_ids_json, published_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ko.object_id,
                ko.object_type.value,
                ko.subject_key,
                ko.company_symbol.upper() if ko.company_symbol else None,
                ko.sector_key,
                ko.market_key,
                ko.version,
                ko.previous_object_id,
                json.dumps(ko.changed_fields),
                ko.change_summary,
                json.dumps(knowledge, default=str),
                json.dumps(knowledge, default=str),
                ko.metadata.model_dump_json(),
                ko.entity_refs.model_dump_json(),
                json.dumps(ko.source_event_ids),
                _iso(ko.published_at),
                _iso(ko.created_at),
                _iso(ko.updated_at),
            ),
        )
        self._mirror_typed(ko)
        self._conn.commit()

    def mark_published(self, object_id: str, published_at: datetime) -> None:
        self._conn.execute(
            "UPDATE knowledge_objects SET published_at = ?, updated_at = ? WHERE object_id = ?",
            (_iso(published_at), _iso(published_at), object_id),
        )
        self._conn.commit()

    def _mirror_typed(self, ko: KnowledgeObject) -> None:
        knowledge = ko.knowledge or ko.payload
        blob = json.dumps(knowledge, default=str)
        meta = ko.metadata.model_dump_json()
        refs = ko.entity_refs.model_dump_json()
        now = _iso(ko.updated_at)
        symbol = ko.company_symbol.upper() if ko.company_symbol else None

        if ko.object_type == KnowledgeObjectType.COMPANY_PROFILE and symbol:
            self._conn.execute(
                """
                INSERT INTO company_profiles (
                    company_symbol, object_id, knowledge_json, payload_json, metadata_json,
                    entity_refs_json, version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_symbol) DO UPDATE SET
                    object_id = excluded.object_id,
                    knowledge_json = excluded.knowledge_json,
                    payload_json = excluded.payload_json,
                    metadata_json = excluded.metadata_json,
                    entity_refs_json = excluded.entity_refs_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (symbol, ko.object_id, blob, blob, meta, refs, ko.version, now),
            )
        elif ko.object_type == KnowledgeObjectType.MARKET_SNAPSHOT and symbol:
            self._conn.execute(
                """
                INSERT INTO market_snapshots (
                    snapshot_id, company_symbol, object_id, knowledge_json, payload_json,
                    metadata_json, as_of, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.object_id,
                    blob,
                    blob,
                    meta,
                    knowledge.get("as_of") or now,
                    now,
                ),
            )
        elif ko.object_type == KnowledgeObjectType.CORPORATE_EVENT and symbol:
            self._conn.execute(
                """
                INSERT INTO corporate_events (
                    event_object_id, company_symbol, object_id, knowledge_json, payload_json,
                    metadata_json, event_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ko.object_id, symbol, ko.object_id, blob, blob, meta, knowledge.get("event_date"), now),
            )
        elif ko.object_type == KnowledgeObjectType.CORPORATE_ACTION and symbol:
            self._conn.execute(
                """
                INSERT INTO corporate_actions (
                    action_object_id, company_symbol, object_id, knowledge_json, payload_json,
                    metadata_json, ex_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ko.object_id, symbol, ko.object_id, blob, blob, meta, knowledge.get("ex_date"), now),
            )
        elif ko.object_type == KnowledgeObjectType.FINANCIAL_STATEMENT and symbol:
            self._conn.execute(
                """
                INSERT INTO financial_statements (
                    statement_id, company_symbol, object_id, statement_type, period_end,
                    knowledge_json, payload_json, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.object_id,
                    knowledge.get("statement_type") or "unknown",
                    knowledge.get("period_end"),
                    blob,
                    blob,
                    meta,
                    now,
                ),
            )
        elif ko.object_type == KnowledgeObjectType.OWNERSHIP and symbol:
            self._conn.execute(
                """
                INSERT INTO ownership (
                    ownership_id, company_symbol, object_id, knowledge_json, metadata_json,
                    as_of, version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ko.object_id, symbol, ko.object_id, blob, meta, knowledge.get("as_of"), ko.version, now),
            )
        elif ko.object_type == KnowledgeObjectType.ANALYST_CONSENSUS and symbol:
            self._conn.execute(
                """
                INSERT INTO analyst_consensus (
                    consensus_id, company_symbol, object_id, knowledge_json, metadata_json,
                    version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ko.object_id, symbol, ko.object_id, blob, meta, ko.version, now),
            )
        elif ko.object_type == KnowledgeObjectType.NEWS_EVENT:
            self._conn.execute(
                """
                INSERT INTO news_events (
                    news_id, company_symbol, object_id, knowledge_json, metadata_json,
                    event_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.object_id,
                    blob,
                    meta,
                    knowledge.get("event_date"),
                    now,
                ),
            )
        elif ko.object_type == KnowledgeObjectType.SECTOR_KNOWLEDGE and ko.sector_key:
            self._conn.execute(
                """
                INSERT INTO sector_knowledge (
                    sector_key, object_id, knowledge_json, metadata_json, version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(sector_key) DO UPDATE SET
                    object_id = excluded.object_id,
                    knowledge_json = excluded.knowledge_json,
                    metadata_json = excluded.metadata_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (ko.sector_key, ko.object_id, blob, meta, ko.version, now),
            )
        elif ko.object_type == KnowledgeObjectType.MARKET_KNOWLEDGE and ko.market_key:
            self._conn.execute(
                """
                INSERT INTO market_knowledge (
                    market_key, object_id, knowledge_json, metadata_json, version, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(market_key) DO UPDATE SET
                    object_id = excluded.object_id,
                    knowledge_json = excluded.knowledge_json,
                    metadata_json = excluded.metadata_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (ko.market_key, ko.object_id, blob, meta, ko.version, now),
            )

    def _row_to_ko(self, row: sqlite3.Row) -> KnowledgeObject:
        knowledge = json.loads(row["knowledge_json"] if "knowledge_json" in row.keys() and row["knowledge_json"] else row["payload_json"])
        meta_raw = row["metadata_json"] if "metadata_json" in row.keys() and row["metadata_json"] else None
        if meta_raw:
            metadata = KnowledgeMetadata.model_validate_json(meta_raw)
        else:
            metadata = KnowledgeMetadata(source=Source.DERIVED, version=row["version"])
        return KnowledgeObject(
            object_id=row["object_id"],
            object_type=KnowledgeObjectType(row["object_type"]),
            company_symbol=row["company_symbol"] if "company_symbol" in row.keys() else None,
            sector_key=row["sector_key"] if "sector_key" in row.keys() else None,
            market_key=row["market_key"] if "market_key" in row.keys() else None,
            subject_key=row["subject_key"] if "subject_key" in row.keys() else (row["company_symbol"] or "unknown"),
            version=row["version"],
            previous_object_id=row["previous_object_id"] if "previous_object_id" in row.keys() else None,
            changed_fields=json.loads(row["changed_fields_json"] or "[]") if "changed_fields_json" in row.keys() else [],
            change_summary=row["change_summary"] if "change_summary" in row.keys() else None,
            knowledge=knowledge,
            payload=knowledge,
            metadata=metadata,
            entity_refs=EntityRefs.model_validate_json(row["entity_refs_json"]),
            source_event_ids=json.loads(row["source_event_ids_json"] or "[]"),
            published_at=_parse_dt(row["published_at"]),
            created_at=_parse_dt(row["created_at"]) or datetime.now(timezone.utc),
            updated_at=_parse_dt(row["updated_at"]) or datetime.now(timezone.utc),
        )

    def get_company_profile(self, symbol: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM company_profiles WHERE company_symbol = ?",
            (symbol.upper(),),
        ).fetchone()
        if not row:
            return None
        knowledge = json.loads(row["knowledge_json"] if row["knowledge_json"] else row["payload_json"])
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return {
            "object_id": row["object_id"],
            "company_symbol": row["company_symbol"],
            "version": row["version"],
            "knowledge": knowledge,
            "payload": knowledge,
            "metadata": meta,
            "entity_refs": json.loads(row["entity_refs_json"]),
            "updated_at": row["updated_at"],
        }

    def get_latest_market(self, symbol: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT * FROM market_snapshots
            WHERE company_symbol = ?
            ORDER BY as_of DESC
            LIMIT 1
            """,
            (symbol.upper(),),
        ).fetchone()
        if not row:
            return None
        knowledge = json.loads(row["knowledge_json"] if row["knowledge_json"] else row["payload_json"])
        return {
            "object_id": row["object_id"],
            "company_symbol": row["company_symbol"],
            "knowledge": knowledge,
            "payload": knowledge,
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            "as_of": row["as_of"],
            "updated_at": row["updated_at"],
        }

    def list_events(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM corporate_events
            WHERE company_symbol = ?
            ORDER BY IFNULL(event_date, updated_at) DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [
            {
                "object_id": r["object_id"],
                "company_symbol": r["company_symbol"],
                "knowledge": json.loads(r["knowledge_json"] if r["knowledge_json"] else r["payload_json"]),
                "payload": json.loads(r["knowledge_json"] if r["knowledge_json"] else r["payload_json"]),
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                "event_date": r["event_date"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def list_financials(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM financial_statements
            WHERE company_symbol = ?
            ORDER BY IFNULL(period_end, updated_at) DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [
            {
                "object_id": r["object_id"],
                "company_symbol": r["company_symbol"],
                "statement_type": r["statement_type"],
                "period_end": r["period_end"],
                "knowledge": json.loads(r["knowledge_json"] if r["knowledge_json"] else r["payload_json"]),
                "payload": json.loads(r["knowledge_json"] if r["knowledge_json"] else r["payload_json"]),
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else {},
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def get_sector_knowledge(self, sector_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM sector_knowledge WHERE sector_key = ?",
            (sector_key,),
        ).fetchone()
        if not row:
            return None
        return {
            "object_id": row["object_id"],
            "sector_key": row["sector_key"],
            "version": row["version"],
            "knowledge": json.loads(row["knowledge_json"]),
            "metadata": json.loads(row["metadata_json"]),
            "updated_at": row["updated_at"],
        }

    def get_market_knowledge(self, market_key: str = "india_equity") -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM market_knowledge WHERE market_key = ?",
            (market_key,),
        ).fetchone()
        if not row:
            return None
        return {
            "object_id": row["object_id"],
            "market_key": row["market_key"],
            "version": row["version"],
            "knowledge": json.loads(row["knowledge_json"]),
            "metadata": json.loads(row["metadata_json"]),
            "updated_at": row["updated_at"],
        }

    def insert_learning_event(self, event: LearningEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO learning_events (
                learning_id, company_symbol, sector_key, market_key, category, category_label,
                importance, confidence, field_name, previous_value_json, new_value_json,
                delta_json, materiality, materiality_score, reason, observation, evidence,
                affected_json, object_type, object_id, source_event_ids_json,
                created_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.learning_id,
                event.company_symbol.upper() if event.company_symbol else None,
                event.sector_key,
                event.market_key,
                event.category.value,
                event.category_label,
                event.importance.value,
                event.confidence.value,
                event.field_name,
                json.dumps(event.previous_value, default=str),
                json.dumps(event.new_value, default=str),
                json.dumps(event.delta, default=str),
                event.materiality,
                float(event.materiality_score or 0),
                event.reason,
                event.observation or event.reason,
                event.evidence,
                json.dumps(event.affected),
                event.object_type.value if event.object_type else None,
                event.object_id,
                json.dumps(event.source_event_ids),
                _iso(event.created_at),
                _iso(event.published_at),
            ),
        )
        self._conn.commit()

    def mark_learning_published(self, learning_id: str, published_at: datetime) -> None:
        self._conn.execute(
            "UPDATE learning_events SET published_at = ? WHERE learning_id = ?",
            (_iso(published_at), learning_id),
        )
        self._conn.commit()

    def list_learning(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM learning_events
            WHERE company_symbol = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        out = []
        for r in rows:
            keys = r.keys()
            out.append(
                {
                    "learning_id": r["learning_id"],
                    "company_symbol": r["company_symbol"],
                    "category": r["category"],
                    "category_label": r["category_label"] if "category_label" in keys else r["category"],
                    "importance": r["importance"],
                    "confidence": r["confidence"] if "confidence" in keys else None,
                    "field_name": r["field_name"],
                    "previous_value": json.loads(r["previous_value_json"]) if r["previous_value_json"] else None,
                    "new_value": json.loads(r["new_value_json"]) if r["new_value_json"] else None,
                    "delta": json.loads(r["delta_json"]) if r["delta_json"] else None,
                    "materiality": r["materiality"],
                    "materiality_score": r["materiality_score"] if "materiality_score" in keys else None,
                    "reason": r["reason"],
                    "observation": r["observation"] if "observation" in keys else r["reason"],
                    "evidence": r["evidence"] if "evidence" in keys else None,
                    "affected": json.loads(r["affected_json"] or "[]"),
                    "object_type": r["object_type"],
                    "object_id": r["object_id"],
                    "created_at": r["created_at"],
                    "published_at": r["published_at"],
                }
            )
        return out

    def insert_relationship_change(self, *, company_symbol: str, field_name: str, detail: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO relationship_changes (change_id, company_symbol, field_name, detail_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid4()), company_symbol.upper(), field_name, json.dumps(detail, default=str), _iso(datetime.now(timezone.utc))),
        )
        self._conn.commit()

    def record_sector_signal(
        self, *, sector_key: str, field_name: str, direction: int, company_symbol: str
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO sector_signals (signal_id, sector_key, field_name, direction, company_symbol, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                sector_key,
                field_name,
                int(direction),
                company_symbol.upper(),
                _iso(datetime.now(timezone.utc)),
            ),
        )
        self._conn.commit()

    def sector_signal_supporters(
        self, *, sector_key: str, field_name: str, direction: int, limit: int = 10
    ) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT company_symbol FROM sector_signals
            WHERE sector_key = ? AND field_name = ? AND direction = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (sector_key, field_name, int(direction), limit),
        ).fetchall()
        return [r["company_symbol"] for r in rows]

    def insert_sector_learning(self, item) -> None:
        self._conn.execute(
            """
            INSERT INTO sector_learning (
                learning_id, sector, sector_key, observation, supporting_companies_json,
                field_name, importance, created_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.learning_id,
                item.sector,
                item.sector_key,
                item.observation,
                json.dumps(item.supporting_companies),
                item.field_name,
                item.importance,
                item.created_at,
                None,
            ),
        )
        self._conn.commit()

    def list_sector_learning(self, sector_key: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM sector_learning
            WHERE sector_key = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (sector_key, limit),
        ).fetchall()
        return [
            {
                "learning_id": r["learning_id"],
                "sector": r["sector"],
                "sector_key": r["sector_key"],
                "observation": r["observation"],
                "supporting_companies": json.loads(r["supporting_companies_json"] or "[]"),
                "field_name": r["field_name"],
                "importance": r["importance"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def record_market_theme_signal(self, *, theme: str, sector: str) -> None:
        self._conn.execute(
            """
            INSERT INTO market_theme_signals (signal_id, theme, sector, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (str(uuid4()), theme, sector, _iso(datetime.now(timezone.utc))),
        )
        self._conn.commit()

    def market_theme_sectors(self, theme: str) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT sector FROM market_theme_signals
            WHERE theme = ?
            ORDER BY created_at DESC
            """,
            (theme,),
        ).fetchall()
        return [r["sector"] for r in rows]

    def insert_market_learning(self, item) -> None:
        self._conn.execute(
            """
            INSERT INTO market_learning (
                learning_id, theme, observation, beneficiaries_json, supporting_sectors_json,
                historical_confidence, created_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.learning_id,
                item.theme,
                item.observation,
                json.dumps(item.beneficiaries),
                json.dumps(item.supporting_sectors),
                item.historical_confidence,
                item.created_at,
                None,
            ),
        )
        self._conn.commit()

    def list_market_learning(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM market_learning
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "learning_id": r["learning_id"],
                "theme": r["theme"],
                "observation": r["observation"],
                "beneficiaries": json.loads(r["beneficiaries_json"] or "[]"),
                "supporting_sectors": json.loads(r["supporting_sectors_json"] or "[]"),
                "historical_confidence": r["historical_confidence"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def insert_knowledge_conflict(self, conflict) -> None:
        self._conn.execute(
            """
            INSERT INTO knowledge_conflicts (
                conflict_id, company_symbol, status, reason, previous_assumption,
                new_observation, field_name, previous_value_json, new_value_json,
                object_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conflict.conflict_id,
                conflict.company_symbol.upper() if conflict.company_symbol else None,
                conflict.status,
                conflict.reason,
                conflict.previous_assumption,
                conflict.new_observation,
                conflict.field_name,
                json.dumps(conflict.previous_value, default=str),
                json.dumps(conflict.new_value, default=str),
                conflict.object_id,
                _iso(datetime.now(timezone.utc)),
            ),
        )
        self._conn.commit()

    def list_conflicts(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM knowledge_conflicts
            WHERE company_symbol = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [
            {
                "conflict_id": r["conflict_id"],
                "company_symbol": r["company_symbol"],
                "status": r["status"],
                "reason": r["reason"],
                "previous_assumption": r["previous_assumption"],
                "new_observation": r["new_observation"],
                "field_name": r["field_name"],
                "previous_value": json.loads(r["previous_value_json"]) if r["previous_value_json"] else None,
                "new_value": json.loads(r["new_value_json"]) if r["new_value_json"] else None,
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def insert_institutional_memory(self, mem) -> None:
        self._conn.execute(
            """
            INSERT INTO institutional_memory (
                memory_id, company_symbol, narrative, category, importance,
                source_learning_fields_json, object_id, created_at, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mem.memory_id,
                mem.company_symbol.upper(),
                mem.narrative,
                mem.category,
                mem.importance,
                json.dumps(mem.source_learning_fields),
                mem.object_id,
                mem.created_at,
                None,
            ),
        )
        self._conn.commit()

    def list_memory(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM institutional_memory
            WHERE company_symbol = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [
            {
                "memory_id": r["memory_id"],
                "company_symbol": r["company_symbol"],
                "narrative": r["narrative"],
                "category": r["category"],
                "importance": r["importance"],
                "source_learning_fields": json.loads(r["source_learning_fields_json"] or "[]"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def insert_timeline_entry(self, entry) -> None:
        self._conn.execute(
            """
            INSERT INTO learning_timeline (
                entry_id, company_symbol, year, label, detail, field_name,
                importance, object_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.entry_id,
                entry.company_symbol.upper(),
                entry.year,
                entry.label,
                entry.detail,
                entry.field_name,
                entry.importance,
                entry.object_id,
                entry.created_at,
            ),
        )
        self._conn.commit()

    def list_timeline(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM learning_timeline
            WHERE company_symbol = ?
            ORDER BY year ASC, created_at ASC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [
            {
                "entry_id": r["entry_id"],
                "company_symbol": r["company_symbol"],
                "year": r["year"],
                "label": r["label"],
                "detail": r["detail"],
                "field_name": r["field_name"],
                "importance": r["importance"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]

    def log_publication(self, envelope: PublicationEnvelope) -> None:
        self._conn.execute(
            """
            INSERT INTO publication_log (publication_id, envelope_json, published_at)
            VALUES (?, ?, ?)
            """,
            (str(uuid4()), envelope.model_dump_json(), _iso(envelope.published_at)),
        )
        self._conn.commit()

    def count_raw_events(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM raw_events").fetchone()["c"])

    def count_published_kos(self) -> int:
        return int(
            self._conn.execute(
                "SELECT COUNT(*) AS c FROM knowledge_objects WHERE published_at IS NOT NULL"
            ).fetchone()["c"]
        )

    # ----- Sprint 6.4 KRIG -----

    def put_bundle_cache(self, cache_key: str, bundle: dict[str, Any], *, ttl_seconds: int) -> None:
        now = datetime.now(timezone.utc)
        expires = now.timestamp() + ttl_seconds
        expires_at = datetime.fromtimestamp(expires, tz=timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO knowledge_bundle_cache (cache_key, bundle_json, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                bundle_json = excluded.bundle_json,
                expires_at = excluded.expires_at,
                created_at = excluded.created_at
            """,
            (cache_key, json.dumps(bundle, default=str), expires_at, _iso(now)),
        )
        self._conn.commit()

    def get_bundle_cache(self, cache_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT bundle_json, expires_at FROM knowledge_bundle_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if not row:
            return None
        exp = _parse_dt(row["expires_at"])
        if exp is None or exp < datetime.now(timezone.utc):
            self._conn.execute("DELETE FROM knowledge_bundle_cache WHERE cache_key = ?", (cache_key,))
            self._conn.commit()
            return None
        return json.loads(row["bundle_json"])

    def insert_retrieval_log(self, detail: dict[str, Any]) -> None:
        self._conn.execute(
            """
            INSERT INTO retrieval_logs (log_id, detail_json, created_at)
            VALUES (?, ?, ?)
            """,
            (str(uuid4()), json.dumps(detail, default=str), _iso(datetime.now(timezone.utc))),
        )
        self._conn.commit()

    def sources_for_event_ids(self, event_ids: list[str]) -> list[str]:
        if not event_ids:
            return []
        placeholders = ",".join("?" for _ in event_ids)
        rows = self._conn.execute(
            f"SELECT DISTINCT source FROM raw_events WHERE event_id IN ({placeholders})",
            tuple(event_ids),
        ).fetchall()
        return [str(r["source"]) for r in rows if r["source"]]

    def upsert_freshness(
        self,
        *,
        object_type: str,
        subject_key: str,
        updated_at: str,
        status: str | None = None,
        age_seconds: int | None = None,
        sla_label: str | None = None,
        current_as_of: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO freshness_registry (
                object_type, subject_key, updated_at, status, age_seconds, sla_label, current_as_of
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_type, subject_key) DO UPDATE SET
                updated_at = excluded.updated_at,
                status = excluded.status,
                age_seconds = excluded.age_seconds,
                sla_label = excluded.sla_label,
                current_as_of = excluded.current_as_of
            """,
            (object_type, subject_key, updated_at, status, age_seconds, sla_label, current_as_of),
        )
        self._conn.commit()

    def get_freshness(self, *, object_type: str, subject_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT * FROM freshness_registry
            WHERE object_type = ? AND subject_key = ?
            """,
            (object_type, subject_key),
        ).fetchone()
        if not row:
            return None
        return dict(row)

    def list_freshness(self, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM freshness_registry
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_confidence(
        self,
        *,
        object_type: str,
        subject_key: str,
        confidence_pct: float,
        label: str,
        sources: list[str],
        reasons: list[str],
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO confidence_registry (
                object_type, subject_key, confidence_pct, label, sources_json, reasons_json, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_type, subject_key) DO UPDATE SET
                confidence_pct = excluded.confidence_pct,
                label = excluded.label,
                sources_json = excluded.sources_json,
                reasons_json = excluded.reasons_json,
                updated_at = excluded.updated_at
            """,
            (
                object_type,
                subject_key,
                float(confidence_pct),
                label,
                json.dumps(sources),
                json.dumps(reasons),
                _iso(datetime.now(timezone.utc)),
            ),
        )
        self._conn.commit()

    def get_confidence(self, *, object_type: str, subject_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT * FROM confidence_registry
            WHERE object_type = ? AND subject_key = ?
            """,
            (object_type, subject_key),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["sources"] = json.loads(data.pop("sources_json") or "[]")
        data["reasons"] = json.loads(data.pop("reasons_json") or "[]")
        return data

    def list_confidence(self, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM confidence_registry
            ORDER BY confidence_pct DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            data = dict(r)
            data["sources"] = json.loads(data.pop("sources_json") or "[]")
            data["reasons"] = json.loads(data.pop("reasons_json") or "[]")
            out.append(data)
        return out

    def upsert_knowledge_dependencies(self, *, subject: str, depends_on: list[str]) -> None:
        self._conn.execute(
            """
            INSERT INTO knowledge_dependencies (subject, depends_on_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(subject) DO UPDATE SET
                depends_on_json = excluded.depends_on_json,
                updated_at = excluded.updated_at
            """,
            (subject, json.dumps(depends_on), _iso(datetime.now(timezone.utc))),
        )
        self._conn.commit()

    def increment_retrieval_metric(self, *, query_type: str, cache_hit: bool, latency_ms: float) -> None:
        key = f"krig:{query_type}"
        row = self._conn.execute(
            "SELECT hits, misses, total_latency_ms FROM retrieval_metrics WHERE metric_key = ?",
            (key,),
        ).fetchone()
        hits = int(row["hits"]) if row else 0
        misses = int(row["misses"]) if row else 0
        total = float(row["total_latency_ms"]) if row else 0.0
        if cache_hit:
            hits += 1
        else:
            misses += 1
        total += float(latency_ms)
        self._conn.execute(
            """
            INSERT INTO retrieval_metrics (metric_key, query_type, hits, misses, total_latency_ms, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(metric_key) DO UPDATE SET
                hits = excluded.hits,
                misses = excluded.misses,
                total_latency_ms = excluded.total_latency_ms,
                updated_at = excluded.updated_at
            """,
            (key, query_type, hits, misses, total, _iso(datetime.now(timezone.utc))),
        )
        self._conn.commit()

    def retrieval_metrics_snapshot(self) -> list[dict[str, Any]]:
        rows = self._conn.execute("SELECT * FROM retrieval_metrics ORDER BY query_type").fetchall()
        out = []
        for r in rows:
            total_calls = int(r["hits"]) + int(r["misses"])
            out.append(
                {
                    "query_type": r["query_type"],
                    "hits": r["hits"],
                    "misses": r["misses"],
                    "avg_latency_ms": round(float(r["total_latency_ms"]) / total_calls, 2) if total_calls else 0,
                    "updated_at": r["updated_at"],
                }
            )
        return out
