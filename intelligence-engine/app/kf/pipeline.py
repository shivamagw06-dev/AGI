"""KF1 learning / build pipeline.

Classification → extraction → mapping → merge → conflict/house-view impact
→ confidence/freshness update.

Uses KIP read APIs only — no KIP redesign.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

from app.aws.adapters import dump, soft
from app.kf.catalogs import COMPANIES, MACROS, SECTORS, THEMES
from app.kf.extract import extract_research_object
from app.kf.merge import bump_version, changed_fields, merge_list, merge_string
from app.kf.models import (
    CompanyKnowledgeObject,
    KnowledgeMeta,
    KnowledgeSearchHit,
    MacroKnowledgeObject,
    PredictionKnowledgeObject,
    SectorKnowledgeObject,
    ThemeKnowledgeObject,
)
from app.kf.scoring import confidence_score, count_filled, freshness_score, source_reliability
from app.kf.store import KfStore


class KfPipeline:
    def __init__(self, store: KfStore, *, kip: Any | None = None) -> None:
        self.store = store
        self.kip = kip
        self._seeded = False

    def ensure_seeded(self) -> dict[str, int]:
        if not self._seeded:
            self.seed()
        return {
            "companies": len(COMPANIES),
            "sectors": len(SECTORS),
            "themes": len(THEMES),
            "macros": len(MACROS),
        }

    def seed(self) -> dict[str, int]:
        for row in COMPANIES:
            self._seed_company(row)
        for row in SECTORS:
            self._seed_sector(row)
        for row in THEMES:
            self._seed_theme(row)
        for row in MACROS:
            self._seed_macro(row)
        self._seeded = True
        self._recompute_relationships()
        return self.ensure_seeded()

    def rebuild_from_kip(self) -> dict[str, int]:
        self.ensure_seeded()
        if not self.kip:
            return {"documents": 0, "extracts": 0, "companies_updated": 0}
        docs = 0
        extracts = 0
        updated: set[str] = set()
        # KIP store access is soft — no redesign
        store = getattr(self.kip, "store", None)
        documents = getattr(store, "documents", None) if store is not None else None
        if isinstance(documents, dict):
            for doc in documents.values():
                docs += 1
                if self.ingest_document(doc):
                    extracts += 1
                    d = dump(doc) or {}
                    inv = d.get("investment") if isinstance(d.get("investment"), dict) else {}
                    for t in inv.get("tickers") or []:
                        updated.add(str(t).upper())
        for t in sorted(updated):
            self.build_company(t)
        # Refresh sectors/themes with research overlays
        for sid in list(self.store.sectors.keys()):
            self.build_sector(sid)
        for tid in list(self.store.themes.keys()):
            self.build_theme(tid)
        self._recompute_relationships()
        return {"documents": docs, "extracts": extracts, "companies_updated": len(updated)}

    def ingest_document(self, doc: Any) -> bool:
        """Phase 7 learning pipeline entry for one document."""
        self.ensure_seeded()
        extract = extract_research_object(doc)
        if extract is None:
            return False
        self.store.upsert_extract(extract)
        # Map into company / sector / theme / macro objects
        for t in extract.companies:
            self._merge_extract_into_company(t, extract)
        for s in extract.sectors:
            sid = _sector_key(s)
            if sid and sid in self.store.sectors:
                self._merge_extract_into_sector(sid, extract)
        for theme in extract.themes:
            tid = _theme_key(theme)
            if tid and tid in self.store.themes:
                self._merge_extract_into_theme(tid, extract)
        for m in extract.macro_factors:
            mid = _macro_key(m)
            if mid and mid in self.store.macros:
                self._merge_extract_into_macro(mid, extract)
        return True

    def build_company(self, ticker: str) -> CompanyKnowledgeObject:
        self.ensure_seeded()
        t = ticker.upper()
        existing = self.store.companies.get(t)
        if existing is None:
            existing = self._seed_company({"ticker": t, "name": t, "sector": "", "industry": ""})

        kip_co = dump(soft(self.kip.get_company, t)) if self.kip else None
        dossier = dump(soft(self.kip.company_dossier, t)) if self.kip else None
        house = dump(soft(self.kip.house_view, t)) if self.kip else None
        preds = soft(self.kip.predictions, t, default=[]) if self.kip else []

        before = existing.model_dump(mode="json")
        data = existing.model_dump(mode="json")
        if isinstance(kip_co, dict):
            data["latest_thesis"] = merge_string(data.get("latest_thesis") or "", str(kip_co.get("latest_thesis") or ""))
            data["bull_case"] = merge_list(data.get("bull_case"), kip_co.get("bull_case"))
            data["bear_case"] = merge_list(data.get("bear_case"), kip_co.get("bear_case"))
            data["key_risks"] = merge_list(data.get("key_risks"), kip_co.get("risks"))
            data["key_catalysts"] = merge_list(data.get("key_catalysts"), kip_co.get("catalysts"))
            data["themes"] = merge_list(data.get("themes"), kip_co.get("themes"))
            data["competitors"] = merge_list(data.get("competitors"), kip_co.get("related_companies"))
            data["related_research"] = merge_list(data.get("related_research"), kip_co.get("documents"), limit=30)
            if kip_co.get("sectors"):
                data["sector"] = merge_string(data.get("sector") or "", str((kip_co.get("sectors") or [""])[0]))

        hist = []
        if isinstance(house, dict):
            cv = house.get("current_view") if isinstance(house.get("current_view"), dict) else {}
            if cv.get("thesis"):
                data["latest_thesis"] = merge_string(data.get("latest_thesis") or "", str(cv.get("thesis") or ""))
            data["bull_case"] = merge_list(data.get("bull_case"), cv.get("bull_case") if isinstance(cv, dict) else [])
            data["bear_case"] = merge_list(data.get("bear_case"), cv.get("bear_case") if isinstance(cv, dict) else [])
            hist = list(house.get("historical_views") or [])[:12]
            data["historical_house_views"] = hist
            if cv.get("valuation"):
                data["valuation"] = merge_string(data.get("valuation") or "", str(cv.get("valuation") or ""))

        pred_rows = []
        for p in preds or []:
            pd = dump(p) or {}
            if not pd:
                continue
            pred_rows.append(pd)
            self.store.upsert_prediction(
                PredictionKnowledgeObject(
                    meta=KnowledgeMeta(
                        kind="prediction",
                        key=str(pd.get("prediction_id") or f"pred_{t}"),
                        confidence=float(pd.get("confidence") or 0.5)
                        if float(pd.get("confidence") or 0.5) <= 1
                        else float(pd.get("confidence") or 50) / 100.0,
                        freshness=0.8,
                        source_reliability=0.9,
                        sources=["agi"],
                        document_ids=[str(pd.get("document_id") or "")] if pd.get("document_id") else [],
                    ),
                    prediction_id=str(pd.get("prediction_id") or f"pred_{t}"),
                    prediction=str(pd.get("thesis") or pd.get("target_price") or "")[:500],
                    date=str(pd.get("predicted_at") or "")[:10] or None,
                    company=t,
                    sector=str(pd.get("sector") or data.get("sector") or ""),
                    confidence=0.6,
                    expected_catalysts=[str(x) for x in (pd.get("catalysts") or [])][:8],
                    expected_timeline=f"{pd.get('horizon_days') or 90} days",
                    expected_outcome=str(pd.get("expected_return") or pd.get("target_price") or ""),
                    actual_outcome=str(pd.get("outcome_return") or ""),
                    lessons_learned=[str(pd.get("notes") or "")] if pd.get("notes") else [],
                    status=str(pd.get("status") or "open"),
                )
            )
        data["predictions"] = pred_rows[:20]

        if isinstance(dossier, dict) and dossier.get("house_view"):
            data["related_research"] = merge_list(
                data.get("related_research"),
                [str(x) for x in ((dossier.get("research_history") or {}).get("agi_reports") or [])[:10]],
            )

        filled = count_filled(
            [
                data.get("latest_thesis"),
                data.get("bull_case"),
                data.get("bear_case"),
                data.get("key_risks"),
                data.get("key_catalysts"),
                data.get("valuation"),
                data.get("business_description"),
            ]
        )
        meta = dict(data["meta"])
        diffs = changed_fields(before, data, ["latest_thesis", "bull_case", "bear_case", "key_risks", "key_catalysts", "valuation"])
        if diffs:
            meta = bump_version(meta, reason=f"merged KIP fields: {', '.join(diffs)}")
        meta["confidence"] = confidence_score(
            has_thesis=bool(data.get("latest_thesis")),
            n_sources=len(meta.get("sources") or []) + (1 if kip_co else 0),
            source_reliability=0.9 if kip_co or house else 0.65,
            n_structured_fields=filled,
            has_house_view=bool(house),
            has_predictions=bool(pred_rows),
        )
        meta["freshness"] = freshness_score(_parse_dt(meta.get("updated_at")))
        meta["document_ids"] = merge_list(meta.get("document_ids"), data.get("related_research"), limit=40)
        data["meta"] = meta
        obj = CompanyKnowledgeObject.model_validate(data)
        return self.store.upsert_company(obj)

    def build_sector(self, sector_id: str) -> SectorKnowledgeObject:
        self.ensure_seeded()
        sid = sector_id.lower()
        existing = self.store.sectors.get(sid)
        if existing is None:
            raise KeyError(f"Unknown sector '{sector_id}'")
        before = existing.model_dump(mode="json")
        data = existing.model_dump(mode="json")
        # Overlay from company objects + extracts
        theses: list[str] = []
        risks: list[str] = []
        catalysts: list[str] = []
        for t in [c.get("ticker") for c in data.get("major_companies") or [] if isinstance(c, dict)]:
            co = self.store.companies.get(str(t).upper())
            if not co:
                continue
            if co.latest_thesis:
                theses.append(co.latest_thesis)
            risks = merge_list(risks, co.key_risks)
            catalysts = merge_list(catalysts, co.key_catalysts)
        for ex in self.store.extracts.values():
            if any(_sector_key(s) == sid for s in ex.sectors) or sid.replace("_", " ") in (ex.title + ex.summary).lower():
                if ex.investment_thesis:
                    theses.append(ex.investment_thesis)
                risks = merge_list(risks, ex.risks)
                catalysts = merge_list(catalysts, ex.catalysts)
                if ex.investment_thesis and not data.get("current_agi_view"):
                    data["current_agi_view"] = "Research-informed"
        if theses:
            data["latest_thesis"] = theses[0][:1200]
            data["current_agi_view"] = data.get("current_agi_view") or "Under active research"
        data["risks"] = merge_list(data.get("risks"), risks)
        data["catalysts"] = merge_list(data.get("catalysts"), catalysts)
        meta = dict(data["meta"])
        diffs = changed_fields(before, data, ["latest_thesis", "risks", "catalysts", "current_agi_view"])
        if diffs:
            meta = bump_version(meta, reason=f"sector refresh: {', '.join(diffs)}")
        meta["confidence"] = confidence_score(
            has_thesis=bool(data.get("latest_thesis")),
            n_sources=2 + len(theses[:3]),
            source_reliability=0.85 if theses else 0.65,
            n_structured_fields=count_filled([data.get("growth_drivers"), data.get("major_companies"), data.get("risks")]),
            has_house_view=bool(data.get("current_agi_view")),
        )
        meta["freshness"] = freshness_score(_parse_dt(meta.get("updated_at")))
        data["meta"] = meta
        return self.store.upsert_sector(SectorKnowledgeObject.model_validate(data))

    def build_theme(self, theme_id: str) -> ThemeKnowledgeObject:
        self.ensure_seeded()
        tid = theme_id.lower()
        existing = self.store.themes.get(tid)
        if existing is None:
            raise KeyError(f"Unknown theme '{theme_id}'")
        data = existing.model_dump(mode="json")
        views = []
        for ex in self.store.extracts.values():
            if any(_theme_key(t) == tid for t in ex.themes) or tid.replace("_", " ") in (ex.title + " " + ex.summary).lower():
                views.append(ex.investment_thesis or ex.summary)
                data["risks"] = merge_list(data.get("risks"), ex.risks)
                data["catalysts"] = merge_list(data.get("catalysts"), ex.catalysts)
        if views:
            data["current_agi_view"] = "Active theme coverage"
            data["historical_evolution"] = merge_list(data.get("historical_evolution"), [v[:200] for v in views[:5]])
            if not data.get("investment_thesis"):
                data["investment_thesis"] = views[0][:800]
        meta = dict(data["meta"])
        meta = bump_version(meta, reason="theme refresh from research extracts") if views else meta
        meta["confidence"] = confidence_score(
            has_thesis=bool(data.get("investment_thesis")),
            n_sources=1 + len(views[:4]),
            source_reliability=0.8 if views else 0.65,
            n_structured_fields=count_filled([data.get("companies"), data.get("risks"), data.get("catalysts")]),
        )
        meta["freshness"] = freshness_score(_parse_dt(meta.get("updated_at")))
        data["meta"] = meta
        return self.store.upsert_theme(ThemeKnowledgeObject.model_validate(data))

    def build_macro(self, macro_id: str) -> MacroKnowledgeObject:
        self.ensure_seeded()
        mid = macro_id.lower()
        existing = self.store.macros.get(mid)
        if existing is None:
            raise KeyError(f"Unknown macro '{macro_id}'")
        data = existing.model_dump(mode="json")
        hits = []
        for ex in self.store.extracts.values():
            if any(_macro_key(m) == mid for m in ex.macro_factors) or mid in (ex.title + " " + ex.summary).lower():
                hits.append(ex.summary or ex.investment_thesis)
        if hits:
            data["current_agi_view"] = hits[0][:500]
            data["affected_companies"] = merge_list(
                data.get("affected_companies"),
                [c for ex in self.store.extracts.values() for c in ex.companies][:12],
            )
        meta = dict(data["meta"])
        if hits:
            meta = bump_version(meta, reason="macro refresh from research")
        meta["confidence"] = confidence_score(
            has_thesis=bool(data.get("current_agi_view") or data.get("definition")),
            n_sources=1 + len(hits[:3]),
            source_reliability=0.75,
            n_structured_fields=count_filled([data.get("affected_sectors"), data.get("leading_indicators")]),
        )
        meta["freshness"] = freshness_score(_parse_dt(meta.get("updated_at")))
        data["meta"] = meta
        return self.store.upsert_macro(MacroKnowledgeObject.model_validate(data))

    def search(self, query: str, *, limit: int = 12) -> list[KnowledgeSearchHit]:
        """Knowledge-object-first search."""
        self.ensure_seeded()
        q = (query or "").lower().strip()
        if not q:
            return []
        hits: list[KnowledgeSearchHit] = []

        def consider(kind: str, key: str, label: str, blob: str, conf: float, fresh: float, summary: str, object_id: str):
            score = 0.0
            key_l = key.lower().replace("_", " ")
            label_l = label.lower()
            blob_l = blob.lower()
            if key_l in q or q in key_l or key.lower() in q:
                score += 0.55
            if label_l in q or q in label_l:
                score += 0.45
            # Phrase boosts for common institutional queries (e.g. "Indian FMCG").
            compact_q = q.replace("indian ", "").replace("india ", "").strip()
            if compact_q and (compact_q == key_l or compact_q == label_l or compact_q in blob_l):
                score += 0.35
            tokens = [t for t in q.replace("/", " ").replace("_", " ").split() if len(t) > 2 and t not in {"the", "and", "for", "how", "doing"}]
            overlap = sum(1 for t in tokens if t in blob_l or t in key_l or t in label_l)
            score += min(0.45, 0.1 * overlap)
            if score <= 0:
                return
            hits.append(
                KnowledgeSearchHit(
                    kind=kind,  # type: ignore[arg-type]
                    key=key,
                    label=label,
                    score=round(min(1.0, score + 0.1 * conf), 4),
                    confidence=conf,
                    freshness=fresh,
                    summary=summary[:280],
                    object_id=object_id,
                )
            )

        for c in self.store.companies.values():
            consider(
                "company",
                c.ticker,
                c.company_name,
                f"{c.ticker} {c.company_name} {c.sector} {c.industry} {c.latest_thesis}",
                c.meta.confidence,
                c.meta.freshness,
                c.latest_thesis or c.business_description,
                c.meta.object_id,
            )
        for s in self.store.sectors.values():
            consider(
                "sector",
                s.sector_id,
                s.label,
                f"{s.sector_id} {s.label} {s.definition} {s.latest_thesis}",
                s.meta.confidence,
                s.meta.freshness,
                s.latest_thesis or s.definition,
                s.meta.object_id,
            )
        for t in self.store.themes.values():
            consider(
                "theme",
                t.theme_id,
                t.label,
                f"{t.theme_id} {t.label} {t.definition} {t.investment_thesis}",
                t.meta.confidence,
                t.meta.freshness,
                t.investment_thesis or t.definition,
                t.meta.object_id,
            )
        for m in self.store.macros.values():
            consider(
                "macro",
                m.macro_id,
                m.label,
                f"{m.macro_id} {m.label} {m.definition} {m.why_investors_care}",
                m.meta.confidence,
                m.meta.freshness,
                m.current_agi_view or m.definition,
                m.meta.object_id,
            )
        hits.sort(key=lambda h: (-h.score, -h.confidence, -h.freshness))
        return hits[:limit]

    # --- seed helpers ---
    def _seed_company(self, row: dict[str, str]) -> CompanyKnowledgeObject:
        t = row["ticker"].upper()
        if t in self.store.companies:
            return self.store.companies[t]
        obj = CompanyKnowledgeObject(
            meta=KnowledgeMeta(
                kind="company",
                key=t,
                confidence=0.45,
                freshness=1.0,
                source_reliability=0.65,
                sources=["catalog"],
                change_log=["seeded from KF1 company catalog"],
            ),
            company_name=row.get("name") or t,
            ticker=t,
            sector=row.get("sector") or "",
            industry=row.get("industry") or "",
            business_description=f"{row.get('name') or t} — {row.get('sector') or 'Indian listed company'}.",
            countries=["India"],
        )
        return self.store.upsert_company(obj)

    def _seed_sector(self, row: dict) -> SectorKnowledgeObject:
        sid = str(row["sector_id"]).lower()
        if sid in self.store.sectors:
            return self.store.sectors[sid]
        majors = []
        for t in row.get("major_tickers") or []:
            co = self.store.companies.get(str(t).upper())
            majors.append({"ticker": str(t).upper(), "name": co.company_name if co else str(t).upper()})
        obj = SectorKnowledgeObject(
            meta=KnowledgeMeta(
                kind="sector",
                key=sid,
                confidence=0.5,
                freshness=1.0,
                source_reliability=0.65,
                sources=["catalog"],
                change_log=["seeded from KF1 sector catalog"],
            ),
            sector_id=sid,
            label=str(row.get("label") or sid),
            definition=str(row.get("definition") or ""),
            growth_drivers=list(row.get("growth_drivers") or []),
            demand_drivers=list(row.get("demand_drivers") or []),
            key_metrics=list(row.get("key_metrics") or []),
            major_companies=majors,
            valuation_framework=str(row.get("valuation_framework") or ""),
            risks=list(row.get("risks") or []),
            catalysts=list(row.get("catalysts") or []),
            countries=["India"],
        )
        return self.store.upsert_sector(obj)

    def _seed_theme(self, row: dict) -> ThemeKnowledgeObject:
        tid = str(row["theme_id"]).lower()
        if tid in self.store.themes:
            return self.store.themes[tid]
        obj = ThemeKnowledgeObject(
            meta=KnowledgeMeta(
                kind="theme",
                key=tid,
                confidence=0.5,
                freshness=1.0,
                source_reliability=0.65,
                sources=["catalog"],
                change_log=["seeded from KF1 theme catalog"],
            ),
            theme_id=tid,
            label=str(row.get("label") or tid),
            definition=str(row.get("definition") or ""),
            investment_thesis=str(row.get("investment_thesis") or ""),
            companies=[str(x).upper() for x in (row.get("companies") or [])],
            countries=list(row.get("countries") or []),
            beneficiaries=list(row.get("beneficiaries") or []),
            risks=list(row.get("risks") or []),
            catalysts=list(row.get("catalysts") or []),
            macro_drivers=list(row.get("macro_drivers") or []),
            related_sectors=list(row.get("related_sectors") or []),
        )
        return self.store.upsert_theme(obj)

    def _seed_macro(self, row: dict) -> MacroKnowledgeObject:
        mid = str(row["macro_id"]).lower()
        if mid in self.store.macros:
            return self.store.macros[mid]
        obj = MacroKnowledgeObject(
            meta=KnowledgeMeta(
                kind="macro",
                key=mid,
                confidence=0.5,
                freshness=1.0,
                source_reliability=0.65,
                sources=["catalog"],
                change_log=["seeded from KF1 macro catalog"],
            ),
            macro_id=mid,
            label=str(row.get("label") or mid),
            definition=str(row.get("definition") or ""),
            why_investors_care=str(row.get("why_investors_care") or ""),
            affected_sectors=list(row.get("affected_sectors") or []),
            leading_indicators=list(row.get("leading_indicators") or []),
            lagging_indicators=list(row.get("lagging_indicators") or []),
            historical_episodes=list(row.get("historical_episodes") or []),
        )
        return self.store.upsert_macro(obj)

    def _merge_extract_into_company(self, ticker: str, extract) -> None:
        t = ticker.upper()
        if t not in self.store.companies:
            self._seed_company({"ticker": t, "name": t, "sector": "", "industry": ""})
        co = self.store.companies[t]
        data = co.model_dump(mode="json")
        data["latest_thesis"] = merge_string(data.get("latest_thesis") or "", extract.investment_thesis)
        data["bull_case"] = merge_list(data.get("bull_case"), extract.bull_case)
        data["bear_case"] = merge_list(data.get("bear_case"), extract.bear_case)
        data["key_risks"] = merge_list(data.get("key_risks"), extract.risks)
        data["key_catalysts"] = merge_list(data.get("key_catalysts"), extract.catalysts)
        data["themes"] = merge_list(data.get("themes"), extract.themes)
        data["valuation"] = merge_string(data.get("valuation") or "", extract.valuation_view)
        data["related_research"] = merge_list(data.get("related_research"), [extract.document_id, extract.title])
        meta = bump_version(dict(data["meta"]), reason=f"research extract {extract.document_id}")
        meta["sources"] = merge_list(meta.get("sources"), ["agi_research"])
        meta["document_ids"] = merge_list(meta.get("document_ids"), [extract.document_id])
        meta["confidence"] = confidence_score(
            has_thesis=bool(data.get("latest_thesis")),
            n_sources=len(meta.get("document_ids") or []),
            source_reliability=source_reliability("agi_research"),
            n_structured_fields=count_filled([data.get("bull_case"), data.get("bear_case"), data.get("key_risks")]),
            has_house_view=bool(data.get("latest_thesis")),
        )
        meta["freshness"] = 1.0
        data["meta"] = meta
        self.store.upsert_company(CompanyKnowledgeObject.model_validate(data))

    def _merge_extract_into_sector(self, sector_id: str, extract) -> None:
        sec = self.store.sectors.get(sector_id)
        if not sec:
            return
        data = sec.model_dump(mode="json")
        data["latest_thesis"] = merge_string(data.get("latest_thesis") or "", extract.investment_thesis)
        data["risks"] = merge_list(data.get("risks"), extract.risks)
        data["catalysts"] = merge_list(data.get("catalysts"), extract.catalysts)
        data["current_agi_view"] = "Updated from latest AGI research"
        meta = bump_version(dict(data["meta"]), reason=f"extract {extract.document_id}")
        meta["freshness"] = 1.0
        meta["document_ids"] = merge_list(meta.get("document_ids"), [extract.document_id])
        data["meta"] = meta
        self.store.upsert_sector(SectorKnowledgeObject.model_validate(data))

    def _merge_extract_into_theme(self, theme_id: str, extract) -> None:
        th = self.store.themes.get(theme_id)
        if not th:
            return
        data = th.model_dump(mode="json")
        data["investment_thesis"] = merge_string(data.get("investment_thesis") or "", extract.investment_thesis)
        data["risks"] = merge_list(data.get("risks"), extract.risks)
        data["catalysts"] = merge_list(data.get("catalysts"), extract.catalysts)
        data["companies"] = merge_list(data.get("companies"), extract.companies)
        data["current_agi_view"] = "Updated from latest AGI research"
        meta = bump_version(dict(data["meta"]), reason=f"extract {extract.document_id}")
        meta["freshness"] = 1.0
        data["meta"] = meta
        self.store.upsert_theme(ThemeKnowledgeObject.model_validate(data))

    def _merge_extract_into_macro(self, macro_id: str, extract) -> None:
        m = self.store.macros.get(macro_id)
        if not m:
            return
        data = m.model_dump(mode="json")
        data["current_agi_view"] = merge_string(data.get("current_agi_view") or "", extract.summary or extract.investment_thesis)
        data["affected_companies"] = merge_list(data.get("affected_companies"), extract.companies)
        meta = bump_version(dict(data["meta"]), reason=f"extract {extract.document_id}")
        meta["freshness"] = 1.0
        data["meta"] = meta
        self.store.upsert_macro(MacroKnowledgeObject.model_validate(data))

    def _recompute_relationships(self) -> None:
        n = 0
        for c in self.store.companies.values():
            n += len(c.competitors) + len(c.themes) + len(c.customers) + len(c.suppliers)
        for s in self.store.sectors.values():
            n += len(s.major_companies) + len(s.themes)
        for t in self.store.themes.values():
            n += len(t.companies) + len(t.related_sectors)
        for m in self.store.macros.values():
            n += len(m.affected_sectors) + len(m.affected_companies)
        self.store.relationships = n


def _parse_dt(value: Any) -> _dt.datetime | None:
    if isinstance(value, _dt.datetime):
        return value
    if not value:
        return None
    try:
        return _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _sector_key(value: str) -> str | None:
    v = (value or "").lower().strip().replace(" ", "_").replace("-", "_")
    aliases = {
        "information_technology": "it_services",
        "it": "it_services",
        "it_services": "it_services",
        "software": "it_services",
        "banks": "banking",
        "bank": "banking",
        "banking": "banking",
        "financials": "financial_services",
        "nbfc": "financial_services",
        "fmcg": "fmcg",
        "pharma": "pharma",
        "pharmaceuticals": "pharma",
        "auto": "auto",
        "automobile": "auto",
        "defence": "defence",
        "defense": "defence",
        "power": "power",
        "telecom": "telecom",
        "retail": "retail",
        "real_estate": "real_estate",
        "realty": "real_estate",
        "metals": "metals",
        "chemicals": "chemicals",
        "capital_goods": "capital_goods",
        "energy": "energy",
    }
    if v in aliases:
        return aliases[v]
    for key in aliases:
        if key in v or v in key:
            return aliases[key]
    return v if v else None


def _theme_key(value: str) -> str | None:
    v = (value or "").lower().strip().replace(" ", "_").replace("-", "_")
    aliases = {
        "ai": "artificial_intelligence",
        "ai_adoption": "artificial_intelligence",
        "genai": "artificial_intelligence",
        "artificial_intelligence": "artificial_intelligence",
        "ev": "ev",
        "electric_vehicles": "ev",
        "renewables": "renewables",
        "china_plus_one": "china_plus_one",
        "china+1": "china_plus_one",
        "defence": "defence_theme",
        "defense": "defence_theme",
        "defence_theme": "defence_theme",
        "data_centres": "data_centres",
        "data_centers": "data_centres",
        "digital_payments": "digital_payments",
        "upi": "digital_payments",
        "semiconductors": "semiconductors",
        "manufacturing": "manufacturing",
        "railways": "railways",
    }
    return aliases.get(v, v if v in {
        "artificial_intelligence", "ev", "renewables", "railways", "manufacturing",
        "semiconductors", "china_plus_one", "defence_theme", "data_centres", "digital_payments",
    } else None)


def _macro_key(value: str) -> str | None:
    v = (value or "").lower().strip().replace(" ", "_")
    aliases = {
        "inflation": "inflation",
        "cpi": "inflation",
        "rates": "interest_rates",
        "interest_rates": "interest_rates",
        "repo": "interest_rates",
        "gdp": "gdp",
        "fiscal": "fiscal_policy",
        "fiscal_policy": "fiscal_policy",
        "oil": "oil",
        "crude": "oil",
        "fx": "currency",
        "currency": "currency",
        "inr": "currency",
        "yields": "bond_yields",
        "bond_yields": "bond_yields",
        "employment": "employment",
        "trade": "trade",
        "geopolitics": "geopolitics",
    }
    return aliases.get(v)
