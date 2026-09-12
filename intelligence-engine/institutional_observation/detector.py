"""Detector — find new / changed / removed evidence and factor updates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set


@dataclass
class DetectedChange:
    kind: str  # new_evidence | changed_evidence | removed_evidence | valuation | macro | forecast | factor | event
    key: str
    detail: str
    before: Any = None
    after: Any = None
    category_hint: str = ""
    severity_hint: str = ""
    magnitude: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "key": self.key,
            "detail": self.detail,
            "before": self.before,
            "after": self.after,
            "category_hint": self.category_hint,
            "severity_hint": self.severity_hint,
            "magnitude": float(self.magnitude),
        }


@dataclass
class CompanySnapshot:
    """Lightweight institutional state for diffing (no English)."""

    ticker: str
    evidence_ids: tuple[str, ...] = ()
    valuation: str = ""
    business_quality: float | str = ""
    financial_quality: str = ""
    overall_risk: str = ""
    recommendation: str = ""
    confidence: int = 0
    decision_id: str = ""
    evidence_snapshot_id: str = ""
    company_name: str = ""
    sector: str = ""
    unknowns: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    catalysts: tuple[str, ...] = ()
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "evidence_ids": list(self.evidence_ids),
            "valuation": self.valuation,
            "business_quality": self.business_quality,
            "financial_quality": self.financial_quality,
            "overall_risk": self.overall_risk,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "decision_id": self.decision_id,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "company_name": self.company_name,
            "sector": self.sector,
            "unknowns": list(self.unknowns),
            "risks": list(self.risks),
            "catalysts": list(self.catalysts),
            "extras": dict(self.extras or {}),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "CompanySnapshot":
        body = dict(payload or {})
        return cls(
            ticker=str(body.get("ticker") or "").strip().upper(),
            evidence_ids=tuple(str(x) for x in (body.get("evidence_ids") or []) if str(x).strip()),
            valuation=str(body.get("valuation") or "").strip(),
            business_quality=body.get("business_quality") if body.get("business_quality") is not None else "",
            financial_quality=str(body.get("financial_quality") or "").strip(),
            overall_risk=str(body.get("overall_risk") or "").strip(),
            recommendation=str(body.get("recommendation") or "").strip().upper(),
            confidence=int(body.get("confidence") or 0),
            decision_id=str(body.get("decision_id") or "").strip(),
            evidence_snapshot_id=str(body.get("evidence_snapshot_id") or "").strip(),
            company_name=str(body.get("company_name") or "").strip(),
            sector=str(body.get("sector") or "").strip(),
            unknowns=tuple(str(x) for x in (body.get("unknowns") or []) if str(x).strip()),
            risks=tuple(str(x) for x in (body.get("risks") or []) if str(x).strip()),
            catalysts=tuple(str(x) for x in (body.get("catalysts") or []) if str(x).strip()),
            extras=dict(body.get("extras") or {}),
        )


def snapshot_from_inputs(
    report_input: Any,
    decision: Any = None,
) -> CompanySnapshot:
    evidence_ids = tuple(
        e.evidence_id for e in (getattr(report_input, "evidence", None) or ()) if getattr(e, "evidence_id", None)
    )
    conf = int(getattr(decision, "confidence", None) or getattr(report_input, "confidence", 0) or 0)
    rec = str(
        getattr(decision, "recommendation", None) or getattr(report_input, "recommendation", "") or ""
    ).upper()
    return CompanySnapshot(
        ticker=str(getattr(report_input, "ticker", "") or "").upper(),
        evidence_ids=evidence_ids,
        valuation=str(getattr(report_input, "valuation", "") or ""),
        business_quality=getattr(report_input, "business_quality", ""),
        financial_quality=str(getattr(report_input, "financial_quality", "") or ""),
        overall_risk=str(getattr(report_input, "overall_risk", "") or ""),
        recommendation=rec,
        confidence=conf,
        decision_id=str(getattr(decision, "decision_id", "") or ""),
        evidence_snapshot_id=str(getattr(decision, "evidence_snapshot_id", "") or ""),
        company_name=str(getattr(report_input, "company_name", "") or ""),
        sector=str(getattr(report_input, "sector", "") or ""),
        unknowns=tuple(getattr(report_input, "unknowns", ()) or ()),
        risks=tuple(getattr(report_input, "risks", ()) or ()),
        catalysts=tuple(getattr(report_input, "catalysts", ()) or ()),
    )


def _bq_num(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def detect_changes(
    previous: Optional[CompanySnapshot],
    current: CompanySnapshot,
    *,
    injected_events: Sequence[dict[str, Any]] | None = None,
) -> List[DetectedChange]:
    """Detect institutional state diffs + optional injected institutional events."""
    changes: list[DetectedChange] = []

    for event in injected_events or ():
        changes.append(
            DetectedChange(
                kind="event",
                key=str(event.get("key") or event.get("type") or "event"),
                detail=str(event.get("detail") or event.get("summary") or "injected event"),
                before=event.get("before"),
                after=event.get("after"),
                category_hint=str(event.get("category") or ""),
                severity_hint=str(event.get("severity") or ""),
                magnitude=float(event.get("magnitude") or 1.0),
            )
        )

    if previous is None:
        if current.evidence_ids:
            changes.append(
                DetectedChange(
                    kind="new_evidence",
                    key="baseline",
                    detail="Initial evidence snapshot established",
                    after=list(current.evidence_ids),
                    category_hint="Evidence",
                    severity_hint="low",
                    magnitude=0.0,
                )
            )
        return changes

    prev_ev: Set[str] = set(previous.evidence_ids)
    cur_ev: Set[str] = set(current.evidence_ids)
    for eid in sorted(cur_ev - prev_ev):
        changes.append(
            DetectedChange(
                kind="new_evidence",
                key=eid,
                detail=f"New evidence: {eid}",
                after=eid,
                category_hint="Evidence",
                severity_hint="medium",
                magnitude=0.5,
            )
        )
    for eid in sorted(prev_ev - cur_ev):
        changes.append(
            DetectedChange(
                kind="removed_evidence",
                key=eid,
                detail=f"Removed evidence: {eid}",
                before=eid,
                category_hint="Evidence",
                severity_hint="medium",
                magnitude=0.4,
            )
        )

    if str(previous.valuation).title() != str(current.valuation).title():
        changes.append(
            DetectedChange(
                kind="valuation",
                key="valuation",
                detail=f"Valuation {previous.valuation} → {current.valuation}",
                before=previous.valuation,
                after=current.valuation,
                category_hint="Valuation",
                severity_hint="high" if current.valuation.title() in {"Expensive", "Cheap"} else "medium",
                magnitude=1.0,
            )
        )

    pbq, cbq = _bq_num(previous.business_quality), _bq_num(current.business_quality)
    if pbq is not None and cbq is not None and abs(cbq - pbq) > 0:
        changes.append(
            DetectedChange(
                kind="factor",
                key="business_quality",
                detail=f"Business quality {pbq} → {cbq}",
                before=pbq,
                after=cbq,
                category_hint="Governance" if abs(cbq - pbq) >= 5 else "Evidence",
                severity_hint="high" if abs(cbq - pbq) >= 5 else "low",
                magnitude=abs(cbq - pbq),
            )
        )

    if str(previous.financial_quality).title() != str(current.financial_quality).title():
        changes.append(
            DetectedChange(
                kind="factor",
                key="financial_quality",
                detail=f"Financial quality {previous.financial_quality} → {current.financial_quality}",
                before=previous.financial_quality,
                after=current.financial_quality,
                category_hint="Quarterly Results",
                severity_hint="high",
                magnitude=1.0,
            )
        )

    if str(previous.overall_risk).title() != str(current.overall_risk).title():
        changes.append(
            DetectedChange(
                kind="factor",
                key="overall_risk",
                detail=f"Risk {previous.overall_risk} → {current.overall_risk}",
                before=previous.overall_risk,
                after=current.overall_risk,
                category_hint="Risk",
                severity_hint="critical" if str(current.overall_risk).title() in {"High", "Severe"} else "high",
                magnitude=1.0,
            )
        )

    if int(previous.confidence) != int(current.confidence):
        changes.append(
            DetectedChange(
                kind="factor",
                key="confidence",
                detail=f"Confidence {previous.confidence} → {current.confidence}",
                before=previous.confidence,
                after=current.confidence,
                category_hint="Decision",
                severity_hint="low",
                magnitude=abs(int(current.confidence) - int(previous.confidence)),
            )
        )

    if previous.recommendation != current.recommendation and current.recommendation:
        changes.append(
            DetectedChange(
                kind="factor",
                key="recommendation",
                detail=f"Recommendation {previous.recommendation} → {current.recommendation}",
                before=previous.recommendation,
                after=current.recommendation,
                category_hint="Decision",
                severity_hint="critical",
                magnitude=1.0,
            )
        )

    # Forecast extras (optional FG-01 / soft)
    prev_fc = (previous.extras or {}).get("forecast_revision")
    cur_fc = (current.extras or {}).get("forecast_revision")
    if cur_fc is not None and prev_fc != cur_fc:
        try:
            mag = abs(float(cur_fc) - float(prev_fc or 0))
        except (TypeError, ValueError):
            mag = 1.0
        changes.append(
            DetectedChange(
                kind="forecast",
                key="forecast_revision",
                detail=f"Forecast revision {prev_fc} → {cur_fc}",
                before=prev_fc,
                after=cur_fc,
                category_hint="Forecast",
                severity_hint="medium",
                magnitude=mag,
            )
        )

    return changes
