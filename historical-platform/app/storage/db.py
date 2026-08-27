"""Append-only Historical Knowledge Store — never overwrites history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.contracts.models import (
    HistoricalKnowledgeObject,
    HistoricalObjectType,
    IngestionRun,
    RawHistoricalEvent,
    ValidationStatus,
)
from app.coverage.policy import COVERAGE_TARGETS, expected_for, score_completeness

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


class HipStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ----- raw archive -----

    def insert_raw(self, event: RawHistoricalEvent) -> bool:
        """Insert raw event. Returns False if checksum already archived (idempotent)."""
        try:
            self._conn.execute(
                """
                INSERT INTO historical_raw_archive (
                    event_id, source, collector_id, endpoint, company_symbol, category,
                    payload_json, retrieved_at, effective_start, effective_end, checksum,
                    validation_status, validation_errors_json, ingestion_run_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.source.value,
                    event.collector_id,
                    event.endpoint,
                    event.company_symbol.upper() if event.company_symbol else None,
                    event.category,
                    json.dumps(event.payload, default=str),
                    _iso(event.retrieved_at),
                    event.effective_start,
                    event.effective_end,
                    event.checksum,
                    event.validation_status.value if event.validation_status else None,
                    json.dumps(event.validation_errors),
                    event.ingestion_run_id,
                    _iso(event.created_at),
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_raw_validation(self, event: RawHistoricalEvent) -> None:
        self._conn.execute(
            """
            UPDATE historical_raw_archive
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

    def checksum_exists(self, checksum: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM historical_raw_archive WHERE checksum = ?",
            (checksum,),
        ).fetchone()
        return row is not None

    def count_raw(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM historical_raw_archive").fetchone()["c"])

    # ----- ingestion runs -----

    def start_run(self, run: IngestionRun) -> None:
        self._conn.execute(
            """
            INSERT INTO historical_ingestion_runs (
                run_id, mode, collector_id, symbols_json, categories_json,
                started_at, ended_at, status, raw_accepted, raw_rejected,
                objects_written, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run.run_id,
                run.mode,
                run.collector_id,
                json.dumps(run.symbols),
                json.dumps(run.categories),
                _iso(run.started_at),
                _iso(run.ended_at),
                run.status,
                run.raw_accepted,
                run.raw_rejected,
                run.objects_written,
                json.dumps(run.detail, default=str),
            ),
        )
        self._conn.commit()

    def finish_run(self, run: IngestionRun) -> None:
        self._conn.execute(
            """
            UPDATE historical_ingestion_runs
            SET ended_at = ?, status = ?, raw_accepted = ?, raw_rejected = ?,
                objects_written = ?, detail_json = ?
            WHERE run_id = ?
            """,
            (
                _iso(run.ended_at),
                run.status,
                run.raw_accepted,
                run.raw_rejected,
                run.objects_written,
                json.dumps(run.detail, default=str),
                run.run_id,
            ),
        )
        self._conn.commit()

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM historical_ingestion_runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["symbols"] = json.loads(d.pop("symbols_json") or "[]")
            d["categories"] = json.loads(d.pop("categories_json") or "[]")
            d["detail"] = json.loads(d.pop("detail_json") or "{}")
            out.append(d)
        return out

    # ----- entities -----

    def upsert_entity(
        self,
        *,
        company_symbol: str,
        company_name: str | None = None,
        sector: str | None = None,
        sector_key: str | None = None,
        industry: str | None = None,
        index_membership: list[str] | None = None,
    ) -> None:
        symbol = company_symbol.upper()
        self._conn.execute(
            """
            INSERT INTO historical_entities (
                company_symbol, company_name, sector, sector_key, industry,
                index_membership_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(company_symbol) DO UPDATE SET
                company_name = COALESCE(excluded.company_name, historical_entities.company_name),
                sector = COALESCE(excluded.sector, historical_entities.sector),
                sector_key = COALESCE(excluded.sector_key, historical_entities.sector_key),
                industry = COALESCE(excluded.industry, historical_entities.industry),
                index_membership_json = excluded.index_membership_json,
                updated_at = excluded.updated_at
            """,
            (
                symbol,
                company_name,
                sector,
                sector_key,
                industry,
                json.dumps(index_membership or []),
                _iso(datetime.now(timezone.utc)),
            ),
        )
        self._conn.commit()

    def get_entity(self, symbol: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM historical_entities WHERE company_symbol = ?",
            (symbol.upper(),),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["index_membership"] = json.loads(d.pop("index_membership_json") or "[]")
        return d

    # ----- knowledge objects -----

    def latest_version(
        self, object_type: HistoricalObjectType, subject_key: str, effective_date: str
    ) -> int:
        row = self._conn.execute(
            """
            SELECT MAX(version) AS v FROM historical_knowledge_objects
            WHERE object_type = ? AND subject_key = ? AND effective_date = ?
            """,
            (object_type.value, subject_key, effective_date),
        ).fetchone()
        return int(row["v"] or 0)

    def insert_historical_object(self, ko: HistoricalKnowledgeObject) -> None:
        self._conn.execute(
            """
            INSERT INTO historical_knowledge_objects (
                object_id, object_type, subject_key, company_symbol, effective_date,
                period_kind, version, previous_object_id, knowledge_json,
                entity_refs_json, provenance_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ko.object_id,
                ko.object_type.value,
                ko.subject_key,
                ko.company_symbol.upper() if ko.company_symbol else None,
                ko.effective_date,
                ko.period_kind.value,
                ko.version,
                ko.previous_object_id,
                json.dumps(ko.knowledge, default=str),
                json.dumps(ko.entity_refs.model_dump(mode="json"), default=str),
                json.dumps(ko.provenance.model_dump(mode="json"), default=str),
                _iso(ko.created_at),
            ),
        )
        self._mirror(ko)
        self._conn.commit()

    def _mirror(self, ko: HistoricalKnowledgeObject) -> None:
        prov = json.dumps(ko.provenance.model_dump(mode="json"), default=str)
        knowledge = json.dumps(ko.knowledge, default=str)
        created = _iso(ko.created_at)
        symbol = ko.company_symbol.upper() if ko.company_symbol else ""
        if ko.object_type == HistoricalObjectType.PRICE_HISTORY:
            self._conn.execute(
                """
                INSERT INTO historical_prices (
                    object_id, company_symbol, effective_date, period_kind, version,
                    open, high, low, close, volume, knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.period_kind.value,
                    ko.version,
                    ko.knowledge.get("open"),
                    ko.knowledge.get("high"),
                    ko.knowledge.get("low"),
                    ko.knowledge.get("close"),
                    ko.knowledge.get("volume"),
                    knowledge,
                    prov,
                    created,
                ),
            )
        elif ko.object_type == HistoricalObjectType.FINANCIAL_STATEMENT:
            self._conn.execute(
                """
                INSERT INTO historical_financials (
                    object_id, company_symbol, effective_date, period_kind, statement_type,
                    version, revenue, net_income, knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.period_kind.value,
                    ko.knowledge.get("statement_type") or "income",
                    ko.version,
                    ko.knowledge.get("revenue"),
                    ko.knowledge.get("net_income"),
                    knowledge,
                    prov,
                    created,
                ),
            )
        elif ko.object_type == HistoricalObjectType.BALANCE_SHEET:
            self._conn.execute(
                """
                INSERT INTO historical_balance_sheets (
                    object_id, company_symbol, effective_date, period_kind, version,
                    knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ko.object_id, symbol, ko.effective_date, ko.period_kind.value, ko.version, knowledge, prov, created),
            )
        elif ko.object_type == HistoricalObjectType.CASH_FLOW:
            self._conn.execute(
                """
                INSERT INTO historical_cashflows (
                    object_id, company_symbol, effective_date, period_kind, version,
                    knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ko.object_id, symbol, ko.effective_date, ko.period_kind.value, ko.version, knowledge, prov, created),
            )
        elif ko.object_type == HistoricalObjectType.DIVIDEND_HISTORY:
            self._conn.execute(
                """
                INSERT INTO historical_dividends (
                    object_id, company_symbol, effective_date, version, amount,
                    knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.version,
                    ko.knowledge.get("amount"),
                    knowledge,
                    prov,
                    created,
                ),
            )
        elif ko.object_type == HistoricalObjectType.CORPORATE_ACTION:
            self._conn.execute(
                """
                INSERT INTO historical_actions (
                    object_id, company_symbol, effective_date, action_type, version,
                    knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.knowledge.get("action_type") or "unknown",
                    ko.version,
                    knowledge,
                    prov,
                    created,
                ),
            )
        elif ko.object_type == HistoricalObjectType.CORPORATE_EVENT:
            self._conn.execute(
                """
                INSERT INTO historical_events (
                    object_id, company_symbol, effective_date, event_type, version,
                    knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.knowledge.get("event_type") or "announcement",
                    ko.version,
                    knowledge,
                    prov,
                    created,
                ),
            )
            if ko.knowledge.get("report_type"):
                self._conn.execute(
                    """
                    INSERT INTO historical_reports (
                        object_id, company_symbol, effective_date, report_type, version, title,
                        knowledge_json, provenance_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ko.object_id,
                        symbol,
                        ko.effective_date,
                        ko.knowledge.get("report_type"),
                        ko.version,
                        ko.knowledge.get("title"),
                        knowledge,
                        prov,
                        created,
                    ),
                )
        elif ko.object_type == HistoricalObjectType.COMPANY_PROFILE:
            self._conn.execute(
                """
                INSERT INTO historical_company_profiles (
                    object_id, company_symbol, effective_date, version,
                    knowledge_json, entity_refs_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.version,
                    knowledge,
                    json.dumps(ko.entity_refs.model_dump(mode="json"), default=str),
                    prov,
                    created,
                ),
            )
        elif ko.object_type == HistoricalObjectType.NEWS_EVENT:
            self._conn.execute(
                """
                INSERT INTO historical_news (
                    object_id, company_symbol, effective_date, version, title,
                    knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.version,
                    ko.knowledge.get("title"),
                    knowledge,
                    prov,
                    created,
                ),
            )
        elif ko.knowledge.get("report_type"):
            self._conn.execute(
                """
                INSERT INTO historical_reports (
                    object_id, company_symbol, effective_date, report_type, version, title,
                    knowledge_json, provenance_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ko.object_id,
                    symbol,
                    ko.effective_date,
                    ko.knowledge.get("report_type"),
                    ko.version,
                    ko.knowledge.get("title"),
                    knowledge,
                    prov,
                    created,
                ),
            )

    # ----- retrieval (no external calls) -----

    def list_prices(
        self, symbol: str, *, period_kind: str = "daily", limit: int = 5000
    ) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_prices
            WHERE company_symbol = ? AND period_kind = ?
            ORDER BY effective_date ASC, version DESC
            LIMIT ?
            """,
            (symbol.upper(), period_kind, limit),
        ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def list_financials(
        self, symbol: str, *, period_kind: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        if period_kind:
            rows = self._conn.execute(
                """
                SELECT * FROM historical_financials
                WHERE company_symbol = ? AND period_kind = ?
                ORDER BY effective_date ASC, version DESC
                LIMIT ?
                """,
                (symbol.upper(), period_kind, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM historical_financials
                WHERE company_symbol = ?
                ORDER BY effective_date ASC, version DESC
                LIMIT ?
                """,
                (symbol.upper(), limit),
            ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def list_events(self, symbol: str, limit: int = 200) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_events
            WHERE company_symbol = ?
            ORDER BY effective_date DESC, version DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def list_actions(self, symbol: str, limit: int = 200) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_actions
            WHERE company_symbol = ?
            ORDER BY effective_date DESC, version DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def list_dividends(self, symbol: str, limit: int = 200) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_dividends
            WHERE company_symbol = ?
            ORDER BY effective_date ASC, version DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def list_reports(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_reports
            WHERE company_symbol = ?
            ORDER BY effective_date DESC, version DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def list_profiles(self, symbol: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_company_profiles
            WHERE company_symbol = ?
            ORDER BY effective_date DESC, version DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def list_news(self, symbol: str, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_news
            WHERE company_symbol = ?
            ORDER BY effective_date DESC, version DESC
            LIMIT ?
            """,
            (symbol.upper(), limit),
        ).fetchall()
        return [self._row_knowledge(r) for r in rows]

    def revenue_series(self, symbol: str, *, from_period: str, to_period: str) -> list[dict[str, Any]]:
        """FY/period revenue series for IE — store only, no external providers."""
        rows = self.list_financials(symbol, limit=500)
        out = []
        seen: set[str] = set()
        for row in rows:
            period = row.get("effective_date") or ""
            if period < from_period or period > to_period:
                continue
            if period in seen:
                continue
            seen.add(period)
            out.append(
                {
                    "period": period,
                    "period_kind": row.get("period_kind"),
                    "revenue": row.get("revenue") or (row.get("knowledge") or {}).get("revenue"),
                    "net_income": row.get("net_income") or (row.get("knowledge") or {}).get("net_income"),
                    "pe": (row.get("knowledge") or {}).get("pe"),
                    "valuation": (row.get("knowledge") or {}).get("valuation"),
                    "version": row.get("version"),
                    "provenance": row.get("provenance"),
                }
            )
        return out

    def coverage_report(self, symbol: str, settings: Any | None = None) -> dict[str, Any]:
        symbol = symbol.upper()
        counts = {
            "daily_ohlcv": self._count("historical_prices", symbol, "period_kind = 'daily'"),
            "quarterly_financials": self._count(
                "historical_financials", symbol, "period_kind = 'quarterly'"
            ),
            "annual_financials": self._count(
                "historical_financials", symbol, "period_kind = 'annual'"
            ),
            "balance_sheets": self._count("historical_balance_sheets", symbol),
            "cash_flows": self._count("historical_cashflows", symbol),
            "dividends": self._count("historical_dividends", symbol),
            "corporate_actions": self._count("historical_actions", symbol),
            "corporate_events": self._count("historical_events", symbol),
            "company_ir_reports": self._count("historical_reports", symbol),
            "company_profile_history": self._count("historical_company_profiles", symbol),
            "news_metadata": self._count("historical_news", symbol),
        }
        categories = {}
        for t in COVERAGE_TARGETS:
            categories[t.category] = {
                "description": t.description,
                **score_completeness(counts.get(t.category, 0), expected_for(t.category, settings)),
            }
        return {"company_symbol": symbol, "categories": categories, "counts": counts}

    def _count(self, table: str, symbol: str, extra: str | None = None) -> int:
        where = "company_symbol = ?"
        if extra:
            where += f" AND {extra}"
        # distinct effective dates for completeness
        sql = f"SELECT COUNT(DISTINCT effective_date) AS c FROM {table} WHERE {where}"
        return int(self._conn.execute(sql, (symbol.upper(),)).fetchone()["c"])

    def count_objects(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) AS c FROM historical_knowledge_objects").fetchone()["c"]
        )

    def list_entity_symbols(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT company_symbol FROM historical_entities ORDER BY company_symbol"
        ).fetchall()
        return [str(r["company_symbol"]) for r in rows]

    # ----- Sprint 8.2 timelines -----

    def replace_timeline(self, scope: str, subject_key: str, events: list[Any]) -> None:
        """Replace timeline nodes for a subject (narrative rebuild; HKO remain immutable)."""
        self._conn.execute(
            "DELETE FROM historical_timelines WHERE scope = ? AND subject_key = ?",
            (scope, subject_key),
        )
        # Narrative edges for this subject are rebuilt with the timeline
        self._conn.execute(
            "DELETE FROM historical_timeline_links WHERE subject_key = ?",
            (subject_key,),
        )
        now = _iso(datetime.now(timezone.utc))
        for ev in events:
            self._conn.execute(
                """
                INSERT INTO historical_timelines (
                    event_id, scope, subject_key, year, date, title, description,
                    importance, event_type, source, links_json, evidence_refs_json,
                    version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev.event_id,
                    ev.scope.value if hasattr(ev.scope, "value") else ev.scope,
                    ev.subject_key,
                    ev.year,
                    ev.date,
                    ev.title,
                    ev.description,
                    ev.importance.value if hasattr(ev.importance, "value") else ev.importance,
                    ev.event_type,
                    ev.source.value if hasattr(ev.source, "value") else ev.source,
                    json.dumps([lnk.model_dump() if hasattr(lnk, "model_dump") else lnk for lnk in (ev.links or [])]),
                    json.dumps(list(ev.evidence_refs or [])),
                    ev.version,
                    now,
                ),
            )
        self._conn.commit()

    def get_timeline(self, scope: str, subject_key: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT * FROM historical_timelines
            WHERE scope = ? AND subject_key = ?
            ORDER BY year ASC, title ASC
            """,
            (scope, subject_key),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["links"] = json.loads(d.pop("links_json") or "[]")
            d["evidence_refs"] = json.loads(d.pop("evidence_refs_json") or "[]")
            out.append(d)
        return out

    def insert_timeline_link(
        self,
        *,
        from_key: str,
        to_key: str,
        relation: str,
        note: str | None = None,
        subject_key: str | None = None,
    ) -> None:
        from uuid import uuid4

        self._conn.execute(
            """
            INSERT INTO historical_timeline_links (
                link_id, from_key, to_key, relation, note, subject_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                from_key,
                to_key,
                relation,
                note,
                subject_key,
                _iso(datetime.now(timezone.utc)),
            ),
        )
        self._conn.commit()

    def list_timeline_links(self, subject_key: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        if subject_key:
            rows = self._conn.execute(
                """
                SELECT * FROM historical_timeline_links
                WHERE subject_key = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (subject_key, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM historical_timeline_links ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def timeline_completeness(self, symbol: str) -> dict[str, Any]:
        symbol = symbol.upper()
        events = self.get_timeline("company", symbol)
        years = sorted({int(e["year"]) for e in events}) if events else []
        # Expected narrative anchors for institutional completeness
        expected_anchors = {"IPO", "Global Financial Crisis", "COVID", "AI Transformation", "Leadership Change", "Margin Compression"}
        titles = {e["title"] for e in events}
        present_anchors = expected_anchors.intersection(titles)
        # Years coverage from financials
        fins = self.list_financials(symbol, period_kind="annual", limit=50)
        fin_years = sorted(
            {
                int(str(f["effective_date"])[2:6])
                for f in fins
                if str(f.get("effective_date") or "").startswith("FY")
                and len(str(f.get("effective_date"))) >= 6
            }
        )
        missing_periods = []
        if fin_years:
            for y in range(fin_years[0], fin_years[-1] + 1):
                if y not in fin_years:
                    missing_periods.append(f"FY{y}")
        ratio = (len(present_anchors) / max(1, len(expected_anchors))) if events else 0.0
        # Non-seed companies: completeness from having chronological events
        if symbol not in {"INFY", "TCS", "HDFCBANK", "RELIANCE"}:
            ratio = min(1.0, len(events) / 6.0) if events else 0.0
        status = (
            "Complete"
            if ratio >= 0.8
            else "Partial"
            if ratio >= 0.4
            else "Sparse"
            if events
            else "Missing"
        )
        return {
            "company_symbol": symbol,
            "timeline_events": len(events),
            "years_span": {"min": years[0], "max": years[-1]} if years else None,
            "years_ingested": years,
            "anchor_completeness": round(ratio, 4),
            "status": status,
            "financial_years": fin_years,
            "missing_periods": missing_periods,
        }

    def count_timeline_events(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM historical_timelines").fetchone()["c"])

    # ----- Sprint 8.3 Historical Relationship Intelligence -----

    def clear_relationship_graph(self) -> None:
        """Ops rebuild helper — clears published graph tables (not HKO facts)."""
        for table in (
            "relationship_evidence",
            "relationship_versions",
            "company_relationships",
            "sector_relationships",
            "macro_relationships",
            "market_relationships",
            "historical_relationships",
        ):
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.commit()

    def upsert_relationship(self, rel: Any) -> None:
        """Insert/replace a validated relationship + evidence + version snapshot."""
        from uuid import uuid4

        now = _iso(datetime.now(timezone.utc))
        self._conn.execute(
            """
            INSERT INTO historical_relationships (
                relationship_id, domain, source_key, source_label, target_key, target_label,
                relationship_type, direction, confidence, occurrences, average_delay,
                first_observed, last_confirmed, chain_json, version, published, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(relationship_id) DO UPDATE SET
                confidence=excluded.confidence,
                occurrences=excluded.occurrences,
                average_delay=excluded.average_delay,
                last_confirmed=excluded.last_confirmed,
                chain_json=excluded.chain_json,
                version=excluded.version,
                published=excluded.published,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                rel.relationship_id,
                rel.domain.value if hasattr(rel.domain, "value") else rel.domain,
                rel.source_key,
                rel.source_label,
                rel.target_key,
                rel.target_label,
                rel.relationship_type.value
                if hasattr(rel.relationship_type, "value")
                else rel.relationship_type,
                rel.direction.value if hasattr(rel.direction, "value") else rel.direction,
                rel.confidence.value if hasattr(rel.confidence, "value") else rel.confidence,
                rel.occurrences,
                rel.average_delay,
                rel.first_observed,
                rel.last_confirmed,
                json.dumps(list(rel.chain or [])),
                rel.version,
                1 if rel.published else 0,
                rel.status,
                _iso(rel.created_at) if getattr(rel, "created_at", None) else now,
                now,
            ),
        )
        domain = rel.domain.value if hasattr(rel.domain, "value") else rel.domain
        known_symbols = {"INFY", "TCS", "HDFCBANK", "RELIANCE"}
        known_sectors = {
            "information_technology",
            "financials",
            "energy",
            "autos",
            "housing",
            "capital_goods",
            "railways",
            "infrastructure",
            "banks",
            "paints",
            "airlines",
            "omcs",
            "upstream_energy",
            "real_estate",
            "consumption",
            "private_banks",
        }

        keys = {rel.source_key, rel.target_key, *(rel.chain or [])}
        for key in keys:
            if not key:
                continue
            ku = str(key).upper()
            kl = str(key).lower().replace(" ", "_")
            if ku in known_symbols:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO company_relationships (relationship_id, company_symbol)
                    VALUES (?, ?)
                    """,
                    (rel.relationship_id, ku),
                )
            if kl in known_sectors:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO sector_relationships (relationship_id, sector_key)
                    VALUES (?, ?)
                    """,
                    (rel.relationship_id, kl),
                )

        if domain == "macro":
            macro_keys = {str(rel.source_key).lower().replace(" ", "_")}
            if ":" in str(rel.source_key):
                macro_keys.add(str(rel.source_key).split(":")[0].lower())
            # Alias common event names for retrieval
            label = str(rel.source_label or "").lower()
            if "rbi" in label or "rate cut" in label:
                macro_keys.update({"rbi", "rbi_rate_cut", "rate_cut"})
            if "crude" in label or "oil" in label:
                macro_keys.update({"crude", "higher_crude_oil", "oil"})
            for mk in macro_keys:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO macro_relationships (relationship_id, macro_event_key)
                    VALUES (?, ?)
                    """,
                    (rel.relationship_id, mk),
                )
        elif domain == "market":
            self._conn.execute(
                """
                INSERT OR IGNORE INTO market_relationships (relationship_id, market_key)
                VALUES (?, ?)
                """,
                (rel.relationship_id, "nifty"),
            )

        # Evidence rows
        self._conn.execute(
            "DELETE FROM relationship_evidence WHERE relationship_id = ?",
            (rel.relationship_id,),
        )
        for ev in rel.evidence or []:
            self._conn.execute(
                """
                INSERT INTO relationship_evidence (
                    evidence_id, relationship_id, kind, summary, period,
                    source_refs_json, weight, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev.evidence_id,
                    rel.relationship_id,
                    ev.kind,
                    ev.summary,
                    ev.period,
                    json.dumps(list(ev.source_refs or [])),
                    float(ev.weight),
                    now,
                ),
            )

        # Version snapshot (append-only)
        snap = rel.model_dump(mode="json") if hasattr(rel, "model_dump") else dict(rel)
        self._conn.execute(
            """
            INSERT INTO relationship_versions (
                version_id, relationship_id, version, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid4()), rel.relationship_id, rel.version, json.dumps(snap, default=str), now),
        )
        self._conn.commit()

    def list_relationships(
        self,
        *,
        domain: str | None = None,
        company_symbol: str | None = None,
        sector_key: str | None = None,
        macro_event: str | None = None,
        market: bool = False,
        published_only: bool = True,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        ids: list[str] | None = None
        if company_symbol:
            rows = self._conn.execute(
                "SELECT relationship_id FROM company_relationships WHERE company_symbol = ?",
                (company_symbol.upper(),),
            ).fetchall()
            ids = [r["relationship_id"] for r in rows]
        elif sector_key:
            sk = sector_key.lower().replace(" ", "_")
            rows = self._conn.execute(
                "SELECT relationship_id FROM sector_relationships WHERE sector_key = ? OR sector_key LIKE ?",
                (sk, f"%{sk}%"),
            ).fetchall()
            ids = [r["relationship_id"] for r in rows]
        elif macro_event:
            key = macro_event.lower().replace(" ", "_")
            rows = self._conn.execute(
                """
                SELECT relationship_id FROM macro_relationships
                WHERE macro_event_key = ? OR macro_event_key LIKE ?
                """,
                (key, f"%{key}%"),
            ).fetchall()
            # Also match historical_relationships source/target labels
            rows2 = self._conn.execute(
                """
                SELECT relationship_id FROM historical_relationships
                WHERE domain = 'macro'
                  AND (lower(source_key) LIKE ? OR lower(source_label) LIKE ?
                       OR lower(target_key) LIKE ? OR lower(target_label) LIKE ?)
                """,
                (f"%{key}%", f"%{key}%", f"%{key}%", f"%{key}%"),
            ).fetchall()
            ids = list({r["relationship_id"] for r in rows} | {r["relationship_id"] for r in rows2})
        elif market:
            rows = self._conn.execute(
                "SELECT relationship_id FROM market_relationships WHERE market_key = 'nifty'"
            ).fetchall()
            ids = [r["relationship_id"] for r in rows]

        sql = "SELECT * FROM historical_relationships WHERE 1=1"
        params: list[Any] = []
        if domain:
            sql += " AND domain = ?"
            params.append(domain)
        if published_only:
            sql += " AND published = 1"
        if ids is not None:
            if not ids:
                return []
            placeholders = ",".join("?" for _ in ids)
            sql += f" AND relationship_id IN ({placeholders})"
            params.extend(ids)
        sql += " ORDER BY confidence DESC, occurrences DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["chain"] = json.loads(d.pop("chain_json") or "[]")
            d["published"] = bool(d.get("published"))
            d["evidence"] = self.list_relationship_evidence(d["relationship_id"])
            out.append(d)
        return out

    def list_relationship_evidence(self, relationship_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM relationship_evidence WHERE relationship_id = ? ORDER BY weight DESC",
            (relationship_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["source_refs"] = json.loads(d.pop("source_refs_json") or "[]")
            out.append(d)
        return out

    def count_relationships(self, *, published_only: bool = True) -> int:
        if published_only:
            return int(
                self._conn.execute(
                    "SELECT COUNT(*) AS c FROM historical_relationships WHERE published = 1"
                ).fetchone()["c"]
            )
        return int(self._conn.execute("SELECT COUNT(*) AS c FROM historical_relationships").fetchone()["c"])

    def relationship_dashboard(self) -> dict[str, Any]:
        total = self.count_relationships(published_only=False)
        published = self.count_relationships(published_only=True)
        conf = self._conn.execute(
            """
            SELECT confidence, COUNT(*) AS c FROM historical_relationships
            WHERE published = 1 GROUP BY confidence
            """
        ).fetchall()
        domains = self._conn.execute(
            """
            SELECT domain, COUNT(*) AS c FROM historical_relationships
            WHERE published = 1 GROUP BY domain
            """
        ).fetchall()
        stale = self._conn.execute(
            "SELECT COUNT(*) AS c FROM historical_relationships WHERE status = 'stale'"
        ).fetchone()["c"]
        # Evidence strength: avg evidence rows per published relationship
        ev_count = self._conn.execute("SELECT COUNT(*) AS c FROM relationship_evidence").fetchone()["c"]
        strength = round(float(ev_count) / max(1, published), 2)
        recent = self._conn.execute(
            """
            SELECT relationship_id, source_label, target_label, relationship_type, confidence, created_at
            FROM historical_relationships
            WHERE published = 1
            ORDER BY created_at DESC LIMIT 15
            """
        ).fetchall()
        company_cov = self._conn.execute(
            """
            SELECT company_symbol, COUNT(*) AS c FROM company_relationships
            GROUP BY company_symbol ORDER BY c DESC
            """
        ).fetchall()
        return {
            "relationship_count": published,
            "draft_count": total - published,
            "evidence_strength": strength,
            "evidence_rows": ev_count,
            "confidence_distribution": {r["confidence"]: r["c"] for r in conf},
            "domain_distribution": {r["domain"]: r["c"] for r in domains},
            "newly_discovered": [dict(r) for r in recent],
            "stale_relationships": int(stale),
            "coverage_by_company": {r["company_symbol"]: r["c"] for r in company_cov},
        }

    # ----- Sprint 8.4 Historical Analogue Intelligence -----

    def insert_analogue_search(
        self,
        *,
        search_id: str,
        scope: str,
        entity_key: str,
        question: str | None,
        situation: str | None,
        as_of_period: str | None,
        features: dict[str, Any],
        top_k: int,
        result_count: int,
        avg_similarity: float | None,
        latency_ms: float,
        results: list[dict[str, Any]],
    ) -> None:
        now = _iso(datetime.now(timezone.utc))
        self._conn.execute(
            """
            INSERT INTO analogue_searches (
                search_id, scope, entity_key, question, situation, as_of_period,
                features_json, top_k, result_count, avg_similarity, latency_ms, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                search_id,
                scope,
                entity_key,
                question,
                situation,
                as_of_period,
                json.dumps(features or {}),
                top_k,
                result_count,
                avg_similarity,
                latency_ms,
                now,
            ),
        )
        for i, row in enumerate(results, start=1):
            self._conn.execute(
                """
                INSERT INTO analogue_results (
                    result_id, search_id, analogue_id, rank, matched_period,
                    similarity_score, confidence, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{search_id}:{i}",
                    search_id,
                    row.get("analogue_id") or f"{search_id}-a{i}",
                    i,
                    row.get("matched_period"),
                    float(row.get("similarity_score") or 0),
                    row.get("confidence") or "Medium",
                    json.dumps(row, default=str),
                    now,
                ),
            )
        self._conn.commit()

    def analogue_dashboard(self) -> dict[str, Any]:
        total = int(self._conn.execute("SELECT COUNT(*) AS c FROM analogue_searches").fetchone()["c"])
        avg_sim = self._conn.execute(
            "SELECT AVG(avg_similarity) AS a FROM analogue_searches WHERE avg_similarity IS NOT NULL"
        ).fetchone()["a"]
        avg_lat = self._conn.execute(
            "SELECT AVG(latency_ms) AS a FROM analogue_searches WHERE latency_ms IS NOT NULL"
        ).fetchone()["a"]
        by_company = self._conn.execute(
            """
            SELECT entity_key, COUNT(*) AS c FROM analogue_searches
            WHERE scope = 'company' GROUP BY entity_key ORDER BY c DESC
            """
        ).fetchall()
        by_sector = self._conn.execute(
            """
            SELECT entity_key, COUNT(*) AS c FROM analogue_searches
            WHERE scope = 'sector' GROUP BY entity_key ORDER BY c DESC
            """
        ).fetchall()
        conf = self._conn.execute(
            """
            SELECT confidence, COUNT(*) AS c FROM analogue_results
            GROUP BY confidence
            """
        ).fetchall()
        recent = self._conn.execute(
            """
            SELECT search_id, scope, entity_key, question, avg_similarity, latency_ms, created_at
            FROM analogue_searches ORDER BY created_at DESC LIMIT 15
            """
        ).fetchall()
        return {
            "analogue_searches_executed": total,
            "average_similarity_score": round(float(avg_sim or 0), 2),
            "average_retrieval_latency_ms": round(float(avg_lat or 0), 2),
            "coverage_by_company": {r["entity_key"]: r["c"] for r in by_company},
            "coverage_by_sector": {r["entity_key"]: r["c"] for r in by_sector},
            "confidence_distribution": {r["confidence"]: r["c"] for r in conf},
            "recent_searches": [dict(r) for r in recent],
        }

    @staticmethod
    def _row_knowledge(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        if "knowledge_json" in d:
            d["knowledge"] = json.loads(d.pop("knowledge_json") or "{}")
        if "provenance_json" in d:
            d["provenance"] = json.loads(d.pop("provenance_json") or "{}")
        if "entity_refs_json" in d:
            d["entity_refs"] = json.loads(d.pop("entity_refs_json") or "{}")
        return d
