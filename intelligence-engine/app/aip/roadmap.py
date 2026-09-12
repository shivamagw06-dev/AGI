"""AIP long-term research roadmap — workstreams AIP-01 … AIP-10."""

from __future__ import annotations

from typing import Any

AIP_VERSION = "aip-research-1.0.0"
ARCHITECTURE_STATUS = "v1.0.1 LOCKED"
PROGRAMME = "Alpha Improvement Programme"

WORKSTREAMS: list[dict[str, Any]] = [
    {
        "id": "AIP-01",
        "name": "Cross-engine calibration",
        "objective": "Align confidence and score scales across engines before L4 fusion.",
        "improves": ["Calibration", "Prediction Accuracy", "Explainability"],
    },
    {
        "id": "AIP-02",
        "name": "Dynamic Weight Registry",
        "objective": "Registry of shadow L4 weight sets with regime/sector variants; never mutates production.",
        "improves": ["Portfolio Construction", "Prediction Accuracy"],
    },
    {
        "id": "AIP-03",
        "name": "Engine contribution analysis",
        "objective": "Measure which engines improve alpha, Sharpe, drawdown, and calibration.",
        "improves": ["Research Quality", "Explainability", "Portfolio Construction"],
    },
    {
        "id": "AIP-04",
        "name": "Regime-specific weighting",
        "objective": "Candidate L4 weights conditioned on E01 regime (shadow experiments only).",
        "improves": ["Risk Management", "Portfolio Construction"],
    },
    {
        "id": "AIP-05",
        "name": "Confidence calibration",
        "objective": "Recalibrate confidence so stated confidence matches hit rate.",
        "improves": ["Calibration", "Prediction Accuracy"],
    },
    {
        "id": "AIP-06",
        "name": "Portfolio attribution",
        "objective": "Attribute paper-portfolio PnL and risk to engine contributions.",
        "improves": ["Portfolio Construction", "Explainability", "Risk Management"],
    },
    {
        "id": "AIP-07",
        "name": "Prediction accuracy",
        "objective": "Track IC, hit rate, and prediction accuracy deltas vs baselines.",
        "improves": ["Prediction Accuracy", "Research Quality"],
    },
    {
        "id": "AIP-08",
        "name": "House View evolution",
        "objective": "Track thesis/label evolution, assumption changes, and prediction outcomes.",
        "improves": ["Research Quality", "Explainability"],
    },
    {
        "id": "AIP-09",
        "name": "Research quality scoring",
        "objective": "Score research packages on evidence, calibration, and continuity.",
        "improves": ["Research Quality", "Explainability"],
    },
    {
        "id": "AIP-10",
        "name": "Client answer quality",
        "objective": "Score client-facing answers on grounding, calibration, and completeness.",
        "improves": ["Research Quality", "Calibration", "Explainability"],
    },
]


def roadmap() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": AIP_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "philosophy": [
            "No new platforms",
            "No duplicate engines",
            "No architectural expansion",
            "L4 remains shadow",
            "Nothing reaches production without evidence",
        ],
        "validation_metrics": [
            "sharpe_delta",
            "sortino_delta",
            "ic_delta",
            "hit_rate_delta",
            "calibration_delta",
            "max_drawdown_delta",
            "turnover_delta",
            "prediction_accuracy_delta",
        ],
        "promotion_gates": [
            "replay_superiority",
            "cre_superiority",
            "statistical_significance",
            "risk_approval",
            "architecture_approval",
        ],
        "baselines": [
            "current_l4",
            "current_e03",
            "historical_replay",
            "golden_dataset",
            "paper_portfolio",
        ],
        "workstreams": list(WORKSTREAMS),
        "production_influence": False,
    }
