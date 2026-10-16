"""IIE service facade — investment intelligence APIs and Ask AGI consult."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.iie.evidence import VerifiedEvidenceReader
from app.iie.flags import IieFlags
from app.iie.pipeline import IiePipeline
from app.iie.store import IieStore


class IieService:
    """Investment Intelligence Engine — after EVE / KCV / KF, before reasoning."""

    def __init__(
        self,
        *,
        flags: IieFlags | None = None,
        store: IieStore | None = None,
        eve: Any | None = None,
        kc: Any | None = None,
        kf: Any | None = None,
        aoi: Any | None = None,
    ) -> None:
        self.flags = flags or IieFlags.from_settings(get_settings())
        self.store = store or IieStore()
        self.eve = eve
        self.kc = kc
        self.kf = kf
        self.aoi = aoi
        self.reader = VerifiedEvidenceReader(eve=eve, kc=kc, kf=kf)
        self.pipeline = IiePipeline(self.store, self.reader)
        if self.flags.iie and not self.store.sectors:
            self.pipeline.seed_sectors_and_themes()

    def bind_eve(self, eve: Any) -> None:
        """Soft extension point — refresh evidence reader when EVE is available."""
        self.eve = eve
        self.reader.eve = eve

    def health(self) -> dict[str, Any]:
        snap = self.store.snapshot() if self.flags.iie else {}
        return {
            "status": "ok" if self.flags.iie else "disabled",
            "layer": "Investment Intelligence Engine",
            "programme": "IIE",
            "version": "iie-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "after_eve_kcv_kf_before_reasoning",
            "no_redesign": ["kf1", "kcv1", "aoi", "eve", "kip", "irp", "rsp", "ask_agi"],
            "inputs": ["eve_verified_evidence", "kcv", "kf"],
            "never_consumes": ["raw_documents"],
            "flags": self.flags.as_dict(),
            "snapshot": snap,
            "metrics": self.store.metrics.model_dump(),
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        profiles = sorted(self.store.profiles.values(), key=lambda p: p.updated_at, reverse=True)
        return {
            "programme": "IIE",
            "architecture_status": "v1.0.1 LOCKED",
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
            "confidence_heatmap": [
                {
                    "company_id": p.company_id,
                    "name": p.company_name,
                    "confidence": p.confidence,
                    "version": p.version,
                    "evidence": len(p.evidence_ids),
                }
                for p in profiles[:50]
            ],
            "recent_profiles": [p.to_dict() for p in profiles[:15]],
            "sectors": [s.to_dict() for s in list(self.store.sectors.values())[:30]],
            "themes": [t.to_dict() for t in list(self.store.themes.values())[:30]],
            "catalysts": [
                c.to_dict()
                for c in sorted(self.store.catalysts.values(), key=lambda x: x.updated_at, reverse=True)[:25]
            ],
            "risks": [
                r.to_dict()
                for r in sorted(self.store.risks.values(), key=lambda x: x.updated_at, reverse=True)[:25]
            ],
            "opportunities": [
                o.to_dict()
                for o in sorted(self.store.opportunities.values(), key=lambda x: x.updated_at, reverse=True)[:25]
            ],
            "theses": [t.to_dict() for t in list(self.store.theses.values())[:20]],
            "confidence_distribution": self.store.confidence_distribution(),
            "knowledge_freshness": {
                "profiles_with_evidence": sum(1 for p in self.store.profiles.values() if p.evidence_ids),
                "history_entries": len(self.store.history),
            },
            "audit": [a.to_dict() for a in self.store.audit[-30:]],
        }

    def analyse(self, key: str) -> dict[str, Any]:
        self._require()
        if not self.flags.iie_auto_analyse:
            raise RuntimeError("IIE auto-analyse disabled")
        return self.pipeline.analyse_company(key)

    def run_batch(self, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        return self.pipeline.analyse_from_eve_companies(limit=limit)

    def company(self, key: str, *, analyse_if_missing: bool = True) -> dict[str, Any]:
        self._require()
        company_id, symbol, name = self.reader.resolve_company(key)
        profile = self.store.profiles.get(company_id) or self.store.profiles.get(key)
        if profile is None and analyse_if_missing and self.flags.iie_auto_analyse:
            self.pipeline.analyse_company(key)
            profile = self.store.profiles.get(company_id) or self.store.profiles.get(key)
        if profile is None:
            raise KeyError(f"Company intelligence not found for '{key}'")
        cid = profile.company_id
        return {
            "company_id": cid,
            "symbol": symbol,
            "name": name or profile.company_name,
            "profile": profile.to_dict(),
            "dna": self.store.dna[cid].to_dict() if cid in self.store.dna else {},
            "thesis": self.store.theses[cid].to_dict() if cid in self.store.theses else {},
            "scenarios": self.store.scenarios[cid].to_dict() if cid in self.store.scenarios else {},
            "monitor": self.store.monitors[cid].to_dict() if cid in self.store.monitors else {},
            "risks": [r.to_dict() for r in self.store.risks.values() if r.company_id == cid],
            "opportunities": [o.to_dict() for o in self.store.opportunities.values() if o.company_id == cid],
            "catalysts": [
                c.to_dict() for c in self.store.catalysts.values() if cid in c.affected_companies
            ],
            "themes": [
                t.to_dict() for t in self.store.themes.values() if cid in t.company_ids
            ],
            "relationships": [
                e.to_dict()
                for e in self.store.relationships.values()
                if e.from_id == cid or e.to_id == cid
            ],
            "evolution": [h.to_dict() for h in self.store.evolution(entity_id=cid, limit=30)],
        }

    def sector(self, sector_id: str) -> dict[str, Any]:
        self._require()
        sec = self.store.sectors.get(sector_id)
        if not sec:
            # try label match
            for s in self.store.sectors.values():
                if s.name.lower() == sector_id.lower() or s.sector_id == sector_id.lower():
                    sec = s
                    break
        if not sec:
            raise KeyError(f"Sector '{sector_id}' not found")
        return {
            "sector": sec.to_dict(),
            "companies": [
                self.store.profiles[c].to_dict()
                for c in sec.key_listed_companies
                if c in self.store.profiles
            ],
            "themes": [
                t.to_dict()
                for t in self.store.themes.values()
                if sec.sector_id in t.sector_ids
            ],
            "macro": [
                m.to_dict()
                for m in self.store.macro_impacts.values()
                if sec.sector_id in m.affected_sectors
            ],
        }

    def list_sectors(self) -> dict[str, Any]:
        self._require()
        rows = [s.to_dict() for s in self.store.sectors.values()]
        return {"count": len(rows), "sectors": rows}

    def theme(self, theme_id: str) -> dict[str, Any]:
        self._require()
        th = self.store.themes.get(theme_id)
        if not th:
            raise KeyError(f"Theme '{theme_id}' not found")
        return {"theme": th.to_dict()}

    def list_themes(self) -> dict[str, Any]:
        self._require()
        rows = [t.to_dict() for t in self.store.themes.values()]
        return {"count": len(rows), "themes": rows}

    def thesis(self, key: str) -> dict[str, Any]:
        self._require()
        pack = self.company(key, analyse_if_missing=True)
        return {"thesis": pack.get("thesis") or {}, "company_id": pack.get("company_id")}

    def scenario(self, key: str) -> dict[str, Any]:
        self._require()
        if not self.flags.iie_scenarios:
            raise RuntimeError("IIE scenarios disabled")
        pack = self.company(key, analyse_if_missing=True)
        return {"scenarios": pack.get("scenarios") or {}, "company_id": pack.get("company_id")}

    def catalysts(self, *, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        if not self.flags.iie_catalysts:
            raise RuntimeError("IIE catalysts disabled")
        rows = list(self.store.catalysts.values())
        if company_id:
            rows = [c for c in rows if company_id in c.affected_companies]
        rows = sorted(rows, key=lambda c: c.updated_at, reverse=True)[:limit]
        return {"count": len(rows), "catalysts": [c.to_dict() for c in rows]}

    def risks(self, *, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        if not self.flags.iie_risks:
            raise RuntimeError("IIE risks disabled")
        rows = list(self.store.risks.values())
        if company_id:
            rows = [r for r in rows if r.company_id == company_id]
        rows = sorted(rows, key=lambda r: r.updated_at, reverse=True)[:limit]
        return {"count": len(rows), "risks": [r.to_dict() for r in rows]}

    def opportunities(self, *, company_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        self._require()
        rows = list(self.store.opportunities.values())
        if company_id:
            rows = [o for o in rows if o.company_id == company_id]
        rows = sorted(rows, key=lambda o: o.updated_at, reverse=True)[:limit]
        return {"count": len(rows), "opportunities": [o.to_dict() for o in rows]}

    def monitor(self, key: str) -> dict[str, Any]:
        self._require()
        pack = self.company(key, analyse_if_missing=True)
        return {"monitor": pack.get("monitor") or {}, "company_id": pack.get("company_id")}

    def dna(self, key: str) -> dict[str, Any]:
        self._require()
        pack = self.company(key, analyse_if_missing=True)
        return {"dna": pack.get("dna") or {}, "company_id": pack.get("company_id")}

    def compare(self, company_ids: list[str], *, dimensions: list[str] | None = None) -> dict[str, Any]:
        self._require()
        if not self.flags.iie_compare:
            raise RuntimeError("IIE compare disabled")
        ids = [c.strip() for c in company_ids if c and c.strip()]
        if len(ids) < 2:
            raise ValueError("compare requires at least two company ids")
        for cid in ids:
            if cid not in self.store.profiles and self.flags.iie_auto_analyse:
                try:
                    self.pipeline.analyse_company(cid)
                except Exception:
                    pass
        result = self.pipeline.analyser.compare(ids, dimensions=dimensions)
        return result.to_dict()

    def macro(self, event: str) -> dict[str, Any]:
        self._require()
        impact = self.pipeline.analyser.map_macro(event)
        return impact.to_dict()

    def evolution(
        self,
        *,
        entity_id: str | None = None,
        object_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        self._require()
        rows = self.store.evolution(entity_id=entity_id, object_type=object_type, limit=limit)
        return {"count": len(rows), "history": [h.to_dict() for h in rows]}

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        q = (query or "").lower().strip()
        hits: list[dict[str, Any]] = []
        if not q:
            return {"query": query, "hits": [], "count": 0}
        for p in self.store.profiles.values():
            blob = f"{p.company_id} {p.company_name} {p.sections.get('business_summary', '')}".lower()
            if q in blob or any(tok in blob for tok in q.split() if len(tok) > 2):
                hits.append(
                    {
                        "kind": "company_profile",
                        "id": p.company_id,
                        "label": p.company_name or p.company_id,
                        "score": float(p.confidence),
                        "confidence": p.confidence,
                        "snippet": str(p.sections.get("investment_thesis") or p.sections.get("business_summary") or "")[:200],
                    }
                )
        for t in self.store.theses.values():
            blob = f"{t.company_id} {t.investment_thesis}".lower()
            if q in blob:
                hits.append(
                    {
                        "kind": "thesis",
                        "id": t.thesis_id,
                        "label": f"Thesis · {t.company_id}",
                        "score": float(t.confidence),
                        "snippet": t.investment_thesis[:200],
                    }
                )
        for s in self.store.sectors.values():
            blob = f"{s.sector_id} {s.name} {' '.join(s.growth_drivers)}".lower()
            if q in blob:
                hits.append(
                    {
                        "kind": "sector",
                        "id": s.sector_id,
                        "label": s.name,
                        "score": float(s.confidence),
                        "snippet": s.demand_outlook[:200],
                    }
                )
        for th in self.store.themes.values():
            blob = f"{th.theme_id} {th.name}".lower()
            if q in blob:
                hits.append(
                    {
                        "kind": "theme",
                        "id": th.theme_id,
                        "label": th.name,
                        "score": float(th.confidence),
                        "snippet": th.description[:200],
                    }
                )
        for c in self.store.catalysts.values():
            if q in c.title.lower() or q in c.catalyst_type.lower():
                hits.append(
                    {
                        "kind": "catalyst",
                        "id": c.catalyst_id,
                        "label": c.title[:80],
                        "score": float(c.confidence),
                        "snippet": c.catalyst_type,
                    }
                )
        hits.sort(key=lambda h: -float(h.get("score") or 0))
        return {"query": query, "hits": hits[:limit], "count": len(hits[:limit])}

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Ask AGI soft retrieval — structured investment intelligence before reasoning."""
        self._require()
        search = self.search(query, limit=limit)
        company_pack = None
        # Resolve company via EVE/AOI then ensure analysed
        resolved = None
        if self.aoi is not None:
            try:
                co = self.aoi.registry.resolve(query)
                if co:
                    resolved = co.company_id or co.nse_symbol
            except Exception:
                resolved = None
        if resolved is None:
            for tok in (query or "").upper().split():
                if len(tok) >= 2 and tok.isalpha():
                    # try analyse/lookup
                    if tok in self.store.profiles or any(
                        (p.company_name or "").upper() == tok for p in self.store.profiles.values()
                    ):
                        resolved = tok
                        break
                    if self.eve is not None:
                        try:
                            pack = self.eve.company_pack(tok)
                            if pack and pack.get("evidence"):
                                resolved = pack.get("company_id") or tok
                                break
                        except Exception:
                            pass
        if resolved and self.flags.iie_auto_analyse:
            try:
                company_pack = self.company(resolved, analyse_if_missing=True)
            except Exception:
                company_pack = None

        finance_academy: dict = {}
        sector_intelligence: dict = {}
        try:
            from academy.fapi.production import attach_for_engine

            finance_academy = attach_for_engine("iie", query).get("finance_academy") or {}
            sector_intelligence = finance_academy.get("sector_intelligence") or {}
        except Exception:
            finance_academy = {}
        if not sector_intelligence:
            try:
                from sif.production import attach_for_engine as sif_attach

                sector_intelligence = sif_attach("iie", query).get("sector_intelligence") or {}
            except Exception:
                sector_intelligence = {}
        return {
            "answer_policy": "investment_intelligence_before_reasoning",
            "query": query,
            "hits": search["hits"],
            "company": company_pack,
            "guidance": {
                "use_structured_intelligence_first": True,
                "trace_to_eve_evidence": True,
                "preserve_uncertainty": True,
                "never_hallucinate": True,
                "versioned_outputs": True,
                "academy_capital_allocation": True,
                "sector_iie_focus": sector_intelligence.get("iie_focus") or [],
            },
            "primary_source_of_truth": "investment_intelligence_objects",
            "upstream_evidence": "eve_verified_only",
            "finance_academy": finance_academy,
            "sector_intelligence": sector_intelligence,
        }

    def _require(self) -> None:
        if not self.flags.iie:
            raise RuntimeError("IIE is disabled (IIE=false)")
