"""RSP reasoning pipeline — Retrieve→…→Institutional Reasoning Package."""

from __future__ import annotations

from typing import Any

from app.rsp.change_detection import detect_changes
from app.rsp.consensus import build_consensus, cluster_opinions
from app.rsp.contradictions import detect_contradictions
from app.rsp.evidence import extract_evidence, separate_facts_opinions
from app.rsp.flags import RspFlags
from app.rsp.models import (
    EngineBundle,
    ReasoningPackage,
    ReasoningValidation,
    REASONING_VERSION,
)
from app.rsp.ranking import collect_kip_sources, dedupe_documents, rank_sources
from app.rsp.synthesis import synthesize

PIPELINE_STAGES = [
    "retrieve",
    "deduplicate",
    "rank_sources",
    "detect_contradictions",
    "cluster_opinions",
    "separate_facts",
    "separate_opinions",
    "extract_evidence",
    "score_evidence",
    "build_consensus",
    "compare_house_view",
    "identify_changes",
    "generate_reasoning_package",
]


class RspPipeline:
    def __init__(self, flags: RspFlags) -> None:
        self.flags = flags

    def reason(
        self,
        *,
        question: str,
        ticker: str | None,
        kip_context: dict[str, Any] | None,
        house_view: dict[str, Any] | None,
        engines: EngineBundle | dict[str, Any] | None,
    ) -> ReasoningPackage:
        if not self.flags.rsp:
            raise RuntimeError("RSP is disabled")
        if not self.flags.rsp_reasoning:
            raise RuntimeError("RSP_REASONING is disabled")

        stages: list[str] = []
        eng = _engines_dict(engines)

        # Retrieve (from provided KIP context — never pass raw docs to LLM)
        sources = collect_kip_sources(kip_context)
        stages.append("retrieve")

        sources = dedupe_documents(sources)
        stages.append("deduplicate")

        ranked = rank_sources(sources)
        stages.append("rank_sources")

        evidence = extract_evidence(
            ranked_sources=ranked,
            house_view=house_view,
            engines=eng,
            kip_context=kip_context,
        )
        stages.extend(["extract_evidence", "score_evidence"])

        facts, opinions = separate_facts_opinions(evidence)
        stages.extend(["separate_facts", "separate_opinions"])

        clusters = cluster_opinions(evidence)
        stages.append("cluster_opinions")

        contradictions: list = []
        if self.flags.rsp_contradictions:
            contradictions = detect_contradictions(
                evidence=evidence,
                kip_context=kip_context,
                house_view=house_view,
                engines=eng,
            )
        stages.append("detect_contradictions")

        consensus = None
        if self.flags.rsp_consensus:
            consensus = build_consensus(
                evidence=evidence,
                clusters=clusters,
                house_view=house_view,
                engines=eng,
                kip_context=kip_context,
            )
        else:
            from app.rsp.models import ConsensusView

            consensus = ConsensusView(agi_view=str((house_view or {}).get("latest_thesis") or ""))
        stages.extend(["build_consensus", "compare_house_view"])

        changes = detect_changes(house_view=house_view, evidence=evidence, kip_context=kip_context)
        stages.append("identify_changes")

        synthesis = synthesize(
            question=question,
            ticker=ticker,
            facts=facts,
            opinions=opinions,
            consensus=consensus,
            contradictions=contradictions,
            changes=changes,
            house_view=house_view,
        )
        stages.append("generate_reasoning_package")

        supporting_docs = sorted(
            {
                d
                for e in evidence
                for d in e.supporting_documents
                if d
            }
        )
        contradicting_docs = sorted(
            {
                d
                for e in evidence
                for d in e.contradicting_documents
                if d
            }
            | {d for c in contradictions for d in c.document_ids if d}
        )
        alignments = [e.house_view_alignment for e in evidence if e.house_view_alignment != "unknown"]
        if alignments:
            aligned = alignments.count("aligned")
            contrary = alignments.count("contrary")
            hv_align = "aligned" if aligned >= contrary else ("contrary" if contrary > aligned else "mixed")
        else:
            hv_align = "unknown"

        freshness = (
            sum(e.freshness for e in evidence) / len(evidence) if evidence else float((kip_context or {}).get("freshness_score") or 0)
        )
        confidence = synthesis.confidence

        validation = ReasoningValidation(
            evidence_tree=synthesis.evidence_tree,
            supporting_documents=supporting_docs[:40],
            contradicting_documents=list(contradicting_docs)[:40],
            house_view_alignment=hv_align,
            freshness=round(freshness, 4),
            confidence=confidence,
            reasoning_version=REASONING_VERSION,
        )

        return ReasoningPackage(
            question=question,
            ticker=ticker.upper() if ticker else None,
            facts=facts,
            opinions=opinions,
            evidence=evidence,
            contradictions=contradictions,
            opinion_clusters=clusters,
            consensus=consensus,
            confidence=confidence,
            house_view=house_view,
            research_continuity=changes,
            synthesis=synthesis,
            ranked_sources=ranked[:40],
            pipeline_stages=stages,
            engine_inputs={k: v for k, v in eng.items() if v},
            validation=validation,
            reasoning_version=REASONING_VERSION,
            answer_policy="rsp_reasons_before_llm",
        )


def _engines_dict(engines: EngineBundle | dict[str, Any] | None) -> dict[str, Any]:
    if engines is None:
        return {}
    if isinstance(engines, EngineBundle):
        data = engines.model_dump(mode="json")
    else:
        data = dict(engines)
    # normalize keys to lowercase e01.. and l4/e10
    out: dict[str, Any] = {}
    for k, v in data.items():
        if v is None:
            continue
        out[str(k).lower()] = v
    return out
