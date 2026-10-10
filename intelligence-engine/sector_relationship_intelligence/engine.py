"""SRI engine — discover, validate, publish, retrieve sector relationships."""

from __future__ import annotations

from typing import Any

from sector_relationship_intelligence import traces
from sector_relationship_intelligence.discovery import (
    discover_from_catalog,
    enrich_with_hmip,
    enrich_with_hsip,
    enrich_with_mri_tip,
)
from sector_relationship_intelligence.graph import build_graph, find_paths
from sector_relationship_intelligence.schema import (
    NO_SRI_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    SRI_VERSION,
)
from sector_relationship_intelligence.store import STORE
from sector_relationship_intelligence.validation import (
    is_stale,
    score_confidence,
    validate_relationship,
)


class SectorRelationshipIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": SRI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_SRI_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "consumes": ["HSIP", "HMIP", "MRI tips", "CSKP universe"],
            "phase": "11.3",
            "preceded_by": ["CSKP 11.1", "HSIP 11.2"],
            "enables": ["HSAI 11.4", "SFI 11.5"],
        }

    def run(
        self,
        *,
        enrich_hsip: bool = True,
        enrich_hmip: bool = True,
        enrich_mri: bool = True,
    ) -> dict[str, Any]:
        """Ops rebuild — discover → enrich → validate → publish. Never Ask."""
        span = traces.begin(
            "sector_relationship_discovery",
            meta={
                "enrich_hsip": enrich_hsip,
                "enrich_hmip": enrich_hmip,
                "enrich_mri": enrich_mri,
            },
        )
        STORE.clear()
        candidates = discover_from_catalog()
        traces.end(span, output={"candidates": len(candidates)})

        published = 0
        rejected = 0
        newly: list[str] = []

        for rel in candidates:
            if enrich_hsip:
                rel = enrich_with_hsip(rel)
            if enrich_hmip:
                rel = enrich_with_hmip(rel)
            if enrich_mri:
                rel = enrich_with_mri_tip(rel)

            vspan = traces.begin(
                "sector_relationship_validation",
                meta={"source": rel.source, "target": rel.target, "kind": rel.kind},
            )
            errors = validate_relationship(rel)
            if errors:
                STORE.record_validation_failure(
                    {
                        "source": rel.source,
                        "target": rel.target,
                        "relationship": rel.relationship,
                        "errors": errors,
                    }
                )
                traces.end(vspan, ok=False, output={"errors": errors})
                rejected += 1
                continue

            pct, label, strength = score_confidence(rel)
            rel.confidence_pct = pct
            rel.confidence_label = label  # type: ignore[assignment]
            rel.evidence_strength = strength  # type: ignore[assignment]
            rel.stale = is_stale(rel)
            traces.end(
                vspan,
                output={
                    "confidence_pct": pct,
                    "label": label,
                    "evidence_n": len(rel.evidence),
                    "stale": rel.stale,
                },
            )

            frozen = STORE.publish(rel)
            STORE.record_discovery(
                {
                    "relationship_id": frozen.relationship_id,
                    "source": frozen.source,
                    "target": frozen.target,
                    "kind": frozen.kind,
                    "confidence_pct": frozen.confidence_pct,
                    "version": frozen.version,
                }
            )
            published += 1
            newly.append(frozen.relationship_id)

        gspan = traces.begin("sector_relationship_graph", meta={"published": published})
        graph = build_graph()
        traces.end(gspan, output={"nodes": graph["n_nodes"], "edges": graph["n_edges"]})

        rspan = traces.begin("sector_relationship_refresh", meta={"published": published})
        summary = {
            "ok": True,
            "published": published,
            "rejected": rejected,
            "total": STORE.coverage()["total_relationships"],
            "graph": {"nodes": graph["n_nodes"], "edges": graph["n_edges"]},
            "ask_triggered": False,
            "providers_queried": [],
            "new_relationship_ids": newly[:40],
        }
        STORE.record_run(summary)
        traces.end(rspan, output={"total": summary["total"], "rejected": rejected})
        return summary

    def relationships(self, *, limit: int = 200) -> dict[str, Any]:
        span = traces.begin("sector_relationship_retrieval", meta={"scope": "all"})
        rows = STORE.list_all(limit=limit)
        out = {
            "n": len(rows),
            "relationships": [r.to_public_dict() for r in rows],
            "coverage": STORE.coverage(),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "SRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def for_sector(self, sector: str, *, limit: int = 100) -> dict[str, Any]:
        span = traces.begin(
            "sector_relationship_retrieval",
            meta={"scope": "sector", "sector": sector},
        )
        rows = STORE.for_sector(sector, limit=limit)
        out = {
            "sector": sector,
            "n": len(rows),
            "relationships": [r.to_public_dict() for r in rows],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "SRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def for_company(self, ticker: str, *, limit: int = 100) -> dict[str, Any]:
        span = traces.begin(
            "sector_relationship_retrieval",
            meta={"scope": "company", "ticker": ticker},
        )
        rows = STORE.for_company(ticker, limit=limit)
        out = {
            "ticker": ticker.upper(),
            "n": len(rows),
            "relationships": [r.to_public_dict() for r in rows],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "SRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def search(
        self,
        *,
        q: str | None = None,
        kind: str | None = None,
        source: str | None = None,
        target: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        span = traces.begin(
            "sector_relationship_retrieval",
            meta={"scope": "search", "q": q, "kind": kind},
        )
        rows = STORE.list_all(limit=500)
        qn = (q or "").strip().lower()
        kn = (kind or "").strip().lower()
        sn = (source or "").strip().lower()
        tn = (target or "").strip().lower()

        filtered = []
        for r in rows:
            if kn and r.kind != kn:
                continue
            if sn and sn not in r.source.lower():
                continue
            if tn and tn not in r.target.lower():
                continue
            if qn:
                blob = " ".join(
                    [
                        r.source,
                        r.target,
                        r.relationship,
                        r.kind,
                        " ".join(r.chain),
                        " ".join(e.summary for e in r.evidence),
                    ]
                ).lower()
                if qn not in blob:
                    continue
            filtered.append(r)

        filtered = filtered[:limit]
        out = {
            "q": q,
            "kind": kind,
            "n": len(filtered),
            "relationships": [r.to_public_dict() for r in filtered],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "SRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def graph(self, *, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        span = traces.begin("sector_relationship_graph", meta={"source": "api", "start": start})
        g = build_graph()
        if start:
            g["paths_from"] = find_paths(start=start, end=end)
        traces.end(span, output={"nodes": g["n_nodes"], "edges": g["n_edges"]})
        return g

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        rows = STORE.list_all(limit=200)
        recent = sorted(rows, key=lambda r: r.published_at or r.created_at, reverse=True)[:15]
        high = [r for r in rows if r.confidence_label == "High"]
        stale = [r for r in rows if r.stale]
        by_sector: dict[str, int] = {}
        for r in rows:
            for name in (r.source, r.target):
                if name.isupper() and len(name) <= 12 and name not in {"NIFTY", "SENSEX", "USDINR", "CPI"}:
                    continue  # tickers / macros rough skip for coverage chart
                key = name if " " in name or name[0].isupper() else name
                if r.kind.endswith("sector") or "sector" in r.kind:
                    by_sector[name] = by_sector.get(name, 0) + 1

        return {
            "board": "Sector Relationship Intelligence",
            "programme": PROGRAMME,
            "version": SRI_VERSION,
            "principles": {
                "evidence_backed_only": True,
                "versioned_graph": True,
                "no_hardcoded_rules_without_history": True,
                "ask_never_fetches": True,
                "providers_queried_always_empty": True,
            },
            "does_not": list(NO_SRI_ACTIONS),
            "total_relationships": cov.get("total_relationships"),
            "active_relationships": cov.get("active_relationships"),
            "confidence_distribution": cov.get("confidence_distribution"),
            "recently_validated_relationships": [r.to_public_dict() for r in recent],
            "newly_discovered_relationships": STORE.recent_discoveries(20),
            "relationship_coverage_by_sector": {
                "sectors_covered": cov.get("sectors_covered"),
                "edge_counts_sample": dict(list(sorted(by_sector.items(), key=lambda x: -x[1])[:25])),
            },
            "relationship_freshness": {
                "stale": cov.get("stale"),
                "active": cov.get("active_relationships"),
                "stale_sample": [r.to_public_dict() for r in stale[:15]],
            },
            "validation_failures": STORE.validation_failures(40),
            "by_kind": cov.get("by_kind"),
            "high_confidence": len(high),
            "recent_runs": STORE.recent_runs(10),
            "retrieval_performance": {"traces": traces.recent(80)},
            "ingestion_idle": cov.get("total_relationships", 0) == 0,
            "phase": "11.3",
            "note": "Read APIs never rebuild the graph. Use POST /v1/sector/relationships/run.",
        }
