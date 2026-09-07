"""Proposal-only bridge into the locked thesis engine."""
from __future__ import annotations
import hashlib
from typing import Iterable
from causal_research_engine.schema import CausalRelationship, FinancialImpact, ThesisUpdateProposal

def propose_thesis_update(*, thesis_id: str, relationships: Iterable[CausalRelationship], impacts: Iterable[FinancialImpact]) -> ThesisUpdateProposal:
    rels = list(relationships); rows = list(impacts)
    positive = sum(x.direction == "POSITIVE" for x in rows); negative = sum(x.direction == "NEGATIVE" for x in rows)
    direction = "STRENGTHEN" if positive > negative else "WEAKEN" if negative > positive else "REVIEW"
    rel_ids = tuple(x.relationship_id for x in rels); impact_ids = tuple(x.impact_id for x in rows)
    pid = "CRE-THESIS-" + hashlib.sha256(f"{thesis_id}|{rel_ids}|{impact_ids}".encode()).hexdigest()[:16].upper()
    counters = tuple(c.effect for row in rels for c in row.counter_effects)
    indicators = tuple(dict.fromkeys(row.effect for row in rels))[:12]
    return ThesisUpdateProposal(pid, thesis_id, rel_ids, impact_ids, direction,
        f"{len(rels)} causal relationships and {len(rows)} governed impacts imply {direction.lower()}.",
        counters or ("Reassess if observed KPIs contradict the causal path",), indicators)
