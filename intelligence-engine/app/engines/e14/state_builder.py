"""E14State builder — canonical EngineState envelope."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e14.features.builder import RiskFeatureVector
from app.engines.e14.mapping import ENGINE_VERSION, MODEL_VERSION
from app.engines.e14.models.rules import RiskClassification


def build_e14_state(
    fv: RiskFeatureVector,
    classification: RiskClassification,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
) -> EngineState:
    from app.engines.e14.mapping import P0_REQUIRED_FEATURES

    present_req = sum(1 for f in P0_REQUIRED_FEATURES if f in fv.values)
    c_coverage = present_req / len(P0_REQUIRED_FEATURES)
    stale_ratio = len(fv.stale_inputs) / max(1, len(P0_REQUIRED_FEATURES))
    c_freshness = max(0.0, 1.0 - stale_ratio)
    c_model = 0.70 if flags and flags.get("E14_P0", True) else 0.5
    conf_value = (c_coverage * c_freshness * c_model) ** (1 / 3)
    conf_value *= classification.confidence_adjustment
    if classification.degraded:
        conf_value = min(conf_value, 0.70)
    conf_value = float(max(0.0, min(1.0, conf_value)))

    evidence = empty_evidence_pack()
    for fl in classification.risk_flags:
        item = {
            "id": f"e14_{fl['taxonomy_id']}_{fl['severity']}",
            "claim": fl["message"],
        }
        evidence["risks"].append(item)
        if fl["severity"] in {"S3", "S4"}:
            evidence["negative"].append(item)
    for mid in fv.missing:
        evidence["missing_data"].append({"id": f"e14_missing_{mid}", "claim": f"missing feature {mid}"})
    if not fv.e01_present:
        evidence["unknowns"].append({"id": "e14_unk_e01", "claim": "E01State missing — fail-closed prior applied"})

    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {"E14_P0": True, "E14_ML": False, "E14_BAYES": False}
    input_payload = {
        "as_of": fv.as_of,
        "values": {k: fv.values[k] for k in sorted(fv.values)},
        "e01_ref": fv.e01_ref,
        "model_version": MODEL_VERSION,
        "flags": flag_map,
    }
    input_hash = _sha(input_payload)

    risk_score = classification.risk_score
    signed = max(-1.0, min(1.0, (50.0 - risk_score) / 50.0))  # higher risk → negative

    metadata: dict[str, Any] = {
        "risk_score": risk_score,
        "risk_level": classification.risk_level,
        "size_mult": classification.size_multiplier,
        "size_multiplier": classification.size_multiplier,
        "confidence_adjustment": classification.confidence_adjustment,
        "playbook": classification.playbook,
        "gate": classification.gate,
        "block_promotion": classification.gate in {"block_promotion", "research_hedge_only"},
        "crowding_score": classification.crowding_score,
        "liquidity_score": classification.liquidity_score,
        "tail_risk_score": classification.tail_risk_score,
        "taxonomy_scores": classification.taxonomy_scores,
        "risk_flags": classification.risk_flags,
        "engine_weight_adjustments": classification.engine_weight_adjustments,
        "suggested_hedging": classification.suggested_hedging,
        "vol_target_suggested": classification.vol_target_suggested,
        "max_allocation_defaults": {"name": 0.08, "sector": 0.30, "top5": 0.35},
        "portfolio_risk": {
            "portfolio_beta": fv.get("portfolio_beta"),
            "name_hhi": fv.get("name_hhi"),
            "sector_hhi": fv.get("sector_hhi"),
            "gross": fv.get("gross"),
            "net": fv.get("net"),
        },
        "expected_drawdown": {
            "expected_3m_p95": fv.get("expected_dd_3m_p95"),
        },
        "e01_ref": fv.e01_ref,
        "top_risk_drivers": classification.top_risk_drivers,
        "degraded": classification.degraded,
        "flags": flag_map,
        "feature_sources": fv.sources,
    }

    warnings: list[str] = []
    if classification.degraded:
        warnings.append("degraded_inputs")
    if fv.e01_present:
        warnings.append("e01_soft_dependency_ok")
    else:
        warnings.append("e01_missing_fail_closed")

    state_body = {
        "engine": "E14",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": fv.as_of,
        "universe_id": "FIRM",
        "symbol": None,
        "score": {
            "raw": risk_score,
            "normalized_0_100": risk_score,
            "normalized_signed": signed,
            "unit": "score",
        },
        "confidence": {
            "value": conf_value,
            "components": {
                "C_coverage": round(c_coverage, 4),
                "C_freshness": round(c_freshness, 4),
                "C_model": round(c_model, 4),
            },
            "method_version": "conf-1.0",
        },
        "reliability": {
            "sample_size": float(len(fv.values)),
            "historical_accuracy": None,
            "stability": 0.6 if not classification.degraded else 0.4,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"Firm risk prior is {classification.risk_level}; "
                f"playbook={classification.playbook}; gate={classification.gate}; "
                f"size multiplier haircut applied ({classification.size_multiplier})."
            ),
            "top_drivers": classification.top_risk_drivers,
            "falsifiers": [
                "corr_normalization",
                "liquidity_recovery",
                "crowding_mean_reversion",
                "e01_stress_clear",
            ],
        },
        "warnings": warnings,
        "stale_inputs": list(fv.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    state_body["hash"] = _sha(
        {k: v for k, v in state_body.items() if k not in {"hash", "timestamp_generated"}}
    )
    return EngineState.model_validate(state_body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
