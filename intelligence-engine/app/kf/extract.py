"""Structured research extraction from KIP documents (Phase 5)."""

from __future__ import annotations

from typing import Any

from app.aws.adapters import dump
from app.kf.models import KnowledgeMeta, ResearchExtractObject
from app.kf.scoring import confidence_score, source_reliability


def extract_research_object(doc: Any) -> ResearchExtractObject | None:
    d = dump(doc) if not isinstance(doc, dict) else doc
    if not isinstance(d, dict):
        return None
    document = d.get("document") if isinstance(d.get("document"), dict) else {}
    research = d.get("research") if isinstance(d.get("research"), dict) else {}
    investment = d.get("investment") if isinstance(d.get("investment"), dict) else {}
    knowledge = d.get("knowledge") if isinstance(d.get("knowledge"), dict) else {}

    doc_id = str(d.get("document_id") or document.get("document_id") or "")
    if not doc_id:
        return None
    title = str(document.get("title") or d.get("title") or "")
    thesis = str(research.get("investment_thesis") or knowledge.get("summary") or "")[:2000]
    bull = [str(x) for x in (research.get("bull_case") or [])][:12]
    bear = [str(x) for x in (research.get("bear_case") or [])][:12]
    risks = [str(x) for x in (research.get("risks") or [])][:12]
    catalysts = [str(x) for x in (research.get("catalysts") or [])][:12]
    companies = [str(x).upper() for x in (investment.get("tickers") or [])][:20]
    sectors = [str(x) for x in (investment.get("sectors") or investment.get("industries") or [])][:12]
    themes = [str(x) for x in (investment.get("themes") or [])][:12]
    macro = [str(x) for x in (investment.get("macro_topics") or [])][:12]
    conf = float(knowledge.get("confidence") or 0.5)
    if conf > 1:
        conf = conf / 100.0
    src = str(document.get("source") or d.get("source") or "agi")
    rel = source_reliability(src)
    meta = KnowledgeMeta(
        kind="research_extract",
        key=doc_id,
        confidence=confidence_score(
            has_thesis=bool(thesis),
            n_sources=1,
            source_reliability=rel,
            n_structured_fields=sum(bool(x) for x in (bull, bear, risks, catalysts, companies)),
        ),
        freshness=float(knowledge.get("freshness") or 0.8),
        source_reliability=rel,
        sources=[src],
        document_ids=[doc_id],
        change_log=["extracted from AGI / institutional document"],
    )
    return ResearchExtractObject(
        meta=meta,
        document_id=doc_id,
        title=title,
        question=str(research.get("question") or title or "")[:300],
        summary=str(knowledge.get("summary") or thesis)[:800],
        investment_thesis=thesis,
        bull_case=bull,
        bear_case=bear,
        neutral_case=[str(x) for x in (research.get("counter_arguments") or [])][:8],
        catalysts=catalysts,
        risks=risks,
        valuation_view=str(research.get("valuation") or "")[:500],
        time_horizon=str(research.get("time_horizon") or "")[:80],
        confidence=round(conf, 4),
        prediction=str((research.get("target_prices") or [""])[0] if research.get("target_prices") else "")[:200],
        success_criteria=[str(x) for x in (research.get("assumptions") or [])][:8],
        failure_criteria=risks[:4],
        companies=companies,
        sectors=sectors,
        themes=themes,
        macro_factors=macro,
        evidence=[str(x) for x in (research.get("supporting_evidence") or [])][:12],
    )
