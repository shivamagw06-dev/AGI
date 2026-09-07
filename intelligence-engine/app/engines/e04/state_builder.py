"""E04-003 EngineState builder — schema / conf-1.0 / evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e04.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e04.rv_state import E04State


def build_e04_engine_state(
    rv: E04State,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
    confidence_value: float | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E04_P0": True,
        "E04_KALMAN": False,
        "E04_DYNAMIC_HEDGE": False,
        "E04_ETF_BASIS": False,
        "E04_ML": False,
    }
    base = float(
        max(0.0, min(1.0, confidence_value if confidence_value is not None else rv.confidence))
    )
    c_coverage = base
    c_freshness = 1.0 - min(0.5, 0.05 * len(rv.stale_inputs))
    c_stability = 0.75 if rv.cointegrated else 0.45
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_stability) ** (1 / 3))))

    evidence = empty_evidence_pack()
    evidence["positive"].append(
        {
            "id": "e04_pos_pair",
            "claim": f"{rv.pair_id} z={rv.z_score:.2f} label={rv.label}",
        }
    )
    evidence["positive"].append(
        {
            "id": "e04_pos_ols",
            "claim": f"OLS beta={rv.hedge_beta:.4f} R²={rv.r_squared:.3f}",
        }
    )
    if rv.cointegrated:
        evidence["positive"].append(
            {
                "id": "e04_pos_coint",
                "claim": f"Engle-Granger cointegrated (ADF={rv.adf_stat:.3f})",
            }
        )
    else:
        evidence["negative"].append(
            {"id": "e04_neg_coint", "claim": f"Not cointegrated (ADF={rv.adf_stat:.3f})"}
        )
    if rv.half_life is not None:
        evidence["positive"].append(
            {"id": "e04_pos_hl", "claim": f"Half-life {rv.half_life:.2f} days"}
        )
    else:
        evidence["unknowns"].append({"id": "e04_unk_hl", "claim": "Half-life unavailable/unstable"})
    for sid in rv.stale_inputs[:5]:
        evidence["unknowns"].append({"id": f"e04_stale_{sid}", "claim": f"stale/synthetic {sid}"})
    evidence["risks"].append(
        {"id": "e04_risk_scope", "claim": "P0 OLS/EG only — no Kalman/dynamic hedge/ETF basis"}
    )

    input_payload = {
        "pair_id": rv.pair_id,
        "as_of": rv.as_of,
        "hedge_beta": rv.hedge_beta,
        "spread": rv.spread,
        "z_score": rv.z_score,
        "cointegrated": rv.cointegrated,
        "half_life": rv.half_life,
        "composite_score": rv.composite_score,
        "model_version": MODEL_VERSION,
        "formula_id": FORMULA_ID,
        "flags": flag_map,
        "e01_ref": rv.e01_ref,
        "e14_ref": rv.e14_ref,
        "e02_ref": rv.e02_ref,
        "e03_ref": rv.e03_ref,
    }
    input_hash = _sha(input_payload)
    signed = max(-1.0, min(1.0, rv.mean_reversion_signal / 3.0))

    metadata: dict[str, Any] = {
        "e04_state": rv.model_dump(mode="json"),
        "pair_id": rv.pair_id,
        "leg_a": rv.leg_a,
        "leg_b": rv.leg_b,
        "z_score": rv.z_score,
        "cointegrated": rv.cointegrated,
        "half_life": rv.half_life,
        "mispricing_score": rv.mispricing_score,
        "mean_reversion_signal": rv.mean_reversion_signal,
        "side": rv.side,
        "label": rv.label,
        "formula_id": FORMULA_ID,
        "universe_id": rv.universe_id,
        "flags": flag_map,
    }

    body = {
        "engine": "E04",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": rv.as_of,
        "universe_id": rv.universe_id,
        "symbol": rv.pair_id,
        "score": {
            "raw": rv.composite_score,
            "normalized_0_100": rv.composite_score,
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
            "sample_size": float(DEFAULT_LOOKBACK_SAFE),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{rv.pair_id} {rv.label}: z={rv.z_score:.2f}, "
                f"coint={rv.cointegrated}, hl={rv.half_life}, "
                f"composite={rv.composite_score:.1f}."
            ),
            "top_drivers": [
                f"z_score:{rv.z_score:.2f}",
                f"beta:{rv.hedge_beta:.4f}",
                f"half_life:{rv.half_life}",
            ],
            "falsifiers": [
                "cointegration_break",
                "hedge_drift",
                "liquidity_shock",
                "e14_hard_derisk",
            ],
        },
        "warnings": [],
        "stale_inputs": list(rv.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if rv.e14_ref.get("playbook") == "hard_derisk":
        body["warnings"].append("e14_hard_derisk_context")
    if not rv.cointegrated:
        body["warnings"].append("e04_not_cointegrated")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


DEFAULT_LOOKBACK_SAFE = 60


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
