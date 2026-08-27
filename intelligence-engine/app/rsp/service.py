"""RSP service facade — Research Committee reasoning layer."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.rsp.flags import RspFlags
from app.rsp.models import (
    CommitteeRequest,
    EngineBundle,
    EvidenceStatement,
    ReasonRequest,
    ReasoningPackage,
    SynthesizeRequest,
)
from app.rsp.pipeline import RspPipeline
from app.rsp.store import RspStore


class RspService:
    """Transforms retrieved knowledge into institutional reasoning before the LLM writes."""

    def __init__(
        self,
        store: RspStore | None = None,
        flags: RspFlags | None = None,
        kip: Any | None = None,
    ) -> None:
        self.flags = flags or RspFlags.from_settings(get_settings())
        self.store = store or RspStore()
        self.pipeline = RspPipeline(self.flags)
        self.kip = kip

    def reason(self, request: ReasonRequest) -> ReasoningPackage:
        self._require_enabled()
        kip_context, house_view = self._resolve_kip(request.question, request.ticker, request.kip_context, request.house_view)
        pkg = self.pipeline.reason(
            question=request.question,
            ticker=request.ticker,
            kip_context=kip_context,
            house_view=house_view,
            engines=request.engines,
        )
        self.store.put(pkg)
        return pkg

    def synthesize(self, request: SynthesizeRequest) -> ReasoningPackage:
        """Produce / refresh synthesis; reuses prior package when reasoning_id provided."""
        self._require_enabled()
        if request.reasoning_id:
            existing = self.store.get(request.reasoning_id)
            if existing is None:
                raise KeyError(f"reasoning not found: {request.reasoning_id}")
            # Re-run synthesis path with stored inputs context
            req = ReasonRequest(
                question=request.question or existing.question,
                ticker=request.ticker or existing.ticker,
                kip_context=request.kip_context,
                house_view=request.house_view or existing.house_view,
                engines=request.engines
                if request.engines and _bundle_nonempty(request.engines)
                else EngineBundle(**(existing.engine_inputs or {})),
            )
            # If no new kip context, reconstruct a minimal one from ranked sources
            if req.kip_context is None:
                req.kip_context = {
                    "supporting_evidence": existing.ranked_sources,
                    "freshness_score": existing.validation.freshness,
                    "confidence_score": existing.confidence,
                    "agi_research_used": [
                        d for d in existing.validation.supporting_documents if d
                    ],
                }
            return self.reason(req)

        return self.reason(
            ReasonRequest(
                question=request.question,
                ticker=request.ticker,
                kip_context=request.kip_context,
                house_view=request.house_view,
                engines=request.engines,
            )
        )

    def committee(self, request: CommitteeRequest) -> ReasoningPackage:
        """Full Research Committee pass — reason + synthesize (single package)."""
        self._require_enabled()
        return self.reason(
            ReasonRequest(
                question=request.question,
                ticker=request.ticker,
                kip_context=request.kip_context,
                house_view=request.house_view,
                engines=request.engines,
                metadata=request.metadata,
            )
        )

    def get_reasoning(self, reasoning_id: str) -> ReasoningPackage | None:
        self._require_enabled()
        return self.store.get(reasoning_id)

    def get_evidence(self, evidence_id: str) -> EvidenceStatement | None:
        self._require_enabled()
        return self.store.get_evidence(evidence_id)

    def reason_for_writer(
        self,
        question: str,
        *,
        ticker: str | None = None,
        engines: EngineBundle | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Soft hook for Research Director / client answers.
        Returns structured ReasoningPackage dict — never raw retrieved documents.
        """
        if not self.flags.rsp:
            return {}
        pkg = self.reason(
            ReasonRequest(
                question=question,
                ticker=ticker,
                engines=engines if isinstance(engines, EngineBundle) else EngineBundle(**(engines or {})),
            )
        )
        return {
            "reasoning_id": pkg.reasoning_id,
            "reasoning_version": pkg.reasoning_version,
            "answer_policy": pkg.answer_policy,
            "synthesis": pkg.synthesis.model_dump(mode="json"),
            "consensus": pkg.consensus.model_dump(mode="json"),
            "contradictions": [c.model_dump(mode="json") for c in pkg.contradictions],
            "research_continuity": pkg.research_continuity.model_dump(mode="json"),
            "confidence": pkg.confidence,
            "validation": pkg.validation.model_dump(mode="json"),
            "facts": [f.model_dump(mode="json") for f in pkg.facts[:20]],
            "opinions": [o.model_dump(mode="json") for o in pkg.opinions[:20]],
            # Explicitly omit raw document bodies
            "raw_documents_included": False,
        }

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.rsp else "disabled",
            "platform": "RSP",
            "reasoning_version": "rsp-v1.0.1",
            "flags": self.flags.as_dict(),
            "stats": self.store.stats(),
            "contract": "KIP retrieves → RSP reasons → LLM writes",
            "out_of_scope": [
                "model_fine_tuning",
                "engine_redesign",
                "broker_execution",
                "portfolio_optimisation",
                "autonomous_decisions",
            ],
        }

    def _resolve_kip(
        self,
        question: str,
        ticker: str | None,
        kip_context: dict[str, Any] | None,
        house_view: dict[str, Any] | None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        ctx = kip_context
        hv = house_view
        kip = self.kip
        if kip is None:
            return ctx, hv
        try:
            if ctx is None and getattr(getattr(kip, "flags", None), "kip_rag", False):
                ctx = kip.research_context(question, ticker=ticker)
            if hv is None and ticker and getattr(getattr(kip, "flags", None), "kip_house_view", False):
                hv = kip.house_view(ticker).model_dump(mode="json")
        except Exception:
            # Soft-fail — RSP can still reason on provided engines / partial context
            pass
        return ctx, hv

    def _require_enabled(self) -> None:
        if not self.flags.rsp:
            raise RuntimeError("RSP is disabled")


def _bundle_nonempty(bundle: EngineBundle) -> bool:
    data = bundle.model_dump()
    return any(v is not None for v in data.values())
