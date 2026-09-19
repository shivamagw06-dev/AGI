"""Classifier — type, priority, severity, confidence for detected changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from institutional_observation.detector import DetectedChange
from institutional_observation.schema import OBSERVATION_CATEGORIES


@dataclass(frozen=True)
class ClassifiedChange:
    change: DetectedChange
    category: str
    severity: str
    confidence: float
    priority: int  # 1 highest

    def to_dict(self) -> dict:
        return {
            "change": self.change.to_dict(),
            "category": self.category,
            "severity": self.severity,
            "confidence": self.confidence,
            "priority": self.priority,
        }


_EVENT_MAP = {
    "quarterly_results": ("Quarterly Results", "critical", 0.92, 1),
    "earnings_miss": ("Quarterly Results", "critical", 0.94, 1),
    "earnings_beat": ("Quarterly Results", "high", 0.9, 2),
    "repo_rate": ("Macro", "high", 0.96, 2),
    "rbi_repo_cut": ("Macro", "high", 0.96, 2),
    "rbi_repo_hike": ("Macro", "high", 0.96, 2),
    "ceo_resignation": ("Governance", "critical", 0.95, 1),
    "management_change": ("Governance", "critical", 0.93, 1),
    "share_split": ("Corporate Actions", "low", 0.9, 4),
    "dividend": ("Corporate Actions", "medium", 0.88, 3),
    "corporate_action": ("Corporate Actions", "medium", 0.85, 3),
    "shareholding": ("Shareholding", "medium", 0.84, 3),
    "regulation": ("Regulation", "high", 0.9, 2),
    "forecast_revision": ("Forecast", "medium", 0.82, 3),
    "valuation_update": ("Valuation", "medium", 0.8, 3),
    "sector": ("Sector", "medium", 0.78, 3),
    "news": ("News", "low", 0.7, 5),
}


def _normalize_category(raw: str) -> str:
    text = str(raw or "").strip()
    for cat in OBSERVATION_CATEGORIES:
        if cat.lower() == text.lower():
            return cat
    # title-case fallback from hint
    for cat in OBSERVATION_CATEGORIES:
        if cat.lower() in text.lower():
            return cat
    return text.title() if text else "News"


def classify_change(change: DetectedChange) -> ClassifiedChange:
    key = str(change.key or "").strip().lower()
    detail = str(change.detail or "").lower()

    if change.kind == "event" or key in _EVENT_MAP:
        mapped = _EVENT_MAP.get(key)
        if mapped is None:
            for mk, mv in _EVENT_MAP.items():
                if mk in key or mk in detail:
                    mapped = mv
                    break
        if mapped:
            category, severity, conf, priority = mapped
            if change.severity_hint:
                severity = change.severity_hint.lower()
            if change.category_hint:
                category = _normalize_category(change.category_hint)
            return ClassifiedChange(change, category, severity, conf, priority)

    category = _normalize_category(change.category_hint or change.kind)
    severity = str(change.severity_hint or "medium").lower()
    confidence = 0.8
    priority = 3

    if change.kind == "valuation":
        category, confidence, priority = "Valuation", 0.86, 2
    elif change.kind in {"new_evidence", "removed_evidence", "changed_evidence"}:
        category, confidence, priority = "Evidence", 0.8, 3
        if "QR-" in change.key or "quarterly" in detail:
            category, severity, confidence, priority = "Quarterly Results", "high", 0.9, 2
    elif change.key == "overall_risk":
        category, confidence, priority = "Risk", 0.88, 2
    elif change.key == "financial_quality":
        category, confidence, priority = "Quarterly Results", 0.87, 2
    elif change.key == "recommendation":
        category, severity, confidence, priority = "Decision", "critical", 0.95, 1
    elif change.key == "confidence":
        category, severity, confidence, priority = "Decision", "low", 0.75, 5
    elif change.kind == "forecast":
        category, confidence, priority = "Forecast", 0.82, 3
    elif change.kind == "macro" or "rbi" in key or "repo" in detail:
        category, severity, confidence, priority = "Macro", "high", 0.96, 2

    if change.severity_hint:
        severity = change.severity_hint.lower()

    return ClassifiedChange(change, category, severity, confidence, priority)


def classify_all(changes: List[DetectedChange]) -> List[ClassifiedChange]:
    rows = [classify_change(c) for c in changes]
    rows.sort(key=lambda r: (r.priority, -r.confidence))
    return rows
