"""IES schema + Phase 2 exit targets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

IES_VERSION = "institutional-evaluation-suite-v1.0.0"
MODULE_CODE = "IES"
PROGRAMME = "Institutional Evaluation Suite"

SUITES = (
    "valuation",
    "business_quality",
    "accounting",
    "comparison",
    "insufficient",
    "edge_cases",
    "education",
)

# Phase 2 Definition of Done (exit criteria before Phase 3)
PHASE2_TARGETS: dict[str, float] = {
    "overall": 90.0,
    "valuation": 95.0,
    "business_quality": 90.0,
    "accounting": 90.0,
    "comparison": 90.0,
    "insufficient": 100.0,
    "edge_cases": 95.0,
    "education": 98.0,
    "unsupported_conclusions": 0.0,
    "editorial_violations": 0.0,
    "wrong_entity_execution": 0.0,
    "evidence_provenance": 100.0,
    "framework_execution_success": 95.0,
}

VALUATION_METRIC_TARGETS: dict[str, float] = {
    "framework_execution": 95.0,
    "wrong_framework_selection": 2.0,  # max allowed %
    "unsupported_valuation_claims": 0.0,
    "entity_mismatch": 0.0,
}


@dataclass
class GoldExpectation:
    """What correct institutional behaviour looks like for one case."""

    question_type: str | None = None
    question_types: tuple[str, ...] = ()  # accept any of these
    entity_id: str | None = None
    entity_type: str | None = None
    path: str | None = None  # education | research | clarification
    paths: tuple[str, ...] = ()  # accept any of these
    # Framework statuses expected (framework_id -> status or set of allowed)
    framework_status: dict[str, str] = field(default_factory=dict)
    require_executed: tuple[str, ...] = ()
    require_insufficient: tuple[str, ...] = ()
    require_not_applicable: tuple[str, ...] = ()
    narrative_allowed: bool | None = None
    must_report_insufficient: bool = False
    must_list_missing: bool = False
    forbid_guessing: bool = False
    unsupported_claims_forbidden: bool = True
    education_bypass: bool = False
    min_evidence_score: float | None = None
    require_provenance: bool = False
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Case:
    case_id: str
    suite: str
    question: str
    gold: GoldExpectation
    tags: tuple[str, ...] = ()
    packs: dict[str, Any] | None = None
    build_institutional_evidence: bool = True
    ticker_hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "suite": self.suite,
            "question": self.question,
            "gold": self.gold.to_dict(),
            "tags": list(self.tags),
            "build_institutional_evidence": self.build_institutional_evidence,
            "ticker_hint": self.ticker_hint,
        }
