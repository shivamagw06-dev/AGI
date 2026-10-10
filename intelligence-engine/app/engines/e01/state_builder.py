"""E01State builder — canonical EngineState envelope (engine_state.schema.json)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e01.features.builder import FeatureVector
from app.engines.e01.mapping import ENGINE_VERSION, MODEL_VERSION
from app.engines.e01.models.fusion import fuse_primary_regime
from app.engines.e01.models.macro_score import compute_macro_score
from app.engines.e01.models.sizing import risk_level, size_and_vol, weight_adjustments
from app.engines.e01.models.thresholds import AxisState, classify_axes


def build_e01_state(
    fv: FeatureVector,
    *,
    prior_cycle: str | None = None,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
) -> EngineState:
    axes = classify_axes(fv, prior_cycle=prior_cycle)
    primary = fuse_primary_regime(axes)
    macro_score = compute_macro_score(fv, axes)
    size_mult, vol_target = size_and_vol(axes)
    rlevel = risk_level(fv.get("stress_index"))
    weights = weight_adjustments(axes, size_mult)

    coverage = 1.0 - (len(fv.missing) / max(1, len(fv.missing) + len(fv.values)))
    # Prefer required-feature coverage
    from app.engines.e01.mapping import P0_REQUIRED_FEATURES

    present_req = sum(1 for f in P0_REQUIRED_FEATURES if f in fv.values)
    c_coverage = present_req / len(P0_REQUIRED_FEATURES)
    stale_ratio = len(fv.stale_inputs) / max(1, len(P0_REQUIRED_FEATURES))
    c_freshness = max(0.0, 1.0 - stale_ratio)
    c_stability = 0.70 if prior_cycle is None or prior_cycle == axes["R_CYCLE"].state else 0.55

    conf_value = (c_coverage * c_freshness * c_stability) ** (1 / 3)
    if stale_ratio > 0.40:
        conf_value *= 0.7
    conf_value = float(max(0.0, min(1.0, conf_value)))

    axis_conf = sum(a.confidence for a in axes.values()) / len(axes)
    conf_value = float(max(0.0, min(1.0, 0.5 * conf_value + 0.5 * axis_conf)))

    evidence = empty_evidence_pack()
    for axis_id, axis in axes.items():
        item = {"id": f"e01_{axis_id}", "claim": f"{axis_id}={axis.state}", "confidence": axis.confidence}
        if axis.state in {"bull", "expansion", "risk_on", "low_vol", "liq_expansion", "disinflationary", "recovery"}:
            evidence["positive"].append(item)
        elif axis.state in {"bear", "recession", "risk_off", "high_vol", "crisis_vol", "crisis", "liq_contraction", "inflationary"}:
            evidence["negative"].append(item)
        if axis_id in ("R_STRESS", "R_VOL") and axis.state in {"crisis", "crisis_vol", "elevated_stress", "high_vol"}:
            evidence["risks"].append(item)
    for mid in fv.missing:
        evidence["missing_data"].append({"id": f"e01_missing_{mid}", "claim": f"missing feature {mid}"})
    for sid in fv.stale_inputs:
        if sid not in fv.missing:
            evidence["unknowns"].append({"id": f"e01_stale_{sid}", "claim": f"stale/partial feature {sid}"})

    top_drivers = _top_drivers(fv, axes)
    falsifiers = [
        "VIX pctile > 0.85",
        "HY OAS z > 1.5",
        "hard_derisk_from_E14",
        "crisis_vol_spike",
    ]

    ts = generated_at or datetime.now(timezone.utc)
    # Deterministic timestamp for hash: use as_of noon UTC if generated_at not fixed by caller tests
    payload_for_input = {
        "as_of": fv.as_of,
        "values": {k: fv.values[k] for k in sorted(fv.values)},
        "model_version": MODEL_VERSION,
        "flags": flags or {"E01_P0": True, "E01_HMM": False, "E01_ML": False},
    }
    input_hash = _sha(payload_for_input)

    metadata: dict[str, Any] = {
        "primary_regime": primary,
        "macro_score": macro_score,
        "axes": {k: {"state": v.state, "confidence": v.confidence} for k, v in axes.items()},
        "risk_level": rlevel,
        "size_multiplier": size_mult,
        "vol_target": vol_target,
        "weight_adjustments": weights,
        "top_features": top_drivers,
        "submodels": {},
        "degraded": stale_ratio > 0.40,
        "flags": flags or {"E01_P0": True, "E01_HMM": False, "E01_ML": False},
        "feature_sources": fv.sources,
    }

    signed = max(-1.0, min(1.0, (macro_score - 50.0) / 50.0))
    warnings: list[str] = []
    if metadata["degraded"]:
        warnings.append("degraded_stale_inputs")
    if flags and not flags.get("E01_P0", True):
        warnings.append("E01_P0_disabled")

    state_body = {
        "engine": "E01",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": fv.as_of,
        "universe_id": "GLOBAL_MACRO",
        "symbol": None,
        "score": {
            "raw": macro_score,
            "normalized_0_100": macro_score,
            "normalized_signed": signed,
            "unit": "score",
        },
        "confidence": {
            "value": conf_value,
            "components": {
                "C_coverage": round(c_coverage, 4),
                "C_freshness": round(c_freshness, 4),
                "C_stability": round(c_stability, 4),
            },
            "method_version": "conf-1.0",
        },
        "reliability": {
            "sample_size": float(len(fv.values)),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"Macro state is {primary} with {rlevel} risk "
                f"and size_multiplier={size_mult}."
            ),
            "top_drivers": top_drivers,
            "falsifiers": falsifiers,
        },
        "warnings": warnings,
        "stale_inputs": list(fv.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),  # placeholder replaced below
        "timestamp_generated": ts.isoformat(),
    }
    # Hash excludes wall-clock timestamp so replays are deterministic
    state_body["hash"] = _sha(
        {k: v for k, v in state_body.items() if k not in {"hash", "timestamp_generated"}}
    )
    return EngineState.model_validate(state_body)


def _top_drivers(fv: FeatureVector, axes: dict[str, AxisState]) -> list[str]:
    ranked = sorted(
        (
            ("growth_impulse", abs(fv.get("growth_impulse", 0.0) or 0.0)),
            ("liquidity_axis", abs(fv.get("liq_trend", 0.0) or 0.0)),
            ("risk_appetite", abs(fv.get("risk_appetite", 0.0) or 0.0)),
            ("stress_index", abs(fv.get("stress_index", 0.0) or 0.0)),
            ("vix_pctile_5y", abs(fv.get("vix_pctile_5y", 0.0) or 0.0)),
            (f"axis:{axes['R_CYCLE'].state}", axes["R_CYCLE"].confidence),
        ),
        key=lambda x: x[1],
        reverse=True,
    )
    return [name for name, _ in ranked[:5]]


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
