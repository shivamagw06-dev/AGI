"""CAE assembler — plan → retrieve → rank → package."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from app.cae.config import DEFAULT_TOKEN_BUDGET
from app.cae.models import ContextPackage, QueryPlan, new_id
from app.cae.planner import plan_query
from app.cae.ranking import apply_token_budget, assign_priority, dedupe, score_item
from app.cae.retrieval import CaeRetriever
from app.cae.store import CaeStore


def _cache_key(query: str, ticker: str | None, engines: list[str]) -> str:
    blob = f"{query.strip().lower()}|{ticker or ''}|{','.join(engines)}"
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


class CaeAssembler:
    def __init__(
        self,
        store: CaeStore,
        retriever: CaeRetriever,
        *,
        use_cache: bool = True,
        compress: bool = True,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        aoi: Any | None = None,
        eve: Any | None = None,
    ) -> None:
        self.store = store
        self.retriever = retriever
        self.use_cache = use_cache
        self.compress = compress
        self.token_budget = token_budget
        self.aoi = aoi
        self.eve = eve

    def assemble(self, query: str, *, ticker: str | None = None, use_cache: bool | None = None) -> ContextPackage:
        t0 = time.perf_counter()
        plan = plan_query(query, ticker=ticker, aoi=self.aoi)
        cache_enabled = self.use_cache if use_cache is None else use_cache
        key = _cache_key(query, plan.primary_ticker, plan.engines)
        if cache_enabled:
            cached = self.store.cache_get(key)
            if cached:
                pkg = ContextPackage(
                    package_id=cached.get("package_id") or new_id("ctx"),
                    query=query,
                    query_summary=cached.get("query_summary") or query,
                    plan=cached.get("plan") or plan.to_dict(),
                    entities=list(cached.get("entities") or []),
                    knowledge=list(cached.get("knowledge") or []),
                    evidence=list(cached.get("evidence") or []),
                    investment_intelligence=list(cached.get("investment_intelligence") or []),
                    forecasts=list(cached.get("forecasts") or []),
                    events=list(cached.get("events") or []),
                    risks=list(cached.get("risks") or []),
                    catalysts=list(cached.get("catalysts") or []),
                    macro=list(cached.get("macro") or []),
                    relationships=list(cached.get("relationships") or []),
                    conflicts=list(cached.get("conflicts") or []),
                    confidence_summary=dict(cached.get("confidence_summary") or {}),
                    recommended_reasoning_strategy=cached.get("recommended_reasoning_strategy")
                    or plan.reasoning_strategy,
                    engine_contributions=list(cached.get("engine_contributions") or []),
                    ranking=list(cached.get("ranking") or []),
                    token_usage=dict(cached.get("token_usage") or {}),
                    duplicates_removed=int(cached.get("duplicates_removed") or 0),
                    compression_ratio=float(cached.get("compression_ratio") or 1.0),
                    cache_hit=True,
                    assembly_latency_ms=round((time.perf_counter() - t0) * 1000, 2),
                    explain=list(cached.get("explain") or []),
                    soft_fields=dict(cached.get("soft_fields") or {}),
                )
                self.store.put_package(pkg)
                return pkg

        items, contribs = self.retriever.retrieve(query, plan.engines, limit=8)
        for c in contribs:
            if not c.succeeded and c.error:
                self.store.metrics.retrieval_failures += 1

        for item in items:
            score_item(item, query=query, intents=plan.intents)
            assign_priority(item, intents=plan.intents)

        deduped, removed = dedupe(items)
        kept, usage, compression = apply_token_budget(
            deduped, budget=self.token_budget, compress=self.compress
        )

        package = self._package(query, plan, kept, contribs, removed, usage, compression)
        package.assembly_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        package.cache_hit = False
        self.store.put_package(package)
        if cache_enabled:
            self.store.cache_set(key, package.to_dict())
        return package

    def explain_package(self, package_id: str) -> dict[str, Any]:
        pkg = self.store.get_package(package_id)
        if not pkg:
            raise KeyError(f"Package '{package_id}' not found")
        return {
            "package_id": package_id,
            "query": pkg.query,
            "plan": pkg.plan,
            "explain": pkg.explain,
            "token_usage": pkg.token_usage,
            "ranking": pkg.ranking,
            "engine_contributions": pkg.engine_contributions,
            "duplicates_removed": pkg.duplicates_removed,
            "compression_ratio": pkg.compression_ratio,
            "assembly_latency_ms": pkg.assembly_latency_ms,
            "cache_hit": pkg.cache_hit,
        }

    def _package(
        self,
        query: str,
        plan: QueryPlan,
        items: list,
        contribs: list,
        duplicates_removed: int,
        usage: dict[str, Any],
        compression: float,
    ) -> ContextPackage:
        knowledge, evidence, investment, forecasts, events = [], [], [], [], []
        risks, catalysts, macro, relationships, conflicts = [], [], [], [], []
        explain = []
        ranking = []

        for item in items:
            row = item.to_dict()
            ranking.append(
                {
                    "item_id": item.item_id,
                    "engine": item.engine,
                    "kind": item.kind,
                    "title": item.title,
                    "priority": item.priority,
                    "ranking_score": item.ranking_score,
                    "confidence": item.confidence,
                }
            )
            explain.append(
                {
                    "item_id": item.item_id,
                    "why_included": item.why_included,
                    "source_engine": item.engine,
                    "confidence": item.confidence,
                    "priority": item.priority,
                    "token_usage": item.token_estimate,
                    "version": item.version,
                    "timestamp": item.timestamp,
                    "ranking_score": item.ranking_score,
                    "retrieval_latency_ms": item.retrieval_latency_ms,
                }
            )
            bucket = {
                "knowledge": knowledge,
                "evidence": evidence,
                "conflict": conflicts,
                "investment": investment,
                "forecast": forecasts,
                "event": events,
                "risk": risks,
                "catalyst": catalysts,
                "open_intelligence": knowledge,
            }.get(item.kind)
            if bucket is not None:
                bucket.append(row)
            elif item.engine in {"mee", "aoi"} and item.kind != "event":
                macro.append(row)
            else:
                relationships.append(row)

        # Macro-ish from events/forecasts tagged macro category
        for e in events:
            content = e.get("content") if isinstance(e, dict) else None
            if isinstance(content, dict) and content.get("category") in {"macro", "central_bank", "commodity", "currency"}:
                macro.append(e)

        confs = [i.confidence for i in items if i.confidence]
        confidence_summary = {
            "average_confidence": round(sum(confs) / len(confs), 4) if confs else 0.0,
            "critical_items": len([i for i in items if i.priority == "critical"]),
            "conflicts": len(conflicts),
            "engines_succeeded": len([c for c in contribs if c.succeeded]),
            "engines_failed": len([c for c in contribs if not c.succeeded]),
        }

        soft_fields = self._soft_fields(
            plan, evidence, investment, forecasts, events, knowledge, conflicts, items, query=query
        )

        return ContextPackage(
            package_id=new_id("ctx"),
            query=query,
            query_summary=f"Intents={','.join(plan.intents)}; entities={','.join(plan.entities) or 'none'}",
            plan=plan.to_dict(),
            entities=list(plan.entities),
            knowledge=knowledge,
            evidence=evidence,
            investment_intelligence=investment,
            forecasts=forecasts,
            events=events,
            risks=risks,
            catalysts=catalysts,
            macro=macro,
            relationships=relationships,
            conflicts=conflicts,
            confidence_summary=confidence_summary,
            recommended_reasoning_strategy=plan.reasoning_strategy,
            engine_contributions=[c.to_dict() for c in contribs],
            ranking=ranking,
            token_usage=usage,
            duplicates_removed=duplicates_removed,
            compression_ratio=compression,
            explain=explain,
            soft_fields=soft_fields,
        )

    def _soft_fields(
        self,
        plan: QueryPlan,
        evidence: list,
        investment: list,
        forecasts: list,
        events: list,
        knowledge: list,
        conflicts: list,
        items: list,
        query: str = "",
    ) -> dict[str, Any]:
        """Populate backward-compatible Ask AGI soft field shapes from unified package."""
        def _hits(rows: list, kind: str) -> list[dict[str, Any]]:
            out = []
            for r in rows[:8]:
                content = r.get("content") if isinstance(r, dict) else r
                if isinstance(content, dict) and content.get("kind"):
                    out.append(content)
                else:
                    out.append(
                        {
                            "kind": kind,
                            "id": r.get("item_id"),
                            "label": r.get("title"),
                            "score": r.get("ranking_score"),
                            "confidence": r.get("confidence"),
                            "snippet": str(content)[:200],
                        }
                    )
            return out

        kf_hits = _hits([r for r in knowledge if r.get("engine") in {"kf", "kc"}], "knowledge")
        return {
            "knowledge_foundation": {
                "answer_policy": "knowledge_objects_before_documents",
                "hits": kf_hits,
                "count": len(kf_hits),
            },
            "knowledge_corpus": {
                "answer_policy": "knowledge_corpus_before_documents",
                "hits": kf_hits,
                "count": len(kf_hits),
                "primary_source_of_truth": "knowledge_objects",
            },
            "open_intelligence": {
                "answer_policy": "structured_open_intelligence",
                "hits": _hits([r for r in knowledge if r.get("engine") == "aoi"], "open_intelligence"),
            },
            "evidence_verification": {
                "answer_policy": "verified_evidence_before_raw_facts",
                "hits": _hits(evidence, "evidence"),
                "conflicts": _hits(conflicts, "conflict"),
                "guidance": {
                    "use_highest_confidence_first": True,
                    "avoid_hallucinated_certainty": True,
                    "present_conflicts": bool(conflicts),
                },
            },
            "investment_intelligence": {
                "answer_policy": "investment_intelligence_before_reasoning",
                "hits": _hits(investment, "investment"),
                "guidance": {
                    "use_structured_intelligence_first": True,
                    "trace_to_eve_evidence": True,
                    "preserve_uncertainty": True,
                    "never_hallucinate": True,
                },
            },
            "forecast_learning": {
                "answer_policy": "forecast_history_and_calibration_before_reasoning",
                "hits": _hits(forecasts, "forecast"),
                "current_predictions": [
                    r.get("content") for r in forecasts if isinstance(r.get("content"), dict)
                ][:8],
                "guidance": {
                    "use_forecast_history_first": True,
                    "never_forget_predictions": True,
                },
            },
            "market_events": {
                "answer_policy": "what_changed_before_reasoning",
                "hits": _hits(events, "event"),
                "recent_events": [
                    r.get("content") for r in events if isinstance(r.get("content"), dict)
                ][:8],
                "guidance": {
                    "always_ask_what_changed": True,
                    "use_event_context_first": True,
                    "immutable_events": True,
                },
            },
            "context_assembly": {
                "answer_policy": "unified_context_before_reasoning",
                "plan_id": plan.plan_id,
                "intents": plan.intents,
                "engines": plan.engines,
                "reasoning_strategy": plan.reasoning_strategy,
                "primary_ticker": plan.primary_ticker,
            },
            # FAPI v1.0 — Finance Academy production context (additive soft field)
            "finance_academy": self._finance_academy_soft(query or "", plan.primary_ticker),
            # LEO v1.0 — Live Evidence package before reasoning (additive soft field)
            "live_evidence": self._live_evidence_soft(query or "", plan.primary_ticker),
            # CID v1.0 — living company dossier before raw API rebuilds
            "company_dossier": self._company_dossier_soft(query or "", plan.primary_ticker),
        }

    def _finance_academy_soft(self, query: str, ticker: str | None) -> dict[str, Any]:
        """Soft-retrieve Finance Academy concepts for CAE packaging (no engine redesign)."""
        try:
            from academy.fapi.production import package_for_query

            return package_for_query(query, engine="cae", ticker=ticker)
        except Exception as exc:  # noqa: BLE001
            return {"enabled": False, "error": str(exc), "concept_ids": []}

    def _live_evidence_soft(self, query: str, ticker: str | None) -> dict[str, Any]:
        """Soft-orchestrate live evidence for CAE packaging (no engine redesign)."""
        try:
            from leo.production import package_for_query

            return package_for_query(
                query,
                ticker=ticker,
                engine="cae",
                eve=getattr(self, "eve", None),
                aoi=getattr(self, "aoi", None),
            )
        except Exception as exc:  # noqa: BLE001
            return {"enabled": False, "error": str(exc), "evidence_objects": []}

    def _company_dossier_soft(self, query: str, ticker: str | None) -> dict[str, Any]:
        """Soft-load Company Intelligence Dossier for CAE (dossier before raw APIs)."""
        try:
            from cid.production import get_or_build

            # Prefer existing living dossier; LEO Ask-AGI path already ingests before CAE.
            return get_or_build(ticker, query=query)
        except Exception as exc:  # noqa: BLE001
            return {"enabled": False, "error": str(exc)}
