"""AOI service facade — autonomous public knowledge acquisition."""

from __future__ import annotations

from typing import Any

from app.aoi.flags import AoiFlags
from app.aoi.graph import traverse
from app.aoi.pipeline import AoiPipeline
from app.aoi.registry import CompanyRegistry
from app.aoi.store import AoiStore
from app.aoi.versioning import company_timeline, latest_facts_by_field
from app.core.config import get_settings


class AoiService:
    """Enterprise acquisition platform feeding KC/KF without redesigning them."""

    def __init__(
        self,
        *,
        kip: Any | None = None,
        kc: Any | None = None,
        kf: Any | None = None,
        eve: Any | None = None,
        flags: AoiFlags | None = None,
        store: AoiStore | None = None,
        registry: CompanyRegistry | None = None,
    ) -> None:
        self.flags = flags or AoiFlags.from_settings(get_settings())
        self.store = store or AoiStore()
        self.registry = registry or CompanyRegistry()
        self.eve = eve
        self.pipeline = AoiPipeline(
            flags=self.flags,
            store=self.store,
            registry=self.registry,
            kip=kip,
            kc=kc,
            kf=kf,
            eve=eve,
        )
        if self.flags.aoi:
            self.pipeline.ensure_registry()

    def bind_eve(self, eve: Any) -> None:
        """Soft extension point — attach EVE without redesigning AOI internals."""
        self.eve = eve
        self.pipeline.eve = eve

    def health(self) -> dict[str, Any]:
        cov = self.store.coverage_counts() if self.flags.aoi else {}
        return {
            "status": "ok" if self.flags.aoi else "disabled",
            "layer": "AGI Open Intelligence",
            "programme": "AOI",
            "version": "aoi-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "public_acquisition_into_kc_kf",
            "no_redesign": ["kf1", "kcv1", "kip", "irp", "rsp", "ask_agi", "existing_apis"],
            "flags": self.flags.as_dict(),
            "coverage": cov,
            "connectors": sorted(self.pipeline.connectors.keys()),
            "optional_connectors": __import__(
                "app.aoi.connectors.factory", fromlist=["list_optional_connectors"]
            ).list_optional_connectors(),
        }

    def seed_registry(self) -> dict[str, Any]:
        self._require()
        return self.pipeline.ensure_registry()

    def run_cycle(
        self,
        *,
        connector_ids: list[str] | None = None,
        limit_per_connector: int | None = None,
        publish: bool | None = None,
    ) -> dict[str, Any]:
        self._require()
        return self.pipeline.run(
            connector_ids=connector_ids,
            limit_per_connector=limit_per_connector,
            publish=publish,
        )

    def dashboard(self) -> dict[str, Any]:
        self._require()
        qualities = sorted(self.store.quality.values(), key=lambda q: -q.overall)
        gaps = self.store.gaps or []
        digest = self.store.digests[-1].model_dump(mode="json") if self.store.digests else {}
        latest_docs = sorted(
            self.store.artifacts.values(),
            key=lambda a: a.discovered_at or "",
            reverse=True,
        )[:25]
        return {
            "programme": "AOI",
            "architecture_status": "v1.0.1 LOCKED",
            "coverage": self.store.coverage_counts(),
            "registry": {
                "companies": len(list(self.registry.all())),
                "nifty_50": len(self.registry.nifty50()),
            },
            "connector_health": [h.model_dump(mode="json") for h in self.pipeline.connector_health.values()],
            "scheduler": self.pipeline.scheduler.status(),
            "quality_heatmap": [q.model_dump(mode="json") for q in qualities[:50]],
            "gaps": [g.model_dump(mode="json") for g in gaps[:40]],
            "learning": digest,
            "latest_documents": [
                {
                    "artifact_id": a.artifact_id,
                    "title": a.title,
                    "connector_id": a.connector_id,
                    "doc_type": a.doc_type,
                    "status": a.status,
                    "company_id": a.company_id,
                }
                for a in latest_docs
            ],
            "observability": self.store.metrics.model_dump(mode="json"),
            "failures": [
                {
                    "artifact_id": a.artifact_id,
                    "title": a.title,
                    "error": a.error,
                    "connector_id": a.connector_id,
                }
                for a in self.store.artifacts.values()
                if a.status == "failed"
            ][:30],
        }

    def list_companies(self, *, universe: str | None = "nifty_50") -> dict[str, Any]:
        self._require()
        rows = self.registry.list(universe=universe) if universe else list(self.registry.all())
        return {
            "count": len(rows),
            "companies": [c.model_dump(mode="json") for c in rows],
        }

    def get_company(self, key: str) -> dict[str, Any]:
        self._require()
        co = self.registry.resolve(key)
        if co is None:
            raise KeyError(f"Unknown company '{key}'")
        facts = latest_facts_by_field(self.store, co.company_id)
        versions = company_timeline(self.store, co.company_id)
        docs = [a for a in self.store.artifacts.values() if a.company_id == co.company_id]
        return {
            "company": co.model_dump(mode="json"),
            "quality": (self.store.quality.get(co.company_id).model_dump(mode="json")
                        if self.store.quality.get(co.company_id) else {}),
            "latest_facts": {k: v.model_dump(mode="json") for k, v in facts.items()},
            "versions": [v.model_dump(mode="json") for v in versions],
            "documents": [
                {
                    "artifact_id": d.artifact_id,
                    "title": d.title,
                    "doc_type": d.doc_type,
                    "status": d.status,
                    "connector_id": d.connector_id,
                    "checksum": d.checksum,
                }
                for d in sorted(docs, key=lambda x: x.discovered_at or "", reverse=True)
            ],
            "graph": traverse(self.store, co.company_id, max_depth=2)[:40],
            "diffs": [
                d.model_dump(mode="json")
                for d in self.store.diffs
                if d.company_id == co.company_id
            ][-20:],
        }

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        """Semantic-lite search across companies, documents, facts, macro, relationships."""
        self._require()
        q = (query or "").lower().strip()
        if not q:
            return {"query": query, "hits": [], "count": 0}
        hits: list[dict[str, Any]] = []

        co = self.registry.resolve(query)
        if co:
            hits.append(
                {
                    "kind": "company",
                    "id": co.company_id,
                    "label": co.company_name,
                    "score": 0.99,
                    "snippet": f"{co.nse_symbol} · {co.sector}",
                }
            )

        for c in self.registry.all():
            blob = f"{c.company_name} {c.nse_symbol} {c.sector} {' '.join(c.aliases)}".lower()
            if q in blob or any(tok in blob for tok in q.split() if len(tok) > 2):
                hits.append(
                    {
                        "kind": "company",
                        "id": c.company_id,
                        "label": c.company_name,
                        "score": 0.8,
                        "snippet": f"{c.nse_symbol} · {c.sector}",
                    }
                )

        for a in self.store.artifacts.values():
            blob = f"{a.title} {a.doc_type} {a.content_text[:300]}".lower()
            if q in blob or any(tok in blob for tok in q.split() if len(tok) > 3):
                hits.append(
                    {
                        "kind": "document",
                        "id": a.artifact_id,
                        "label": a.title,
                        "score": 0.7,
                        "snippet": (a.content_text or "")[:180],
                    }
                )

        for f in list(self.store.facts.values())[:5000]:
            blob = f"{f.field} {f.value_text}".lower()
            if q in blob:
                hits.append(
                    {
                        "kind": "fact",
                        "id": f.fact_id,
                        "label": f.field,
                        "score": 0.65,
                        "snippet": f.value_text[:180],
                    }
                )

        # Dedup by kind+id
        uniq: dict[str, dict[str, Any]] = {}
        for h in hits:
            uniq[f"{h['kind']}:{h['id']}"] = h
        ranked = sorted(uniq.values(), key=lambda h: -float(h["score"]))[:limit]
        return {"query": query, "hits": ranked, "count": len(ranked), "answer_policy": "aoi_structured_knowledge"}

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Ask AGI soft retrieval — canonical company → structured knowledge → updates."""
        self._require()
        search = self.search(query, limit=limit)
        company_hit = next((h for h in search["hits"] if h["kind"] == "company"), None)
        company_pack = None
        if company_hit:
            try:
                company_pack = self.get_company(company_hit["id"])
            except KeyError:
                company_pack = None
        return {
            "answer_policy": "aoi_then_kc_kf_then_documents",
            "query": query,
            "hits": search["hits"],
            "company": company_pack,
            "primary_source_of_truth": "structured_knowledge",
        }

    def connector_health(self) -> dict[str, Any]:
        self._require()
        # Ensure health entries exist even before run
        for cid, conn in self.pipeline.connectors.items():
            if cid not in self.pipeline.connector_health:
                hc = conn.health_check()
                from app.aoi.models import ConnectorHealth

                self.pipeline.connector_health[cid] = ConnectorHealth(
                    connector_id=cid,
                    name=conn.name,
                    enabled=True,
                    status=str(hc.get("status") or "ok"),
                )
        return {
            "connectors": [h.model_dump(mode="json") for h in self.pipeline.connector_health.values()],
            "optional": __import__("app.aoi.connectors.factory", fromlist=["list_optional_connectors"]).list_optional_connectors(),
        }

    def _require(self) -> None:
        if not self.flags.aoi:
            raise RuntimeError("AOI is disabled (AOI=false)")
