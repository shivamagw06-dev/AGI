"""IDS-01 InstitutionalDecision — immutable, versioned, auditable."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


def _tup(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        text = value.strip()
        return (text,) if text else ()
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return tuple(out)


@dataclass(frozen=True)
class DecisionGraph:
    """Transparent path from quality factors to recommendation."""

    nodes: tuple[dict[str, Any], ...]
    version: str

    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "nodes": [dict(n) for n in self.nodes]}


@dataclass(frozen=True)
class InstitutionalDecision:
    """Canonical investment decision — single source of truth for reports/Ask/API."""

    ticker: str
    recommendation: str
    conviction: str
    confidence: int
    investment_horizon: str
    supporting_reasons: tuple[str, ...] = ()
    contradicting_reasons: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    upgrade_conditions: tuple[str, ...] = ()
    downgrade_conditions: tuple[str, ...] = ()
    monitoring_items: tuple[str, ...] = ()
    # Versioned audit metadata (immutable)
    decision_id: str = ""
    decision_version: int = 1
    generated_at: str = ""
    reason_version: str = ""
    report_version: str = ""
    evidence_snapshot_id: str = ""
    decision_engine_version: str = ""
    validator_version: str = ""
    company_name: str = ""
    sector: str = ""
    decision_graph: Optional[DecisionGraph] = None
    evidence_ids: tuple[str, ...] = ()
    rule_path: str = ""
    score: int = 0
    llm: bool = False
    # IDS-02 — calibrated confidence (computed; never manually assigned)
    calibrated: bool = False
    calibration_version: str = ""
    calibration_profile_version: str = ""
    calibration_engine_version: str = ""
    calibration: Any = None  # institutional_calibration.models.Calibration | dict | None
    # KG-01 — decision references DecisionNode in the company knowledge graph
    knowledge_graph_id: str = ""
    decision_node_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["supporting_reasons"] = list(self.supporting_reasons)
        data["contradicting_reasons"] = list(self.contradicting_reasons)
        data["unknowns"] = list(self.unknowns)
        data["upgrade_conditions"] = list(self.upgrade_conditions)
        data["downgrade_conditions"] = list(self.downgrade_conditions)
        data["monitoring_items"] = list(self.monitoring_items)
        data["evidence_ids"] = list(self.evidence_ids)
        data["llm"] = False
        if self.decision_graph is not None:
            data["decision_graph"] = self.decision_graph.to_dict()
        if self.calibration is not None and hasattr(self.calibration, "to_dict"):
            data["calibration"] = self.calibration.to_dict()
        elif self.calibration is not None:
            data["calibration"] = self.calibration
        return data

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "InstitutionalDecision":
        body = dict(payload or {})
        graph_raw = body.get("decision_graph")
        graph = None
        if isinstance(graph_raw, dict):
            nodes = tuple(dict(n) for n in (graph_raw.get("nodes") or []) if isinstance(n, dict))
            graph = DecisionGraph(nodes=nodes, version=str(graph_raw.get("version") or ""))
        return cls(
            ticker=str(body.get("ticker") or "").strip().upper(),
            recommendation=str(body.get("recommendation") or "").strip().upper(),
            conviction=str(body.get("conviction") or "").strip().upper(),
            confidence=int(body.get("confidence") if body.get("confidence") is not None else -1),
            investment_horizon=str(body.get("investment_horizon") or body.get("horizon") or "").strip(),
            supporting_reasons=_tup(body.get("supporting_reasons")),
            contradicting_reasons=_tup(body.get("contradicting_reasons")),
            unknowns=_tup(body.get("unknowns")),
            upgrade_conditions=_tup(body.get("upgrade_conditions")),
            downgrade_conditions=_tup(body.get("downgrade_conditions")),
            monitoring_items=_tup(body.get("monitoring_items")),
            decision_id=str(body.get("decision_id") or "").strip(),
            decision_version=int(body.get("decision_version") or 1),
            generated_at=str(body.get("generated_at") or "").strip(),
            reason_version=str(body.get("reason_version") or "").strip(),
            report_version=str(body.get("report_version") or "").strip(),
            evidence_snapshot_id=str(body.get("evidence_snapshot_id") or "").strip(),
            decision_engine_version=str(body.get("decision_engine_version") or "").strip(),
            validator_version=str(body.get("validator_version") or "").strip(),
            company_name=str(body.get("company_name") or "").strip(),
            sector=str(body.get("sector") or "").strip(),
            decision_graph=graph,
            evidence_ids=_tup(body.get("evidence_ids")),
            rule_path=str(body.get("rule_path") or "").strip(),
            score=int(body.get("score") or 0),
            llm=False,
            calibrated=bool(body.get("calibrated") or False),
            calibration_version=str(body.get("calibration_version") or "").strip(),
            calibration_profile_version=str(body.get("calibration_profile_version") or "").strip(),
            calibration_engine_version=str(body.get("calibration_engine_version") or "").strip(),
            calibration=body.get("calibration"),
            knowledge_graph_id=str(body.get("knowledge_graph_id") or "").strip(),
            decision_node_id=str(body.get("decision_node_id") or "").strip(),
        )


@dataclass
class DecisionValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors)}


@dataclass
class DecisionHistoryEntry:
    decision: InstitutionalDecision
    previous_recommendation: str = ""
    transition: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "previous_recommendation": self.previous_recommendation,
            "transition": self.transition,
            "timestamp": self.decision.generated_at,
            "reasons": list(self.decision.supporting_reasons),
            "evidence_ids": list(self.decision.evidence_ids),
            "confidence": self.decision.confidence,
        }
