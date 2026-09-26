from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.models import ResearchRun

log = get_logger(__name__)

DISK_DIR = Path(__file__).resolve().parents[2] / "data" / "runs"


class ResearchStore:
    """
    Memory layer: in-memory + disk always.
    Optional Supabase/Postgres when DATABASE_URL or SUPABASE credentials exist.
    """

    def __init__(self):
        self._memory: dict[str, ResearchRun] = {}
        DISK_DIR.mkdir(parents=True, exist_ok=True)

    async def save_run(self, run: ResearchRun) -> None:
        self._memory[run.run_id] = run
        path = DISK_DIR / f"{run.run_id}.json"
        path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        await self._save_supabase(run)

    async def get_run(self, run_id: str) -> ResearchRun | None:
        if run_id in self._memory:
            return self._memory[run_id]
        path = DISK_DIR / f"{run_id}.json"
        if path.exists():
            run = ResearchRun.model_validate_json(path.read_text(encoding="utf-8"))
            self._memory[run_id] = run
            return run
        return await self._load_supabase(run_id)

    async def latest_runs(self, desk: str | None = None, limit: int = 10) -> list[ResearchRun]:
        runs = list(self._memory.values())
        if not runs:
            for path in sorted(DISK_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
                try:
                    runs.append(ResearchRun.model_validate_json(path.read_text(encoding="utf-8")))
                except Exception:
                    continue
        if desk:
            runs = [r for r in runs if r.desk.value == desk]
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return runs[:limit]

    async def similar_runs(self, desk: str, limit: int = 3) -> list[dict[str, Any]]:
        # Phase 1: keyword/desk similarity via latest runs (embeddings in save_report_embedding)
        latest = await self.latest_runs(desk=desk, limit=limit)
        return [
            {
                "run_id": r.run_id,
                "desk": r.desk.value,
                "status": r.status.value,
                "thesis": (r.cio_thesis or "")[:240],
                "created_at": r.created_at.isoformat(),
            }
            for r in latest
        ]

    async def save_report_embedding(self, run: ResearchRun) -> None:
        """Store embedding metadata; actual vector write when DB configured."""
        if not run.report:
            return
        meta = {
            "run_id": run.run_id,
            "desk": run.desk.value,
            "title": run.report.title,
            "executive_summary": run.report.executive_summary[:2000],
        }
        path = DISK_DIR / f"{run.run_id}.embedding.json"
        path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        await self._save_embedding_supabase(meta)

    async def _save_supabase(self, run: ResearchRun) -> None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return
        try:
            import httpx

            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/intelligence_research_runs"
            payload = {
                "run_id": run.run_id,
                "desk": run.desk.value,
                "status": run.status.value,
                "payload": json.loads(run.model_dump_json()),
                "updated_at": run.updated_at.isoformat(),
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    url,
                    headers={
                        "apikey": settings.supabase_service_role_key,
                        "Authorization": f"Bearer {settings.supabase_service_role_key}",
                        "Content-Type": "application/json",
                        "Prefer": "resolution=merge-duplicates",
                    },
                    json=payload,
                )
        except Exception as exc:
            log.warning("supabase_run_save_failed", extra={"error": str(exc)})

    async def _load_supabase(self, run_id: str) -> ResearchRun | None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return None
        try:
            import httpx

            url = (
                f"{settings.supabase_url.rstrip('/')}/rest/v1/intelligence_research_runs"
                f"?run_id=eq.{run_id}&select=payload&limit=1"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "apikey": settings.supabase_service_role_key,
                        "Authorization": f"Bearer {settings.supabase_service_role_key}",
                        "Accept": "application/json",
                    },
                )
                if response.status_code >= 400:
                    return None
                rows = response.json()
                if not rows:
                    return None
                return ResearchRun.model_validate(rows[0]["payload"])
        except Exception as exc:
            log.warning("supabase_run_load_failed", extra={"error": str(exc)})
            return None

    async def _save_embedding_supabase(self, meta: dict[str, Any]) -> None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return
        try:
            import httpx

            url = f"{settings.supabase_url.rstrip('/')}/rest/v1/intelligence_report_embeddings"
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    url,
                    headers={
                        "apikey": settings.supabase_service_role_key,
                        "Authorization": f"Bearer {settings.supabase_service_role_key}",
                        "Content-Type": "application/json",
                        "Prefer": "resolution=merge-duplicates",
                    },
                    json={
                        "run_id": meta["run_id"],
                        "desk": meta["desk"],
                        "title": meta["title"],
                        "content": meta["executive_summary"],
                        # embedding vector filled later when OpenAI embeddings enabled
                    },
                )
        except Exception as exc:
            log.warning("supabase_embedding_save_failed", extra={"error": str(exc)})
