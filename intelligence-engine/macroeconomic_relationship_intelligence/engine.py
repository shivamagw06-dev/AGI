"""MRI engine — discover, validate, publish, retrieve macro relationships."""

from __future__ import annotations

from typing import Any

from macroeconomic_relationship_intelligence import traces
from macroeconomic_relationship_intelligence.discovery import discover_from_catalog, enrich_with_hmip
from macroeconomic_relationship_intelligence.graph import build_graph
from macroeconomic_relationship_intelligence.schema import (
    MRI_VERSION,
    NO_MRI_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
)
from macroeconomic_relationship_intelligence.store import STORE
from macroeconomic_relationship_intelligence.validation import (
    is_stale,
    score_confidence,
    validate_relationship,
)


class MacroeconomicRelationshipIntelligenceEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": MRI_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_MRI_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "consumes": ["HMIP", "Historical Company/Sector/Market knowledge tips"],
            "phase": "10.3",
            "preceded_by": ["CMKP 10.1", "HMIP 10.2"],
        }

    def run(self, *, enrich_hmip: bool = True) -> dict[str, Any]:
        """Ops rebuild — discover → validate → publish. Never Ask."""
        span = traces.begin("macro_relationship_discovery", meta={"enrich_hmip": enrich_hmip})
        STORE.clear()
        candidates = discover_from_catalog()
        traces.end(span, output={"candidates": len(candidates)})

        published = 0
        rejected = 0
        newly: list[str] = []

        for rel in candidates:
            if enrich_hmip:
                rel = enrich_with_hmip(rel)

            vspan = traces.begin(
                "macro_relationship_validation",
                meta={"source": rel.source, "target": rel.target},
            )
            errors = validate_relationship(rel)
            if errors:
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
            published += 1
            newly.append(frozen.relationship_id)

        gspan = traces.begin("macro_relationship_graph", meta={"published": published})
        graph = build_graph()
        traces.end(gspan, output={"nodes": graph["n_nodes"], "edges": graph["n_edges"]})

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
        return summary

    def relationships(self, *, limit: int = 200) -> dict[str, Any]:
        span = traces.begin("macro_relationship_retrieval", meta={"scope": "all"})
        rows = STORE.list_all(limit=limit)
        out = {
            "n": len(rows),
            "relationships": [r.to_public_dict() for r in rows],
            "coverage": STORE.coverage(),
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "MRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def for_indicator(self, indicator: str, *, limit: int = 100) -> dict[str, Any]:
        span = traces.begin(
            "macro_relationship_retrieval",
            meta={"scope": "indicator", "indicator": indicator},
        )
        # Auto-build if empty so ops-less smoke still works? No — never collect on read.
        rows = STORE.for_indicator(indicator, limit=limit)
        out = {
            "indicator": indicator,
            "n": len(rows),
            "relationships": [r.to_public_dict() for r in rows],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "MRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def for_company(self, ticker: str, *, limit: int = 100) -> dict[str, Any]:
        span = traces.begin(
            "macro_relationship_retrieval",
            meta={"scope": "company", "ticker": ticker},
        )
        rows = STORE.for_company(ticker, limit=limit)
        out = {
            "ticker": ticker.upper(),
            "n": len(rows),
            "relationships": [r.to_public_dict() for r in rows],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "MRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def for_sector(self, sector: str, *, limit: int = 100) -> dict[str, Any]:
        span = traces.begin(
            "macro_relationship_retrieval",
            meta={"scope": "sector", "sector": sector},
        )
        rows = STORE.for_sector(sector, limit=limit)
        out = {
            "sector": sector,
            "n": len(rows),
            "relationships": [r.to_public_dict() for r in rows],
            "providers_queried": [],
            "collected_on_request": False,
            "gateway": "MRI_KRIG",
        }
        traces.end(span, output={"n": out["n"]})
        return out

    def graph(self) -> dict[str, Any]:
        span = traces.begin("macro_relationship_graph", meta={"source": "api"})
        g = build_graph()
        traces.end(span, output={"nodes": g["n_nodes"], "edges": g["n_edges"]})
        return g

    def dashboard(self) -> dict[str, Any]:
        cov = STORE.coverage()
        rows = STORE.list_all(limit=200)
        recent = sorted(rows, key=lambda r: r.published_at or r.created_at, reverse=True)[:15]
        high = [r for r in rows if r.confidence_label == "High"]
        stale = [r for r in rows if r.stale]
        return {
            "board": "Macro Relationship Intelligence",
            "programme": PROGRAMME,
            "version": MRI_VERSION,
            "principles": {
                "evidence_backed_only": True,
                "versioned_graph": True,
                "no_hardcoded_rules_without_history": True,
                "ask_never_fetches": True,
                "providers_queried_always_empty": True,
            },
            "does_not": list(NO_MRI_ACTIONS),
            "total_relationships": cov.get("total_relationships"),
            "relationship_confidence_distribution": cov.get("confidence_distribution"),
            "recently_validated_relationships": [r.to_public_dict() for r in recent],
            "newly_discovered_relationships": STORE.recent_discoveries(20),
            "stale_relationships": [r.to_public_dict() for r in stale[:20]],
            "coverage_by_indicator_sector_company": {
                "indicators": cov.get("indicators_covered"),
                "sectors": cov.get("sectors_covered"),
                "companies": cov.get("companies_covered"),
                "by_kind": cov.get("by_kind"),
            },
            "high_confidence": len(high),
            "recent_runs": STORE.recent_runs(10),
            "retrieval_performance": {"traces": traces.recent(80)},
            "ingestion_idle": cov.get("total_relationships", 0) == 0,
            "phase": "10.3",
            "note": "Read APIs never rebuild the graph. Use POST /v1/macro/relationships/run.",
        }
