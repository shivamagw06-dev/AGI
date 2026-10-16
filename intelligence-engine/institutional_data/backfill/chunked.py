"""Chunked resumable historical backfill — company → time chunk → checkpoint."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from institutional_data.persistence.resume import ResumeManager

CHUNK_YEARS_DEFAULT = int(os.getenv("KF_HD_CHUNK_YEARS") or "5")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChunkedBackfillEngine:
    """Resumable chunked enrichment used by HD backfill without redesigning the queue."""

    def __init__(self, *, chunk_years: int | None = None) -> None:
        self.chunk_years = max(1, int(chunk_years or CHUNK_YEARS_DEFAULT))
        self.resume = ResumeManager()

    def plan_chunks(self, *, target_years: float = 15.0) -> list[tuple[int, int]]:
        """Return (start_year, end_year) chunks covering target history ending this year."""
        end = datetime.now(timezone.utc).year
        start = end - int(target_years) + 1
        chunks = []
        y = start
        while y <= end:
            y1 = min(end, y + self.chunk_years - 1)
            chunks.append((y, y1))
            y = y1 + 1
        return chunks

    def next_chunk_for(self, company: str, *, target_years: float = 15.0) -> dict[str, Any] | None:
        state = self.resume.company_chunk_state(company)
        done = set(state.get("completed_chunks") or [])
        for a, b in self.plan_chunks(target_years=target_years):
            key = f"{a}-{b}"
            if key not in done:
                return {"start_year": a, "end_year": b, "key": key, "partial": True}
        return None

    def enrich_company_chunked(self, company: str, *, maintenance: bool = False) -> dict[str, Any]:
        """Run connector suite for one company, checkpointing by time chunk."""
        from knowledge_factory.historical_depth.completion import evaluate_completion, record_attempt, TARGET_YEARS
        from institutional_data.connectors.registry import get_connector

        e = company.upper()
        target = float(os.getenv("KF_HD_TARGET_YEARS") or TARGET_YEARS)
        chunk = None if maintenance else self.next_chunk_for(e, target_years=target)

        # Always collect OHLCV via existing HD path for the company (Yahoo handles full span;
        # chunk checkpoint tracks logical progress for resume UX / partial completion).
        from knowledge_factory.historical_depth.collectors import collect_entity_history

        live_on = str(os.getenv("KF_HD_LIVE_COLLECTORS", "false")).lower() in {"1", "true", "yes", "on"}
        row = collect_entity_history(e, prefer_live=live_on and not maintenance)

        # Financial statements (no fixtures in production)
        fin = get_connector("financial_statements").run(entity=e)
        row["financials"] = fin.to_dict()

        # Shareholding
        sh = get_connector("shareholding").run(entity=e)
        if sh.ok:
            record_attempt(e, "shareholding", status="complete", detail=f"n={len(sh.normalized or sh.records)}")
        else:
            record_attempt(e, "shareholding", status="n_a", detail=sh.error or "unavailable")
        row["shareholding"] = sh.to_dict()

        # IR discovery
        ir = get_connector("company_ir").run(entity=e, download_files=live_on, max_downloads=4)
        docs = ir.normalized or ir.records
        types = {str(d.get("doc_type")) for d in docs}
        record_attempt(e, "annual_reports", status="complete" if "annual_report" in types else ("empty" if ir.ok else "n_a"))
        record_attempt(
            e,
            "investor_presentations",
            status="complete" if "investor_presentation" in types else ("empty" if ir.ok else "n_a"),
        )
        record_attempt(
            e,
            "earnings_transcripts",
            status="complete" if "earnings_transcript" in types else "n_a",
        )
        record_attempt(e, "esg_reports", status="complete" if "esg_report" in types else "n_a")
        row["ir"] = ir.to_dict()

        # Mark chunk complete
        if chunk:
            self.resume.save_company_chunk(
                e,
                chunk_start_year=chunk["start_year"],
                chunk_end_year=chunk["end_year"],
                completed_chunks=[chunk["key"]],
                next_chunk=None,
                partial=self.next_chunk_for(e, target_years=target) is not None,
                meta={"connectors": ["financials", "shareholding", "ir"]},
            )

        # Knowledge extract + embed (existing CGL)
        try:
            from continuous_gather_learn.embeddings import embed_knowledge_extract
            from continuous_gather_learn.knowledge_extract import extract_from_hd_series

            extract = extract_from_hd_series(e)
            embedding = embed_knowledge_extract(e, extract)
            row["extract_ok"] = bool(extract)
            row["embedding_ok"] = bool(embedding and embedding.get("vector"))
        except Exception as exc:  # noqa: BLE001
            row["extract_error"] = str(exc)[:160]

        evaluation = evaluate_completion(e)
        row.update(
            {
                "entity": e,
                "chunk": chunk,
                "history_years": evaluation.get("history_years"),
                "complete": evaluation.get("complete"),
                "coverage_pct": evaluation.get("coverage_pct"),
                "evaluation": evaluation,
                "maintenance": maintenance,
                "resumable": True,
            }
        )
        return row

    def run_parallel(self, companies: list[str], *, workers: int = 2, maintenance: bool = False) -> list[dict[str, Any]]:
        workers = max(1, min(workers, len(companies) or 1))
        rows: list[dict[str, Any]] = []
        if workers == 1:
            for c in companies:
                rows.append(self.enrich_company_chunked(c, maintenance=maintenance))
            return rows
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(self.enrich_company_chunked, c, maintenance=maintenance): c for c in companies}
            for fut in as_completed(futs):
                try:
                    rows.append(fut.result())
                except Exception as exc:  # noqa: BLE001
                    rows.append({"entity": futs[fut], "status": "error", "error": str(exc)[:200]})
        return rows
