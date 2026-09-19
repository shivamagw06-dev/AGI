"""KG-01 inference engine — deterministic derived relationships."""

from __future__ import annotations

from typing import List

from institutional_graph.graph import InstitutionalKnowledgeGraph
from institutional_graph.provenance import build_provenance
from institutional_graph.relationships import make_relationship
from institutional_graph.schema import INFERENCE_VERSION, KG_VERSION

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def infer(graph: InstitutionalKnowledgeGraph) -> List[str]:
    """
    Public API: infer(graph) → derived relationship ids.

    Example:
      ROE improving + Credit Cost falling
        → Profitability improving
        → Business Quality improving
        → Recommendation score path strengthens
    """
    created: list[str] = []
    meta = graph.meta or {}
    metric_ids = meta.get("metric_ids") or {}
    ts = graph.generated_at or now_iso()
    ticker = graph.ticker

    def _add(src: str, tgt: str, kind: str, strength: float, label: str, evidence_ids: tuple[str, ...] = ()) -> None:
        if not src or not tgt or src not in graph.nodes or tgt not in graph.nodes:
            return
        # Avoid duplicate inferred edges with same endpoints+label
        for existing in graph.relationships.values():
            if (
                existing.source_id == src
                and existing.target_id == tgt
                and existing.label == label
                and existing.inferred
            ):
                return
        import hashlib

        digest = hashlib.sha256(f"{ticker}|inf|{label}|{src}|{tgt}".encode()).hexdigest()[:10]
        rel_id = f"kg:{ticker.lower()}:inferred:{digest}"
        rel = make_relationship(
            rel_id=rel_id,
            source_id=src,
            target_id=tgt,
            kind=kind,
            strength=strength,
            confidence=strength,
            evidence_ids=evidence_ids,
            version=INFERENCE_VERSION,
            timestamp=ts,
            label=label,
            inferred=True,
            attributes={"inference_version": INFERENCE_VERSION},
            provenance=build_provenance(
                origin="inference_engine",
                timestamp=ts,
                evidence_ids=evidence_ids,
                engine=INFERENCE_VERSION,
                version=KG_VERSION,
            ),
        )
        graph.add_relationship(rel)
        created.append(rel_id)

    roe = metric_ids.get("roe")
    credit = metric_ids.get("credit_cost")
    profit = metric_ids.get("profitability")
    bq = metric_ids.get("business_quality")
    fq = metric_ids.get("financial_quality")
    decision_id = graph.decision_node_id

    # Gather evidence ids from existing metric edges
    def _ev_for(*node_ids: str) -> tuple[str, ...]:
        out: list[str] = []
        for nid in node_ids:
            node = graph.get(nid)
            if node and node.provenance:
                out.extend(node.provenance.evidence_ids)
        # unique preserve order
        seen: set[str] = set()
        uniq: list[str] = []
        for e in out:
            if e in seen:
                continue
            seen.add(e)
            uniq.append(e)
        return tuple(uniq[:6])

    # Rule 1: ROE + falling credit cost pressure path → profitability improving
    if roe and credit and profit:
        _add(
            roe,
            profit,
            "derived",
            0.82,
            "roe_and_credit_path_implies_profitability",
            _ev_for(roe, credit),
        )
        _add(
            credit,
            profit,
            "derived",
            0.8,
            "credit_cost_moderation_supports_profitability",
            _ev_for(credit),
        )

    # Rule 2: Profitability improving → Business Quality improving
    if profit and bq:
        _add(
            profit,
            bq,
            "derived",
            0.84,
            "profitability_improving_implies_business_quality_improving",
            _ev_for(profit, bq),
        )

    # Rule 3: Financial quality + profitability → stronger BQ
    if fq and profit and bq:
        _add(
            fq,
            bq,
            "derived",
            0.78,
            "financial_quality_and_profitability_lift_business_quality",
            _ev_for(fq, profit),
        )

    # Rule 4: Business quality improving → recommendation score path
    if bq and decision_id:
        decision = graph.get(decision_id)
        rec = ""
        if decision:
            rec = str((decision.attributes or {}).get("recommendation") or "").upper()
        kind = "supports" if rec in {"BUY", "HOLD"} else "derived"
        _add(
            bq,
            decision_id,
            kind,
            0.86,
            "business_quality_improving_raises_recommendation_score",
            _ev_for(bq),
        )

    # Rule 5: Macro (RBI) → NIM → profitability chain reinforcement (derived)
    rbi = meta.get("rbi_node_id")
    nim = metric_ids.get("nim")
    if rbi and nim and profit:
        _add(
            rbi,
            profit,
            "derived",
            0.55,
            "rbi_rate_transmits_to_profitability_via_nim",
            _ev_for(nim),
        )

    return created
