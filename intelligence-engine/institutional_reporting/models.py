"""IRE-01 reporting contract — immutable structured facts only (no English generation)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class EvidenceItem:
    """Structured evidence reference — engines supply IDs/labels, not prose."""

    evidence_id: str
    label: str
    source_type: str = ""
    section_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "label": self.label,
            "source_type": self.source_type,
            "section_keys": list(self.section_keys),
        }


@dataclass(frozen=True)
class InstitutionalReportInput:
    """Immutable fact object for a Company Recommendation Report.

    Rule: every intelligence engine returns facts. Nothing returns English.
    """

    ticker: str
    company_name: str
    sector: str
    recommendation: str
    conviction: str
    confidence: int
    horizon: str
    business_quality: int | float | str
    financial_quality: str
    valuation: str
    overall_risk: str
    thesis: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    catalysts: tuple[str, ...] = ()
    watch_items: tuple[str, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()
    # Optional structured drivers for confidence explanation
    positive_drivers: tuple[str, ...] = ()
    negative_drivers: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    # Optional bull/bear fact bullets (not free-form paragraphs)
    bull_points: tuple[str, ...] = ()
    bear_points: tuple[str, ...] = ()
    business_quality_reasons: tuple[str, ...] = ()
    financial_quality_reasons: tuple[str, ...] = ()
    valuation_reasons: tuple[str, ...] = ()
    risk_reasons: tuple[str, ...] = ()
    as_of: str = ""

    @staticmethod
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

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "InstitutionalReportInput":
        body = dict(payload or {})
        evidence_raw = body.get("evidence") or []
        evidence_items: list[EvidenceItem] = []
        for row in evidence_raw:
            if isinstance(row, EvidenceItem):
                evidence_items.append(row)
                continue
            if not isinstance(row, dict):
                continue
            section_keys = row.get("section_keys") or row.get("sections") or ()
            if isinstance(section_keys, str):
                section_keys = (section_keys,)
            evidence_items.append(
                EvidenceItem(
                    evidence_id=str(row.get("evidence_id") or row.get("id") or "").strip(),
                    label=str(row.get("label") or row.get("title") or "").strip(),
                    source_type=str(row.get("source_type") or row.get("type") or "").strip(),
                    section_keys=tuple(str(s).strip() for s in section_keys if str(s).strip()),
                )
            )
        return cls(
            ticker=str(body.get("ticker") or "").strip().upper(),
            company_name=str(body.get("company_name") or body.get("name") or "").strip(),
            sector=str(body.get("sector") or "").strip(),
            recommendation=str(body.get("recommendation") or "").strip().upper(),
            conviction=str(body.get("conviction") or "").strip().upper(),
            confidence=int(body.get("confidence") if body.get("confidence") is not None else -1),
            horizon=str(body.get("horizon") or "").strip().title()
            if str(body.get("horizon") or "").strip().lower() in {"short", "medium", "long"}
            else str(body.get("horizon") or "").strip(),
            business_quality=body.get("business_quality")
            if body.get("business_quality") is not None
            else "",
            financial_quality=str(body.get("financial_quality") or "").strip(),
            valuation=str(body.get("valuation") or "").strip().title(),
            overall_risk=str(body.get("overall_risk") or body.get("risk") or "").strip().title(),
            thesis=cls._tup(body.get("thesis")),
            risks=cls._tup(body.get("risks")),
            catalysts=cls._tup(body.get("catalysts")),
            watch_items=cls._tup(body.get("watch_items")),
            evidence=tuple(evidence_items),
            positive_drivers=cls._tup(body.get("positive_drivers")),
            negative_drivers=cls._tup(body.get("negative_drivers")),
            unknowns=cls._tup(body.get("unknowns")),
            bull_points=cls._tup(body.get("bull_points") or body.get("bull_case")),
            bear_points=cls._tup(body.get("bear_points") or body.get("bear_case")),
            business_quality_reasons=cls._tup(body.get("business_quality_reasons")),
            financial_quality_reasons=cls._tup(body.get("financial_quality_reasons")),
            valuation_reasons=cls._tup(body.get("valuation_reasons")),
            risk_reasons=cls._tup(body.get("risk_reasons")),
            as_of=str(body.get("as_of") or "").strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"] = [e.to_dict() if hasattr(e, "to_dict") else e for e in self.evidence]
        data["thesis"] = list(self.thesis)
        data["risks"] = list(self.risks)
        data["catalysts"] = list(self.catalysts)
        data["watch_items"] = list(self.watch_items)
        data["positive_drivers"] = list(self.positive_drivers)
        data["negative_drivers"] = list(self.negative_drivers)
        data["unknowns"] = list(self.unknowns)
        data["bull_points"] = list(self.bull_points)
        data["bear_points"] = list(self.bear_points)
        data["business_quality_reasons"] = list(self.business_quality_reasons)
        data["financial_quality_reasons"] = list(self.financial_quality_reasons)
        data["valuation_reasons"] = list(self.valuation_reasons)
        data["risk_reasons"] = list(self.risk_reasons)
        return data


@dataclass
class ReportSection:
    key: str
    title: str
    body: str
    evidence_ids: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    reason: Any = None  # Reason | None — kept Any to avoid circular import at runtime

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "body": self.body,
            "evidence_ids": list(self.evidence_ids),
            "meta": dict(self.meta or {}),
            "reason": self.reason.to_dict() if self.reason is not None and hasattr(self.reason, "to_dict") else None,
        }


@dataclass
class InstitutionalReport:
    """Deterministic company recommendation report — fixed section order."""

    ok: bool
    workstream_id: str
    version: str
    report_type: str
    ticker: str
    company_name: str
    recommendation: str
    conviction: str
    confidence: int
    sections: list[ReportSection]
    text: str
    quality_gates: dict[str, bool]
    validation_errors: list[str] = field(default_factory=list)
    rejected: bool = False
    llm: bool = False
    as_of: str = ""
    input_fingerprint: str = ""
    reasons: list[Any] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    reason_graph_text: str = ""
    decision: Any = None  # InstitutionalDecision | dict | None
    knowledge_graph: Any = None  # InstitutionalKnowledgeGraph summary | dict | None

    def to_dict(self) -> dict[str, Any]:
        decision_payload = None
        if self.decision is not None:
            decision_payload = (
                self.decision.to_dict() if hasattr(self.decision, "to_dict") else self.decision
            )
        kg_payload = None
        if self.knowledge_graph is not None:
            kg_payload = (
                self.knowledge_graph.to_dict()
                if hasattr(self.knowledge_graph, "to_dict")
                else self.knowledge_graph
            )
        return {
            "ok": self.ok,
            "workstream_id": self.workstream_id,
            "version": self.version,
            "report_type": self.report_type,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "recommendation": self.recommendation,
            "conviction": self.conviction,
            "confidence": self.confidence,
            "sections": [s.to_dict() for s in self.sections],
            "text": self.text,
            "quality_gates": dict(self.quality_gates),
            "validation_errors": list(self.validation_errors),
            "rejected": self.rejected,
            "llm": False,
            "external_writer": False,
            "reason_composer": True,
            "decision_system": True,
            "knowledge_graph": True,
            "forecast_scenarios": bool(
                (self.diagnostics or {}).get("forecast_scenarios")
            ),
            "as_of": self.as_of,
            "input_fingerprint": self.input_fingerprint,
            "reasons": [
                r.to_dict() if hasattr(r, "to_dict") else r for r in (self.reasons or [])
            ],
            "diagnostics": dict(self.diagnostics or {}),
            "reason_graph_text": self.reason_graph_text,
            "decision": decision_payload,
            "graph": kg_payload,
        }


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors)}
