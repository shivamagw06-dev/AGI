"""IIE analysis pipeline — incremental company / sector / theme refresh."""

from __future__ import annotations

import time
from typing import Any

from app.iie.engines import IieAnalyser
from app.iie.evidence import VerifiedEvidenceReader
from app.iie.store import IieStore


class IiePipeline:
    def __init__(self, store: IieStore, reader: VerifiedEvidenceReader) -> None:
        self.store = store
        self.reader = reader
        self.analyser = IieAnalyser(store, reader)

    def analyse_company(self, key: str) -> dict[str, Any]:
        t0 = time.perf_counter()
        try:
            result = self.analyser.analyse_company(key)
            self.store.metrics.last_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            self.store.audit_event("analyse_company", object_kind="company", object_id=result.get("company_id") or key)
            return result
        except Exception as exc:
            self.store.metrics.failures += 1
            self.store.audit_event("analyse_company_failed", object_kind="company", object_id=key, detail=str(exc)[:200])
            raise

    def analyse_from_eve_companies(self, *, limit: int = 20) -> dict[str, Any]:
        """Discover company_ids from EVE evidence and analyse incrementally."""
        if not self.reader.eve:
            return {"analysed": 0, "companies": []}
        try:
            listed = self.reader.eve.list_evidence(limit=500)
            rows = listed.get("evidence") if isinstance(listed, dict) else []
        except Exception:
            rows = []
        company_ids: list[str] = []
        for ev in rows or []:
            cid = (ev.get("company_id") if isinstance(ev, dict) else None) or ""
            if cid and cid not in company_ids:
                company_ids.append(cid)
            if len(company_ids) >= limit:
                break
        done = []
        for cid in company_ids:
            try:
                done.append(self.analyse_company(cid)["company_id"])
            except Exception:
                continue
        return {"analysed": len(done), "companies": done}

    def seed_sectors_and_themes(self) -> dict[str, Any]:
        from app.iie.config import SECTOR_CATALOG, THEME_CATALOG
        from app.iie.models import Explainability, SectorIntelligence, ThemeIntelligence

        for row in SECTOR_CATALOG:
            if row["sector_id"] in self.store.sectors:
                continue
            self.store.put_sector(
                SectorIntelligence(
                    sector_id=row["sector_id"],
                    name=row["label"],
                    industry_structure=f"{row['label']} — structure populated as verified company evidence arrives.",
                    explainability=Explainability(
                        reasoning_summary="Catalog seed; not a hallucinated assessment.",
                        confidence=0.2,
                        responsible_engine="iie.sector",
                    ),
                    confidence=0.2,
                )
            )
        for row in THEME_CATALOG:
            if row["theme_id"] in self.store.themes:
                continue
            self.store.put_theme(
                ThemeIntelligence(
                    theme_id=row["theme_id"],
                    name=row["label"],
                    description="Theme shell; membership assigned from verified evidence keywords.",
                    confidence=0.2,
                )
            )
        return {"sectors": len(self.store.sectors), "themes": len(self.store.themes)}
