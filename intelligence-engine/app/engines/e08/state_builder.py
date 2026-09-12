"""E08-003 EngineState builder — schema / conf-1.0 / evidence compliant."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.contracts.engine_state import EngineState, empty_evidence_pack
from app.engines.e08.mapping import ENGINE_VERSION, FORMULA_ID, MODEL_VERSION
from app.engines.e08.vol_state import E08State


def build_e08_engine_state(
    vol: E08State,
    *,
    generated_at: datetime | None = None,
    flags: dict[str, bool] | None = None,
    confidence_value: float | None = None,
) -> EngineState:
    ts = generated_at or datetime.now(timezone.utc)
    flag_map = flags or {
        "E08_P0": True,
        "E08_GAMMA": False,
        "E08_DEALER": False,
        "E08_SURFACE": False,
        "E08_ML": False,
    }
    base = float(
        max(0.0, min(1.0, confidence_value if confidence_value is not None else vol.confidence))
    )
    c_coverage = base
    c_freshness = 1.0 - min(0.5, 0.05 * len(vol.stale_inputs))
    c_stability = 0.70
    conf_value = float(max(0.0, min(1.0, (c_coverage * c_freshness * c_stability) ** (1 / 3))))

    evidence = empty_evidence_pack()
    evidence["positive"].append(
        {
            "id": "e08_pos_regime",
            "claim": f"Volatility regime {vol.vol_regime} (composite {vol.composite_score:.1f})",
        }
    )
    evidence["positive"].append(
        {
            "id": "e08_pos_rv",
            "claim": f"Realized vol {vol.realized_vol:.3f} vs hist {vol.historical_vol:.3f}",
        }
    )
    if vol.expansion:
        evidence["risks"].append(
            {"id": "e08_risk_expansion", "claim": "Volatility expansion in progress"}
        )
    if vol.compression:
        evidence["positive"].append(
            {"id": "e08_pos_compression", "claim": "Volatility compression environment"}
        )
    if vol.expected_move is None:
        evidence["missing_data"].append(
            {"id": "e08_miss_em", "claim": "expected move unavailable without IV metadata"}
        )
    for sid in vol.stale_inputs[:5]:
        evidence["unknowns"].append({"id": f"e08_stale_{sid}", "claim": f"stale/derived metric {sid}"})
    evidence["risks"].append(
        {"id": "e08_risk_scope", "claim": "P0 uses realized/hist vol only (no dealer/surface/gamma)"}
    )

    input_payload = {
        "symbol": vol.symbol,
        "as_of": vol.as_of,
        "composite_score": vol.composite_score,
        "vol_regime": vol.vol_regime,
        "realized_vol": vol.realized_vol,
        "historical_vol": vol.historical_vol,
        "metrics": vol.metrics,
        "model_version": MODEL_VERSION,
        "formula_id": FORMULA_ID,
        "flags": flag_map,
        "e01_ref": vol.e01_ref,
        "e14_ref": vol.e14_ref,
    }
    input_hash = _sha(input_payload)
    signed = max(-1.0, min(1.0, (vol.composite_score - 50.0) / 50.0))

    metadata: dict[str, Any] = {
        "e08_state": vol.model_dump(mode="json"),
        "vol_regime": vol.vol_regime,
        "expansion": vol.expansion,
        "compression": vol.compression,
        "realized_vol": vol.realized_vol,
        "historical_vol": vol.historical_vol,
        "expected_move": vol.expected_move,
        "formula_id": FORMULA_ID,
        "universe_id": vol.universe_id,
        "sector_id": vol.sector_id,
        "flags": flag_map,
    }

    body = {
        "engine": "E08",
        "version": ENGINE_VERSION,
        "model_version": MODEL_VERSION,
        "as_of": vol.as_of,
        "universe_id": vol.universe_id,
        "symbol": vol.symbol,
        "score": {
            "raw": vol.composite_score,
            "normalized_0_100": vol.composite_score,
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
            "sample_size": float(len(vol.metrics)),
            "historical_accuracy": None,
            "stability": c_stability,
        },
        "metadata": metadata,
        "evidence": evidence,
        "explanation": {
            "summary": (
                f"{vol.symbol} {vol.label}: RV={vol.realized_vol:.3f}, "
                f"HV={vol.historical_vol:.3f}, composite={vol.composite_score:.1f}."
            ),
            "top_drivers": [
                f"regime:{vol.vol_regime}",
                f"rv:{vol.realized_vol:.3f}",
                f"expansion:{vol.expansion_score:.1f}",
            ],
            "falsifiers": [
                "vol_crash",
                "gap_shock",
                "e14_hard_derisk",
                "iv_disconnect",
            ],
        },
        "warnings": [],
        "stale_inputs": list(vol.stale_inputs),
        "input_hash": input_hash,
        "hash": "sha256:" + ("0" * 64),
        "timestamp_generated": ts.isoformat(),
    }
    if vol.e14_ref.get("playbook") == "hard_derisk":
        body["warnings"].append("e14_hard_derisk_context")
    if vol.vol_regime == "extreme":
        body["warnings"].append("e08_extreme_vol_regime")
    body["hash"] = _sha({k: v for k, v in body.items() if k not in {"hash", "timestamp_generated"}})
    return EngineState.model_validate(body)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
