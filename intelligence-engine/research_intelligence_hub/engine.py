"""Research Intelligence Hub engine — every note is an Intelligence Object."""

from __future__ import annotations

from typing import Any

from research_intelligence_hub import traces
from research_intelligence_hub.catalog import get_seed, list_seeds
from research_intelligence_hub.extractors import (
    build_executive_summary,
    extract_companies,
    extract_global,
    extract_historical_context,
    extract_ipo,
    extract_macro,
    extract_markets,
    extract_sectors,
    infer_session,
)
from research_intelligence_hub.links import (
    enrich_market_links,
    soft_analogues,
    soft_evidence,
    soft_forecast,
    soft_market_tip,
    soft_relationships,
)
from research_intelligence_hub.schema import (
    LINK_DOMAINS,
    NO_RIH_ACTIONS,
    PRIMARY_PRINCIPLE,
    PROGRAMME,
    PROGRAMME_SHORT,
    RIH_VERSION,
    AnalogueLink,
    EntityLink,
    EvidenceItem,
    HubGraph,
    RelationshipLink,
    ResearchObject,
)
from research_intelligence_hub.store import STORE


class ResearchIntelligenceHubEngine:
    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "ok": True,
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": RIH_VERSION,
            "principle": PRIMARY_PRINCIPLE,
            "does_not": list(NO_RIH_ACTIONS),
            "ask_triggers_collection": False,
            "providers_queried_always": [],
            "primary_knowledge_object": "ResearchObject",
            "is_document": False,
            "is_intelligence_hub": True,
            "link_domains": list(LINK_DOMAINS),
            "consumes": [
                "Company Intelligence",
                "Sector Intelligence",
                "Market Intelligence (CMKTP/HMKIP/MKRI/HMKAI/MKFI)",
                "Macro Intelligence (MFI)",
                "IPO Intelligence",
                "Global Intelligence",
                "Relationship Intelligence",
                "Analogue Intelligence",
                "Evidence / Validation",
            ],
            "feeds": ["UI Article", "Investment Office", "Ask AGI", "Mission Control"],
            "phase": "4.0",
            "langsmith_traces": list(traces.TRACE_NAMES),
            "design_principle": PRIMARY_PRINCIPLE,
        }

    def run(self, *, note_id: str | None = None) -> dict[str, Any]:
        """Ops publish — build hubs for catalog seeds (or one note). Never Ask."""
        seeds = [get_seed(note_id)] if note_id else list_seeds()
        seeds = [s for s in seeds if s]
        published = 0
        per: dict[str, Any] = {}
        for seed in seeds:
            hub = self.build(
                note_id=seed["id"],
                headline=seed["headline"],
                body=seed.get("body") or "",
                publication_date=seed.get("publication_date"),
                session=seed.get("session"),
                tickers=seed.get("tickers") or [],
                importance_score=int(seed.get("importance_score") or 50),
                persist=True,
            )
            published += 1
            per[hub.id] = {
                "version": hub.version,
                "companies": len(hub.companies),
                "sectors": len(hub.sectors),
                "relationships": len(hub.relationships),
                "analogues": len(hub.historical_analogues),
                "importance_score": hub.importance_score,
            }
        summary = {
            "ok": True,
            "published": published,
            "per_hub": per,
            "ask_triggered": False,
            "providers_queried": [],
            "programme_short": PROGRAMME_SHORT,
        }
        STORE.record_run(summary)
        return summary

    def build(
        self,
        *,
        note_id: str | None = None,
        headline: str,
        body: str = "",
        publication_date: str | None = None,
        session: str | None = None,
        tickers: list[str] | None = None,
        importance_score: int = 50,
        persist: bool = False,
    ) -> ResearchObject:
        nid = note_id or f"rih_{abs(hash(headline)) % 10**10:x}"
        ispan = traces.begin("research_hub_ingest", meta={"note_id": nid, "headline": headline[:80]})
        traces.end(ispan, output={"note_id": nid, "body_chars": len(body or "")})

        espan = traces.begin("research_entity_extraction", meta={"note_id": nid})
        companies_raw = extract_companies(headline, body, hinted=tickers)
        sectors_raw = extract_sectors(headline, body, companies_raw)
        markets_raw = extract_markets(headline, body)
        macro_raw = extract_macro(headline, body)
        global_raw = extract_global(headline, body)
        ipo_raw = extract_ipo(headline, body)
        hist_raw = extract_historical_context(headline, body)
        session_label = infer_session(headline, body, session=session)
        summary_pack = build_executive_summary(headline, body, companies_raw, sectors_raw)
        traces.end(
            espan,
            output={
                "companies": len(companies_raw),
                "sectors": len(sectors_raw),
                "macro": len(macro_raw),
                "markets": len(markets_raw),
            },
        )

        lspan = traces.begin("research_link_assembly", meta={"note_id": nid})
        sources: list[str] = ["RIH_extractors"]
        market_tip = soft_market_tip()
        if market_tip.get("inherited"):
            sources.append("CMKTP")
        markets_raw = enrich_market_links(markets_raw, market_tip)
        traces.end(lspan, output={"market_inherited": bool(market_tip.get("inherited"))})

        rspan = traces.begin("research_relationship_retrieval", meta={"note_id": nid})
        relationships = soft_relationships(
            [s["label"] for s in sectors_raw],
            [m["label"] for m in macro_raw],
        )
        if relationships:
            sources.append("MKRI" if any(r.gateway == "MKRI_KRIG" for r in relationships) else "MKRI_catalog")
        traces.end(rspan, output={"n": len(relationships)})

        aspan = traces.begin("research_analogue_retrieval", meta={"note_id": nid})
        analogues = soft_analogues("India")
        if analogues:
            sources.append(
                "HMKAI" if any(a.gateway == "HMKAI_KRIG" for a in analogues) else "HMKAI_catalog"
            )
        traces.end(aspan, output={"n": len(analogues)})

        fspan = traces.begin("research_forecast_attachment", meta={"note_id": nid})
        primary_sector = next(
            (s["label"] for s in sectors_raw if s.get("role") in {"primary", "beneficiary"}),
            None,
        )
        if primary_sector == "Market-wide":
            primary_sector = None
        forecast = soft_forecast(primary_sector=primary_sector)
        sources.extend(forecast.gateways)
        traces.end(
            fspan,
            output={
                "scenarios": len(forecast.scenarios),
                "distribution": forecast.probability_distribution,
            },
        )

        evspan = traces.begin("research_evidence_attachment", meta={"note_id": nid})
        evidence_rows = soft_evidence(
            companies=[c["id"] for c in companies_raw],
            sectors=[s["label"] for s in sectors_raw],
            macro=[m["label"] for m in macro_raw],
            sources=sources,
        )
        traces.end(evspan, output={"n": len(evidence_rows)})

        related = self._related_research(nid, [c["id"] for c in companies_raw], [s["label"] for s in sectors_raw])

        confidence = self._score_confidence(
            companies=companies_raw,
            relationships=relationships,
            analogues=analogues,
            forecast=forecast,
            evidence=evidence_rows,
            sources=sources,
        )

        hub = ResearchObject(
            id=nid,
            headline=headline,
            publication_date=publication_date,
            session=session_label,  # type: ignore[arg-type]
            body=body,
            executive_summary=summary_pack["executive_summary"],
            investment_thesis=summary_pack["investment_thesis"],
            key_conclusions=summary_pack["key_conclusions"],
            why_it_matters=summary_pack["why_it_matters"],
            companies=[EntityLink.model_validate(c) for c in companies_raw],
            sectors=[EntityLink.model_validate(s) for s in sectors_raw],
            markets=[EntityLink.model_validate(m) for m in markets_raw],
            macro_topics=[EntityLink.model_validate(m) for m in macro_raw],
            ipo_links=[EntityLink.model_validate(m) for m in ipo_raw],
            global_topics=[EntityLink.model_validate(m) for m in global_raw],
            historical_context=[EntityLink.model_validate(m) for m in hist_raw],
            relationships=relationships,
            historical_analogues=analogues,
            forecast=forecast,
            supporting_evidence=[EvidenceItem.model_validate(e) for e in evidence_rows],
            related_research=related,
            confidence=confidence,
            importance_score=importance_score,
            freshness={
                "dynamic_retrieval": True,
                "note_stores_references_only": True,
                "underlying_platforms_refresh_independently": True,
            },
            sources=list(dict.fromkeys(sources)),
            providers_queried=[],
            provenance={
                "extractors": "deterministic_lexicon",
                "soft_gateways": forecast.gateways,
                "market_tip": bool(market_tip.get("inherited")),
            },
        )

        if persist:
            pspan = traces.begin("research_hub_publication", meta={"note_id": nid})
            published = STORE.publish(hub)
            traces.end(
                pspan,
                output={"note_id": published.id, "version": published.version},
            )
            return published
        return hub

    def hub(self, note_id: str, *, persist_if_missing: bool = False) -> dict[str, Any]:
        latest = STORE.latest(note_id)
        if latest:
            return {**latest.to_public_dict(), "mode": "published", "gateway": "RIH_KRIG"}
        seed = get_seed(note_id)
        if seed:
            hub = self.build(
                note_id=seed["id"],
                headline=seed["headline"],
                body=seed.get("body") or "",
                publication_date=seed.get("publication_date"),
                session=seed.get("session"),
                tickers=seed.get("tickers") or [],
                importance_score=int(seed.get("importance_score") or 50),
                persist=persist_if_missing,
            )
            return {
                **hub.to_public_dict(),
                "mode": "published" if persist_if_missing else "computed",
                "gateway": "RIH_KRIG",
            }
        # Build from bare id as headline fallback
        hub = self.build(
            note_id=note_id,
            headline=note_id.replace("_", " ").replace("-", " ").title(),
            body="",
            persist=False,
        )
        return {**hub.to_public_dict(), "mode": "computed", "gateway": "RIH_KRIG"}

    def list_hubs(self, *, limit: int = 50) -> dict[str, Any]:
        rows = STORE.list_hubs(limit=limit)
        if not rows:
            # Soft compute catalog tips without forcing publish
            rows = []
            for seed in list_seeds()[:limit]:
                rows.append(
                    self.build(
                        note_id=seed["id"],
                        headline=seed["headline"],
                        body=seed.get("body") or "",
                        publication_date=seed.get("publication_date"),
                        session=seed.get("session"),
                        tickers=seed.get("tickers") or [],
                        importance_score=int(seed.get("importance_score") or 50),
                        persist=False,
                    )
                )
        return {
            "n": len(rows),
            "hubs": [
                {
                    "id": h.id,
                    "headline": h.headline,
                    "session": h.session,
                    "publication_date": h.publication_date,
                    "importance_score": h.importance_score,
                    "companies": [c.id for c in h.companies[:6]],
                    "sectors": [s.label for s in h.sectors[:4]],
                    "probability_distribution": h.forecast.probability_distribution,
                    "confidence_pct": (h.confidence or {}).get("overall_pct"),
                    "version": h.version,
                    "published": h.published,
                }
                for h in rows
            ],
            "providers_queried": [],
            "gateway": "RIH_KRIG",
            "primary_knowledge_object": "ResearchObject",
        }

    def graph(self, note_id: str) -> dict[str, Any]:
        pack = self.hub(note_id)
        nodes = [
            {
                "id": pack["id"],
                "label": pack["headline"],
                "kind": "research_note",
                "root": True,
            }
        ]
        edges: list[dict[str, Any]] = []
        for domain, kind in (
            ("companies", "company"),
            ("sectors", "sector"),
            ("markets", "market"),
            ("macro_topics", "macro"),
            ("ipo_links", "ipo"),
            ("global_topics", "global"),
            ("historical_context", "historical_event"),
        ):
            for item in pack.get(domain) or []:
                nid = f"{kind}:{item.get('id')}"
                nodes.append(
                    {
                        "id": nid,
                        "label": item.get("label"),
                        "kind": kind,
                        "href": item.get("href"),
                        "gateway": item.get("gateway"),
                    }
                )
                edges.append(
                    {
                        "source": pack["id"],
                        "target": nid,
                        "type": f"LINKS_{kind.upper()}",
                        "role": item.get("role"),
                    }
                )
        for rel in pack.get("relationships") or []:
            edges.append(
                {
                    "source": rel.get("source"),
                    "target": rel.get("target"),
                    "type": rel.get("relationship"),
                    "confidence_pct": rel.get("confidence_pct"),
                }
            )
        g = HubGraph(
            note_id=pack["id"],
            headline=pack["headline"],
            nodes=nodes,
            edges=edges,
            providers_queried=[],
        )
        return g.model_dump(mode="json")

    def history(self, note_id: str, *, limit: int = 20) -> dict[str, Any]:
        rows = STORE.history(note_id, limit=limit)
        return {
            "note_id": note_id,
            "n": len(rows),
            "versions": [
                {
                    "id": r.id,
                    "version": r.version,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "importance_score": r.importance_score,
                    "confidence_pct": (r.confidence or {}).get("overall_pct"),
                }
                for r in rows
            ],
            "providers_queried": [],
            "gateway": "RIH_KRIG",
        }

    def dashboard(self) -> dict[str, Any]:
        if STORE.coverage()["total_hubs"] == 0:
            self.run()
        hubs = STORE.list_hubs(limit=20)
        latest = hubs[0] if hubs else None
        pub = latest.to_public_dict() if latest else {}
        return {
            "board": "Research Intelligence Hub",
            "programme": PROGRAMME,
            "programme_short": PROGRAMME_SHORT,
            "version": RIH_VERSION,
            "principles": {
                "research_is_primary_knowledge_object": True,
                "note_is_intelligence_hub": True,
                "not_a_static_document": True,
                "dynamic_retrieval": True,
                "agi_owned_knowledge_only": True,
                "ask_never_fetches": True,
                "every_insight_traceable": True,
            },
            "does_not": list(NO_RIH_ACTIONS),
            "design_principle": PRIMARY_PRINCIPLE,
            "current_hub": {
                "id": pub.get("id"),
                "headline": pub.get("headline"),
                "session": pub.get("session"),
                "importance_score": pub.get("importance_score"),
            },
            "hub_count": STORE.coverage()["total_hubs"],
            "link_coverage": {
                "companies": len(pub.get("companies") or []),
                "sectors": len(pub.get("sectors") or []),
                "markets": len(pub.get("markets") or []),
                "macro_topics": len(pub.get("macro_topics") or []),
                "relationships": len(pub.get("relationships") or []),
                "analogues": len(pub.get("historical_analogues") or []),
                "evidence": len(pub.get("supporting_evidence") or []),
            },
            "forecast_attachment": pub.get("forecast"),
            "navigation": pub.get("navigation"),
            "hubs": self.list_hubs(limit=20).get("hubs"),
            "coverage": STORE.coverage(),
            "retrieval_performance": {"traces": traces.recent(40)},
            "langsmith_traces": list(traces.TRACE_NAMES),
            "recent_runs": STORE.recent_runs(10),
            "ingestion_idle": STORE.coverage()["total_hubs"] == 0,
            "phase": "4.0",
            "providers_queried": [],
        }

    def _related_research(
        self, note_id: str, companies: list[str], sectors: list[str]
    ) -> list[EntityLink]:
        out: list[EntityLink] = []
        for seed in list_seeds():
            if seed["id"] == note_id:
                continue
            overlap = set(seed.get("tickers") or []) & set(companies)
            sector_hit = any(s.lower() in seed["body"].lower() for s in sectors[:3])
            if overlap or sector_hit:
                out.append(
                    EntityLink(
                        id=seed["id"],
                        label=seed["headline"],
                        kind="research_note",
                        role="related",
                        href=f"/research/hub/{seed['id']}",
                        gateway="RIH_KRIG",
                        meta={"shared_companies": list(overlap)},
                    )
                )
        return out[:6]

    def _score_confidence(
        self,
        *,
        companies: list[dict[str, Any]],
        relationships: list[RelationshipLink],
        analogues: list[AnalogueLink],
        forecast: Any,
        evidence: list[dict[str, Any]],
        sources: list[str],
    ) -> dict[str, Any]:
        entity_cov = min(95, 40 + len(companies) * 6 + len(relationships) * 3)
        analogue_str = 0
        if analogues:
            analogue_str = int(min(95, max(a.similarity_score for a in analogues)))
        forecast_q = 80 if forecast.scenarios else 40
        evidence_q = min(95, 45 + len(evidence) * 8)
        source_q = min(95, 50 + len(sources) * 5)
        overall = int(
            round(
                0.25 * entity_cov
                + 0.20 * analogue_str
                + 0.20 * forecast_q
                + 0.20 * evidence_q
                + 0.15 * source_q
            )
        )
        overall = max(45, min(95, overall))
        return {
            "overall_pct": overall,
            "entity_coverage_pct": entity_cov,
            "analogue_strength_pct": analogue_str,
            "forecast_attachment_pct": forecast_q,
            "evidence_traceability_pct": evidence_q,
            "source_breadth_pct": source_q,
            "label": "High" if overall >= 80 else ("Medium" if overall >= 60 else "Low"),
            "note": "Confidence scores hub completeness — not a price prediction.",
        }
