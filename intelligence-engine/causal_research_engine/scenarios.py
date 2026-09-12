"""Explicit, non-factual causal scenario assembly."""

from __future__ import annotations

import hashlib
from typing import Iterable

from causal_research_engine.schema import CausalRelationship, FinancialImpact, ScenarioResult


def build_scenarios(relationships: Iterable[CausalRelationship], impacts: Iterable[FinancialImpact],
                    *, probabilities: dict[str, float] | None = None) -> list[ScenarioResult]:
    probs = probabilities or {"BEAR": .25, "BASE": .5, "BULL": .25}
    if abs(sum(probs.values()) - 1.0) > 1e-9 or any(v < 0 for v in probs.values()):
        raise ValueError("SCENARIO_PROBABILITIES_MUST_SUM_TO_ONE")
    rel_ids = tuple(x.relationship_id for x in relationships)
    impact_rows = list(impacts)
    out = []
    for name, probability in probs.items():
        ids = tuple(x.impact_id for x in impact_rows if not x.scenario or x.scenario == name)
        directions = [x.direction for x in impact_rows if x.impact_id in ids]
        effect = "POSITIVE" if directions.count("POSITIVE") > directions.count("NEGATIVE") else "NEGATIVE" if directions.count("NEGATIVE") > directions.count("POSITIVE") else "MIXED"
        sid = "CRE-SCENARIO-" + hashlib.sha256(f"{name}|{rel_ids}|{ids}".encode()).hexdigest()[:16].upper()
        out.append(ScenarioResult(sid, name, probability, rel_ids, ids, ("Scenario, not reported fact",), effect))
    return out
