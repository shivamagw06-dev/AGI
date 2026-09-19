"""Immutable contracts for strategy research and capital governance.

The objects in this module are deliberately provider-neutral. A strategy
definition describes an investment hypothesis; a run manifest proves exactly
which code, data, universe, features, actions and costs evaluated it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "alpha-operating-system-v1.0.0"


class InvestmentStage(str, Enum):
    DEFINED = "DEFINED"
    DATA_VALIDATED = "DATA_VALIDATED"
    RESEARCH_VALIDATED = "RESEARCH_VALIDATED"
    ECONOMICALLY_VALIDATED = "ECONOMICALLY_VALIDATED"
    PAPER_VALIDATED = "PAPER_VALIDATED"
    LIVE_VALIDATED = "LIVE_VALIDATED"
    PRODUCTION = "PRODUCTION"
    SUSPENDED = "SUSPENDED"
    INVALIDATED = "INVALIDATED"


STAGE_GATES: tuple[tuple[InvestmentStage, tuple[str, ...]], ...] = (
    (
        InvestmentStage.DATA_VALIDATED,
        (
            "implementation",
            "data_freshness",
            "data_completeness",
            "point_in_time",
            "universe_integrity",
            "corporate_actions",
        ),
    ),
    (
        InvestmentStage.RESEARCH_VALIDATED,
        (
            "backtest",
            "out_of_sample",
            "regime_robustness",
            "confidence_interval",
        ),
    ),
    (
        InvestmentStage.ECONOMICALLY_VALIDATED,
        (
            "transaction_costs",
            "slippage",
            "liquidity_capacity",
            "risk",
            "parameter_stability",
        ),
    ),
    (InvestmentStage.PAPER_VALIDATED, ("walk_forward_paper",)),
    (
        InvestmentStage.LIVE_VALIDATED,
        ("execution_simulation", "live_attribution", "operational_controls"),
    ),
    (InvestmentStage.PRODUCTION, ("capital_governance",)),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalise(value: Any) -> Any:
    if is_dataclass(value):
        return _normalise(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _normalise(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (set, frozenset)):
        return sorted((_normalise(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non_finite_number")
        return float(f"{value:.15g}")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StrategyDefinition:
    strategy_id: str
    strategy_name: str
    version: int
    owner: str
    description: str
    role: str
    universe_definition: Mapping[str, Any]
    signal_definition: Mapping[str, Any]
    feature_dependencies: tuple[str, ...]
    information_cutoff: str
    signal_timestamp: str
    entry_rule: Mapping[str, Any]
    exit_rule: Mapping[str, Any]
    rebalance_frequency: str
    holding_period: str
    benchmark: str
    risk_constraints: Mapping[str, Any]
    transaction_cost_model: Mapping[str, Any]
    slippage_model: Mapping[str, Any]
    event_policy: Mapping[str, Any] = field(default_factory=dict)
    parameters: Mapping[str, Any] = field(default_factory=dict)
    status: str = InvestmentStage.DEFINED.value
    created_at: str = "2026-08-23T00:00:00Z"
    approved_at: str | None = None

    def __post_init__(self) -> None:
        if not self.strategy_id or not self.strategy_id.endswith(f"_v{self.version}"):
            raise ValueError("strategy_id_must_end_with_version")
        if not self.owner.strip():
            raise ValueError("strategy_owner_required")
        if not self.feature_dependencies:
            raise ValueError("feature_dependencies_required")
        if self.status not in {stage.value for stage in InvestmentStage}:
            raise ValueError("unknown_strategy_status")

    @property
    def definition_hash(self) -> str:
        return content_hash(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = _normalise(asdict(self))
        payload["contract_version"] = CONTRACT_VERSION
        if include_hash:
            payload["definition_hash"] = content_hash(payload)
        return payload


@dataclass(frozen=True)
class RunManifest:
    strategy_id: str
    strategy_version: int
    definition_hash: str
    code_commit: str
    dataset_hash: str
    universe_hash: str
    feature_hash: str
    corporate_action_hash: str
    cost_model_hash: str
    parameters_hash: str
    start_date: str
    end_date: str
    information_cutoff: str
    created_at: str
    parent_run_id: str | None = None
    notes: tuple[str, ...] = ()

    @property
    def run_id(self) -> str:
        return f"run_{content_hash(self.to_dict(include_id=False))[:24]}"

    def to_dict(self, *, include_id: bool = True) -> dict[str, Any]:
        payload = _normalise(asdict(self))
        payload["contract_version"] = CONTRACT_VERSION
        if include_id:
            payload["run_id"] = f"run_{content_hash(payload)[:24]}"
        return payload


def evidence_state(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("state") or value.get("status")
    return str(value or "MISSING").upper()


def stage_assessment(
    evidence: Mapping[str, Any] | None,
    *,
    health: str = "HEALTHY",
    invalidated: bool = False,
) -> dict[str, Any]:
    states = {name: evidence_state(value) for name, value in (evidence or {}).items()}
    if invalidated:
        return {
            "stage": InvestmentStage.INVALIDATED.value,
            "eligible_for_capital": False,
            "passed_gates": sorted(name for name, state in states.items() if state == "PASSED"),
            "missing_gates": [],
            "reason": "strategy_invalidated",
        }
    if str(health).upper() in {"DEGRADED", "STALE", "SUSPENDED", "FAILED"}:
        return {
            "stage": InvestmentStage.SUSPENDED.value,
            "eligible_for_capital": False,
            "passed_gates": sorted(name for name, state in states.items() if state == "PASSED"),
            "missing_gates": [],
            "reason": f"health_{str(health).lower()}",
        }

    stage = InvestmentStage.DEFINED
    missing: list[str] = []
    for candidate, gates in STAGE_GATES:
        failed = [gate for gate in gates if states.get(gate) != "PASSED"]
        if failed:
            missing = failed
            break
        stage = candidate
    return {
        "stage": stage.value,
        "eligible_for_capital": stage == InvestmentStage.PRODUCTION,
        "passed_gates": sorted(name for name, state in states.items() if state == "PASSED"),
        "missing_gates": missing,
        "reason": "all_gates_passed" if stage == InvestmentStage.PRODUCTION else "next_stage_incomplete",
    }


def capital_decision_for(
    definition: StrategyDefinition,
    evidence: Mapping[str, Any] | None,
    *,
    health: str = "HEALTHY",
    invalidated: bool = False,
) -> dict[str, Any]:
    assessment = stage_assessment(evidence, health=health, invalidated=invalidated)
    allowed = bool(assessment["eligible_for_capital"] and definition.status == InvestmentStage.PRODUCTION.value)
    return {
        "strategy_id": definition.strategy_id,
        "definition_hash": definition.definition_hash,
        **assessment,
        "capital_allocation_allowed": allowed,
        "decision": "APPROVED" if allowed else "BLOCKED",
        "blockers": [] if allowed else list(assessment.get("missing_gates") or [assessment["reason"]]),
    }
