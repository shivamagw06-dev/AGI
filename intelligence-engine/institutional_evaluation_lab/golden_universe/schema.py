"""Golden-universe evaluation constants — IEL company-level runner."""

from __future__ import annotations

from typing import Any

GOLDEN_EVAL_VERSION = "iel-golden-eval-v1.0.0"
RUNNER_VERSION = "1.0.0"
SUITE_ID = "phase1_golden_200"
PROGRAMME = "AGIB_INSTITUTIONAL_EVALUATION_LAB_GOLDEN"

# Institutional constitution tag for reproducible evaluation manifests
CONSTITUTION_VERSION = "v1.4"

# Governance floors (aligned with readiness gate philosophy)
HIGH_CONVICTION_READINESS_FLOOR = 80.0
HIGH_CONVICTION_BANDS = frozenset({"high_conviction_allowed"})
CONSTRUCTIVE_DECISIONS = frozenset(
    {"constructive", "accumulate", "high conviction", "high_conviction", "buy_biased"}
)

DRIFT_CLASSES = (
    "expected_new_evidence",
    "expected_algorithm_improvement",
    "unexpected_possible_regression",
    "no_change",
)

EVIDENCE_BUCKETS = ("Complete", "Partial", "Insufficient")

# Fields compared on deterministic replay (order matters for messaging)
REPLAY_COMPARE_FIELDS = (
    "decision",
    "gate",
    "recommendation_readiness",
    "company_quality",
    "financial_quality",
    "valuation",
    "investment_thesis_status",
    "readiness_band",
)


def collect_version_metadata() -> dict[str, Any]:
    """Assemble reproducible version stamps for manifests / ticker JSON."""
    ide_version = "unknown"
    readiness_version = "unknown"
    golden_set_version = "v1.0"
    golden_set_semver = "v1.0"
    golden_fingerprint = None
    try:
        from decision_engine.schema import IDE_VERSION

        ide_version = IDE_VERSION
    except Exception:
        pass
    try:
        from decision_engine.readiness_gate import evaluate_readiness_gate

        # Probe version from a tiny call is heavy; use known constant if present
        readiness_version = "readiness-gate-v1.0.0"
        _ = evaluate_readiness_gate  # keep import honest
    except Exception:
        readiness_version = "readiness-gate-unknown"
    try:
        from knowledge_factory.phase1_golden_test_set import (
            GOLDEN_UNIVERSE_VERSION,
            PHASE1_VERSION,
            composition_fingerprint,
        )

        golden_set_version = PHASE1_VERSION
        golden_set_semver = GOLDEN_UNIVERSE_VERSION
        golden_fingerprint = composition_fingerprint()
    except Exception:
        pass

    return {
        "constitution_version": CONSTITUTION_VERSION,
        "decision_engine_version": ide_version,
        "readiness_gate_version": readiness_version,
        "golden_set_version": golden_set_version,
        "golden_universe_version": golden_set_semver,
        "golden_composition_sha256": golden_fingerprint,
        "runner_version": RUNNER_VERSION,
        "eval_version": GOLDEN_EVAL_VERSION,
    }
