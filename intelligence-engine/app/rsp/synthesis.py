"""Research synthesis — Research Brief / Thesis / Counter / Evidence Tree."""

from __future__ import annotations

from typing import Any

from app.rsp.models import (
    ChangeDetection,
    ConsensusView,
    Contradiction,
    EvidenceStatement,
    ResearchSynthesis,
)


def synthesize(
    *,
    question: str,
    ticker: str | None,
    facts: list[EvidenceStatement],
    opinions: list[EvidenceStatement],
    consensus: ConsensusView,
    contradictions: list[Contradiction],
    changes: ChangeDetection,
    house_view: dict[str, Any] | None,
) -> ResearchSynthesis:
    t = ticker or "the subject"
    thesis = consensus.agi_view or _best(opinions, prefer_cluster="bull") or f"Insufficient AGI thesis for {t}"
    counter = consensus.contrarian_view or _best(opinions, prefer_cluster="bear") or "No clear counter-thesis"
    catalysts = [e.statement for e in opinions + facts if e.cluster == "catalyst"][:8]
    if not catalysts and house_view:
        catalysts = [str(x) for x in (house_view.get("catalysts_occurred") or [])][:8]
    risks = [e.statement for e in opinions + facts if e.cluster == "risk"][:8]
    valuation = _best(opinions + facts, prefer_cluster="valuation") or "Valuation summary unavailable"

    brief_parts = [
        f"Research Brief — {t}",
        f"Question: {question}",
        f"AGI view: {thesis[:280]}",
        f"Broker: {consensus.broker_consensus[:200]}",
        f"Market: {consensus.market_consensus[:160]}",
    ]
    if contradictions:
        brief_parts.append(f"Key contradiction: {contradictions[0].summary}")
    if changes.what_changed:
        brief_parts.append(f"Changed: {changes.what_changed[0]}")
    if changes.strengthens_thesis:
        brief_parts.append(f"Strengthens: {changes.strengthens_thesis[0][:160]}")
    if changes.weakens_thesis:
        brief_parts.append(f"Weakens: {changes.weakens_thesis[0][:160]}")

    conf = _synthesis_confidence(opinions + facts, contradictions, consensus)

    tree = build_evidence_tree(facts, opinions, contradictions, consensus)

    return ResearchSynthesis(
        research_brief=" | ".join(brief_parts)[:1500],
        investment_thesis=thesis[:1000],
        counter_thesis=counter[:800],
        catalysts=_uniq(catalysts)[:10],
        risks=_uniq(risks)[:10],
        valuation_summary=valuation[:600],
        confidence=conf,
        evidence_tree=tree,
    )


def build_evidence_tree(
    facts: list[EvidenceStatement],
    opinions: list[EvidenceStatement],
    contradictions: list[Contradiction],
    consensus: ConsensusView,
) -> dict[str, Any]:
    return {
        "root": "institutional_reasoning",
        "nodes": {
            "facts": [e.evidence_id for e in facts[:20]],
            "opinions": [e.evidence_id for e in opinions[:20]],
            "consensus": {
                "agi_view": consensus.agi_view[:200],
                "broker_consensus": consensus.broker_consensus[:200],
                "market_consensus": consensus.market_consensus[:200],
                "contrarian_view": consensus.contrarian_view[:200],
            },
            "contradictions": [c.contradiction_id for c in contradictions[:12]],
            "clusters": {
                "bull": [e.evidence_id for e in opinions if e.cluster == "bull"][:10],
                "bear": [e.evidence_id for e in opinions if e.cluster == "bear"][:10],
                "valuation": [e.evidence_id for e in opinions + facts if e.cluster == "valuation"][:10],
                "risk": [e.evidence_id for e in opinions + facts if e.cluster == "risk"][:10],
                "catalyst": [e.evidence_id for e in opinions + facts if e.cluster == "catalyst"][:10],
            },
        },
        "edges": [
            {"from": "root", "to": "facts"},
            {"from": "root", "to": "opinions"},
            {"from": "root", "to": "consensus"},
            {"from": "opinions", "to": "contradictions"},
        ],
    }


def _best(rows: list[EvidenceStatement], *, prefer_cluster: str) -> str:
    ranked = sorted(
        [e for e in rows if e.cluster == prefer_cluster] or rows,
        key=lambda e: e.score,
        reverse=True,
    )
    return ranked[0].statement if ranked else ""


def _synthesis_confidence(
    evidence: list[EvidenceStatement],
    contradictions: list[Contradiction],
    consensus: ConsensusView,
) -> float:
    if not evidence:
        return 0.2
    base = sum(e.score for e in evidence) / len(evidence)
    base = 0.6 * base + 0.4 * consensus.agreement_score
    if contradictions:
        base *= max(0.55, 1.0 - 0.08 * len(contradictions))
    return round(min(0.97, base), 4)


def _uniq(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for i in items:
        k = i.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(i.strip())
    return out
