"""Knowledge Retrieval Gateway — assemble Knowledge Bundles for the Intelligence Engine."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from app.contracts.iko import company_knowledge_view
from app.contracts.models import Source
from app.krig.bundle import KnowledgeBundle, empty_section_flags
from app.kce.engine import KnowledgeConfidenceEngine
from app.kfe.engine import KnowledgeFreshnessEngine
from app.krig.historical_bridge import HistoricalKnowledgeBridge
from app.krig.policies import BundleSection, QueryType, policy_for
from app.krig.query import KnowledgeQuery, classify_query
from app.storage.db import KaipStore

logger = logging.getLogger("kaip.krig")

# Seed macro tips for Sprint 6.4 (collectors not required)
DEFAULT_MACRO: dict[str, Any] = {
    "market_key": "india_equity",
    "theme": "Monetary Policy",
    "rbi": {
        "stance": "Easing bias",
        "latest_action": "Rate cut",
        "policy_rate": None,
        "summary": "RBI rate-cut cycle supporting banks, autos and housing demand.",
    },
    "inflation": {"summary": "Disinflation supportive of further easing optionality."},
    "gdp": {"summary": "Domestic demand resilient; credit growth remains a watchpoint."},
    "policy": {"summary": "Lower rates historically benefit Financials, Autos and Real Estate."},
    "historical_cycles": [
        {
            "theme": "RBI Cut Cycle",
            "beneficiaries": ["Banks", "Autos", "Housing"],
            "historical_confidence": "High",
        }
    ],
}


class KnowledgeRetrievalGateway:
    def __init__(self, store: KaipStore, *, hip_base_url: str | None = None) -> None:
        self.store = store
        self.freshness = KnowledgeFreshnessEngine()
        self.confidence = KnowledgeConfidenceEngine()
        self.historical = HistoricalKnowledgeBridge(hip_base_url)

    def retrieve(
        self,
        *,
        question: str | None = None,
        symbols: list[str] | None = None,
        sector_key: str | None = None,
        query_type: str | None = None,
        use_cache: bool = True,
    ) -> KnowledgeBundle:
        t0 = time.perf_counter()
        kq = classify_query(
            question=question,
            symbols=symbols,
            sector_key=sector_key,
            query_type=query_type,
        )
        policy = policy_for(kq.query_type)
        cache_key = self._cache_key(kq, policy.cache_ttl_seconds)

        if use_cache:
            cached = self.store.get_bundle_cache(cache_key)
            if cached:
                bundle = KnowledgeBundle.model_validate(cached)
                bundle.cache = {"hit": True, "ttl_seconds": policy.cache_ttl_seconds, "key": cache_key}
                self._log(kq, bundle, cache_hit=True, latency_ms=(time.perf_counter() - t0) * 1000)
                return bundle

        if kq.query_type == QueryType.COMPARE:
            bundle = self._assemble_compare(kq, policy.sections)
        elif kq.query_type == QueryType.SECTOR:
            bundle = self._assemble_sector(kq, policy.sections)
        elif kq.query_type in {QueryType.MACRO, QueryType.MARKET}:
            bundle = self._assemble_macro_market(kq, policy.sections)
        else:
            symbol = (kq.symbols[0] if kq.symbols else None) or "INFY"
            bundle = self._assemble_company(symbol, kq, policy.sections)

        bundle.cache = {"hit": False, "ttl_seconds": policy.cache_ttl_seconds, "key": cache_key}
        self.store.put_bundle_cache(cache_key, bundle.to_public_dict(), ttl_seconds=policy.cache_ttl_seconds)
        self._log(kq, bundle, cache_hit=False, latency_ms=(time.perf_counter() - t0) * 1000)
        return bundle

    def company_bundle(self, symbol: str, *, question: str | None = None) -> KnowledgeBundle:
        return self.retrieve(symbols=[symbol], query_type="company", question=question)

    def compare_bundle(self, symbols: list[str], *, question: str | None = None) -> KnowledgeBundle:
        return self.retrieve(symbols=symbols, query_type="compare", question=question)

    def sector_bundle(self, sector_key: str, *, question: str | None = None) -> KnowledgeBundle:
        return self.retrieve(sector_key=sector_key, query_type="sector", question=question)

    def macro_bundle(self, *, question: str | None = None) -> KnowledgeBundle:
        return self.retrieve(query_type="macro", question=question)

    # ----- assemblers -----

    def _assemble_company(
        self,
        symbol: str,
        kq: KnowledgeQuery,
        sections: tuple[BundleSection, ...],
    ) -> KnowledgeBundle:
        symbol = symbol.upper()
        flags = empty_section_flags(sections)
        freshness: dict[str, Any] = {}
        bundle = KnowledgeBundle(
            query_type=kq.query_type,
            subjects=[symbol],
            question=kq.question,
            sections_present=flags,
        )

        profile = self.store.get_company_profile(symbol)
        if BundleSection.COMPANY in sections and profile:
            meta = profile.get("metadata") or {}
            source = Source(meta["source"]) if meta.get("source") in {s.value for s in Source} else Source.DERIVED
            view = company_knowledge_view(profile["knowledge"], source=source, version=int(profile["version"]))
            bundle.company = {
                **profile,
                "company_knowledge": view.get("CompanyKnowledge"),
            }
            flags[BundleSection.COMPANY.value] = True
            freshness["company"] = self.freshness.section_report(
                BundleSection.COMPANY, updated_at=profile.get("updated_at"), present=True
            )
            # Valuation facet from company knowledge
            val = (profile.get("knowledge") or {}).get("valuation") or {}
            if BundleSection.VALUATION in sections and val:
                market = self.store.get_latest_market(symbol)
                bundle.valuation = {
                    **val,
                    "market_snapshot": (market or {}).get("knowledge") or (market or {}).get("payload"),
                }
                flags[BundleSection.VALUATION.value] = True
                freshness["valuation"] = self.freshness.section_report(
                    BundleSection.VALUATION,
                    updated_at=(market or {}).get("updated_at") or profile.get("updated_at"),
                    present=True,
                )
        else:
            freshness["company"] = self.freshness.section_report(
                BundleSection.COMPANY, updated_at=None, present=False
            )

        if BundleSection.FINANCIALS in sections:
            fins = self.store.list_financials(symbol)
            bundle.financials = fins
            flags[BundleSection.FINANCIALS.value] = bool(fins)
            updated = fins[0].get("updated_at") if fins else None
            freshness["financials"] = self.freshness.section_report(
                BundleSection.FINANCIALS, updated_at=updated, present=bool(fins)
            )

        if BundleSection.CORPORATE_EVENTS in sections:
            events = self.store.list_events(symbol)
            bundle.corporate_events = events
            flags[BundleSection.CORPORATE_EVENTS.value] = bool(events)
            updated = events[0].get("updated_at") if events else None
            freshness["corporate_events"] = self.freshness.section_report(
                BundleSection.CORPORATE_EVENTS, updated_at=updated, present=bool(events)
            )

        entity = self.store.get_entity(symbol)
        sector_key = (entity.sector_key if entity else None) or (
            (profile or {}).get("entity_refs") or {}
        ).get("sector_key")
        if isinstance(sector_key, str):
            pass
        elif entity and entity.sector:
            sector_key = entity.sector.lower().replace(" ", "_")

        if BundleSection.SECTOR in sections and sector_key:
            sector = self.store.get_sector_knowledge(sector_key)
            sector_learning = self.store.list_sector_learning(sector_key, limit=10)
            if sector or sector_learning:
                bundle.sector = {
                    **(sector or {"sector_key": sector_key}),
                    "sector_learning": sector_learning,
                    "leaders": (sector or {}).get("knowledge", {}).get("leaders") if sector else [],
                }
                flags[BundleSection.SECTOR.value] = True
                freshness["sector"] = self.freshness.section_report(
                    BundleSection.SECTOR,
                    updated_at=(sector or {}).get("updated_at"),
                    present=True,
                )

        if BundleSection.MARKET in sections or BundleSection.MACRO in sections:
            market = self.store.get_market_knowledge("india_equity")
            macro = self._macro_view(question=kq.question)
            if BundleSection.MARKET in sections:
                bundle.market = market or {"market_key": "india_equity", "derived": True}
                flags[BundleSection.MARKET.value] = True
                freshness["market"] = self.freshness.section_report(
                    BundleSection.MARKET,
                    updated_at=(market or {}).get("updated_at"),
                    present=bool(market),
                )
            if BundleSection.MACRO in sections:
                bundle.macro = macro
                flags[BundleSection.MACRO.value] = True
                freshness["macro"] = self.freshness.section_report(
                    BundleSection.MACRO, updated_at=macro.get("as_of"), present=True
                )

        if BundleSection.LEARNING in sections:
            learning = self.store.list_learning(symbol, limit=25)
            bundle.learning = learning
            flags[BundleSection.LEARNING.value] = bool(learning)

        if BundleSection.MEMORY in sections:
            memory = self.store.list_memory(symbol, limit=25)
            bundle.memory = memory
            flags[BundleSection.MEMORY.value] = bool(memory)

        if BundleSection.TIMELINE in sections:
            timeline = self.store.list_timeline(symbol, limit=50)
            # Sprint 8.2 — prefer HIP narrative timeline when Historical Intelligence is configured
            hip_timeline = self.historical.fetch_timeline(symbol) if self.historical.enabled else []
            if hip_timeline:
                timeline = hip_timeline
                bundle.provenance = {
                    **bundle.provenance,
                    "historical_source": "hip_hko",
                    "providers_hidden": True,
                }
            bundle.timeline = timeline
            flags[BundleSection.TIMELINE.value] = bool(timeline)

        # Sprint 8.4 — historical analogues for "have we seen this before?" questions
        if self.historical.enabled and BundleSection.LEARNING in sections:
            q = (kq.question or "").lower()
            if any(tok in q for tok in ("before", "similar", "analogue", "analog", "slowdown", "ever seen")):
                analogues = self.historical.search_analogues(
                    scope="company",
                    entity=symbol,
                    question=kq.question,
                    top_k=5,
                )
                if analogues and analogues.get("analogues"):
                    bundle.learning = list(bundle.learning or []) + [
                        {
                            "kind": "historical_analogue",
                            "source": "hip_hai",
                            "analogues": analogues.get("analogues"),
                            "bundle": analogues.get("bundle"),
                        }
                    ]
                    flags[BundleSection.LEARNING.value] = True
                    bundle.provenance = {
                        **bundle.provenance,
                        "historical_analogues": "hip_hai",
                        "providers_hidden": True,
                    }

        if BundleSection.CONFLICTS in sections:
            conflicts = self.store.list_conflicts(symbol, limit=25)
            bundle.conflicts = conflicts
            flags[BundleSection.CONFLICTS.value] = bool(conflicts)

        if BundleSection.RELATIONSHIPS in sections:
            edges = self.store.list_relationships("Company", symbol)
            # Sprint 8.3 — prefer HIP Historical Relationship Intelligence when configured
            if self.historical.enabled:
                hip_edges = self.historical.fetch_company_relationships(symbol)
                q = (kq.question or "").lower()
                if any(tok in q for tok in ("rbi", "rate cut", "historically affected", "crude")):
                    # Macro→company explain path for cause-and-effect questions
                    source = "RBI Rate Cut" if "rbi" in q or "rate" in q else ("Higher Crude Oil" if "crude" in q else "RBI Rate Cut")
                    explained = self.historical.explain_relationship(source=source, target=symbol)
                    if explained and explained.get("relationships"):
                        hip_edges = list(explained.get("relationships") or []) + list(hip_edges or [])
                        bundle.provenance = {
                            **bundle.provenance,
                            "historical_relationships": "hip_hri",
                            "providers_hidden": True,
                        }
                if hip_edges:
                    edges = hip_edges
                    bundle.provenance = {
                        **bundle.provenance,
                        "historical_relationships": "hip_hri",
                        "providers_hidden": True,
                    }
            bundle.relationships = edges
            flags[BundleSection.RELATIONSHIPS.value] = bool(edges)

        if BundleSection.MONITORING in sections:
            monitoring = self._monitoring_tips(symbol, bundle)
            bundle.monitoring = monitoring
            flags[BundleSection.MONITORING.value] = bool(monitoring)

        if BundleSection.EVIDENCE in sections:
            evidence = self._evidence_links(symbol, bundle)
            bundle.evidence = evidence
            flags[BundleSection.EVIDENCE.value] = bool(evidence)

        bundle.sections_present = flags
        bundle.freshness = freshness
        bundle.confidence = self._confidence_summary(symbol, profile, bundle)
        if profile and profile.get("updated_at"):
            bundle.provenance = {
                **bundle.provenance,
                "current_as_of": (freshness.get("company") or {}).get("current_as_of"),
                "operate": {"kfe": True, "kce": True},
            }
        self._register_dependencies(symbol, sector_key)
        return bundle

    def _assemble_compare(
        self,
        kq: KnowledgeQuery,
        sections: tuple[BundleSection, ...],
    ) -> KnowledgeBundle:
        symbols = [s.upper() for s in kq.symbols[:4]]
        companies: dict[str, Any] = {}
        shared_sector = None
        all_learning: list[dict[str, Any]] = []
        all_events: list[dict[str, Any]] = []
        valuations: dict[str, Any] = {}

        for symbol in symbols:
            child = self._assemble_company(
                symbol,
                KnowledgeQuery(query_type=QueryType.COMPANY, question=kq.question, symbols=[symbol]),
                sections,
            )
            companies[symbol] = {
                "company": child.company,
                "financials": child.financials,
                "valuation": child.valuation,
                "corporate_events": child.corporate_events,
                "learning": child.learning,
                "memory": child.memory,
                "timeline": child.timeline,
                "relationships": child.relationships,
                "freshness": child.freshness,
                "checklist": child.checklist(),
            }
            if child.sector and shared_sector is None:
                shared_sector = child.sector
            all_learning.extend(child.learning or [])
            all_events.extend(
                [{**e, "company_symbol": symbol} for e in (child.corporate_events or [])]
            )
            if child.valuation:
                valuations[symbol] = child.valuation

        macro = self._macro_view(question=kq.question)
        bundle = KnowledgeBundle(
            query_type=QueryType.COMPARE,
            subjects=symbols,
            question=kq.question,
            companies=companies,
            sector=shared_sector,
            macro=macro,
            market=self.store.get_market_knowledge("india_equity") or {"market_key": "india_equity"},
            learning=all_learning[:50],
            corporate_events=all_events[:50],
            valuation={"by_company": valuations},
            comparison={
                "symbols": symbols,
                "shared_sector": (shared_sector or {}).get("sector_key")
                or (shared_sector or {}).get("knowledge", {}).get("sector_key"),
                "shared_macro": True,
                "dimensions": ["Financials", "Valuation", "Learning", "Sector", "Macro"],
            },
            evidence=self._compare_evidence(symbols, shared_sector, macro),
            monitoring=[
                {"type": "compare", "symbols": symbols, "note": "Watch relative valuation and sector beta."}
            ],
            freshness={"macro": self.freshness.section_report(BundleSection.MACRO, updated_at=macro.get("as_of"), present=True)},
            sections_present={s.value: True for s in sections},
        )
        return bundle

    def _assemble_sector(
        self,
        kq: KnowledgeQuery,
        sections: tuple[BundleSection, ...],
    ) -> KnowledgeBundle:
        sector_key = kq.sector_key or "technology"
        sector = self.store.get_sector_knowledge(sector_key)
        learning = self.store.list_sector_learning(sector_key, limit=20)
        market_learning = self.store.list_market_learning(limit=20)
        knowledge = (sector or {}).get("knowledge") or {}
        bundle = KnowledgeBundle(
            query_type=QueryType.SECTOR,
            subjects=[sector_key],
            question=kq.question,
            sector={
                **(sector or {"sector_key": sector_key}),
                "leaders": knowledge.get("leaders") or [],
                "risks": knowledge.get("risks") or [],
                "sector_valuation": knowledge.get("sector_valuation") or {},
                "growth": knowledge.get("industry_trends") or [],
                "sector_learning": learning,
            },
            learning=learning,
            market={"market_learning": market_learning},
            macro=self._macro_view(question=kq.question),
            evidence=[
                {"type": "sector", "sector_key": sector_key, "ref": f"sector:{sector_key}"},
            ],
            freshness={
                "sector": self.freshness.section_report(
                    BundleSection.SECTOR,
                    updated_at=(sector or {}).get("updated_at"),
                    present=bool(sector),
                )
            },
        )
        return bundle

    def _assemble_macro_market(
        self,
        kq: KnowledgeQuery,
        sections: tuple[BundleSection, ...],
    ) -> KnowledgeBundle:
        macro = self._macro_view(question=kq.question)
        market = self.store.get_market_knowledge(kq.market_key) or {
            "market_key": kq.market_key,
            "market_regime": macro.get("rbi", {}).get("stance"),
        }
        market_learning = self.store.list_market_learning(limit=20)
        return KnowledgeBundle(
            query_type=kq.query_type,
            subjects=[kq.market_key],
            question=kq.question,
            macro=macro,
            market={**(market if isinstance(market, dict) else {}), "market_learning": market_learning},
            learning=market_learning,
            evidence=[
                {"type": "macro", "theme": "RBI Cut Cycle", "ref": "macro:india_equity:rbi"},
                {"type": "cycle", "theme": "Lower Rates", "ref": "macro:india_equity:rates"},
            ],
            freshness={
                "macro": self.freshness.section_report(
                    BundleSection.MACRO, updated_at=macro.get("as_of"), present=True
                ),
                "market": self.freshness.section_report(
                    BundleSection.MARKET,
                    updated_at=market.get("updated_at") if isinstance(market, dict) else None,
                    present=True,
                ),
            },
        )

    def _macro_view(self, *, question: str | None = None) -> dict[str, Any]:
        stored = self.store.get_market_knowledge("india_equity")
        base = dict(DEFAULT_MACRO)
        base["as_of"] = (stored or {}).get("updated_at")
        if question and "rbi" in question.lower():
            base["focus"] = "RBI policy"
        # Merge market learning themes
        themes = self.store.list_market_learning(limit=10)
        if themes:
            base["market_learning"] = themes
        return base

    def _monitoring_tips(self, symbol: str, bundle: KnowledgeBundle) -> list[dict[str, Any]]:
        tips: list[dict[str, Any]] = []
        if bundle.learning:
            tips.append(
                {
                    "type": "learning",
                    "company_symbol": symbol,
                    "note": "Material learning events present — monitor thesis drift.",
                    "count": len(bundle.learning),
                }
            )
        if bundle.conflicts:
            tips.append(
                {
                    "type": "conflict",
                    "company_symbol": symbol,
                    "note": "Knowledge conflicts need review.",
                    "count": len(bundle.conflicts),
                }
            )
        stale = [k for k, v in (bundle.freshness or {}).items() if isinstance(v, dict) and v.get("needs_refresh")]
        if stale:
            tips.append(
                {
                    "type": "freshness",
                    "company_symbol": symbol,
                    "note": "Sections need refresh.",
                    "sections": stale,
                }
            )
        return tips

    def _confidence_summary(
        self,
        symbol: str,
        profile: dict[str, Any] | None,
        bundle: KnowledgeBundle,
    ) -> dict[str, Any]:
        """KCE surface for IE evidence weighting before IEW."""
        objects: dict[str, Any] = {}
        meta = (profile or {}).get("metadata") or {}
        if profile:
            stored = self.store.get_confidence(
                object_type="CompanyProfile", subject_key=symbol.upper()
            )
            if stored:
                objects["company"] = stored
            elif meta.get("confidence_pct") is not None or meta.get("confidence_detail"):
                objects["company"] = meta.get("confidence_detail") or {
                    "confidence_pct": meta.get("confidence_pct"),
                    "label": meta.get("confidence"),
                    "sources": [meta.get("source")],
                }
            else:
                report = self.confidence.score(
                    object_type="CompanyProfile",
                    primary_source=meta.get("source") or "derived",
                    subject_key=symbol.upper(),
                    knowledge=(profile or {}).get("knowledge") or {},
                )
                objects["company"] = report.to_dict()

        if bundle.financials:
            fin_conf = self.store.get_confidence(
                object_type="FinancialStatement", subject_key=symbol.upper()
            )
            if fin_conf:
                objects["financials"] = fin_conf

        pcts = [
            float(v["confidence_pct"])
            for v in objects.values()
            if isinstance(v, dict) and v.get("confidence_pct") is not None
        ]
        overall = round(sum(pcts) / len(pcts), 1) if pcts else None
        return {
            "overall_pct": overall,
            "objects": objects,
            "note": "Confidence reflects source agreement before IE evidence weighting.",
        }

    def _evidence_links(self, symbol: str, bundle: KnowledgeBundle) -> list[dict[str, Any]]:
        links = [
            {"type": "company", "symbol": symbol, "ref": f"company:{symbol}"},
        ]
        if bundle.sector:
            key = bundle.sector.get("sector_key") or (bundle.sector.get("knowledge") or {}).get("sector_key")
            if key:
                links.append({"type": "sector", "sector_key": key, "ref": f"sector:{key}"})
        for le in (bundle.learning or [])[:5]:
            links.append(
                {
                    "type": "learning_event",
                    "learning_id": le.get("learning_id"),
                    "field_name": le.get("field_name"),
                    "ref": f"learning:{le.get('learning_id')}",
                }
            )
        for edge in (bundle.relationships or [])[:8]:
            links.append(
                {
                    "type": "relationship",
                    "edge_type": edge.get("edge_type"),
                    "to": edge.get("to_key"),
                    "ref": f"rel:{symbol}:{edge.get('edge_type')}:{edge.get('to_key')}",
                }
            )
        return links

    def _compare_evidence(self, symbols: list[str], sector, macro) -> list[dict[str, Any]]:
        links = [{"type": "company", "symbol": s, "ref": f"company:{s}"} for s in symbols]
        if sector:
            key = sector.get("sector_key") or (sector.get("knowledge") or {}).get("sector_key")
            if key:
                links.append({"type": "sector", "sector_key": key, "ref": f"sector:{key}"})
        links.append({"type": "macro", "theme": "RBI Cut Cycle", "ref": "macro:india_equity:rbi"})
        return links

    def _register_dependencies(self, symbol: str, sector_key: str | None) -> None:
        deps = [f"company:{symbol}", "market:india_equity"]
        if sector_key:
            deps.append(f"sector:{sector_key}")
        self.store.upsert_knowledge_dependencies(subject=f"bundle:company:{symbol}", depends_on=deps)

    def _cache_key(self, kq: KnowledgeQuery, ttl: int) -> str:
        raw = json.dumps(
            {
                "qt": kq.query_type.value,
                "symbols": kq.symbols,
                "sector": kq.sector_key,
                "market": kq.market_key,
                "q": kq.question,
            },
            sort_keys=True,
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _log(self, kq: KnowledgeQuery, bundle: KnowledgeBundle, *, cache_hit: bool, latency_ms: float) -> None:
        self.store.insert_retrieval_log(
            {
                "query_type": kq.query_type.value,
                "subjects": bundle.subjects,
                "question": kq.question,
                "cache_hit": cache_hit,
                "latency_ms": round(latency_ms, 2),
                "bundle_id": bundle.bundle_id,
                "checklist": bundle.checklist(),
            }
        )
        self.store.increment_retrieval_metric(
            query_type=kq.query_type.value,
            cache_hit=cache_hit,
            latency_ms=latency_ms,
        )
